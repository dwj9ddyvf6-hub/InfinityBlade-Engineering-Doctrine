"""Client contracts exercised with synthetic responses only; no network or account.

These tests verify successful routes and ambiguous/malformed boundaries. The
indicator dependency is never fabricated; its pure chart geometry imports
without loading that engine and its absence remains an explicit limitation.
"""
import contextlib
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


http = types.ModuleType("requests")
http.RequestException = type("FixtureTransportError", (Exception,), {})
http.request = Mock(side_effect=AssertionError("Real HTTP is forbidden in this suite"))
with patch.object(sys, "path", list(sys.path)), patch.dict(sys.modules, {"requests": http}):
    lib = load("skills/alpaca-paper/bin/alpaca_lib.py", "deep_alpaca")
    with patch.dict(sys.modules, {"alpaca_lib": lib}):
        modules = {name: load(f"skills/alpaca-paper/bin/alpaca_{name}.py", "deep_" + name)
                   for name in ("option_chain", "option_quotes", "submit_order", "option_order",
                                "option_mleg", "get_order", "get_account", "list_positions",
                                "list_orders", "get_bars_1h", "get_bars_5min", "close_position")}
    chart = load("skills/chart-read/bin/pass_a.py", "deep_chart")
    watch = load("skills/chart-read/bin/watch_trigger.py", "deep_watch")


def response(code, body=None, headers=None, text=None):
    body = {} if body is None else body
    return types.SimpleNamespace(status_code=code, headers=headers or {}, content=b"{}",
                                 text=json.dumps(body) if text is None else text, json=lambda: body)


def contract(symbol="FIXTURE", **overrides):
    return {"symbol": symbol, "expiration_date": "2026-12-18", "strike_price": "100",
            "type": "call", "multiplier": "100", "tradable": True, **overrides}


def bar(timestamp="2026-01-01T00:00:00Z", **overrides):
    return {"t": timestamp, "o": 100, "h": 102, "l": 98, "c": 101, "v": 100, **overrides}


class ClientContractTests(unittest.TestCase):
    def cli(self, name, argv, result):
        module = modules[name]
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", [name, *argv]), patch.object(module, "api_request", return_value=result) as request, \
             patch.dict(os.environ, {"ALPACA_ENV": "paper"}), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                module.main()
                code = 0
            except SystemExit as error:
                code = error.code
        return code, out.getvalue(), err.getvalue(), request

    def test_full_chain_across_many_pages_preserves_contracts_and_input(self):
        request = Mock(side_effect=[{"option_contracts": [contract(f"FIXTURE{i}")],
                                     "next_page_token": f"page{i + 1}" if i < 11 else None} for i in range(12)])
        params = {"underlying_symbols": "FIXTURE", "limit": 1}
        result = modules["option_chain"].fetch_contracts(params, 20, request=request)
        self.assertEqual(len(result["contracts"]), 12)
        self.assertTrue(result["coverage"]["complete"])
        self.assertEqual(result["coverage"]["pages"], 12)
        self.assertEqual(params, {"underlying_symbols": "FIXTURE", "limit": 1})
        self.assertEqual(request.call_args_list[-1].kwargs["params"]["page_token"], "page11")

    def test_chain_partial_has_explicit_recovery_metadata(self):
        page = {"option_contracts": [contract()], "next_page_token": "next"}
        code, out, _, _ = self.cli("option_chain", ["--underlying", "FIXTURE", "--max-pages", "1"], page)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        code, out, _, _ = self.cli("option_chain", ["--underlying", "FIXTURE", "--max-pages", "1", "--with-coverage"], page)
        result = json.loads(out)
        self.assertEqual(code, 0)
        self.assertFalse(result["coverage"]["complete"])
        self.assertEqual(result["coverage"]["next_page_token"], "next")
        self.assertEqual(len(result["contracts"]), 1)

    def test_chain_unknown_tradability_is_retained_without_eligibility_upgrade(self):
        unknown = contract("UNKNOWN")
        unknown.pop("tradable")
        page = {"option_contracts": [contract(), contract("EXCLUDED", tradable=False), unknown]}
        result = modules["option_chain"].fetch_contracts({}, request=Mock(return_value=page))
        self.assertEqual([x["symbol"] for x in result["contracts"]], ["FIXTURE"])
        self.assertEqual([x["symbol"] for x in result["unverified_contracts"]], ["UNKNOWN"])
        self.assertEqual(result["coverage"]["excluded_nontradable"], 1)
        self.assertFalse(result["coverage"]["complete"])

    def test_chain_corruption_token_cycles_and_conflicts_never_look_empty(self):
        for page in ({}, {"option_contracts": None}, {"option_contracts": "bad"},
                     {"option_contracts": [None]}, {"option_contracts": [contract(strike_price="NaN")]},
                     {"option_contracts": [], "next_page_token": 0}):
            with self.subTest(page=page), self.assertRaises(lib.AlpacaError):
                modules["option_chain"].fetch_contracts({}, request=Mock(return_value=page))
        request = Mock(return_value={"option_contracts": [contract()], "next_page_token": "loop"})
        with self.assertRaisesRegex(lib.AlpacaError, "repeated"):
            modules["option_chain"].fetch_contracts({}, request=request)
        self.assertEqual(request.call_count, 2)
        request = Mock(side_effect=[{"option_contracts": [contract()], "next_page_token": "next"},
                                    {"option_contracts": [contract(strike_price="101")]}])
        with self.assertRaisesRegex(lib.AlpacaError, "Conflicting"):
            modules["option_chain"].fetch_contracts({}, request=request)

    def test_legacy_chain_success_remains_a_normalized_array(self):
        code, out, _, _ = self.cli("option_chain", ["--underlying", "FIXTURE"], {"option_contracts": [contract()]})
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), [{"symbol": "FIXTURE", "expiration": "2026-12-18",
                                           "strike": "100", "type": "call", "multiplier": "100"}])

    def test_invalid_order_acknowledgements_retain_generated_intent_for_recovery(self):
        code, out, err, request = self.cli("submit_order", ["--symbol", "FIXTURE", "--side", "buy", "--qty", "1"], {})
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        failure = json.loads(err)
        self.assertTrue(failure["outcome_unknown"])
        self.assertTrue(failure["reconciliation_required"])
        self.assertEqual(failure["client_order_id"], request.call_args.kwargs["payload"]["client_order_id"])

    def test_all_submission_routes_preserve_successful_broker_objects(self):
        success = {"id": "order-1", "status": "accepted", "client_order_id": "intent-1", "filled_qty": "0"}
        fixtures = {
            "submit_order": ["--symbol", "FIXTURE", "--side", "buy", "--qty", "1"],
            "option_order": ["--symbol", "FIXTURE", "--side", "buy", "--qty", "1", "--limit-price", "1", "--position-intent", "buy_to_open"],
            "option_mleg": ["--legs", json.dumps([{"symbol": "FIXTURE1", "side": "buy", "position_intent": "buy_to_open"}, {"symbol": "FIXTURE2", "side": "sell", "position_intent": "sell_to_open"}]), "--qty", "1", "--limit-price", "-0.25"],
        }
        for name, args in fixtures.items():
            with self.subTest(name=name):
                code, out, _, _ = self.cli(name, [*args, "--client-order-id", "intent-1"], success)
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(out), success)
                code, out, err, _ = self.cli(name, [*args, "--client-order-id", "intent-1"], {**success, "client_order_id": "wrong-intent"})
                self.assertEqual(code, 1)
                self.assertTrue(json.loads(err)["outcome_unknown"])

    def test_recovery_lookup_by_client_id_preserves_identity(self):
        success = {"id": "order-1", "status": "accepted", "client_order_id": "intent-1"}
        code, out, _, request = self.cli("get_order", ["--client-order-id", "intent-1"], success)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), success)
        self.assertTrue(request.call_args.args[1].endswith("/v2/orders:by_client_order_id"))
        self.assertEqual(request.call_args.kwargs["params"], {"client_order_id": "intent-1"})

    def test_account_response_requires_real_identity_and_keeps_legacy_fields(self):
        code, out, _, _ = self.cli("get_account", [], {})
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        value = {"id": "account-fixture", "account_number": "fixture-number", "status": "ACTIVE", "equity": "100", "cash": "50", "buying_power": "200"}
        code, out, _, _ = self.cli("get_account", [], value)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["account_number"], value["account_number"])
        self.assertEqual(json.loads(out)["environment"], "paper")

    def test_account_identity_assertions_have_success_and_mismatch_paths(self):
        value = {"id": "account-fixture", "account_number": "fixture-number", "status": "ACTIVE"}
        args = ["--expect-environment", "paper", "--expect-account-id", "account-fixture", "--expect-account-number", "fixture-number"]
        code, out, _, _ = self.cli("get_account", args, value)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["id"], "account-fixture")
        code, out, _, request = self.cli("get_account", ["--expect-environment", "live"], value)
        self.assertNotEqual(code, 0)
        self.assertFalse(request.called)
        code, out, _, _ = self.cli("get_account", ["--expect-account-id", "other-fixture"], value)
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")

    def test_market_and_limit_brackets_and_oco_keep_their_successful_routes(self):
        success = {"id": "order-1", "status": "new", "client_order_id": "intent-1"}
        common = ["--symbol", "FIXTURE", "--qty", "1", "--client-order-id", "intent-1", "--take-profit", "110", "--stop-loss", "90"]
        for extra, order_type in ((["--side", "buy", "--bracket"], "market"),
                                  (["--side", "buy", "--bracket", "--type", "limit", "--limit-price", "100"], "limit"),
                                  (["--side", "sell", "--oco"], "limit")):
            with self.subTest(extra=extra):
                code, _, _, request = self.cli("submit_order", [*common, *extra], success)
                self.assertEqual(code, 0)
                payload = request.call_args.kwargs["payload"]
                self.assertEqual(payload["type"], order_type)
                self.assertEqual(payload["take_profit"]["limit_price"], "110")
        code, _, _, request = self.cli("submit_order", [*common, "--side", "sell", "--bracket"], success)
        self.assertNotEqual(code, 0)
        request.assert_not_called()

    def test_quantities_prices_and_spread_ratios_are_exact_on_outbound_requests(self):
        success = {"id": "order-1", "status": "new", "client_order_id": "intent-1"}
        code, _, _, request = self.cli("submit_order", ["--symbol", "FIXTURE", "--side", "buy", "--qty", "9007199254740993", "--type", "limit", "--limit-price", "0.123456789012345678", "--client-order-id", "intent-1"], success)
        self.assertEqual(code, 0)
        self.assertEqual(request.call_args.kwargs["payload"]["qty"], "9007199254740993")
        self.assertEqual(request.call_args.kwargs["payload"]["limit_price"], "0.123456789012345678")
        code, _, _, request = self.cli("close_position", ["--symbol", "FIXTURE", "--qty", "0.99999999999999999"], success)
        self.assertEqual(code, 0)
        self.assertEqual(request.call_args.kwargs["params"]["qty"], "0.99999999999999999")
        legs = [{"symbol": "FIXTURE1", "side": "buy", "position_intent": "buy_to_open", "ratio_qty": "9007199254740993"}, {"symbol": "FIXTURE2", "side": "sell", "position_intent": "sell_to_open"}]
        code, _, _, request = self.cli("option_mleg", ["--legs", json.dumps(legs), "--qty", "1", "--limit-price", "-0.25", "--client-order-id", "intent-1"], success)
        self.assertEqual(code, 0)
        self.assertEqual(request.call_args.kwargs["payload"]["legs"][0]["ratio_qty"], "9007199254740993")

    def test_invalid_numbers_and_malformed_legs_fail_before_request(self):
        for number in ("NaN", "Infinity", "not-a-number", "-1"):
            with self.subTest(number=number):
                code, _, _, request = self.cli("submit_order", ["--symbol", "FIXTURE", "--side", "buy", "--qty", number], {})
                self.assertNotEqual(code, 0)
                request.assert_not_called()
        for invalid in (True, "NaN", "1.5"):
            legs = [{"symbol": "FIXTURE1", "side": "buy", "position_intent": "buy_to_open", "ratio_qty": invalid}, {"symbol": "FIXTURE2", "side": "sell", "position_intent": "sell_to_open"}]
            code, _, _, request = self.cli("option_mleg", ["--legs", json.dumps(legs), "--qty", "1", "--limit-price", "-0.25"], {})
            self.assertNotEqual(code, 0)
            request.assert_not_called()

    def test_decimal_quantity_never_rounds_or_changes_original(self):
        rows = [{"qty": "9007199254740993", "symbol": "FIXTURE"}, {"qty": "0.99999999999999999"}, {"qty": "-70.0"}]
        result = modules["list_positions"]._normalize_qty(rows)
        self.assertEqual([x["qty"] for x in result], ["9007199254740993", "0.99999999999999999", "-70"])
        self.assertEqual(rows[-1]["qty"], "-70.0")
        for value in ("NaN", "Infinity", None, True):
            with self.subTest(value=value), self.assertRaises(lib.AlpacaError):
                modules["list_positions"]._normalize_qty([{"qty": value}])

    def test_quote_states_preserve_valid_prices_and_missing_symbols(self):
        raw = {"quotes": {"GOOD": {"bp": 1, "ap": 3, "t": "2026-11-01T20:00:00Z"},
                           "CROSS": {"bp": 4, "ap": 2}, "BAD": {"bp": "NaN", "ap": 2},
                           "ONE": {"bp": 0, "ap": 2}}}
        result = modules["option_quotes"].normalize_quotes(raw, ["GOOD", "CROSS", "BAD", "ONE", "MISSING"], "indicative")
        self.assertEqual(result["GOOD"]["mid"], 2)
        self.assertEqual(result["GOOD"]["spread_frac"], 1)
        self.assertEqual([result[k]["quote_status"] for k in ("CROSS", "BAD", "ONE", "MISSING")], ["crossed", "invalid", "one_sided", "missing"])
        self.assertTrue(all(result[k]["mid"] is None for k in ("CROSS", "BAD", "ONE", "MISSING")))
        json.dumps(result, allow_nan=False)

    def test_order_list_reports_coverage_without_changing_array_default(self):
        order = {"id": "order-1", "status": "new"}
        code, out, _, _ = self.cli("list_orders", ["--limit", "1", "--with-coverage"], [order])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["coverage"]["possibly_truncated"])
        code, out, _, _ = self.cli("list_orders", [], [order])
        self.assertEqual(json.loads(out), [order])


class TransportAndBarTests(unittest.TestCase):
    @contextlib.contextmanager
    def transport(self, request):
        with patch.object(lib, "key_id", return_value="fixture-account-id"), patch.object(lib, "secret_key", return_value="fixture-secret"), \
             patch.object(http, "request", request), patch.dict(os.environ, {"ALPACA_TELEMETRY_PATH": "", "ALPACA_ENV": "paper"}):
            yield

    def test_environment_host_mismatch_is_rejected_before_credentials(self):
        with patch.dict(os.environ, {"ALPACA_ENV": "paper"}), patch.object(lib, "key_id") as key, self.assertRaisesRegex(lib.AlpacaError, "ALPACA_ENV"):
            lib.api_request("GET", "https://api.alpaca.markets/v2/account")
        key.assert_not_called()
        with self.transport(Mock(return_value=response(200, {"fixture": True}))), patch.dict(os.environ, {"ALPACA_ENV": "live"}):
            self.assertEqual(lib.api_request("GET", "https://api.alpaca.markets/v2/account"), {"fixture": True})

    def test_secret_rotation_is_observed_at_next_call(self):
        with patch.dict(os.environ, {"ALPACA_API_SECRET_KEY": "fixture-first"}):
            self.assertEqual(lib.secret_key(), "fixture-first")
        with patch.dict(os.environ, {"ALPACA_API_SECRET_KEY": "fixture-second"}):
            self.assertEqual(lib.secret_key(), "fixture-second")

    def test_provider_backoff_defers_instead_of_sleeping_beyond_budget(self):
        request = Mock(return_value=response(429, headers={"retry-after": "999999999"}))
        with self.transport(request), patch.object(lib.time, "sleep") as sleep, self.assertRaisesRegex(lib.AlpacaError, "budget") as raised:
            lib.api_request("GET", "https://data.alpaca.markets/v2/stocks/FIXTURE/bars", budget_seconds=60)
        self.assertEqual(request.call_count, 1)
        sleep.assert_not_called()
        self.assertEqual(raised.exception.retry_after_seconds, 999999999)

    def test_http_date_retry_after_and_successful_retry(self):
        now = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
        self.assertEqual(lib.retry_after_seconds("Sat, 07 Nov 2026 12:00:30 GMT", now), 30)
        self.assertIsNone(lib.retry_after_seconds("not-a-date", now))
        request = Mock(side_effect=[response(429, headers={"Retry-After": "2"}), response(200, {"ok": True})])
        with self.transport(request), patch.object(lib.time, "sleep") as sleep:
            self.assertEqual(lib.api_request("GET", "https://data.alpaca.markets/v2/stocks/FIXTURE/bars"), {"ok": True})
        sleep.assert_called_once_with(2)
        self.assertEqual(request.call_count, 2)

    def test_all_credential_occurrences_are_redacted_before_truncation(self):
        body = "fixture-account-id " + "x" * 970 + "fixture-secret " + "fixture-account-id"
        with self.transport(Mock(return_value=response(403, text=body))), self.assertRaises(lib.AlpacaError) as raised:
            lib.api_request("GET", "https://paper-api.alpaca.markets/v2/account")
        self.assertNotIn("fixture-secret", str(raised.exception))
        self.assertNotIn("fixture-account-id", str(raised.exception))
        self.assertNotIn("fixture-se", str(raised.exception))

    def test_timeout_and_redirect_after_mutation_are_unknown_without_replay(self):
        for code in (408, 302, 503):
            request = Mock(return_value=response(code))
            with self.subTest(code=code), self.transport(request), self.assertRaises(lib.AlpacaError) as raised:
                lib.api_request("POST", "https://paper-api.alpaca.markets/v2/orders")
            self.assertTrue(raised.exception.outcome_unknown)
            self.assertEqual(request.call_count, 1)

    def fetch(self, module, params=None, pages=2, windows=2):
        if module is modules["get_bars_1h"]:
            return module.fetch_bars("FIXTURE", "1H", params or {}, pages, windows)
        return module.fetch_bars("FIXTURE", params or {}, pages, windows)

    def test_bar_order_uses_instants_and_preserves_valid_duplicate_boundary(self):
        early, later = bar("2026-01-01T10:00:00+02:00"), bar("2026-01-01T09:00:00Z")
        for module in (modules["get_bars_1h"], modules["get_bars_5min"]):
            request = Mock(side_effect=[{"bars": [later, early], "next_page_token": "next"}, {"bars": [later]}])
            with patch.object(module, "api_request", request):
                result = self.fetch(module)
            self.assertEqual(result, [early, later])

    def test_corrupt_bars_conflicting_duplicates_and_cycle_fail_explicitly(self):
        for module in (modules["get_bars_1h"], modules["get_bars_5min"]):
            for rows in ([None, bar()], [bar(h=99)], [bar(v=float("nan"))], [bar(), bar(c=100)]):
                with self.subTest(module=module.__name__, rows=rows), patch.object(module, "api_request", return_value={"bars": rows}), self.assertRaises(lib.AlpacaError):
                    self.fetch(module)
            with patch.object(module, "api_request", return_value={"bars": [bar()], "next_page_token": "loop"}), self.assertRaisesRegex(lib.AlpacaError, "repeated"):
                self.fetch(module, pages=3)

    def test_complete_bar_window_survives_window_slide_and_preserves_params(self):
        first, last = bar(), bar("2026-01-02T00:00:00Z")
        params = {"start": "2025-12-31T00:00:00Z", "end": "2026-01-03T00:00:00Z"}
        for module in (modules["get_bars_1h"], modules["get_bars_5min"]):
            request = Mock(side_effect=[{"bars": [first], "next_page_token": "next"}, {"bars": [first, last]}])
            with patch.object(module, "api_request", request):
                self.assertEqual(self.fetch(module, params, pages=1), [first, last])
            self.assertEqual(params["start"], "2025-12-31T00:00:00Z")


class ChartTemporalTests(unittest.TestCase):
    def test_geometry_payload_rejects_corruption_and_orders_actual_instants(self):
        earlier, later = bar("2026-01-02T00:00:00+02:00"), bar("2026-01-01T23:00:00Z")
        self.assertEqual(chart._as_bar_list([later, earlier]), [earlier, later])
        self.assertEqual(chart._as_bar_list({"bars": None}), [])
        for payload in ("broken", {}, [None], [bar(c=float("nan"))], [bar(h=99)], [earlier, {**earlier, "c": 100}]):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                chart._as_bar_list(payload)

    def test_historical_gap_uses_each_previous_atr_and_is_prefix_stable(self):
        rows = [bar("2026-01-01", c=100), bar("2026-01-02", o=102), bar("2026-01-03", o=101)]
        expected = [{"t": "2026-01-02", "gap_atr": 2}]
        self.assertEqual(chart.gap_events(rows, [1, 100, 100]), expected)
        self.assertEqual(chart.gap_events(rows[:2], [1, 100]), expected)

    def test_failed_breakout_availability_compares_instants_not_text(self):
        rows = [bar("2026-01-01T00:00:00Z", h=100, c=99), bar("2026-01-02T00:00:00+02:00", h=100.4, c=99), bar("2026-01-02T00:00:00Z", h=100.4, c=99)]
        pivot = {"i": 0, "t": rows[0]["t"], "avail_t": "2026-01-01T23:00:00Z", "kind": "H", "px": 100}
        result = chart.failed_breakouts(rows, [pivot], 1, atr_series=[1, 1, 1])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["t"], "2026-01-02")
        self.assertEqual(chart.failed_breakouts(rows[:2], [pivot], 1, atr_series=[1, 1]), [])
    def test_geometry_import_does_not_substitute_or_require_indicator_engine(self):
        self.assertTrue(callable(chart.failed_breakouts))
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, "Indicator engine unavailable"):
            chart._load_battery()

    def test_failed_breakout_waits_for_available_pivot_and_uses_previous_scale(self):
        bars = [bar(f"2026-01-0{i+1}T00:00:00Z", o=99, h=100, l=98, c=99) for i in range(7)]
        bars[2]["h"] = 100.4
        bars[5]["h"] = 100.4
        pivot = {"i": 1, "t": bars[1]["t"], "avail_t": bars[4]["t"], "kind": "H", "px": 100}
        result = chart.failed_breakouts(bars, [pivot], 0.1, atr_series=[1] * 7)
        self.assertEqual([x["t"] for x in result], ["2026-01-06"])
        self.assertTrue(result[0]["causal_inputs"])
        self.assertEqual(result[0]["poke_atr"], 0.4)

    def test_trigger_uses_complete_subsequent_sessions_and_excludes_open_bar(self):
        now = datetime(2026, 11, 6, 18, tzinfo=timezone.utc)  #13:00ET
        rows = [bar("2026-11-05T05:00:00Z", c=101), bar("2026-11-06T05:00:00Z", c=102)]
        result = watch.evaluate_triggers(rows, "2026-11-04", bullish_above=100, now=now)
        self.assertEqual([x["session"] for x in result["events"]], ["2026-11-05"])
        self.assertEqual(result["provisional_bars_excluded"], 1)
        after_close = watch.evaluate_triggers(rows, "2026-11-04", bullish_above=100, now=now + timedelta(hours=4))
        self.assertEqual(len(after_close["events"]), 2)

    def test_watch_requests_original_read_window_and_is_quiet_without_event(self):
        out = io.StringIO()
        with patch.object(sys, "argv", ["watch", "--symbol", "FIXTURE", "--read-date", "2020-01-01", "--bullish-above", "200"]), \
             patch.object(watch, "fetch", return_value=[bar("2020-01-02T05:00:00Z")]) as fetch, contextlib.redirect_stdout(out):
            watch.main()
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(fetch.call_args.kwargs["start"], "2020-01-01T00:00:00Z")
        self.assertEqual(fetch.call_args.args[2], 10000)

    def test_watch_rejects_nonfinite_threshold_and_future_or_conflicting_daily_data(self):
        now = datetime(2026, 11, 6, 22, tzinfo=timezone.utc)
        for threshold in (float("nan"), -1, True):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                watch.evaluate_triggers([], "2026-11-04", threshold, now=now)
        with self.assertRaisesRegex(ValueError, "future"):
            watch.evaluate_triggers([bar("2026-11-07T05:00:00Z")], "2026-11-04", 100, now=now)
        with self.assertRaisesRegex(ValueError, "conflicting"):
            watch.evaluate_triggers([bar("2026-11-05T05:00:00Z"), bar("2026-11-05T05:00:00Z", c=100)], "2026-11-04", 100, now=now)


if __name__ == "__main__":
    unittest.main(verbosity=2)
