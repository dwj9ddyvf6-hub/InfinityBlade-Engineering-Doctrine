#!/usr/bin/env python3
"""Offline structural integrity and reproducible skill-registry generation.

This validates source structure, local links, syntax and registry freshness.
It does not judge truth, install skills, execute broker tools or claim behavioral
improvement. Run the separately documented behavioral/mechanism tests as well.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import unquote, urlsplit

REGISTRY_PATH = "skills/registry.json"
IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}
KINDS = {
    "infinityblade": ("core-operating-doctrine", "Procedure and local source-checking helpers; no automatic host installation."),
    "agent-enhancement-systems": ("local-reference-mechanisms", "Runnable local mechanisms; host integrations and external effects need separate implementation and proof."),
    "memory-recall-systems": ("local-retrieval-mechanism", "Local index/search/evaluation over explicitly supplied documents; not access to a host's internal memory."),
    "alpaca-paper": ("credentialed-service-client", "Credentialed broker integration; never execute as a repository audit or installation test."),
    "chart-read": ("external-runtime-dependent", "Chart procedure and helpers; external data/analysis dependencies must be verified separately."),
    "stock-analysis": ("external-runtime-dependent", "Analysis procedure and lens helpers; external data and sibling capabilities are not bundled runtime proof."),
    "backtest-crosscheck": ("external-oracle-dependent", "Independent oracle engine is an explicitly external prerequisite; a paper contract is not a runnable oracle."),
}
RELATIONS = {
    "infinityblade": ["efficiency-breakthroughs", "proof-before-green", "memory-recall-systems"],
    "proof-before-green": ["gate-test-integrity", "live-execution-proof", "save-readback-verification"],
    "gate-test-integrity": ["stable-tree-gate-integrity", "hermetic-test-isolation"],
    "claim-verification-ledger": ["absence-proof-coverage-ledger", "save-readback-verification", "live-execution-proof"],
    "single-door-consumer-audit": ["persisted-field-consumption-audit"],
    "judgment-provenance-check": ["doctrine-provenance-check", "conviction-surface-definition"],
    "agent-enhancement-systems": ["memory-recall-systems", "claim-verification-ledger", "literal-scope-and-silent-checks"],
    "chart-read": ["stock-analysis"],
    "stock-analysis": ["chart-read", "backtest-crosscheck"],
}


def source_files(root):
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS)
        for name in dirs:
            if (Path(base) / name).is_symlink():
                raise ValueError(f"Refusing symlink source directory: {Path(base) / name}")
        for name in sorted(files):
            yield Path(base) / name


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("Missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("Unclosed YAML frontmatter") from error
    result = {}
    i = 1
    while i < end:
        line = lines[i]
        match = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if match:
            key, value = match.groups()
            if key in result:
                raise ValueError(f"Duplicate metadata key: {key}")
            if value in {">", "|", ">-", "|-"}:
                chunks = []
                i += 1
                while i < end and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                    chunks.append(lines[i].strip())
                    i += 1
                result[key] = ("\n" if value.startswith("|") else " ").join(chunks)
                continue
            if value.startswith('"'):
                try:
                    value = json.loads(value)
                except ValueError as error:
                    raise ValueError(f"Invalid or unsupported quoted scalar: {key}") from error
            elif value.startswith("'"):
                if len(value) < 2 or not value.endswith("'") or "'" in value[1:-1].replace("''", ""):
                    raise ValueError(f"Invalid quoted scalar: {key}")
                value = value[1:-1].replace("''", "'")
            elif key in {"name", "description", "version"}:
                if (value.startswith(("[", "{", "&", "*", "!")) or ": " in value
                        or value.lower() in {"true", "false", "null", "~"}):
                    raise ValueError(f"Expected a supported string scalar: {key}")
            result[key] = value
        elif line.strip() and not line.lstrip().startswith("#"):
            raise ValueError(f"Unsupported metadata syntax on line {i + 1}")
        i += 1
    for key in ("name", "description"):
        if not result.get(key):
            raise ValueError(f"Missing required metadata: {key}")
    return result


def regular_text(path):
    """Metadata reads cannot follow a final symlink or block on a FIFO."""
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError(f"Metadata must be a regular file: {path}")
        return handle.read().decode("utf-8")


def runtime_dependencies(root, names):
    path = root / "skills/runtime-dependencies.json"
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError("Redirected runtime dependency declaration")
    data = json.loads(regular_text(path))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("skills"), dict):
        raise ValueError("Expected schema_version1 and skills object")
    if set(data["skills"]) - names:
        raise ValueError("Unknown skills in runtime dependencies")
    fields = {"local-file": "path", "python-distribution": "distribution",
              "environment": "environment", "external-source": "environment",
              "external-directory": "environment", "host-capability": None}
    for name, spec in data["skills"].items():
        if not isinstance(spec, dict):
            raise ValueError(f"Runtime specification must be an object: {name}")
        required_skills = spec.get("requires_skills", [])
        if (not isinstance(required_skills, list) or not all(isinstance(x, str) for x in required_skills)
                or set(required_skills) - names or len(set(required_skills)) != len(required_skills)):
            raise ValueError(f"Invalid requires_skills in {name}")
        identifiers = set()
        for necessity in ("required", "optional"):
            rows = spec.get(necessity)
            if not isinstance(rows, list):
                raise ValueError(f"Runtime {name}.{necessity} must be an array")
            for row in rows:
                if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k].strip() for k in ("id", "kind", "required_for", "verification")):
                    raise ValueError(f"Incomplete runtime dependency in {name}.{necessity}")
                if row["id"] in identifiers or row["kind"] not in fields:
                    raise ValueError(f"Duplicate ID or unknown runtime dependency kind in {name}")
                identifiers.add(row["id"])
                field = fields[row["kind"]]
                if field and (not isinstance(row.get(field), str) or not row[field].strip()):
                    raise ValueError(f"Runtime dependency {row['id']} needs {field}")
                for key in ("path", "relative_path"):
                    if key in row:
                        value = row[key]
                        if (not isinstance(value, str) or not value or Path(value).is_absolute()
                                or "\\" in value or any(p in {"", ".", ".."} for p in value.split("/"))):
                            raise ValueError(f"Unsafe runtime dependency {key} in {name}")
                if "environment" in row and (not isinstance(row["environment"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", row["environment"])):
                    raise ValueError(f"Invalid environment variable name in {name}")
    return data


def discover(root):
    root = Path(root).resolve()
    if (root / "skills").is_symlink():
        raise ValueError("Refusing symlink skills directory")
    rows = []
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        if path.is_symlink() or path.parent.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Skill entrypoint is a symlink: {path.relative_to(root)}")
        content = regular_text(path)
        data = content.encode("utf-8")
        meta = frontmatter(content)
        name = meta["name"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
            raise ValueError(f"Invalid portable skill name: {name}")
        if path.parent.name != name:
            raise ValueError(f"Skill name differs from source folder: {name}")
        if len(meta["description"]) > 1024:
            raise ValueError(f"Skill description exceeds 1024 characters: {name}")
        kind, boundary = KINDS.get(name, ("procedure", "Instructional procedure; reading it does not install or execute a host mechanism."))
        files = sorted(p.relative_to(root).as_posix() for p in source_files(path.parent))
        if any((root / relative).is_symlink() for relative in files):
            raise ValueError(f"Refusing symlink resource in skill: {name}")
        rows.append({"name": name, "description": meta["description"],
                     "version": meta.get("version"), "entrypoint": path.relative_to(root).as_posix(),
                     "source_sha256": hashlib.sha256(data).hexdigest(), "kind": kind,
                     "evidence_boundary": boundary,
                     "related_skills": RELATIONS.get(name, []),
                     "files": files,
                     "reading_order": list(dict.fromkeys(["PRIMER.md", "skills/infinityblade/SKILL.md", path.relative_to(root).as_posix()]))})
    names = {row["name"] for row in rows}
    if not rows:
        raise ValueError("No skill entrypoints discovered")
    if len(names) != len(rows):
        raise ValueError("Duplicate skill names")
    for row in rows:
        if set(row["related_skills"]) - names:
            raise ValueError(f"Unknown related skill in registry: {row['name']}")
        for relative in row["reading_order"]:
            target = root / relative
            if not target.is_file() or target.is_symlink() or not target.resolve().is_relative_to(root):
                raise ValueError(f"Required reading resource is missing or redirected: {relative}")
    return {"schema_version": 1, "purpose": "Derived discovery metadata and explicit capability boundaries; source SKILL.md files remain authoritative.",
            "generated_by": "python3 tools/validate_repo.py --write-registry",
            "runtime_dependency_declaration": "skills/runtime-dependencies.json",
            "skill_count": len(rows), "skills": rows}


def without_fences(text):
    lines, fenced = [], None
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)[0]
            if fenced is None:
                fenced = marker
            elif marker == fenced:
                fenced = None
            lines.append("")
        else:
            lines.append("" if fenced else line)
    return "\n".join(lines)


def heading_slugs(path):
    """GitHub-style heading anchors for one Markdown file, deduplicated."""
    slugs, seen = set(), {}
    for line in without_fences(path.read_text(encoding="utf-8")).splitlines():
        heading = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
        if not heading:
            continue
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading.group(1))
        slug = re.sub(r"[^a-z0-9 _-]", "", text.lower()).replace(" ", "-")
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        slugs.add(slug if count == 0 else f"{slug}-{count}")
    return slugs


def markdown_links(root, path):
    """File and fragment checks, not a complete Markdown parser or remote-link check."""
    text = without_fences(path.read_text(encoding="utf-8"))
    links, errors = [], []
    slug_cache = {}
    pattern = re.compile(r"(?<!!)\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)")
    for match in pattern.finditer(text):
        target = match.group(1).strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            continue
        line = text.count("\n", 0, match.start()) + 1
        row = {"source": path.relative_to(root).as_posix(), "line": line, "target": target}
        if not parsed.path:
            resolved = path
        else:
            resolved = (path.parent / unquote(parsed.path)).resolve()
            if not resolved.is_relative_to(root):
                errors.append({**row, "reason": "local link escapes repository"})
                continue
            if not resolved.exists():
                errors.append({**row, "reason": "missing local target"})
                continue
        links.append(row)
        if parsed.fragment and resolved.suffix.lower() == ".md":
            if resolved not in slug_cache:
                slug_cache[resolved] = heading_slugs(resolved)
            if unquote(parsed.fragment) not in slug_cache[resolved]:
                errors.append({"kind": "local_markdown_fragment", **row,
                               "reason": "fragment matches no heading in target"})
    return links, errors


def index_count_errors(root, expected):
    """The skills index table must state each folder's true file count.

    The registry is derived from the tree, so it is the authority here: a
    hand-maintained count in INDEX.md that disagrees with the discovered
    files is a false completeness claim, and a missing or extra row breaks
    the index's contract that every library skill is listed exactly once.
    The core skill is governed by the doctrine itself and is not a library
    row. When no index exists the check is silent: minimal fixture trees
    are not required to carry one.
    """
    path = root / "skills/INDEX.md"
    if not path.exists():
        return []
    text = regular_text(path)
    counts = {row["name"]: len(row["files"]) for row in expected["skills"]}
    seen = {}
    errors = []
    for name, count in re.findall(r"\|\s*\[([a-z0-9-]+)/\]\(\1/\)\s*\|\s*(\d+)\s*\|", text):
        if name in seen:
            errors.append({"kind": "skills_index_rows", "skill": name, "reason": "duplicate index row"})
            continue
        seen[name] = int(count)
        if name not in counts:
            errors.append({"kind": "skills_index_rows", "skill": name, "reason": "index row names an unknown skill"})
        elif seen[name] != counts[name]:
            errors.append({"kind": "skills_index_count", "skill": name,
                           "index_count": seen[name], "actual_count": counts[name]})
    expected_rows = set(counts) - {"infinityblade"}
    if set(seen) != expected_rows:
        errors.append({"kind": "skills_index_rows",
                       "missing": sorted(expected_rows - set(seen)),
                       "extra": sorted(set(seen) - expected_rows)})
    return errors


ENTRY_CONTRACT_DOORS = ("skills/infinityblade/SKILL.md", "PRIMER.md", "README.md", "INSTALL.md")
ENTRY_CONTRACT_VERBS = ("teaching", "summarizing", "extending", "editing")


def entry_contract_errors(root):
    """Every door that states the full-read trigger must state it in full.

    The entry contract is repeated in the core, the primer, the README and
    the install guide because each is an entry point. A door that truncates
    the trigger list (citing, teaching, summarizing, extending, editing)
    quietly narrows when the deep read is required, and hand-synced copies
    drift exactly there. Any sentence invoking the trigger is checked;
    doors that do not state it are silent.
    """
    errors = []
    for relative in ENTRY_CONTRACT_DOORS:
        path = root / relative
        if not path.exists():
            continue
        text = regular_text(path)
        for match in re.finditer(r"[^.]*\bciting\b[^.]*\.", text):
            sentence = match.group(0)
            missing = [verb for verb in ENTRY_CONTRACT_VERBS if verb not in sentence]
            if missing:
                errors.append({"kind": "entry_contract_triggers", "path": relative,
                               "missing": missing})
    return errors


def validate(root, check_registry=True):
    root = Path(root).resolve()
    errors, local_links, parsed_python, markdown_files = [], 0, 0, 0
    try:
        expected = discover(root)
    except (ValueError, UnicodeError, OSError) as error:
        return {"passed": False, "errors": [{"kind": "skill_metadata", "reason": str(error)}]}
    try:
        runtime_dependencies(root, {s["name"] for s in expected["skills"]})
    except (OSError, ValueError) as error:
        errors.append({"kind": "runtime_dependency_declaration", "reason": str(error)})
    try:
        errors.extend(index_count_errors(root, expected))
    except (OSError, ValueError) as error:
        errors.append({"kind": "skills_index", "reason": str(error)})
    try:
        errors.extend(entry_contract_errors(root))
    except (OSError, ValueError) as error:
        errors.append({"kind": "entry_contract", "reason": str(error)})
    for path in source_files(root):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            errors.append({"kind": "symlink_source", "path": rel})
            continue
        if not stat.S_ISREG(path.stat().st_mode):
            errors.append({"kind": "nonregular_source", "path": rel})
            continue
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=rel)
                parsed_python += 1
            except (SyntaxError, UnicodeError) as error:
                errors.append({"kind": "python_syntax", "path": rel, "reason": str(error)})
        if path.suffix.lower() == ".md":
            markdown_files += 1
            good, bad = markdown_links(root, path)
            local_links += len(good)
            errors.extend({"kind": "local_markdown_link", **e} for e in bad)
    if check_registry:
        path = root / REGISTRY_PATH
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("Refusing redirected skill registry")
            actual = json.loads(regular_text(path))
            if actual != expected:
                errors.append({"kind": "stale_skill_registry", "repair": "python3 tools/validate_repo.py --write-registry"})
        except (OSError, ValueError) as error:
            errors.append({"kind": "missing_or_invalid_skill_registry", "reason": str(error)})
    return {"passed": not errors, "skill_count": expected["skill_count"],
            "markdown_files_checked": markdown_files, "local_file_links_checked": local_links,
            "python_files_parsed_without_execution": parsed_python, "errors": errors,
            "limits": ["Local file targets and heading fragments only; remote URL availability is not tested.",
                       "Metadata validation supports the repository's string-scalar frontmatter subset, not arbitrary YAML.",
                       "Syntax and metadata checks are not behavior, host installation, runtime or trading proof."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write-registry", action="store_true", help="Explicitly regenerate only skills/registry.json")
    parser.add_argument("--skip-registry", action="store_true", help="Audit structure while building a new registry")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.write_registry:
            data = discover(root)
            path = root / REGISTRY_PATH
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("Refusing redirected registry destination")
            if path.exists() and not stat.S_ISREG(path.stat().st_mode):
                raise ValueError("Registry destination must be a regular file")
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({"written": REGISTRY_PATH, "skill_count": data["skill_count"]}))
            return 0
        result = validate(root, not args.skip_registry)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
