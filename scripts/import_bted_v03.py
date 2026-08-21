#!/usr/bin/env python3
"""Validate a BTED canonical release and emit a deterministic import plan.

This command is intentionally read-only.  It does not connect to PostgreSQL,
create tables, or modify any release file.

Examples::

    python3 scripts/import_bted_v03.py validate \
        --release-root data/public/v0.2.0
    python3 scripts/import_bted_v03.py validate \
        --release-root data/public/v0.2.0 --plan-json /tmp/bted-plan.json
    python3 scripts/import_bted_v03.py materialize \
        --release-root data/public/v0.2.0 \
        --output-dir /tmp/bted-v03-staging \
        --asset-origin-base https://example.test/assets \
        --generated-at-utc 2026-08-21T00:00:00Z
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
from backend.importer.materialize import MaterializationError, materialize_release  # noqa: E402


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
    validate.add_argument(
        "--contig-registry",
        default=None,
        help=(
            "reference contig provenance TSV; defaults to "
            "data/registry/reference_contigs.v0.2.0.tsv under --repo-root"
        ),
    )
    materialize = subparsers.add_parser(
        "materialize",
        help="在不连接数据库的情况下生成确定性的 JSONL 写库前 staging bundle",
    )
    materialize.add_argument(
        "--release-root",
        default="data/public/v0.2.0",
        help="release root containing release_manifest.json (default: data/public/v0.2.0)",
    )
    materialize.add_argument(
        "--repo-root",
        default=None,
        help="repository root; defaults to the conventional parent of --release-root",
    )
    materialize.add_argument(
        "--contig-registry",
        default=None,
        help="reference contig provenance TSV; defaults to the tracked registry",
    )
    materialize.add_argument(
        "--output-dir",
        required=True,
        help="new or empty directory for the materialization bundle; non-empty directories are refused",
    )
    materialize.add_argument(
        "--asset-origin-base",
        required=True,
        help="HTTPS-only planned origin prefix; no remote request is made",
    )
    materialize.add_argument(
        "--generated-at-utc",
        default=None,
        help="fixed ISO-8601 timestamp for reproducible output (default: current UTC time)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        report = validate_release(
            args.release_root,
            repo_root=args.repo_root,
            contig_registry=args.contig_registry,
        )
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
    if args.command == "materialize":
        try:
            result = materialize_release(
                args.release_root,
                repo_root=args.repo_root,
                contig_registry=args.contig_registry,
                output_dir=args.output_dir,
                asset_origin_base=args.asset_origin_base,
                generated_at_utc=args.generated_at_utc,
            )
        except MaterializationError as exc:
            json.dump({"ok": False, "error": str(exc)}, sys.stderr, ensure_ascii=False)
            sys.stderr.write("\n")
            return 1
        json.dump(
            {"ok": True, "output_dir": str(result.output_dir), "manifest": result.manifest},
            sys.stdout,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        sys.stdout.write("\n")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
