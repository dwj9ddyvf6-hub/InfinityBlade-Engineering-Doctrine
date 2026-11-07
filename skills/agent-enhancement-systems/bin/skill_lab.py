#!/usr/bin/env python3
"""Disciplines 6 and 7: test skills like blockers and gate the library.

The package form is a harness, not a hosted service. A host supplies model
outputs or trigger predictions; this module validates the datasets, scores
them, protects the untouched final test, scans candidates and configuration,
and runs the F7 clean-versus-mutant check.

Standard library only.
"""
import hashlib
import json
import math
from _storage import locked
import os
import re
import subprocess
import sys

ALLOWED_FRONTMATTER = {"name", "description", "license", "allowed-tools", "metadata",
                       "compatibility", "version", "capabilities"}
SKILL_LIMIT_BYTES = 20000
TOKEN_BANDS = {"trigger": (48, 92, 150), "invoke": (220, 480, 900), "deferred": (180, 520, 1200)}
ADOPTION_WEIGHTS = {"review_status": 4, "publisher_binding": 3, "commit_integrity": 3,
                    "manifest_integrity": 3, "domain_proof": 2, "metadata_quality": 3,
                    "taxonomy": 2, "provenance": 4, "health": 2, "scanner": 2}
UNIVERSAL_COMPONENTS = ("review_status", "publisher_binding", "commit_integrity",
                        "manifest_integrity", "domain_proof", "metadata_quality",
                        "taxonomy", "provenance")
SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("generic-secret-assignment", re.compile(
        r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-./+]{16,}['\"]")),
]
CONFIG_RULES = [
    ("permissions", "world-writable-chmod", 10, re.compile(r"chmod\s+(?:-R\s+)?777|0o777")),
    ("permissions", "unsafe-eval-exec", 10, re.compile(r"\b(?:eval|exec)\s*\(\s*(?!['\"])")),
    ("permissions", "shell-true-on-input", 10, re.compile(r"shell\s*=\s*True")),
    ("hooks", "hook-pipes-remote-code", 15, re.compile(r"curl\b[^\n|]*\|\s*(?:sh|bash)")),
    ("hooks", "hook-destructive-command", 15, re.compile(r"\brm\s+-rf\s+[/~]")),
    ("mcp", "mcp-insecure-url", 10, re.compile(r'"url"\s*:\s*"http://')),
    ("mcp", "mcp-unpinned-runner", 10, re.compile(r"\bnpx\s+-y\b|\buvx\s+")),
    ("prompt-defense", "prompt-defense-missing", 15, re.compile(r"(?i)ignore (?:all )?previous instructions|disable (?:the )?safety")),
]


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    fields = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip("'\"")
    return fields


def lint_skill_text(text):
    fields = parse_frontmatter(text)
    if fields is None:
        return ["no frontmatter"]
    errors = []
    for key in fields:
        if key not in ALLOWED_FRONTMATTER:
            errors.append(f"property not allowed: {key}")
    name = fields.get("name", "")
    if not re.fullmatch(r"[a-z0-9-]{1,64}", name or ""):
        errors.append("name must be kebab-case, at most 64 characters")
    description = fields.get("description", "")
    if not description:
        errors.append("description missing: it must state triggers and the negative boundary")
    if len(description) > 1024:
        errors.append("description over 1024 characters")
    if "<" in description or ">" in description:
        errors.append("description contains angle brackets")
    if len(fields.get("compatibility", "")) > 500:
        errors.append("compatibility over 500 characters")
    if "capabilities" not in fields and "## Capabilities" not in text:
        errors.append("capabilities must be declared explicitly: read, write, and external-send")
    return errors


def skill_size(data):
    if isinstance(data, str):
        try:
            is_file = os.path.isfile(data)
        except OSError:
            is_file = False
        size = os.path.getsize(data) if is_file else len(data.encode("utf-8"))
    elif isinstance(data, bytes):
        size = len(data)
    elif os.path.isfile(data):
        size = os.path.getsize(data)
    else:
        raise ValueError("skill_size expects text, bytes, or a file path")
    return {"bytes": size, "limit": SKILL_LIMIT_BYTES, "blocked": size >= SKILL_LIMIT_BYTES,
            "action": "split body plus references" if size >= SKILL_LIMIT_BYTES else "ok"}


def _band(kind, tokens):
    low, mid, high = TOKEN_BANDS[kind]
    return "light" if tokens <= low else "standard" if tokens <= mid else "heavy" if tokens <= high else "over"


def token_cost(skill_text, description, explicit_only=False):
    trigger = len(description) // 4
    invoke = len(skill_text) // 4
    deferred = max(0, invoke - trigger)
    return {"trigger_tokens": trigger, "trigger_band": _band("trigger", trigger),
            "invoke_tokens": invoke, "invoke_band": _band("invoke", invoke),
            "deferred_tokens": deferred, "deferred_band": _band("deferred", deferred),
            "explicit_only": explicit_only,
            "fails_review": (not explicit_only) and _band("invoke", invoke) in ("heavy", "over")}


def validate_eval_set(data):
    errors = []
    if not data.get("reference_solution"):
        errors.append("reference solution missing: the task is not proven solvable")
    if data.get("isolated_trials") is not True:
        errors.append("isolated trials must be true")
    if data.get("judge_unknown_exit") is not True:
        errors.append("model judge needs an explicit Unknown exit")
    kinds = {case.get("kind") for case in data.get("cases", [])}
    cases = data.get("cases", [])
    if kinds != {"should", "should-not"} or sum(c.get("kind") == "should" for c in cases) != sum(c.get("kind") == "should-not" for c in cases):
        errors.append("cases must be balanced should and should-not")
    return errors


def validate_trigger_dataset(cases, require_twenty=True):
    errors = []
    if require_twenty and len(cases) != 20:
        errors.append("trigger set must contain exactly 20 queries at vendor numbers")
    if any(c.get("expect") not in ("trigger", "no-trigger") for c in cases):
        errors.append("unknown trigger label")
    if any(c.get("split") not in ("validation", "final") for c in cases):
        errors.append("unknown dataset split")
    queries = [c.get("query") for c in cases]
    if any(not isinstance(q, str) or not q.strip() for q in queries) or len(set(queries)) != len(queries):
        errors.append("queries must be nonempty and unique across splits")
    positives = sum(1 for c in cases if c.get("expect") == "trigger")
    negatives = sum(1 for c in cases if c.get("expect") == "no-trigger")
    if positives != negatives:
        errors.append("trigger set must be balanced")
    splits = {c.get("split") for c in cases}
    if not {"validation", "final"}.issubset(splits):
        errors.append("trigger set needs validation and untouched final splits")
    validation = [c for c in cases if c.get("split") == "validation"]
    if cases and round(len(validation) / len(cases), 2) not in (0.6, 0.4):
        errors.append("split must be 60/40 train-validation/final in one direction; name which set selects")
    return errors


def score_predictions(cases, predictions, split, runs=3, threshold=0.5):
    if isinstance(runs, bool) or not isinstance(runs, int) or runs < 1:
        raise ValueError("runs must be a positive integer")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be finite and between zero and one")
    selected = [c for c in cases if c.get("split") == split]
    if not selected:
        raise ValueError(f"no cases in split {split!r}")
    tp = fp = fn = tn = 0
    for case in selected:
        outcomes = predictions.get(split, {}).get(case["query"])
        if outcomes is None or len(outcomes) != runs:
            raise ValueError(f"prediction for {case['query']!r} must contain exactly {runs} runs")
        if any(type(x) is not bool for x in outcomes):
            raise ValueError("prediction outcomes must be booleans, not truthy values")
        if case.get("expect") not in ("trigger", "no-trigger"):
            raise ValueError("unknown expected trigger label")
        fired = sum(outcomes) / runs >= threshold
        expected = case["expect"] == "trigger"
        if fired and expected:
            tp += 1
        elif fired:
            fp += 1
        elif expected:
            fn += 1
        else:
            tn += 1
    total = tp + fp + fn + tn
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "accuracy": (tp + tn) / total if total else 0.0,
            "runs_per_query": runs, "threshold": threshold, "split": split}


def dataset_hash(cases):
    canon = json.dumps(cases, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def run_final_test(cases, predictions, candidate_id, ledger_path):
    """Run the untouched final set once per candidate and dataset hash."""
    with locked(ledger_path):
        key = f"{dataset_hash(cases)}:{candidate_id}"
        used = set()
        if os.path.isfile(ledger_path):
            with open(ledger_path, encoding="utf-8") as handle:
                used = {json.loads(line)["key"] for line in handle if line.strip()}
        if key in used:
            raise ValueError("final test already run for this candidate and dataset: it is selection data now")
        result = score_predictions(cases, predictions, "final")
        os.makedirs(os.path.dirname(os.path.abspath(ledger_path)), exist_ok=True)
        with open(ledger_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"key": key, "candidate": candidate_id, "result": result}) + "\n")
        return result

def select_candidate(candidates, cases, predictions_by_candidate):
    scored = []
    for candidate in candidates:
        result = score_predictions(cases, predictions_by_candidate[candidate["id"]], "validation")
        scored.append((result["accuracy"], candidate["id"], result))
    scored.sort(reverse=True)
    return {"winner": scored[0][1] if scored else None,
            "scores": {candidate_id: result for _, candidate_id, result in scored},
            "selection_split": "validation",
            "note": "selection scores are validation scores, never final test scores"}


def reliability(runs_by_task, k=3):
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer")
    if not runs_by_task:
        return {"pass_at_k": 0.0, "pass_pow_k": 0.0, "tasks": 0}
    pass_at = 0
    pass_all = 0
    for runs in runs_by_task.values():
        if len(runs) < k:
            raise ValueError(f"reliability requires at least k={k} runs per task")
        window = runs[:k]
        if any(type(value) is not bool for value in window):
            raise ValueError("run outcomes must be booleans")
        pass_at += any(window)
        pass_all += all(window)
    n = len(runs_by_task)
    return {"pass_at_k": pass_at / n, "pass_pow_k": pass_all / n, "tasks": n, "k": k,
            "capability_gate": (pass_at / n) >= 0.90,
            "regression_gate": (pass_all / n) == 1.00}


def validate_trajectory(fixture):
    errors = []
    sequence = fixture.get("tool_sequence")
    if not isinstance(sequence, list) or not sequence:
        errors.append("trajectory fixture needs an ordered tool_sequence")
    calls = fixture.get("actual_calls", [])
    names = [call.get("tool") for call in calls]
    observed = names[:len(sequence)] if sequence and fixture.get("allow_extra_calls") else names
    if sequence and observed != sequence:
        errors.append("actual tool sequence does not match the fixture order")
    forbidden = set(fixture.get("forbidden_tools", []))
    if forbidden & set(names):
        errors.append("forbidden tool appears in the trajectory")
    for check in fixture.get("arg_checks", []):
        matched = [c for c in calls if c.get("tool") == check.get("tool")]
        occurrence = check.get("occurrence", 0)
        call = matched[occurrence] if isinstance(occurrence, int) and 0 <= occurrence < len(matched) else None
        if not call or call.get("args", {}).get(check.get("arg")) != check.get("equals"):
            errors.append(f"argument check failed for {check.get('tool')}.{check.get('arg')}")
    return errors


def scan_staged_text(text, label="<text>"):
    hits = []
    for name, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            hits.append({"kind": name, "where": label,
                         "line": text[:match.start()].count("\n") + 1})
    return hits


def normalize_evidence(text):
    return re.sub(r"\s+", " ", re.sub(r"\d+", "N", text.strip()))[:160]


def fingerprint(rule_id, evidence):
    return hashlib.sha256(f"{rule_id}|{normalize_evidence(evidence)}".encode()).hexdigest()[:32]


def scan_config(paths):
    findings, scanned = [], 0
    for root in paths:
        files = [root] if os.path.isfile(root) else []
        if os.path.isdir(root):
            for dirpath, _, names in os.walk(root):
                files += [os.path.join(dirpath, n) for n in names
                          if n.endswith((".md", ".py", ".sh", ".yaml", ".yml", ".json"))]
        for path in files:
            scanned += 1
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            for hit in scan_staged_text(text, path):
                findings.append({"category": "secrets", "rule": hit["kind"], "path": path,
                                 "line": hit["line"], "weight": 25, "secret": True,
                                 "fingerprint": fingerprint(hit["kind"], hit["kind"])})
            for i, line in enumerate(text.splitlines(), 1):
                for category, rule_id, weight, pattern in CONFIG_RULES:
                    if pattern.search(line):
                        findings.append({"category": category, "rule": rule_id, "path": path,
                                         "line": i, "weight": weight, "secret": False,
                                         "fingerprint": fingerprint(rule_id, line)})
    categories = ("secrets", "permissions", "hooks", "mcp", "prompt-defense")
    scores = {}
    for category in categories:
        deduction = sum(f["weight"] for f in findings if f["category"] == category)
        scores[category] = max(0.0, 100.0 - deduction)
    return {"scanned_files": scanned, "findings": findings, "category_scores": scores,
            "score": round(sum(scores.values()) / len(scores), 1),
            "recognized_defenses": [],
            "limits": "configuration text only; live connections and prompt text coverage are named limits"}


def adoption_scan(manifest, trust_scanner_config=False):
    """HCS-28-shaped scan. Missing universal components score zero."""
    if manifest.get("scanner_config_in_repo") and not trust_scanner_config:
        raise ValueError("scanner config inside the scanned repo needs an explicit trust flag")
    for key in ADOPTION_WEIGHTS:
        value = manifest.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{key} must be a finite score in [0, 1]")
    emitted = {key: float(manifest.get(key, 0)) for key in UNIVERSAL_COMPONENTS}
    denominator = sum(ADOPTION_WEIGHTS[key] for key in UNIVERSAL_COMPONENTS)
    numerator = sum(ADOPTION_WEIGHTS[key] * emitted[key] for key in UNIVERSAL_COMPONENTS)
    for key in ("health", "scanner"):
        if key in manifest:
            denominator += ADOPTION_WEIGHTS[key]
            numerator += ADOPTION_WEIGHTS[key] * float(manifest[key])
    return {"score": round(28 * numerator / denominator, 2) if denominator else 0,
            "state": manifest.get("review_status_label", "unreviewed"),
            "components": emitted,
            "denominator_weight": denominator}


def directory_description_check(path):
    target = path if os.path.isfile(path) else os.path.join(path, "DIRECTORY.md")
    if not os.path.isfile(target):
        return [f"missing {target}"]
    with open(target, encoding="utf-8") as handle:
        text = handle.read()
    errors = []
    abstract = re.search(r"^Abstract:\s*(.+)$", text, re.M)
    if not abstract:
        errors.append("missing L0 Abstract line")
    else:
        value = abstract.group(1).strip()
        if "TODO" in value:
            errors.append("abstract is a TODO skeleton")
        if len(value) > 200:
            errors.append("abstract over 200 characters")
        if len([s for s in re.split(r"[.!?]+", value) if s.strip()]) > 1:
            errors.append("abstract must be exactly one sentence")
    overview = re.search(r"^Overview:\s*(.+)$", text, re.M | re.S)
    if not overview or len(overview.group(1).strip()) < 40:
        errors.append("missing or too-short L1 Overview")
    elif "TODO" in overview.group(1):
        errors.append("overview is a TODO skeleton")
    return errors


def fragment_hash(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def fragment_lint(text, fragment_dir):
    errors = []
    for name, pin in re.findall(r"\{\{fragment:([A-Za-z0-9_-]+)@([0-9a-f]{8,64})\}\}", text):
        path = os.path.join(fragment_dir, name)
        if not os.path.isfile(path):
            errors.append(f"fragment missing: {name}")
        elif not fragment_hash(path).startswith(pin):
            errors.append(f"fragment hash drift: {name}")
    return errors


def f7_check(clean_dir, mutant_dir, command, expected_failure=None, timeout=60):
    """Accept a strengthened test only if clean passes and mutant fails."""
    clean = subprocess.run(command, cwd=clean_dir, capture_output=True, text=True, timeout=timeout)
    mutant = subprocess.run(command, cwd=mutant_dir, capture_output=True, text=True, timeout=timeout)
    matched = expected_failure is not None and re.search(expected_failure, mutant.stdout + mutant.stderr) is not None
    accepted = clean.returncode == 0 and mutant.returncode != 0 and (matched if expected_failure is not None else True)
    if clean.returncode != 0 and mutant.returncode != 0:
        finding = "test fails both ways: itself a J6 finding"
    elif clean.returncode == 0 and mutant.returncode == 0:
        finding = "mutant survived"
    elif clean.returncode != 0:
        finding = "clean replica failed"
    else:
        finding = ("expected mutant failure observed" if matched else
                   "mutant failure did not match the expected reason" if expected_failure is not None else
                   "exit-code differential only; inspect failure reason before trusting F7")
    return {"clean_exit": clean.returncode, "mutant_exit": mutant.returncode,
            "accepted": accepted, "finding": finding, "failure_reason_verified": matched}


def judge_output(value):
    """A model judge gets an explicit Unknown exit."""
    return value if value in ("pass", "fail", "Unknown") else "Unknown"


if __name__ == "__main__":
    print(__doc__)
