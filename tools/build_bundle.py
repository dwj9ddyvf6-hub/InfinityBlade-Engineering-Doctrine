#!/usr/bin/env python3
"""Build a deterministic full-source ZIP with selected skill entrypoints.

This is a source distribution, not a drop-in standalone skill folder or
runtime installation. No imports from external source, package installation,
credential-file reads, network calls, or host installation are performed. Runtime
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
import subprocess
import tempfile
import zipfile
from urllib.parse import unquote, urlsplit

from validate_repo import source_files, validate, runtime_dependencies, markdown_links

MANIFEST = "BUNDLE-MANIFEST.json"
SKIP_SUFFIXES = {".pyc", ".pyo", ".sqlite", ".sqlite3", ".db", ".zip"}
REQUIRED_SOURCES = {"LICENSE", "PRIMER.md", "skills/infinityblade/SKILL.md", "skills/runtime-dependencies.json"}


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
                    row["available"] = bool(os.environ.get(dependency["environment"], "").strip())
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


def collect_sources(root, *, include_modes=False):
    """Read the exact Git inventory, or the declared clean-directory policy.

    Git mode bits are authoritative in a checkout, including on filesystems
    that do not expose executable bits. An extracted bundle retains its manifest
    inventory/modes, so re-export cannot drop archived binary source assets.
    Untracked state is never traversed in either inventory-backed route. A clean
    directory with neither inventory excludes known runtime/cache suffixes;
    linked excluded assets are rejected by the builder.
    """
    root = Path(root).resolve()
    tracked = None
    inherited = None
    if (root / ".git").exists():
        # Ambient GIT_DIR/INDEX_FILE overrides must not redirect this root's inventory.
        git_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        result = subprocess.run(["git", "-C", str(root), "ls-files", "--stage", "-z"], capture_output=True, env=git_env)
        if result.returncode:
            raise ValueError("cannot enumerate the Git source inventory")
        tracked = {}
        for row in result.stdout.split(b"\0"):
            if not row:
                continue
            metadata, name = row.split(b"\t", 1)
            mode, _, stage = metadata.decode().split()
            if stage != "0" or mode not in {"100644", "100755"}:
                raise ValueError("source export requires resolved regular Git entries")
            tracked[name.decode("utf-8")] = 0o755 if mode == "100755" else 0o644
    elif (root / MANIFEST).exists() or (root / MANIFEST).is_symlink():
        path = root / MANIFEST
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size > 20_000_000:
            raise ValueError("invalid extracted-bundle manifest")
        manifest = json.loads(path.read_bytes(), object_pairs_hook=_unique_json_object)
        records = _manifest_source_records(manifest)
        inherited = {row["path"]: row.get("mode") for row in records}
    sources, modes = {}, {}
    inventory = tracked if tracked is not None else inherited
    paths = (root / relative for relative in sorted(inventory)) if inventory is not None else source_files(root)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.name == ".env" or path.name.startswith(".env.") and path.name not in (".env.example", ".env.sample", ".env.template") or path.suffix in (".key", ".pem", ".p12", ".pfx"):
            raise ValueError(f"potential credential artifact requires exclusion/review before source export: {relative}")
        if relative == MANIFEST or inventory is None and path.suffix in SKIP_SUFFIXES:
            continue
        parents = path.relative_to(root).parts[:-1]
        redirected_parent = any(root.joinpath(*parents[:i]).is_symlink() for i in range(1, len(parents) + 1))
        if path.is_symlink() or redirected_parent or not path.resolve().is_relative_to(root):
            raise ValueError(f"refusing redirected source: {relative}")
        if not path.exists():
            raise ValueError(f"inventoried source is missing; source export is incomplete: {relative}")
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError(f"source is not a regular file: {relative}")
        sources[relative] = path.read_bytes()
        modes[relative] = (inventory.get(relative) if inventory is not None else None) or (0o755 if path.stat().st_mode & 0o111 else 0o644)
    if inventory is not None and set(sources) != set(inventory):
        raise ValueError("inventoried source files are missing or excluded; source export is incomplete")
    for required in sorted(REQUIRED_SOURCES):
        if required not in sources:
            raise ValueError(f"source bundle missing required artifact: {required}")
    sources = dict(sorted(sources.items()))
    return (sources, modes) if include_modes else sources


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
    sources, modes = collect_sources(root, include_modes=True)
    # A valid on-disk target is still missing if export policy omitted it.
    # Never advertise dependency closure merely because the source checkout has it.
    for relative in sources:
        if Path(relative).suffix.lower() == ".md":
            links, _ = markdown_links(root, root / relative)
            for link in links:
                target = ((root / relative).parent / unquote(urlsplit(link["target"]).path)).resolve()
                if target.is_file() and target.relative_to(root).as_posix() not in sources:
                    raise ValueError("referenced local asset excluded from bundle: " + target.relative_to(root).as_posix())
    # Validate the bytes actually being shipped. Untracked notebooks, runtime
    # state or symlinks cannot veto a valid tracked source export, nor can they
    # make an omitted registry resource appear present in the delivered tree.
    with tempfile.TemporaryDirectory(prefix="infinityblade-source-check-") as directory:
        snapshot = Path(directory)
        for relative, data in sources.items():
            destination = snapshot / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            destination.chmod(modes[relative])
        result = validate(snapshot, check_registry=True)
        if not result["passed"]:
            raise ValueError("source validation failed: " + json.dumps(result["errors"], sort_keys=True))
        declaration = read_dependencies(snapshot)
    for spec in declaration["skills"].values():
        for dependency in spec["required"] + spec["optional"]:
            if dependency["kind"] == "local-file" and dependency["path"] not in sources:
                raise ValueError("declared local dependency missing from bundle: " + dependency["path"])
    runtime = runtime_report(root, selected, declaration)
    unresolved = [row for row in runtime if row["required"] and not row["available"]]
    if require_runtime and unresolved:
        raise ValueError("unresolved runtime prerequisites: " + ", ".join(row["id"] for row in unresolved))
    manifest = {"schema_version": 2, "distribution": "complete-repository-source",
                "selected_entrypoints": [f"skills/{skill}/SKILL.md" for skill in selected],
                "files": [{"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "mode": modes[path]}
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
                info.external_attr = (stat.S_IFREG | modes.get(name, 0o644)) << 16
                archive.writestr(info, data)
        # Refuse a mixed snapshot when a source writer moved during validation/export.
        if collect_sources(root, include_modes=True) != (sources, modes):
            raise ValueError("source changed during export; rebuild from a stable tree")
        verify_bundle(temporary)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"output": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "files": len(sources), "selected_skills": selected, "runtime_checks": runtime,
            "unresolved_required": len(unresolved), "external_behavior_verified": False}


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key in bundle manifest")
        result[key] = value
    return result


def _safe_member_name(name):
    return (isinstance(name, str) and bool(name) and not Path(name).is_absolute()
            and not any(part in {"", ".", ".."} for part in name.split("/"))
            and not any(character in name for character in ("\\", ":", "\x00")))


def _manifest_source_records(manifest):
    """Validate claims before using an archive or extracted inventory."""
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] not in (1, 2):
        raise ValueError("unsupported bundle manifest")
    records = manifest.get("files", [])
    if not isinstance(records, list) or not records or len(records) > 100000:
        raise ValueError("bundle needs a nonempty bounded source inventory")
    for row in records:
        if (not isinstance(row, dict) or not _safe_member_name(row.get("path"))
                or type(row.get("bytes")) is not int or row["bytes"] < 0
                or not isinstance(row.get("sha256"), str) or len(row["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in row["sha256"])):
            raise ValueError("malformed bundle source record")
        if manifest["schema_version"] == 2 and (type(row.get("mode")) is not int or row["mode"] not in (0o644, 0o755)):
            raise ValueError("malformed bundle source mode")
        if manifest["schema_version"] == 1 and "mode" in row and (type(row["mode"]) is not int or row["mode"] not in (0o644, 0o755)):
            raise ValueError("malformed bundle source mode")
    paths = [row["path"] for row in records]
    if MANIFEST in paths or len(paths) != len({name.casefold() for name in paths}):
        raise ValueError("duplicate or reserved source inventory member")
    if not REQUIRED_SOURCES <= set(paths) or manifest.get("distribution") != "complete-repository-source":
        raise ValueError("bundle does not contain its mandatory source-layout resources")
    selected = manifest.get("selected_entrypoints")
    if (not isinstance(selected, list) or not selected
            or not all(isinstance(p, str) and p in paths and len(p.split("/")) == 3
                       and p.startswith("skills/") and p.endswith("/SKILL.md")
                       and p.split("/")[1] and all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in p.split("/")[1]) for p in selected)
            or len(selected) != len(set(selected))):
        raise ValueError("bundle selected entrypoints are missing from its source inventory")
    if manifest.get("runtime_dependency_declaration") != "skills/runtime-dependencies.json":
        raise ValueError("bundle runtime declaration is missing")
    return records


def verify_bundle(path):
    """Read back every source byte and reject duplicate/unsafe/undeclared members."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len({name.casefold() for name in names}):
            raise ValueError("duplicate archive members")
        if len(names) > 100000 or sum(x.file_size for x in archive.infolist()) > 2_000_000_000:
            raise ValueError("bundle exceeds the declared verification resource bounds")
        for item in archive.infolist():
            mode = item.external_attr >> 16
            if (not _safe_member_name(item.filename) or item.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                raise ValueError("unsafe archive member")
        if MANIFEST not in names or archive.getinfo(MANIFEST).file_size > 20_000_000:
            raise ValueError("missing or oversized bundle manifest")
        manifest = json.loads(archive.read(MANIFEST), object_pairs_hook=_unique_json_object)
        records = _manifest_source_records(manifest)
        paths = [row["path"] for row in records]
        if set(names) != set(paths) | {MANIFEST}:
            raise ValueError("archive inventory does not match manifest")
        for row in records:
            hashed, count = hashlib.sha256(), 0
            with archive.open(row["path"]) as handle:
                while block := handle.read(65536):
                    count += len(block)
                    hashed.update(block)
            if count != row["bytes"] or hashed.hexdigest() != row["sha256"]:
                raise ValueError("bundle hash mismatch: " + row["path"])
        if manifest["schema_version"] == 2:
            for row in records:
                if stat.S_IMODE(archive.getinfo(row["path"]).external_attr >> 16) != row["mode"]:
                    raise ValueError("bundle mode mismatch: " + row["path"])
    return {"verified": True, "source_files": len(records),
            "file_modes_verified": manifest["schema_version"] == 2,
            "source_authenticity_verified": False}


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
