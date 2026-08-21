#!/usr/bin/env python3
"""Prepare checksum-verified public BTED asset objects for a future object store.

Only inventory rows explicitly marked both public and redistributable are
selected.  This command never uploads anything and never overwrites a non-empty
output directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INVENTORY = REPO_ROOT / "data/registry/jbrowse_assets.v0.2.0.tsv"
DEFAULT_RELEASE = REPO_ROOT / "data/public/v0.2.0"
DEFAULT_BUNDLE = REPO_ROOT.parent / "bted-v0.2/dist/BTED-v0.2.0-jbrowse"
MANIFEST_NAME = "ASSET_OBJECTS.json"
CHECKSUM_NAME = "SHA256SUMS.txt"
GENERATOR_VERSION = "bted-public-asset-objects-0.1.0"
ALLOWED_ROLES = {
    "canonical_endpoints",
    "reference_fasta",
    "reference_fai",
    "reference_gff3",
    "reference_tbi",
    "raw_bigwig_forward",
    "raw_bigwig_reverse",
}


class AssetPreparationError(ValueError):
    """Raised when an inventory or source asset cannot be prepared safely."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative(value: str, *, field: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise AssetPreparationError(f"unsafe {field}: {value!r}")
    return path


def _source_path(row: dict[str, str], bundle: Path, release_root: Path) -> tuple[str, Path, str]:
    bundle_path = row.get("bundle_path", "").strip()
    canonical_path = row.get("canonical_path", "").strip()
    if bool(bundle_path) == bool(canonical_path):
        raise AssetPreparationError(
            f"{row.get('asset_id', '<unknown>')}: expected exactly one source path"
        )
    if bundle_path:
        relative = _safe_relative(bundle_path, field="bundle_path")
        return "jbrowse_bundle", bundle / relative, relative.as_posix()
    relative = _safe_relative(canonical_path, field="canonical_path")
    return "canonical_release", release_root / relative, relative.as_posix()


def _validate_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise AssetPreparationError(f"output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise AssetPreparationError(f"output directory must be empty: {output_dir}")


def prepare_public_asset_objects(
    *,
    inventory_path: Path = DEFAULT_INVENTORY,
    bundle: Path = DEFAULT_BUNDLE,
    release_root: Path = DEFAULT_RELEASE,
    output_dir: Path,
    manifest_only: bool = False,
) -> dict[str, Any]:
    """Validate selected assets and write a deterministic upload-ready layout."""

    _validate_output_dir(output_dir)
    with inventory_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    selected = [
        row
        for row in rows
        if row.get("is_public") == "true"
        and row.get("redistribution_status") == "verified_redistributable"
    ]
    selected.sort(key=lambda row: row["object_path"])
    object_paths: set[str] = set()
    objects: list[dict[str, Any]] = []
    sources: list[tuple[Path, Path]] = []

    for row in selected:
        asset_id = row["asset_id"]
        if row.get("source_id") == "BATTER_S1_002":
            raise AssetPreparationError(f"{asset_id}: audit-only source cannot be public")
        if row.get("asset_role") not in ALLOWED_ROLES:
            raise AssetPreparationError(f"{asset_id}: unsupported public asset role")
        object_relative = _safe_relative(row["object_path"], field="object_path")
        object_path = object_relative.as_posix()
        if object_path in object_paths:
            raise AssetPreparationError(f"duplicate object_path: {object_path}")
        object_paths.add(object_path)

        source_kind, source_path, source_relative = _source_path(row, bundle, release_root)
        if not source_path.is_file():
            raise AssetPreparationError(f"{asset_id}: missing source file: {source_relative}")
        actual_size = source_path.stat().st_size
        actual_sha = sha256(source_path)
        if actual_size != int(row["byte_size"]):
            raise AssetPreparationError(f"{asset_id}: byte_size mismatch")
        if actual_sha != row["sha256"]:
            raise AssetPreparationError(f"{asset_id}: sha256 mismatch")

        objects.append({
            "asset_id": asset_id,
            "release_version": row["release_version"],
            "source_id": row["source_id"] or None,
            "assembly_accession": row["assembly_accession"] or None,
            "asset_role": row["asset_role"],
            "asset_kind": row["asset_kind"],
            "object_path": object_path,
            "byte_size": actual_size,
            "sha256": actual_sha,
            "mime_type": row["mime_type"],
            "supports_range": row["supports_range"] == "true",
            "redistribution_status": row["redistribution_status"],
            "is_public": True,
            "source": {"kind": source_kind, "path": source_relative},
        })
        sources.append((source_path, object_relative))

    release_versions = sorted({item["release_version"] for item in objects})
    if len(release_versions) != 1:
        raise AssetPreparationError(f"expected one release version, found {release_versions}")

    manifest = {
        "schema_version": "1.0",
        "generator": "scripts/prepare_v03_public_asset_objects.py",
        "generator_version": GENERATOR_VERSION,
        "release_version": release_versions[0],
        "mode": "manifest_only" if manifest_only else "copy",
        "inventory": {
            "path": "data/registry/jbrowse_assets.v0.2.0.tsv",
            "sha256": sha256(inventory_path),
            "row_count": len(rows),
        },
        "selection": {
            "policy": "is_public=true AND redistribution_status=verified_redistributable",
            "selected_count": len(objects),
            "excluded_count": len(rows) - len(objects),
        },
        "objects": objects,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    if not manifest_only:
        for source_path, object_relative in sources:
            destination = output_dir / object_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination)
            if destination.stat().st_size != source_path.stat().st_size or sha256(destination) != sha256(source_path):
                raise AssetPreparationError(f"copied object verification failed: {object_relative}")

    manifest_path = output_dir / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    checksum_rows = [(sha256(manifest_path), MANIFEST_NAME)]
    if not manifest_only:
        checksum_rows.extend((item["sha256"], item["object_path"]) for item in objects)
    (output_dir / CHECKSUM_NAME).write_text(
        "".join(f"{digest}  {path}\n" for digest, path in sorted(checksum_rows, key=lambda item: item[1])),
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--jbrowse-bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--release-root", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()
    manifest = prepare_public_asset_objects(
        inventory_path=args.inventory,
        bundle=args.jbrowse_bundle,
        release_root=args.release_root,
        output_dir=args.output_dir,
        manifest_only=args.manifest_only,
    )
    print(
        f"PASS {manifest['selection']['selected_count']} public objects "
        f"({manifest['mode']}) -> {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
