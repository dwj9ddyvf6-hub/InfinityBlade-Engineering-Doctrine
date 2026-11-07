#!/usr/bin/env python3
"""Discover relevant source skills without loading every skill body.

This is a lexical routing aid, not a semantic model or permission engine. It
reads source-derived registry metadata and refuses a stale registry by default.
"""
import argparse
import json
from pathlib import Path
import re
import sys

from validate_repo import discover, REGISTRY_PATH, runtime_dependencies, regular_text


def route(registry, query, limit=5, dependencies=None):
    terms = set(re.findall(r"[a-z0-9]+", query.lower())) - {"a", "and", "for", "i", "in", "of", "the", "to", "with"}
    out = []
    for skill in registry["skills"]:
        matched = sorted(terms & set(re.findall(r"[a-z0-9]+", (skill["name"] + " " + skill["description"]).lower())))
        exact = query.strip().lower() == skill["name"]
        if matched or exact:
            out.append({"name": skill["name"], "description": skill["description"],
                        "kind": skill["kind"], "reading_order": skill["reading_order"],
                        "source_sha256": skill["source_sha256"], "related_skills": skill["related_skills"],
                        "runtime_dependencies": (dependencies or {}).get(skill["name"], {"required": [], "optional": []}),
                        "evidence_boundary": skill["evidence_boundary"], "matched_terms": matched,
                        "lexical_score": 1000 * exact + len(matched)})
    out.sort(key=lambda item: (-item["lexical_score"], item["name"]))
    return out[:limit]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="task keywords or exact skill name")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--list", action="store_true", help="list all skill discovery metadata")
    args = parser.parse_args(argv)
    try:
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        root = args.root.resolve()
        registry_path = root / REGISTRY_PATH
        if registry_path.is_symlink() or not registry_path.resolve().is_relative_to(root):
            raise ValueError("Refusing redirected skill registry")
        registry = json.loads(regular_text(registry_path))
        if registry != discover(root):
            raise ValueError("Stale registry; run python3 tools/validate_repo.py --write-registry")
        dependencies = runtime_dependencies(root, {s["name"] for s in registry["skills"]})["skills"]
        if args.list:
            result = [{**{k: x[k] for k in ("name", "description", "kind", "entrypoint", "evidence_boundary")},
                       "runtime_dependencies": dependencies.get(x["name"], {"required": [], "optional": []})} for x in registry["skills"]]
        elif args.query:
            result = route(registry, args.query, args.limit, dependencies)
        else:
            raise ValueError("Supply task keywords or --list")
        print(json.dumps({"skill_count": registry["skill_count"], "matches": result,
                          "routing_basis": "source metadata and lexical overlap; score is not confidence",
                          "authority": "Host and user instructions govern. Discovery neither installs nor authorizes any skill/tool."}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
