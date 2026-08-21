#!/usr/bin/env python3
"""Validate a BTED canonical release and emit a deterministic import plan.

This command is intentionally read-only.  It does not connect to PostgreSQL,
create tables, or modify any release file.

Examples::

    python3 scripts/import_bted_v03.py validate \
        --release-root data/public/v0.2.0
    python3 scripts/import_bted_v03.py validate \
        --release-root data/public/v0.2.0 --plan-json /tmp/bted-plan.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.importer.canonical import validate_release  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="校验 canonical release；不写数据库")
    validate.add_argument(
        "--release-root",
        default="data/public/v0.2.0",
        help="release root containing release_manifest.json (default: data/public/v0.2.0)",
    )
    validate.add_argument(
        "--repo-root",
        default=None,
        help="repository root; defaults to the conventional parent of --release-root",
    )
    validate.add_argument(
        "--plan-json",
        default=None,
        help="write the deterministic import plan to this path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "validate":
        return 2
    report = validate_release(args.release_root, repo_root=args.repo_root)
    if args.plan_json:
        plan_path = Path(args.plan_json).expanduser()
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(
            json.dumps(report.plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    json.dump(report.as_dict(), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
