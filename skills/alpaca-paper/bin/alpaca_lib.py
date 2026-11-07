"""Shared internals for the alpaca-paper CLIs.

NOT a CLI on its own: imported by bin/alpaca_*.py.

Auth model (environment-based; no credential files anywhere in this skill):
- The API SECRET is read from the ALPACA_API_SECRET_KEY environment
  variable at call time. It is never read from a file in this skill, and
  it is never logged, printed, or persisted by this code.
- The API KEY ID is an account credential identifier. It travels in an
  authenticated HTTPS header and must not be published in diagnostics.
  It is read from the ALPACA_KEY_ID environment variable. It is never a
  substitute for the secret.
- Both reads fail closed when the variable is absent.
"""

from __future__ import annotations

import json
import argparse
import math
import os
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from decimal import Decimal, InvalidOperation

import requests

def ensure_allowed_url(url, allowed_hosts):
    """Refuse to send credentials to any host outside the allowlist."""
    try:
        parsed = urllib.parse.urlparse(url)
        valid = (parsed.scheme == "https" and parsed.hostname in allowed_hosts
                 and parsed.port in (None, 443) and parsed.username is None
                 and parsed.password is None and not parsed.fragment)
    except ValueError:
        valid = False
    if not valid:
        fail("Refusing credential-bearing request: HTTPS, default TLS port, and an allowlisted host are required")

_SECRET_HEADER = "APCA-API-SECRET-KEY"
_KEY_ID_HEADER = "APCA-API-KEY-ID"

# Paper is the only default. The live base below is resolved ONLY when
# ALPACA_ENV=live is explicitly set; there is no other way to reach it.
_ALLOWED_HOSTS = (
    "paper-api.alpaca.markets",
    "data.alpaca.markets",
    "api.alpaca.markets",
)

_MAX_RETRIES = 4  # total attempts on 429 (initial + 3 backoffs)

# Kept as a compatibility name for old importing test fixtures. Credentials
# are read together at request time; rotation must never mix old/new pairs.
_secret_cache: str | None = None


class AlpacaError(Exception):
    """Fatal CLI-level error. Carries a message for stderr and an exit code."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


def fail(message: str, exit_code: int = 1) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(exit_code)


def decimal_argument(value):
    """Parse CLI money/quantity without binary-float rounding."""
    try:
        number = Decimal(value)
        if not number.is_finite():
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        raise argparse.ArgumentTypeError("must be a finite decimal number") from None
    return number


def decimal_text(value):
    """Exact ordinary decimal representation; whole quantities have no .0."""
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("must be a finite decimal number")
    return str(int(number)) if number == number.to_integral_value() else format(number, "f")


# Documented bases (references/api_details.md). Live is selectable only via
# ALPACA_ENV=live; paper is the default. No keys here.
_BASES = {
    "paper": "https://paper-api.alpaca.markets",
    "live": "https://api.alpaca.markets",
}
_DATA_BASE = "https://data.alpaca.markets"


def env_mode() -> str:
    """Resolve paper|live from ALPACA_ENV (default: paper)."""
    mode = os.environ.get("ALPACA_ENV", "paper").strip().lower()
    if mode not in _BASES:
        fail(
            f"ALPACA_ENV must be 'paper' or 'live', got {mode!r}. "
            "Unset it or export ALPACA_ENV=paper."
        )
    return mode


def key_id() -> str:
    """Account credential identifier; fail closed when absent."""
    kid = os.environ.get("ALPACA_KEY_ID", "").strip()
    if not kid:
        fail(
            "Missing Alpaca key ID. Set ALPACA_KEY_ID in the environment "
            "(the account key identifier, not the secret)."
        )
    return kid


def secret_key() -> str:
    """API secret from the ALPACA_API_SECRET_KEY environment variable.

    Read at request time so in-process rotation cannot retain an old secret.
    The value is only
    ever placed in the APCA-API-SECRET-KEY header of requests to
    _ALLOWED_HOSTS. Fail closed when absent.
    """
    secret = os.environ.get("ALPACA_API_SECRET_KEY", "").strip()
    if not secret:
        fail(
            "Missing Alpaca secret. Set ALPACA_API_SECRET_KEY in the "
            "environment; never store it in a file in this skill."
        )
    return secret


def retry_after_seconds(value, now=None):
    """RFC 9110 delay-seconds or HTTP-date; invalid values give no override."""
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            stamp = parsedate_to_datetime(value)
            if stamp.tzinfo is None:
                return None
            seconds = (stamp - (now or datetime.now(timezone.utc))).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return None
    return max(0.0, seconds) if math.isfinite(seconds) else None



def trading_base() -> str:
    """Trading API base URL selected by ALPACA_ENV. Never hardcoded live."""
    return _BASES[env_mode()]


def data_base() -> str:
    return _DATA_BASE


def require_live_confirmation(args) -> None:
    """Refuse any order path unless live mode is explicit AND confirmed."""
    if env_mode() != "live":
        return
    if getattr(args, "i_understand_this_is_live", False):
        return
    fail(
        "Refusing: ALPACA_ENV=live is set but you did not pass "
        "--i-understand-this-is-live. Orders against the live base require "
        "BOTH ALPACA_ENV=live AND --i-understand-this-is-live.",
        exit_code=3,
    )


def api_request(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    payload: dict | None = None,
    budget_seconds: float = 120.0,
) -> object:
    """HTTP call with Alpaca auth headers and exponential backoff on 429.

    The monotonic budget bounds retries and backoff, with each HTTP timeout
    clipped to remaining budget. requests' socket timeout is not a strict
    wall-clock deadline for a peer that continuously trickles bytes.
    Returns decoded JSON; raises AlpacaError on incomplete/invalid transport.
    """
    ensure_allowed_url(url, _ALLOWED_HOSTS)
    host = urllib.parse.urlparse(url).hostname
    if host in {urllib.parse.urlparse(base).hostname for base in _BASES.values()}:
        if host != urllib.parse.urlparse(trading_base()).hostname:
            raise AlpacaError("Trading host does not match the configured ALPACA_ENV")
    if isinstance(budget_seconds, bool) or not isinstance(budget_seconds, (int, float)) or not math.isfinite(budget_seconds) or budget_seconds <= 0:
        raise ValueError("budget_seconds must be positive and finite")
    method = method.upper()
    mutation = method not in ("GET", "HEAD")
    deadline = time.monotonic() + budget_seconds
    kid = key_id()
    secret = secret_key()
    headers = {
        _KEY_ID_HEADER: kid,
        _SECRET_HEADER: secret,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    delay = 1.0
    last_exc: Exception | None = None
    saw_429 = False
    def pause_before_retry(seconds):
        remaining = deadline - time.monotonic()
        if seconds >= remaining:
            error = AlpacaError("Retry deferred: provider backoff exceeds the remaining request budget")
            error.retry_after_seconds = seconds
            error.outcome_unknown = False  # Only called after read failure or explicit429.
            raise error
        time.sleep(seconds)
    for attempt in range(_MAX_RETRIES):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AlpacaError("Request retry budget exhausted before the next attempt")
        # Step-0 telemetry (T11, 2026-10-13): count every physical request
        # per endpoint class; fail-silent -- telemetry never breaks a call.
        try:
            import json as _tj, os as _to
            from datetime import datetime as _tdt, timezone as _ttz
            _tp = os.environ.get("ALPACA_TELEMETRY_PATH", "")
            if not _tp:
                raise RuntimeError("telemetry disabled")
            os.makedirs(os.path.dirname(_tp), exist_ok=True)
            with open(_tp, "a") as _tf:
                _tf.write(json.dumps({
                    "ts": _tdt.now(_ttz.utc).isoformat(),
                    "consumer": "alpaca_lib", "endpoint": url.split("/v")[0][-30:] + "/v" + url.split("/v", 1)[1].split("/")[0] if "/v" in url else url[:60],
                    "timeframe": (params or {}).get("timeframe", ""),
                    "count": 1}) + "\n")
        except Exception:
            pass
        try:
            resp = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=min(30.0, remaining),
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            # Row43-A3 (2026-10-13): a network exception after the request
            # may have reached the broker is only safe to retry for
            # idempotent reads. Non-idempotent methods (DELETE, POST, ...)
            # carry no broker idempotency key here, so re-issuing could
            # double-apply the operation (e.g. a second position close).
            # Fail immediately, marked outcome-unknown, so the caller can
            # reconcile against broker state instead of blindly retrying.
            # The 429 branch below is unchanged for all methods: a 429 is
            # a pre-processing rejection, safe to retry.
            if mutation:
                err = AlpacaError(
                    f"Request failed ({method.upper()}): request outcome "
                    f"unknown -- verify broker state before retrying ({type(exc).__name__})"
                )
                err.outcome_unknown = True
                raise err
            last_exc = exc
            if attempt + 1 < _MAX_RETRIES:
                pause_before_retry(delay)
                delay *= 2
            continue
        if resp.status_code == 429:
            saw_429 = True
            retry_after = next((v for k, v in resp.headers.items() if k.lower() == "retry-after"), None)
            parsed_delay = retry_after_seconds(retry_after)
            pause = max(delay, parsed_delay) if parsed_delay is not None else delay
            if attempt + 1 < _MAX_RETRIES:
                pause_before_retry(pause)
                delay *= 2
            continue
        if 200 <= resp.status_code < 300:
            if resp.status_code == 204 or not resp.content:
                return {}
            try:
                return resp.json()
            except ValueError:
                err = AlpacaError("Successful HTTP response contained invalid JSON; reconcile the requested operation")
                err.outcome_unknown = mutation
                raise err
        # Non-retryable HTTP error: surface the provider's message, never keys.
        if 300 <= resp.status_code < 400:
            err = AlpacaError("Redirect refused: credentials are never forwarded to redirected URLs")
            err.outcome_unknown = mutation
            raise err
        # Redact before truncation: a credential crossing the truncation
        # boundary must not leak its prefix. Both account key and secret count.
        body = resp.text.replace(secret, "[REDACTED]").replace(kid, "[REDACTED]")[:1000]
        # Twice-daily bugcheck 2026-10-06: carry the HTTP status on the
        # exception so callers can match on it robustly instead of
        # substring-matching the message (e.g. " 404" false-matches 1404).
        err = AlpacaError(f"Alpaca API error {resp.status_code}: {body}")
        err.status_code = resp.status_code
        err.outcome_unknown = mutation and (resp.status_code >= 500 or resp.status_code == 408)
        if err.outcome_unknown:
            err.args = (str(err) + "; outcome unknown: reconcile broker state before retrying",)
        raise err
    # 3x-daily bugcheck 2026-10-07: when every attempt was a 429 (no
    # network exception ever occurred), last_exc is None and the old
    # message ended with a literal "None". Report the 429s instead.
    if saw_429 and last_exc is None:
        detail = "HTTP 429 on every attempt"
    else:
        detail = type(last_exc).__name__ if last_exc is not None else "unreachable"
    raise AlpacaError(
        f"Request failed after {_MAX_RETRIES} attempts "
        f"(rate-limited or unreachable): {detail}"
    )


def missing_order(order_id):
    """Absence from one account endpoint is not a terminal-order proof."""
    return {"status": "not_found", "id": order_id, "terminal_state_verified": False,
            "reconciliation_required": True,
            "note": "No record at the queried endpoint; verify account, environment and order identity before resolving local state."}


def require_order_response(result, *, mutation=False, client_order_id=None):
    """Validate an acknowledgement's identity without inventing fill truth."""
    valid = (isinstance(result, dict) and all(isinstance(result.get(k), str) and result[k].strip()
             for k in ("id", "status")))
    if client_order_id is not None:
        valid = valid and result.get("client_order_id") == client_order_id
    if not valid:
        error = AlpacaError("Invalid order acknowledgement: missing or mismatched order identity/status; reconcile by the original client order ID")
        error.outcome_unknown = mutation
        error.client_order_id = client_order_id
        raise error
    return result


def operation_acknowledgement(operation, target, response=None):
    """Distinguish a mutation's HTTP acknowledgement from its final outcome."""
    receipt = dict(response or {})
    receipt.update(request_accepted=True, operation=operation, target=target,
                   final_state_verified=False, reconciliation_required=True)
    if operation == "cancel_order":
        receipt.update(cancel_requested=True, cancelled=None, order_id=target)
    elif operation == "close_position":
        receipt.update(close_requested=True, closed=None, symbol=target)
    else:
        raise ValueError("unknown acknowledgement operation")
    return receipt


def emit(obj: object) -> None:
    """Write JSON to stdout (compact for bars, readable for objects)."""
    print(json.dumps(obj, separators=(",", ":"), default=str, allow_nan=False))


def quote_path(segment: str) -> str:
    return urllib.parse.quote(segment, safe="")


def timestamp_instant(value):
    """Parse an offset-aware provider timestamp; compare instants, not strings."""
    if not isinstance(value, str) or not value:
        raise AlpacaError("Bar coverage incomplete: missing timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("offset missing")
    except (ValueError, TypeError) as error:
        raise AlpacaError("Bar coverage incomplete: invalid timestamp") from error
    return stamp.astimezone(timezone.utc)


def validate_bar(bar):
    """Validate rather than silently omit malformed observations."""
    if not isinstance(bar, dict):
        raise AlpacaError("Bar coverage incomplete: non-object observation")
    stamp = timestamp_instant(bar.get("t"))
    for field in ("o", "h", "l", "c", "v"):
        value = bar.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise AlpacaError("Bar coverage incomplete: invalid OHLCV value")
        if value < 0 or (field != "v" and value == 0):
            raise AlpacaError("Bar coverage incomplete: nonpositive price or negative volume")
    if not bar["l"] <= min(bar["o"], bar["c"]) <= max(bar["o"], bar["c"]) <= bar["h"]:
        raise AlpacaError("Bar coverage incomplete: inconsistent OHLC geometry")
    return stamp
