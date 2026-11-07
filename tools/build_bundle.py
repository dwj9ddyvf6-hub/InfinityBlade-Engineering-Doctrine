#!/usr/bin/env python3
"""Build a deterministic full-source ZIP with selected skill entrypoints.

This is a source distribution, not a drop-in standalone skill folder or
runtime installation. No imports from external source, package installation,
credential reads, network calls, or host changes are performed. Runtime
checks prove only declared local prerequisites, never external behavior.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import stat
import tempfile
import zipfile

from validate_repo import source_files, validate, runtime_dependencies

MANIFEST = "BUNDLE-MANIFEST.json"
SKIP_SUFFIXES = {".pyc", ".pyo", ".sqlite", ".sqlite3", ".db", ".zip"}


def read_dependencies(root):
    names = {path.parent.name for path in (root / "skills").glob("*/SKILL.md")}
    return runtime_dependencies(root, names)


def runtime_report(root, selected, declaration):
    """Check metadata/path presence without importing or executing dependencies."""
    pending, visited, rows = list(selected), set(), []
    skills = declaration["skills"]
    while pending:
        skill = pending.pop(0)
        if skill in visited:
            continue
        visited.add(skill)
        spec = skills.get(skill, {})
        pending.extend(spec.get("requires_skills", []))
        for necessity in ("required", "optional"):
            for dependency in spec.get(necessity, []):
                row = {"skill": skill, "id": dependency["id"], "required": necessity == "required",
                       "kind": dependency["kind"], "verification": dependency["verification"]}
                kind = dependency["kind"]
                if kind == "local-file":
                    path = root / dependency["path"]
                    row["available"] = path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root)
                elif kind == "python-distribution":
                    try:
                        row["version"] = metadata.version(dependency["distribution"])
                        row["available"] = True
                    except metadata.PackageNotFoundError:
                        row["available"] = False
                elif kind == "environment":
                    row["available"] = dependency["environment"] in os.environ
                elif kind in ("external-source", "external-directory"):
                    configured = os.environ.get(dependency["environment"])
                    path = Path(configured) if configured else None
                    if path is not None and dependency.get("relative_path"):
                        path = path / dependency["relative_path"]
                    row["available"] = bool(path and not path.is_symlink() and
                                            (path.is_dir() if kind == "external-directory" else path.is_file()))
                    if row["available"] and kind == "external-source":
                        try:
                            ast.parse(path.read_text(encoding="utf-8"), filename=dependency["id"])
                        except (OSError, SyntaxError, UnicodeError):
                            row["available"] = False
                    # Do not publish host paths, credentials, or external source bytes.
                else:
                    row["available"] = False
                rows.append(row)
    return rows


def collect_sources(root):
    root = Path(root).resolve()
    sources = {}
    for path in source_files(root):
        relative = path.relative_to(root).as_posix()
        if path.name == ".env" or path.name.startswith(".env.") and path.name not in (".env.example", ".env.sample", ".env.template") or path.suffix in (".key", ".pem", ".p12", ".pfx"):
            raise ValueError(f"potential credential artifact requires exclusion/review before source export: {relative}")
        if relative == MANIFEST or path.suffix in SKIP_SUFFIXES:
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"refusing redirected source: {relative}")
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError(f"source is not a regular file: {relative}")
        sources[relative] = path.read_bytes()
    for required in ("LICENSE", "PRIMER.md", "skills/infinityblade/SKILL.md", "skills/runtime-dependencies.json"):
        if required not in sources:
            raise ValueError(f"source bundle missing required artifact: {required}")
    return dict(sorted(sources.items()))


def build_bundle(root, selected, output, require_runtime=False):
    root, output = Path(root).resolve(), Path(output).absolute()
    if output.resolve().is_relative_to(root):
        raise ValueError("write bundles outside the source tree to avoid recursive/self-overwriting exports")
    selected = sorted(set(selected))
    if not selected:
        raise ValueError("select at least one skill entrypoint")
    for skill in selected:
        if not skill or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in skill):
            raise ValueError("skill names must be simple kebab-case identifiers")
        if not (root / "skills" / skill / "SKILL.md").is_file():
            raise ValueError(f"unknown skill: {skill}")
    sources = collect_sources(root)
    result = validate(root, check_registry=True)
    if not result["passed"]:
        raise ValueError("source validation failed: " + json.dumps(result["errors"], sort_keys=True))
    declaration = read_dependencies(root)
    runtime = runtime_report(root, selected, declaration)
    unresolved = [row for row in runtime if row["required"] and not row["available"]]
    if require_runtime and unresolved:
        raise ValueError("unresolved runtime prerequisites: " + ", ".join(row["id"] for row in unresolved))
    manifest = {"schema_version": 1, "distribution": "complete-repository-source",
                "selected_entrypoints": [f"skills/{skill}/SKILL.md" for skill in selected],
                "files": [{"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                          for path, data in sources.items()],
                "runtime_dependency_declaration": "skills/runtime-dependencies.json",
                "runtime_boundary": "Source-only archive. External runtime prerequisites are declared, not included or proven. Run --require-runtime locally for metadata/presence checks; external behavior remains unverified."}
    # Environment-specific runtime results are returned, never embedded: same source => same archive.
    payload = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + output.name + ".", dir=output.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in sorted({**sources, MANIFEST: payload}.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, data)
        # Refuse a mixed snapshot when a source writer moved during validation/export.
        if collect_sources(root) != sources:
            raise ValueError("source changed during export; rebuild from a stable tree")
        verify_bundle(temporary)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"output": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "files": len(sources), "selected_skills": selected, "runtime_checks": runtime,
            "unresolved_required": len(unresolved), "external_behavior_verified": False}


def verify_bundle(path):
    """Read back every source byte and reject duplicate/unsafe/undeclared members."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len({name.casefold() for name in names}):
            raise ValueError("duplicate archive members")
        for item in archive.infolist():
            member = Path(item.filename)
            if member.is_absolute() or ".." in member.parts or "\\" in item.filename or ":" in item.filename or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("unsafe archive member")
        manifest = json.loads(archive.read(MANIFEST))
        if manifest.get("schema_version") != 1:
            raise ValueError("unsupported bundle manifest")
        records = manifest.get("files", [])
        paths = [row["path"] for row in records]
        if len(paths) != len(set(paths)) or set(names) != set(paths) | {MANIFEST}:
            raise ValueError("archive inventory does not match manifest")
        for row in records:
            data = archive.read(row["path"])
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("bundle hash mismatch: " + row["path"])
    return {"verified": True, "source_files": len(records)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skill", action="append")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-runtime", action="store_true")
    parser.add_argument("--verify", type=Path, help="verify an existing archive without extracting or executing it")
    args = parser.parse_args(argv)
    try:
        if args.verify:
            result = verify_bundle(args.verify)
        else:
            if not args.skill or not args.output:
                parser.error("--skill and --output are required when building")
            result = build_bundle(args.root, args.skill, args.output, args.require_runtime)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
