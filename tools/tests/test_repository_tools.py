"""Hermetic contracts for source registry validation and lexical discovery."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_repo as validator
import skill_router


class RepositoryToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        (self.root / "PRIMER.md").write_text("# Fixture primer\n")
        names = {"infinityblade", "example"} | set(validator.RELATIONS)
        names.update(n for related in validator.RELATIONS.values() for n in related)
        for name in names:
            directory = self.root / "skills" / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Fixture {name} procedure\nversion: 1.0.0\n---\n# {name}\n")
        (self.root / "skills/runtime-dependencies.json").write_text(json.dumps({"schema_version": 1, "skills": {}}))
        self.registry()

    def registry(self):
        data = validator.discover(self.root)
        (self.root / validator.REGISTRY_PATH).write_text(json.dumps(data))
        return data

    def cli(self, function, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = function(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_registry_exact_source_and_nonexecuting_validation(self):
        script = self.root / "skills/example/must_not_run.py"
        script.write_text("raise RuntimeError('must not execute source')\n")
        data = self.registry()
        item = next(x for x in data["skills"] if x["name"] == "example")
        self.assertEqual(item["source_sha256"], hashlib.sha256((self.root / item["entrypoint"]).read_bytes()).hexdigest())
        self.assertIn("skills/example/must_not_run.py", item["files"])
        result = validator.validate(self.root)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["python_files_parsed_without_execution"], 1)
        self.assertEqual(self.registry(), data)

    def test_source_drift_refuses_router_until_regenerated(self):
        path = self.root / "skills/example/SKILL.md"
        path.write_text(path.read_text() + "\nAdditional source.\n")
        result = validator.validate(self.root)
        self.assertFalse(result["passed"])
        self.assertIn("stale_skill_registry", {e["kind"] for e in result["errors"]})
        code, _, err = self.cli(skill_router.main, ["example"])
        self.assertEqual(code, 2)
        self.assertIn("Stale registry", err)
        self.assertEqual(self.cli(validator.main, ["--write-registry"])[0], 0)
        code, out, _ = self.cli(skill_router.main, ["example"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["matches"][0]["name"], "example")

    def test_router_unknown_and_limits_are_explicit(self):
        code, out, _ = self.cli(skill_router.main, ["zzzzunmatchedzzzz"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["matches"], [])
        self.assertEqual(self.cli(skill_router.main, ["--limit", "0", "example"])[0], 2)
        code, out, _ = self.cli(skill_router.main, ["--list"])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)["matches"]), self.registry()["skill_count"])

    def test_missing_required_reading_is_rejected(self):
        (self.root / "PRIMER.md").unlink()
        with self.assertRaisesRegex(ValueError, "Required reading"):
            validator.discover(self.root)
        self.assertEqual(self.cli(validator.main, ["--write-registry"])[0], 2)

    def test_malformed_frontmatter_is_rejected(self):
        values = ['"unterminated', "'unterminated", "[unclosed", "{unclosed", "true", "has: mapping"]
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validator.frontmatter(f"---\nname: example\ndescription: {value}\n---\n")
        for content in ["no metadata", "---\nname: example", "---\nname: example\nname: duplicate\ndescription: ok\n---"]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                validator.frontmatter(content)
        self.assertEqual(validator.frontmatter("---\nname: example\ndescription: >\n  useful first\n  second line\n---")["description"], "useful first second line")

    def test_skill_path_and_resource_symlinks_are_rejected(self):
        external = Path(self.temp.name) / "private.txt"
        external.write_text("private fixture")
        link = self.root / "skills/example/linked.txt"
        link.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "symlink"):
            validator.discover(self.root)
        link.unlink()
        directory = self.root / "skills/example/redirected"
        directory.symlink_to(external.parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            validator.discover(self.root)

    def test_registry_symlink_cannot_read_or_overwrite_external_file(self):
        external = Path(self.temp.name) / "outside.json"
        original = b'{"private":"fixture"}'
        external.write_bytes(original)
        registry = self.root / validator.REGISTRY_PATH
        registry.unlink()
        registry.symlink_to(external)
        self.assertEqual(self.cli(validator.main, ["--write-registry"])[0], 2)
        self.assertEqual(self.cli(skill_router.main, ["--list"])[0], 2)
        self.assertEqual(external.read_bytes(), original)
        self.assertFalse(validator.validate(self.root)["passed"])

    def test_broken_links_syntax_and_dependency_records_fail(self):
        (self.root / "README.md").write_text("[bad](missing.md)\n[escape](../private.md)\n```md\n[example](ignored.md)\n```\n")
        (self.root / "broken.py").write_text("def broken(:\n")
        (self.root / "skills/runtime-dependencies.json").write_text('{"schema_version":1,"skills":{"unknown":{}}}')
        self.registry()
        result = validator.validate(self.root)
        kinds = [e["kind"] for e in result["errors"]]
        self.assertFalse(result["passed"])
        self.assertEqual(kinds.count("local_markdown_link"), 2)
        self.assertIn("python_syntax", kinds)
        self.assertIn("runtime_dependency_declaration", kinds)

    def write_index(self, overrides=None, omit=()):
        data = validator.discover(self.root)
        rows = []
        for item in data["skills"]:
            name = item["name"]
            if name == "infinityblade" or name in omit:
                continue
            count = (overrides or {}).get(name, len(item["files"]))
            rows.append(f"| [{name}/]({name}/) | {count} | Fixture | Fixture |")
        (self.root / "skills/INDEX.md").write_text(
            "# Skills Library Index\n\n| Skill folder | Files | Purpose | Disposition |\n"
            "|---|---|---|---|\n" + "\n".join(rows) + "\n")

    def test_skills_index_counts_and_rows_are_validated(self):
        self.write_index(overrides={"example": 99})
        result = validator.validate(self.root)
        self.assertFalse(result["passed"])
        self.assertIn("skills_index_count", {e["kind"] for e in result["errors"]})
        self.write_index(omit={"example"})
        result = validator.validate(self.root)
        self.assertFalse(result["passed"])
        self.assertIn("skills_index_rows", {e["kind"] for e in result["errors"]})
        self.write_index()
        result = validator.validate(self.root)
        self.assertTrue(result["passed"], result)

    def test_empty_skill_repository_fails(self):
        empty = Path(self.temp.name) / "empty"
        empty.mkdir()
        self.assertFalse(validator.validate(empty)["passed"])

    def test_malformed_dependency_shapes_fail_and_router_exposes_valid_requirements(self):
        path = self.root / "skills/runtime-dependencies.json"
        cases = [{"required": [{}], "optional": []},
                 {"required": [], "optional": [], "requires_skills": ["ghost"]},
                 [], {"required": [], "optional": "invalid"},
                 {"required": [{"id": "x", "kind": "local-file", "required_for": "fixture", "verification": "presence"}], "optional": []}]
        for spec in cases:
            with self.subTest(spec=spec):
                path.write_text(json.dumps({"schema_version": 1, "skills": {"example": spec}}))
                self.assertFalse(validator.validate(self.root)["passed"])
                self.assertEqual(self.cli(skill_router.main, ["example"])[0], 2)
        spec = {"required": [{"id": "oracle", "kind": "host-capability", "required_for": "fixture", "verification": "host receipt"}], "optional": [], "requires_skills": ["infinityblade"]}
        path.write_text(json.dumps({"schema_version": 1, "skills": {"example": spec}}))
        code, out, _ = self.cli(skill_router.main, ["example"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["matches"][0]["runtime_dependencies"], spec)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO fixture")
    def test_nonregular_source_is_rejected_without_reading(self):
        os.mkfifo(self.root / "blocked.py")
        result = validator.validate(self.root)
        self.assertFalse(result["passed"])
        self.assertIn("nonregular_source", {e["kind"] for e in result["errors"]})

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO fixture")
    def test_nonregular_metadata_and_registry_destination_are_rejected(self):
        for relative in ("skills/example/SKILL.md", "skills/runtime-dependencies.json", validator.REGISTRY_PATH):
            path = self.root / relative
            original = path.read_bytes()
            path.unlink()
            os.mkfifo(path)
            try:
                self.assertFalse(validator.validate(self.root)["passed"])
                self.assertEqual(self.cli(skill_router.main, ["example"])[0], 2)
                if relative != "skills/runtime-dependencies.json":
                    self.assertEqual(self.cli(validator.main, ["--write-registry"])[0], 2)
            finally:
                path.unlink()
                path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
