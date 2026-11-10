"""The validator enforces the entry pair's word budget.

Amendment A2 of the 3.4.0 adoption replaced the 220-line core cap with a
word budget on the mandatory entry pair (PRIMER.md plus the core skill),
because lines are not the cost a reader pays. These tests pin the guard
both ways: the small fixture pair passes, and a fixture pair inflated
past the budget fails with the counted words named.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

TOOLS = next(p / "tools" for p in Path(__file__).resolve().parents if (p / "tools/validate_repo.py").is_file())
spec = importlib.util.spec_from_file_location("validate_repo", TOOLS / "validate_repo.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


FIXTURE_SKILLS = (
    "infinityblade", "efficiency-breakthroughs", "proof-before-green",
    "memory-recall-systems", "gate-test-integrity", "live-execution-proof",
    "save-readback-verification", "stable-tree-gate-integrity",
    "hermetic-test-isolation",
)


def build_fixture(base):
    """A minimal tree that passes validation on its own merits."""
    repo = Path(base) / "repo"
    (repo / "PRIMER.md").parent.mkdir(parents=True, exist_ok=True)
    (repo / "PRIMER.md").write_text("# Fixture primer\n", encoding="utf-8")
    for name in FIXTURE_SKILLS:
        skill = repo / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Fixture skill for gate tests.\n---\n\n# Fixture\n",
            encoding="utf-8")
    (repo / "skills" / "runtime-dependencies.json").write_text(
        json.dumps({"schema_version": 1, "skills": {}}), encoding="utf-8")
    tools = repo / "tools"
    tools.mkdir()
    (tools / "fixture_tool.py").write_text("VALUE = 1\n", encoding="utf-8")
    registry = validator.discover(repo)
    (repo / "skills" / "registry.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return repo


class EntryPairWordBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = build_fixture(self.temp.name)

    def test_small_fixture_pair_is_within_budget(self):
        self.assertEqual(validator.entry_pair_word_budget_errors(self.repo), [])
        result = validator.validate(self.repo)
        self.assertTrue(result["passed"], result["errors"])

    def test_pair_over_budget_fails_with_the_count_named(self):
        primer = self.repo / "PRIMER.md"
        primer.write_text("word " * (validator.ENTRY_PAIR_WORD_BUDGET + 1),
                          encoding="utf-8")
        found = validator.entry_pair_word_budget_errors(self.repo)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["kind"], "entry_pair_word_budget")
        self.assertGreater(found[0]["words"], validator.ENTRY_PAIR_WORD_BUDGET)
        result = validator.validate(self.repo)
        self.assertFalse(result["passed"])
        kinds = [row["kind"] for row in result["errors"]]
        self.assertIn("entry_pair_word_budget", kinds)

    def test_budget_counts_both_files_of_the_pair(self):
        half = validator.ENTRY_PAIR_WORD_BUDGET // 2 + 1
        (self.repo / "PRIMER.md").write_text("word " * half, encoding="utf-8")
        core = self.repo / "skills" / "infinityblade" / "SKILL.md"
        core.write_text(core.read_text(encoding="utf-8") + "word " * half,
                        encoding="utf-8")
        found = validator.entry_pair_word_budget_errors(self.repo)
        self.assertEqual(len(found), 1)


if __name__ == "__main__":
    unittest.main()
