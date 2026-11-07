#!/usr/bin/env python3
"""Check declared local outcomes and compare paired trials from their artifacts.

No commands, imports from artifacts, model calls, network requests or installed
host changes. A case is an explicit oracle supplied by its author, not a truth
engine. Reports bind observations to bytes; they do not authenticate who made
those bytes or prove a live system's behavior.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from statistics import mean
import sys

MAX_BYTES = 16 * 1024 * 1024
MAX_FILES = 10000
CHECK_KINDS = {"file_sha256", "json_equals", "text_contains", "path_absent", "inventory_equals"}
METRICS = {"elapsed_seconds", "input_tokens", "output_tokens", "tool_calls", "cost_usd"}
CONFIG_KEYS = {"model", "host", "tools_sha256", "system_sha256", "budget", "seed"}
LIMITS = [
    "Only the declared local conditions are checked; an oracle may be incomplete or wrong.",
    "Hashes bind observed bytes, not authorship, authorization, execution history or live service state.",
    "Stable repeated reads are not an atomic filesystem snapshot; freeze writers for release evidence.",
    "Trial configuration and cost metadata are supplied records, not independently measured by this checker.",
]


class Unavailable(ValueError):
    """The observation could not be made; never quietly convert it into success."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON object key")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("Non-finite JSON number")

    try:
        result = json.loads(data, object_pairs_hook=pairs, parse_constant=constant)
        json_bytes(result)  # Also rejects overflow such as 1e999.
        return result
    except (UnicodeError, RecursionError, OverflowError) as error:
        raise ValueError("Invalid or excessively nested JSON") from error


def relative_path(value):
    if (not isinstance(value, str) or not value or "\\" in value or "\0" in value
            or Path(value).is_absolute() or any(x in {"", ".", ".."} for x in value.split("/"))):
        raise ValueError("Expected an exact relative path without traversal")
    return value


def within(root, relative):
    relative_path(relative)
    target = root
    for part in relative.split("/"):
        target = target / part
        if target.is_symlink():
            raise Unavailable("Symlink observation refused")
    if not target.resolve().is_relative_to(root):
        raise Unavailable("Path escaped the declared root")
    return target


def read_regular(path, max_bytes=MAX_BYTES):
    if path.is_symlink():
        raise Unavailable("Symlink observation refused")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        with os.fdopen(os.open(path, flags), "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise Unavailable("Nonregular file observation refused")
            data = stream.read(max_bytes + 1)
    except FileNotFoundError:
        raise
    except OSError as error:
        raise Unavailable("File could not be read: " + type(error).__name__) from error
    if len(data) > max_bytes:
        raise Unavailable(f"File exceeds declared inspection bound of {max_bytes} bytes")
    return data


def named(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + " must be a nonempty string")
    return value


def sha256(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(label + " must be a lowercase SHA-256")
    return value


def pointer_tokens(pointer):
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")) or re.search(r"~(?![01])", pointer):
        raise ValueError("Invalid JSON Pointer")
    return [] if pointer == "" else [x.replace("~1", "/").replace("~0", "~") for x in pointer[1:].split("/")]


def resolve_pointer(value, pointer):
    for token in pointer_tokens(pointer):
        if isinstance(value, dict):
            value = value[token]
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
            value = value[int(token)]
        else:
            raise KeyError("JSON Pointer does not select a value")
    return value


def same_json(a, b):
    # Python says True == 1; the JSON oracle must preserve that distinction.
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same_json(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same_json(x, y) for x, y in zip(a, b))
    return a == b


def summarize(value):
    raw = json_bytes(value)
    if len(raw) <= 512:
        return {"value": value, "complete": True}
    return {"json_sha256": digest(raw), "json_bytes": len(raw), "complete": False,
            "reason": "Value omitted from report because it exceeds 512 bytes"}


def validate_case(case):
    if not isinstance(case, dict) or type(case.get("schema_version")) is not int or case.get("schema_version") != 1:
        raise ValueError("Case needs schema_version 1")
    named(case.get("case_id"), "case_id")
    fixture = case.get("fixture")
    if not isinstance(fixture, dict):
        raise ValueError("Case needs fixture identity")
    named(fixture.get("id"), "fixture.id")
    sha256(fixture.get("sha256"), "fixture.sha256")
    rows = case.get("acceptance")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Case needs nonempty acceptance rows")
    ids, check_ids = set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Acceptance row must be an object")
        identifier = named(row.get("id"), "acceptance.id")
        if identifier in ids:
            raise ValueError("Duplicate acceptance ID")
        ids.add(identifier)
        named(row.get("description"), "acceptance.description")
        named(row.get("subject"), "acceptance.subject")
        if row.get("boundary") != "local-artifact":
            raise ValueError("This oracle supports only the local-artifact boundary")
        checks = row.get("checks")
        if not isinstance(checks, list) or not checks:
            raise ValueError("Each acceptance row needs nonempty checks")
        for check in checks:
            if not isinstance(check, dict):
                raise ValueError("Check must be an object")
            cid = named(check.get("id"), "check.id")
            if cid in check_ids:
                raise ValueError("Duplicate check ID")
            check_ids.add(cid)
            kind = check.get("kind")
            if kind not in CHECK_KINDS:
                raise ValueError("Unknown check kind; no command execution is supported")
            if kind == "inventory_equals":
                expected = check.get("expected")
                if not isinstance(expected, list) or not all(isinstance(x, str) for x in expected):
                    raise ValueError("Inventory expected must be a relative-path array")
                if len(set(expected)) != len(expected):
                    raise ValueError("Duplicate inventory path")
                for path in expected:
                    relative_path(path)
            else:
                relative_path(check.get("path"))
            if kind == "file_sha256":
                sha256(check.get("expected"), "check.expected")
            elif kind == "json_equals":
                pointer_tokens(check.get("pointer"))
                if "expected" not in check:
                    raise ValueError("json_equals needs an expected value, including explicit null")
                json_bytes(check["expected"])
            elif kind == "text_contains":
                named(check.get("expected"), "check.expected")
    return case


class Observation:
    def __init__(self, root, max_bytes=MAX_BYTES):
        self.root = Path(root).absolute()
        if self.root.is_symlink() or not self.root.is_dir():
            raise Unavailable("Artifact root is missing, redirected or not a directory")
        self.root = self.root.resolve()
        self.max_bytes = max_bytes
        self.files, self.absent = {}, set()
        self.listed = None

    def read(self, relative):
        target = within(self.root, relative)
        data = read_regular(target, self.max_bytes)
        signature = {"sha256": digest(data), "bytes": len(data)}
        prior = self.files.get(relative)
        if prior is not None and prior != signature:
            raise Unavailable("Artifact changed during observation")
        self.files[relative] = signature
        return data

    def exists(self, relative):
        target = within(self.root, relative)
        try:
            target.lstat()
            return True
        except FileNotFoundError:
            self.absent.add(relative)
            return False
        except OSError as error:
            raise Unavailable("Could not observe path existence") from error

    def inventory(self):
        paths = []
        def on_error(error):
            raise Unavailable("Could not enumerate artifact directory") from error
        for directory, dirs, files in os.walk(self.root, followlinks=False, onerror=on_error):
            for name in dirs + files:
                path = Path(directory) / name
                try:
                    mode = path.lstat().st_mode
                except OSError as error:
                    raise Unavailable("Inventory changed or became unreadable during observation") from error
                if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                    raise Unavailable("Inventory contains a symlink or nonregular entry")
            paths.extend((Path(directory) / name).relative_to(self.root).as_posix() for name in files)
            if len(paths) > MAX_FILES:
                raise Unavailable("Inventory exceeds 10000-file inspection bound")
        paths.sort()
        if self.listed is not None and paths != self.listed:
            raise Unavailable("Artifact inventory changed during observation")
        self.listed = paths
        return paths

    def confirm(self):
        for relative in list(self.files):
            self.read(relative)
        for relative in sorted(self.absent):
            if self.exists(relative):
                raise Unavailable("Previously missing path appeared during observation")
        if self.listed is not None:
            self.inventory()


def overall(statuses):
    values = set(statuses)
    return "FAIL" if "FAIL" in values else "UNVERIFIED" if "UNVERIFIED" in values else "PASS"


def evaluate(case, artifact_root, *, case_sha=None, task_record=None, max_bytes=MAX_BYTES):
    validate_case(case)
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    record_ids = None
    if task_record is not None:
        if not isinstance(task_record, dict) or not isinstance(task_record.get("acceptance"), list):
            raise ValueError("Task record needs an acceptance array")
        record_ids = [r.get("id") for r in task_record["acceptance"] if isinstance(r, dict)]
        if (len(record_ids) != len(task_record["acceptance"]) or len(set(record_ids)) != len(record_ids)
                or set(record_ids) != {r["id"] for r in case["acceptance"]}):
            raise ValueError("Task record acceptance IDs must match the case exactly; no dropped or duplicate outcomes")
        by_id = {r["id"]: r for r in task_record["acceptance"]}
        for expected in case["acceptance"]:
            actual = by_id[expected["id"]]
            if actual.get("subject") != expected["subject"] or actual.get("boundary") != expected["boundary"]:
                raise ValueError("Task record subjects and boundaries must match the case; adjacent proof is not task proof")
    try:
        snapshot, unavailable = Observation(artifact_root, max_bytes), None
    except Unavailable as error:
        snapshot, unavailable = None, str(error)
    rows = []
    for acceptance in case["acceptance"]:
        checks = []
        for check in acceptance["checks"]:
            result = {"id": check["id"], "kind": check["kind"], "status": "UNVERIFIED"}
            if "path" in check:
                result["path"] = check["path"]
            if "expected" in check:
                result["expected"] = summarize(check["expected"])
            if unavailable:
                result["reason"] = unavailable
                checks.append(result)
                continue
            try:
                kind = check["kind"]
                if kind == "inventory_equals":
                    actual = snapshot.inventory()
                    passed = actual == sorted(check["expected"])
                elif kind == "path_absent":
                    actual = snapshot.exists(check["path"])
                    passed = not actual
                    result["expected"] = {"value": False, "complete": True}
                else:
                    data = snapshot.read(check["path"])
                    if kind == "file_sha256":
                        actual = digest(data)
                        passed = actual == check["expected"]
                    elif kind == "json_equals":
                        actual = resolve_pointer(strict_json(data), check["pointer"])
                        passed = same_json(actual, check["expected"])
                        result["pointer"] = check["pointer"]
                    else:
                        text = data.decode("utf-8")
                        actual = {"found": check["expected"] in text}
                        passed = actual["found"]
                result.update(status="PASS" if passed else "FAIL", observed=summarize(actual))
            except Unavailable as error:
                result["reason"] = str(error)
            except FileNotFoundError:
                if "path" in check:
                    snapshot.absent.add(check["path"])
                    result.update(status="FAIL", reason="Required artifact is missing")
                else:
                    result.update(status="UNVERIFIED", reason="Inventory changed during observation")
            except (ValueError, KeyError, IndexError, UnicodeError) as error:
                result.update(status="FAIL", reason="Produced artifact does not satisfy the declared format/selector", error_type=type(error).__name__)
            checks.append(result)
        rows.append({"id": acceptance["id"], "description": acceptance["description"], "subject": acceptance["subject"],
                     "boundary": acceptance["boundary"], "status": overall(x["status"] for x in checks), "checks": checks})
    stability = "UNVERIFIED" if unavailable else "PASS"
    stability_reason = unavailable
    if snapshot:
        try:
            snapshot.confirm()
        except (Unavailable, FileNotFoundError, OSError) as error:
            stability, stability_reason = "UNVERIFIED", str(error)
    status = overall(r["status"] for r in rows)
    if stability != "PASS":
        status = "UNVERIFIED"  # A mixed-time snapshot cannot substantiate its verdict.
    claim = task_record.get("overall_status") if task_record is not None else None
    return {"schema_version": 1, "case_id": case["case_id"],
            "case_sha256": case_sha or digest(json_bytes(case)), "case_digest_basis": "raw-file" if case_sha else "sorted-json",
            "fixture": case["fixture"], "status": status, "acceptance": rows,
            "fixture_identity_basis": "Declared by the case; paired compare separately reads and verifies fixture bytes.",
            "coverage": {"acceptance_rows": len(rows), "checks": sum(len(r["checks"]) for r in rows),
                         "check_status_counts": dict(Counter(c["status"] for r in rows for c in r["checks"]))},
            "observed_files": snapshot.files if snapshot else {}, "observed_absent_paths": sorted(snapshot.absent) if snapshot else [],
            "stability": {"status": stability, "reason": stability_reason},
            "claimed_overall_status": claim, "claim_supported_at_declared_boundary": (status == "PASS") if claim == "GREEN" else None,
            "checker_sha256": digest(Path(__file__).read_bytes()),
            "observed_at_utc": datetime.now(timezone.utc).isoformat(), "limits": LIMITS}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("observed_at must be an ISO-8601 timestamp with timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("missing timezone")
    except ValueError as error:
        raise ValueError("observed_at must be a valid timestamp with timezone") from error
    return value


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False  # Invalid measurement metadata must not crash the reporter.


def check_configuration(config):
    if not isinstance(config, dict) or set(config) != CONFIG_KEYS:
        raise ValueError("Configuration needs exactly model, host, tools_sha256, system_sha256, budget and seed")
    for key in ("model", "host"):
        named(config[key], key)
    for key in ("tools_sha256", "system_sha256"):
        sha256(config[key], key)
    if not isinstance(config["budget"], dict) or not config["budget"]:
        raise ValueError("Configuration budget must be an explicit nonempty object")
    for value in config["budget"].values():
        if not finite_number(value) or value <= 0:
            raise ValueError("Budget values must be positive finite numbers within evaluation range, with units named in keys")
    if config["seed"] is not None and (isinstance(config["seed"], bool) or not isinstance(config["seed"], int)):
        raise ValueError("seed must be integer or explicit null")


def validate_trial(trial):
    if not isinstance(trial, dict):
        raise ValueError("Trial must be an object")
    named(trial.get("trial_id"), "trial_id")
    named(trial.get("treatment_revision"), "treatment_revision")
    if trial.get("status") not in {"completed", "error", "not_run"}:
        raise ValueError("Trial status must be completed, error or not_run")
    if trial["status"] != "not_run":
        timestamp(trial.get("observed_at"))
    if trial["status"] == "completed":
        relative_path(trial.get("artifacts"))
    else:
        named(trial.get("reason"), "incomplete trial reason")
    check_configuration(trial.get("configuration"))
    sha256(trial.get("case_sha256"), "trial.case_sha256")
    sha256(trial.get("fixture_sha256"), "trial.fixture_sha256")
    metrics = trial.get("metrics", {})
    if not isinstance(metrics, dict) or set(metrics) - METRICS:
        raise ValueError("Unknown metric; preserve units and do not substitute characters for tokens")
    for key, value in metrics.items():
        if value is None:
            continue
        if not finite_number(value) or value < 0:
            raise ValueError("Measured costs must be nonnegative finite numbers within evaluation range, or null")
        if key in {"input_tokens", "output_tokens", "tool_calls"} and not isinstance(value, int):
            raise ValueError("Token and tool-call counts must be integers")


def compare(plan, root, max_bytes=MAX_BYTES):
    if not isinstance(plan, dict) or type(plan.get("schema_version")) is not int or plan.get("schema_version") != 1:
        raise ValueError("Comparison plan needs schema_version 1")
    named(plan.get("experiment_id"), "experiment_id")
    pairs = plan.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("Comparison needs predeclared nonempty pairs")
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Trial bundle root must be an existing directory")
    root = root.resolve()
    seen_pairs, seen_trials = set(), set()
    # Validate the complete design before observing anything or calculating a score.
    for pair in pairs:
        if not isinstance(pair, dict):
            raise ValueError("Pair must be an object")
        pid = named(pair.get("pair_id"), "pair_id")
        if pid in seen_pairs:
            raise ValueError("Duplicate pair ID")
        seen_pairs.add(pid)
        relative_path(pair.get("case"))
        relative_path(pair.get("fixture"))
        for variant in ("baseline", "candidate"):
            trial = pair.get(variant)
            if trial is not None:
                validate_trial(trial)
                if trial["trial_id"] in seen_trials:
                    raise ValueError("Duplicate trial ID")
                seen_trials.add(trial["trial_id"])
    rows, outcomes, metric_pairs = [], Counter(), {k: [] for k in sorted(METRICS)}
    source_hashes = {}
    for pair in pairs:
        row = {"pair_id": pair["pair_id"], "status": "UNVERIFIED", "reasons": [], "trials": {}}
        raw = read_regular(within(root, pair["case"]), max_bytes)
        case = validate_case(strict_json(raw))
        case_hash = digest(raw)
        fixture_path = within(root, pair["fixture"])
        fixture_hash = digest(read_regular(fixture_path, max_bytes))
        if fixture_hash != case["fixture"]["sha256"]:
            raise ValueError("Observed fixture bytes do not match the case's pinned fixture")
        for source_path, source_hash in ((pair["case"], case_hash), (pair["fixture"], fixture_hash)):
            if source_path in source_hashes and source_hashes[source_path] != source_hash:
                raise ValueError("Case or fixture changed between paired observations")
            source_hashes[source_path] = source_hash
        row.update(case_id=case["case_id"], case_sha256=case_hash, fixture=case["fixture"], fixture_bytes_verified=True)
        for variant in ("baseline", "candidate"):
            trial = pair.get(variant)
            if trial is None:
                row["reasons"].append(variant + ": trial absent from declared pair")
                continue
            if trial["case_sha256"] != case_hash or trial["fixture_sha256"] != case["fixture"]["sha256"]:
                raise ValueError("Trial case or fixture identity differs from the pinned oracle")
            if trial["status"] != "completed":
                row["trials"][variant] = {"trial_id": trial["trial_id"], "status": "UNVERIFIED", "reason": trial["reason"]}
                row["reasons"].append(variant + ": " + trial["status"])
                continue
            result = evaluate(case, within(root, trial["artifacts"]), case_sha=case_hash, max_bytes=max_bytes)
            row["trials"][variant] = {"trial_id": trial["trial_id"], "treatment_revision": trial["treatment_revision"],
                                       "metrics": {k: trial.get("metrics", {}).get(k) for k in sorted(METRICS)}, "result": result, "status": result["status"]}
            if result["status"] == "UNVERIFIED":
                row["reasons"].append(variant + ": artifact observation unverified")
        baseline, candidate = pair.get("baseline"), pair.get("candidate")
        if baseline is not None and candidate is not None and not same_json(baseline["configuration"], candidate["configuration"]):
            row["reasons"].append("configuration mismatch; changed variables exceed the declared treatment")
        if not row["reasons"]:
            row["status"] = "COMPARABLE"
            before, after = (row["trials"][v]["status"] for v in ("baseline", "candidate"))
            outcome = {("PASS", "PASS"): "both_pass", ("FAIL", "FAIL"): "both_fail",
                       ("FAIL", "PASS"): "improved", ("PASS", "FAIL"): "regressed"}[(before, after)]
            row["outcome"] = outcome
            outcomes[outcome] += 1
            for key in metric_pairs:
                a, b = (pair[v].get("metrics", {}).get(key) for v in ("baseline", "candidate"))
                if a is not None and b is not None:
                    metric_pairs[key].append(b - a)
        rows.append(row)
    for path, expected in source_hashes.items():
        if digest(read_regular(within(root, path), max_bytes)) != expected:
            raise ValueError("Case or fixture changed during paired observation")
    count = sum(outcomes.values())
    return {"schema_version": 1, "experiment_id": plan["experiment_id"], "plan_sha256": digest(json_bytes(plan)),
            "checker_sha256": digest(Path(__file__).read_bytes()), "pairs": rows,
            "coverage": {"planned_pairs": len(pairs), "comparable_pairs": count, "excluded_or_unverified_pairs": len(pairs) - count},
            "paired_outcomes": {k: outcomes[k] for k in ("both_pass", "both_fail", "improved", "regressed")},
            "baseline_pass_rate_on_comparable_pairs": (outcomes["both_pass"] + outcomes["regressed"]) / count if count else None,
            "candidate_pass_rate_on_comparable_pairs": (outcomes["both_pass"] + outcomes["improved"]) / count if count else None,
            "absolute_pass_rate_change_percentage_points": 100 * (outcomes["improved"] - outcomes["regressed"]) / count if count else None,
            "cost_differences_candidate_minus_baseline": {key: {"paired_observations": len(values), "missing_comparable_pairs": count - len(values),
                   "mean": mean(values) if values else None} for key, values in metric_pairs.items()},
            "status": "COMPLETE" if count == len(pairs) else "PARTIAL",
            "interpretation": "Descriptive paired outcomes, not a causal claim, significance test, deployment gate or universal model-performance estimate.",
            "limits": LIMITS}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Recheck a declared outcome against actual local artifact bytes")
    check.add_argument("--case", type=Path, required=True)
    check.add_argument("--artifacts", type=Path, required=True)
    check.add_argument("--task-record", type=Path)
    pair = sub.add_parser("compare", help="Re-evaluate and compare predeclared paired trials")
    pair.add_argument("--plan", type=Path, required=True)
    pair.add_argument("--root", type=Path, required=True)
    for command in (check, pair):
        command.add_argument("--max-file-bytes", type=int, default=MAX_BYTES)
    args = parser.parse_args(argv)
    try:
        if args.max_file_bytes < 1:
            raise ValueError("--max-file-bytes must be positive")
        if args.command == "check":
            raw = read_regular(args.case.absolute(), args.max_file_bytes)
            record = strict_json(read_regular(args.task_record.absolute(), args.max_file_bytes)) if args.task_record else None
            result = evaluate(strict_json(raw), args.artifacts, case_sha=digest(raw), task_record=record, max_bytes=args.max_file_bytes)
            code = 0 if result["status"] == "PASS" else 1
        else:
            raw = read_regular(args.plan.absolute(), args.max_file_bytes)
            result = compare(strict_json(raw), args.root, args.max_file_bytes)
            result["plan_file_sha256"] = digest(raw)
            code = 0 if result["status"] == "COMPLETE" else 1
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return code
    except (ValueError, OSError, TypeError, RecursionError) as error:
        print(json.dumps({"status": "INVALID", "error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
