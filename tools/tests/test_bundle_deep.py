"""Source-export contracts on disposable repositories and synthetic archives.

Git index writes occur only inside TemporaryDirectory fixtures. Nothing is
installed, imported from an archive, executed from source, or fetched remotely.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

TOOLS = Path(__file__).resolve().parents[1]
with patch.object(sys, "path", [str(TOOLS), *sys.path]):
    spec = importlib.util.spec_from_file_location("deep_bundle", TOOLS / "build_bundle.py")
    bundle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bundle)
    import validate_repo as validator


class BundleFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bundle-contract-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.write("LICENSE", b"Fixture source license\n")
        self.write("PRIMER.md", b"# Fixture primer\n")
        names = {"infinityblade", "example"} | set(validator.RELATIONS)
        names.update(name for related in validator.RELATIONS.values() for name in related)
        for name in names:
            self.write(f"skills/{name}/SKILL.md", f"---\nname: {name}\ndescription: Fixture {name}\nversion: 1.0.0\n---\n# {name}\n".encode())
        self.write("skills/runtime-dependencies.json", b'{"schema_version":1,"skills":{}}')
        self.write("scripts/example.sh", b"#!/bin/sh\nexit 9\n", 0o755)
        self.write("never_execute.py", b"raise RuntimeError('source must not execute')\n")
        self.write("empty.txt", b"")
        self.refresh_registry()

    def write(self, relative, data, mode=0o644):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode)
        return path

    def refresh_registry(self):
        self.write(validator.REGISTRY_PATH, json.dumps(validator.discover(self.root)).encode())

    def git(self, *args, input=None):
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                           GIT_TEMPLATE_DIR=str(self.base / "empty-git-template"))
        (self.base / "empty-git-template").mkdir(exist_ok=True)
        result = subprocess.run(["git", "-C", str(self.root), *args], input=input,
                                capture_output=True, env=environment, check=True)
        return result.stdout

    def tracked(self):
        self.git("init", "-q")
        self.git("add", ".")

    def build(self, name="bundle.zip", **kwargs):
        output = self.base / name
        result = bundle.build_bundle(self.root, ["infinityblade"], output, **kwargs)
        return output, result

    def archive_parts(self, path):
        with zipfile.ZipFile(path) as archive:
            return ({item.filename: archive.read(item.filename) for item in archive.infolist()},
                    {item.filename: item.external_attr for item in archive.infolist()})

    def write_archive(self, path, contents, attributes=None):
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in contents.items():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (attributes or {}).get(name, (stat.S_IFREG | 0o644) << 16)
                archive.writestr(info, data)

    def mutate_manifest(self, change):
        output, _ = self.build()
        contents, attributes = self.archive_parts(output)
        manifest = json.loads(contents[bundle.MANIFEST])
        change(manifest)
        contents[bundle.MANIFEST] = json.dumps(manifest).encode()
        changed = self.base / "changed.zip"
        self.write_archive(changed, contents, attributes)
        return changed


class BundleSuccessTests(BundleFixture):
    def test_extracted_bundle_round_trip_retains_binary_assets_and_modes(self):
        self.write("assets/fixture.db", b"authored binary source")
        self.write("assets/fixture.zip", b"nested authored archive")
        self.tracked()
        original, _ = self.build("original.zip")
        extracted = self.base / "extracted"
        with zipfile.ZipFile(original) as archive:
            archive.extractall(extracted)
        # Python's ordinary extraction does not restore Unix executable bits.
        (extracted / "scripts/example.sh").chmod(0o644)
        (extracted / "private-unlisted.txt").write_text("fixture must not export")
        repeated = self.base / "repeated.zip"
        bundle.build_bundle(extracted, ["infinityblade"], repeated)
        self.assertEqual(original.read_bytes(), repeated.read_bytes())
        self.assertTrue(bundle.verify_bundle(repeated)["file_modes_verified"])

    def test_full_source_is_deterministic_and_binds_executable_modes(self):
        first, report = self.build("first.zip")
        second, _ = self.build("second.zip")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertFalse(report["external_behavior_verified"])
        with zipfile.ZipFile(first) as archive:
            manifest = json.loads(archive.read(bundle.MANIFEST))
            expected = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
            self.assertEqual(set(archive.namelist()), set(expected) | {bundle.MANIFEST})
            for name, data in expected.items():
                self.assertEqual(archive.read(name), data)
            self.assertEqual(stat.S_IMODE(archive.getinfo("scripts/example.sh").external_attr >> 16), 0o755)
            self.assertEqual(next(r["mode"] for r in manifest["files"] if r["path"] == "scripts/example.sh"), 0o755)
        result = bundle.verify_bundle(first)
        self.assertTrue(result["verified"])
        self.assertTrue(result["file_modes_verified"])
        self.assertFalse(result["source_authenticity_verified"])

    def test_git_inventory_keeps_binary_source_and_ignores_untracked_state(self):
        self.write("assets/fixture.db", b"authored binary fixture\x00")
        self.write("assets/fixture.zip", b"archival source fixture")
        self.write("node_modules/authored.txt", b"explicitly tracked source")
        self.tracked()
        expected = set(self.git("ls-files", "-z").decode().rstrip("\0").split("\0"))
        self.write("skills/example/private-untracked.txt", b"do not export fixture")
        self.write("private-untracked.md", b"[invalid](missing-and-private.md)\n")
        self.write("broken-untracked.py", b"not valid Python !\n")
        (self.root / "untracked-directory-link").symlink_to(self.base, target_is_directory=True)
        output, _ = self.build()
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()), expected | {bundle.MANIFEST})
            self.assertEqual(archive.read("assets/fixture.db"), b"authored binary fixture\x00")
            self.assertEqual(archive.read("node_modules/authored.txt"), b"explicitly tracked source")

    def test_git_index_mode_survives_filesystem_permission_loss(self):
        self.tracked()
        (self.root / "scripts/example.sh").chmod(0o644)
        output, _ = self.build()
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(stat.S_IMODE(archive.getinfo("scripts/example.sh").external_attr >> 16), 0o755)

    def test_legacy_complete_manifest_remains_readable_with_limited_mode_claim(self):
        changed = self.mutate_manifest(lambda value: (value.update(schema_version=1), [row.pop("mode") for row in value["files"]]))
        report = bundle.verify_bundle(changed)
        self.assertTrue(report["verified"])
        self.assertFalse(report["file_modes_verified"])

    def test_runtime_checks_do_not_execute_external_source_or_embed_host_state(self):
        external = self.base / "external.py"
        external.write_text("raise RuntimeError('must not execute external source')\n")
        declaration = {"schema_version": 1, "skills": {"infinityblade": {
            "required": [{"id": "external-fixture", "kind": "external-source", "environment": "BUNDLE_TEST_EXTERNAL", "required_for": "fixture", "verification": "syntax only"},
                         {"id": "env-fixture", "kind": "environment", "environment": "BUNDLE_TEST_TOKEN", "required_for": "fixture", "verification": "configured"}], "optional": []}}}
        self.write("skills/runtime-dependencies.json", json.dumps(declaration).encode())
        with patch.dict(os.environ, {"BUNDLE_TEST_EXTERNAL": str(external), "BUNDLE_TEST_TOKEN": ""}):
            with self.assertRaisesRegex(ValueError, "unresolved runtime.*env-fixture"):
                self.build(require_runtime=True)
            with patch.dict(os.environ, {"BUNDLE_TEST_TOKEN": "fixture-configured"}):
                first, report = self.build("ready.zip", require_runtime=True)
            with patch.dict(os.environ, {"BUNDLE_TEST_TOKEN": "different-fixture"}):
                second, _ = self.build("same-source.zip", require_runtime=True)
        self.assertEqual(report["unresolved_required"], 0)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertNotIn(str(external).encode(), first.read_bytes())
        self.assertNotIn(b"fixture-configured", first.read_bytes())


class BundleSourceAdversaries(BundleFixture):
    def test_extracted_manifest_cannot_redirect_source_outside_root(self):
        output, _ = self.build()
        extracted = self.base / "extracted"
        with zipfile.ZipFile(output) as archive:
            archive.extractall(extracted)
        manifest_path = extracted / bundle.MANIFEST
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][0]["path"] = "../private.txt"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "malformed bundle source record"):
            bundle.collect_sources(extracted)

    def test_missing_tracked_source_and_unmerged_index_are_not_partial_success(self):
        self.tracked()
        original = (self.root / "PRIMER.md").read_bytes()
        (self.root / "PRIMER.md").unlink()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.build()
        self.write("PRIMER.md", original)
        oid = self.git("hash-object", "PRIMER.md").decode().strip()
        self.git("update-index", "--index-info", input=("0 " + "0" * 40 + "\tPRIMER.md\n100644 " + oid + " 1\tPRIMER.md\n").encode())
        with self.assertRaisesRegex(ValueError, "resolved regular Git entries"):
            self.build()

    def test_required_artifact_and_reserved_manifest_cannot_disappear(self):
        for required in sorted(bundle.REQUIRED_SOURCES):
            path = self.root / required
            data = path.read_bytes()
            path.unlink()
            try:
                with self.assertRaisesRegex(ValueError, "required artifact"):
                    bundle.collect_sources(self.root)
            finally:
                path.write_bytes(data)
        self.write(bundle.MANIFEST, b"{}")
        self.tracked()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            bundle.collect_sources(self.root)

    def test_tracked_symlink_parent_or_file_is_rejected(self):
        self.tracked()
        original = self.root / "scripts/example.sh"
        original.unlink()
        original.symlink_to(self.root / "never_execute.py")
        with self.assertRaisesRegex(ValueError, "redirected"):
            bundle.collect_sources(self.root)
        original.unlink()
        self.write("scripts/example.sh", b"fixture", 0o755)
        (self.root / "scripts").rename(self.root / "untracked-target")
        (self.root / "scripts").symlink_to(self.root / "untracked-target", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "redirected"):
            bundle.collect_sources(self.root)

    def test_git_environment_cannot_redirect_to_another_index(self):
        self.tracked()
        expected = bundle.collect_sources(self.root)
        with patch.dict(os.environ, {"GIT_DIR": str(self.base / "missing-private-repo"), "GIT_INDEX_FILE": str(self.base / "missing-index")}):
            self.assertEqual(bundle.collect_sources(self.root), expected)

    def test_source_change_preserves_prior_output_and_removes_temporary_archive(self):
        output = self.base / "bundle.zip"
        output.write_bytes(b"prior published artifact")
        original_validate = bundle.validate
        def validation_with_writer(snapshot, **kwargs):
            result = original_validate(snapshot, **kwargs)
            with (self.root / "PRIMER.md").open("ab") as handle:
                handle.write(b"new source after snapshot\n")
            return result
        with patch.object(bundle, "validate", side_effect=validation_with_writer), self.assertRaisesRegex(ValueError, "source changed"):
            self.build()
        self.assertEqual(output.read_bytes(), b"prior published artifact")
        self.assertEqual(list(self.base.glob(".bundle.zip.*")), [])

    def test_excluded_linked_asset_is_explicit_and_in_tree_output_is_refused(self):
        self.write("fixture.db", b"asset")
        self.write("README.md", b"[Asset](fixture.db)\n")
        with self.assertRaisesRegex(ValueError, "referenced local asset excluded"):
            self.build()
        with self.assertRaisesRegex(ValueError, "outside the source tree"):
            bundle.build_bundle(self.root, ["infinityblade"], self.root / "nested.zip")


class BundleManifestAdversaries(BundleFixture):
    def test_empty_or_falsely_complete_manifests_are_rejected(self):
        target = self.base / "false.zip"
        for value in (False, [], {}, {"schema_version": 1, "files": []}):
            self.write_archive(target, {bundle.MANIFEST: json.dumps(value).encode()})
            with self.subTest(value=value), self.assertRaises(ValueError):
                bundle.verify_bundle(target)
        data = b"fixture"
        false = {"schema_version": 1, "distribution": "complete-repository-source", "files": [{"path": "README.md", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}]}
        self.write_archive(target, {bundle.MANIFEST: json.dumps(false).encode(), "README.md": data})
        with self.assertRaisesRegex(ValueError, "mandatory"):
            bundle.verify_bundle(target)

    def test_schema_shapes_inventory_and_entrypoint_claims_are_strict(self):
        changes = [lambda m: m.update(schema_version=True), lambda m: m.update(files=False),
                   lambda m: m["files"][0].update(bytes=True), lambda m: m["files"][0].update(sha256="g" * 64),
                   lambda m: m["files"][0].update(mode=True), lambda m: m["files"][0].update(mode=0o4755),
                   lambda m: m.update(selected_entrypoints=[]),
                   lambda m: m.update(selected_entrypoints=["skills/example/SKILL.md", "skills/example/SKILL.md"]),
                   lambda m: m.update(selected_entrypoints=["skills/missing/SKILL.md"]),
                   lambda m: m.update(runtime_dependency_declaration="wrong.json"),
                   lambda m: m.update(distribution="not-source"), lambda m: m["files"].append(dict(m["files"][0]))]
        for index, change in enumerate(changes):
            with self.subTest(case=index), self.assertRaises(ValueError):
                bundle.verify_bundle(self.mutate_manifest(change))

    def test_hash_size_mode_and_undeclared_members_are_verified(self):
        output, _ = self.build()
        contents, attributes = self.archive_parts(output)
        changed = self.base / "changed.zip"
        self.write_archive(changed, {**contents, "PRIMER.md": b"tampered"}, attributes)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            bundle.verify_bundle(changed)
        self.write_archive(changed, contents, {**attributes, "scripts/example.sh": (stat.S_IFREG | 0o644) << 16})
        with self.assertRaisesRegex(ValueError, "mode mismatch"):
            bundle.verify_bundle(changed)
        self.write_archive(changed, {**contents, "undeclared.txt": b"extra"}, attributes)
        with self.assertRaisesRegex(ValueError, "inventory"):
            bundle.verify_bundle(changed)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            bundle.verify_bundle(self.mutate_manifest(lambda m: m["files"][0].update(bytes=m["files"][0]["bytes"] + 1)))

    def test_duplicate_json_keys_and_duplicate_casefolded_members_are_rejected(self):
        output, _ = self.build()
        contents, attributes = self.archive_parts(output)
        text = contents[bundle.MANIFEST].decode()
        contents[bundle.MANIFEST] = (text[:1] + '"schema_version": 1,' + text[1:]).encode()
        changed = self.base / "duplicate.zip"
        self.write_archive(changed, contents, attributes)
        with self.assertRaisesRegex(ValueError, "duplicate JSON"):
            bundle.verify_bundle(changed)
        shutil.copyfile(output, changed)
        with zipfile.ZipFile(changed, "a") as archive:
            archive.writestr("license", b"case collision")
        with self.assertRaisesRegex(ValueError, "duplicate archive"):
            bundle.verify_bundle(changed)

    def test_unsafe_member_paths_and_special_files_are_rejected(self):
        target = self.base / "unsafe.zip"
        for name in ("../outside", "/absolute", "a/../b", "a/./b", "a//b", "a\\b", "C:drive", "directory/"):
            self.write_archive(target, {name: b"fixture"})
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "unsafe"):
                bundle.verify_bundle(target)
        for mode in (stat.S_IFLNK | 0o777, stat.S_IFIFO | 0o644, stat.S_IFCHR | 0o644):
            self.write_archive(target, {"fixture": b"data"}, {"fixture": mode << 16})
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, "unsafe"):
                bundle.verify_bundle(target)

    def test_advertised_oversized_member_is_rejected_before_decompression(self):
        target = self.base / "oversized.zip"
        self.write_archive(target, {"fixture": b"x"})
        data = bytearray(target.read_bytes())
        offset = data.index(b"PK\x01\x02")
        struct.pack_into("<I", data, offset + 24, 2_000_000_001)
        target.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "resource bounds"):
            bundle.verify_bundle(target)


if __name__ == "__main__":
    unittest.main()
