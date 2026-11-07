"""Shared internals for the alpaca-paper CLIs.

NOT a CLI on its own: imported by bin/alpaca_*.py.

Auth model (environment-based; no credential files anywhere in this skill):
- The API SECRET is read from the ALPACA_API_SECRET_KEY environment
  variable at call time. It is never read from a file in this skill, and
  it is never logged, printed, or persisted by this code.
- The API KEY ID is a public identifier (like a username: it travels in
  plain text on every request and is visible in the Alpaca dashboard).
  It is read from the ALPACA_KEY_ID environment variable. It is never a
  substitute for the secret.
- Both reads fail closed when the variable is absent.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.parse

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

_secret_cache: str | None = None


class AlpacaError(Exception):
    """Fatal CLI-level error. Carries a message for stderr and an exit code."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


def fail(message: str, exit_code: int = 1) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(exit_code)


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
    """Public API key ID from the ALPACA_KEY_ID environment variable.

    The key ID is a public identifier, not a secret. Fail closed when absent.
    """
    kid = os.environ.get("ALPACA_KEY_ID", "").strip()
    if not kid:
        fail(
            "Missing Alpaca key ID. Set ALPACA_KEY_ID in the environment "
            "(the public key identifier, not the secret)."
        )
    return kid


def secret_key() -> str:
    """API secret from the ALPACA_API_SECRET_KEY environment variable.

    Read once per process and cached in memory only. The value is only
    ever placed in the APCA-API-SECRET-KEY header of requests to
    _ALLOWED_HOSTS. Fail closed when absent.
    """
    global _secret_cache
    if _secret_cache:
        return _secret_cache
    secret = os.environ.get("ALPACA_API_SECRET_KEY", "").strip()
    if not secret:
        fail(
            "Missing Alpaca secret. Set ALPACA_API_SECRET_KEY in the "
            "environment; never store it in a file in this skill."
        )
    _secret_cache = secret
    return secret



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
) -> object:
    """HTTP call with Alpaca auth headers and exponential backoff on 429.

    Prints nothing itself; returns the decoded JSON body. Raises AlpacaError
    on unrecoverable HTTP or network failures.
    """
    ensure_allowed_url(url, _ALLOWED_HOSTS)
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
    for attempt in range(_MAX_RETRIES):
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
                timeout=30,
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
            if method.upper() not in ("GET", "HEAD"):
                err = AlpacaError(
                    f"Request failed ({method.upper()}): request outcome "
                    f"unknown -- verify broker state before retrying ({type(exc).__name__})"
                )
                err.outcome_unknown = True
                raise err
            last_exc = exc
            if attempt + 1 < _MAX_RETRIES:
                time.sleep(delay)
                delay *= 2
            continue
        if resp.status_code == 429:
            saw_429 = True
            retry_after = resp.headers.get("Retry-After", "")
            try:
                parsed_delay = float(retry_after)
                pause = max(delay, parsed_delay) if math.isfinite(parsed_delay) else delay
            except (ValueError, TypeError):
                pause = delay
            if attempt + 1 < _MAX_RETRIES:
                time.sleep(pause)
                delay *= 2
            continue
        if 200 <= resp.status_code < 300:
            if resp.status_code == 204 or not resp.content:
                return {}
            try:
                return resp.json()
            except ValueError:
                err = AlpacaError("Successful HTTP response contained invalid JSON; reconcile the requested operation")
                err.outcome_unknown = method.upper() not in ("GET", "HEAD")
                raise err
        # Non-retryable HTTP error: surface the provider's message, never keys.
        if 300 <= resp.status_code < 400:
            raise AlpacaError("Redirect refused: credentials are never forwarded to redirected URLs")
        body = resp.text[:1000].replace(secret, "[REDACTED]")
        # Twice-daily bugcheck 2026-10-06: carry the HTTP status on the
        # exception so callers can match on it robustly instead of
        # substring-matching the message (e.g. " 404" false-matches 1404).
        err = AlpacaError(f"Alpaca API error {resp.status_code}: {body}")
        err.status_code = resp.status_code
        err.outcome_unknown = resp.status_code >= 500 and method.upper() not in ("GET", "HEAD")
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
    print(json.dumps(obj, separators=(",", ":"), default=str))


def quote_path(segment: str) -> str:
    return urllib.parse.quote(segment, safe="")
