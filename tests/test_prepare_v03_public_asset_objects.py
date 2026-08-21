"""Focused tests for preparing public v0.3 browser asset objects."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE = REPO_ROOT.parent / "bted-v0.2/dist/BTED-v0.2.0-jbrowse"
INVENTORY = REPO_ROOT / "data/registry/jbrowse_assets.v0.2.0.tsv"
RELEASE = REPO_ROOT / "data/public/v0.2.0"


def _load_module():
    path = REPO_ROOT / "scripts/prepare_v03_public_asset_objects.py"
    spec = importlib.util.spec_from_file_location("prepare_v03_public_assets", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(BUNDLE.is_dir(), "the frozen v0.2 JBrowse bundle is not available")
class TestRealPublicAssetPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()

    def test_real_inventory_selects_exactly_77_deterministic_objects(self) -> None:
        with tempfile.TemporaryDirectory() as first_temp, tempfile.TemporaryDirectory() as second_temp:
            first = Path(first_temp) / "objects"
            second = Path(second_temp) / "objects"
            manifest = self.module.prepare_public_asset_objects(
                inventory_path=INVENTORY,
                bundle=BUNDLE,
                release_root=RELEASE,
                output_dir=first,
                manifest_only=True,
            )
            self.module.prepare_public_asset_objects(
                inventory_path=INVENTORY,
                bundle=BUNDLE,
                release_root=RELEASE,
                output_dir=second,
                manifest_only=True,
            )
            self.assertEqual(manifest["selection"], {
                "policy": "is_public=true AND redistribution_status=verified_redistributable",
                "selected_count": 77,
                "excluded_count": 28,
            })
            self.assertEqual(
                (first / "ASSET_OBJECTS.json").read_bytes(),
                (second / "ASSET_OBJECTS.json").read_bytes(),
            )
            self.assertEqual(
                (first / "SHA256SUMS.txt").read_bytes(),
                (second / "SHA256SUMS.txt").read_bytes(),
            )
            serialized = json.dumps(manifest).lower()
            self.assertNotIn("batter_s1_002", serialized)
            self.assertNotIn("external_link_only", serialized)
            self.assertNotIn("candidate", serialized)
            self.assertNotIn("signed-log", serialized)
            self.assertNotIn(".config.json", serialized)
            self.assertEqual({path.name for path in first.iterdir()}, {"ASSET_OBJECTS.json", "SHA256SUMS.txt"})


class TestSmallPublicAssetCopy(unittest.TestCase):
    def test_copy_layout_checksums_and_nonempty_output_rejection(self) -> None:
        module = _load_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "bundle"
            release = root / "release"
            bundle.mkdir()
            release.mkdir()
            public_source = bundle / "reference.fna"
            excluded_source = release / "records/S1/endpoints.bed"
            excluded_source.parent.mkdir(parents=True)
            public_source.write_bytes(b">ctg\nACGT\n")
            excluded_source.write_text("ctg\t0\t1\n", encoding="utf-8")
            columns = [
                "asset_id", "release_version", "source_id", "assembly_accession", "asset_role",
                "asset_kind", "bundle_path", "canonical_path", "object_path", "byte_size", "sha256",
                "mime_type", "supports_range", "redistribution_status", "is_public",
            ]
            rows = [
                {
                    "asset_id": "public-fasta", "release_version": "v0.2.0", "source_id": "S1",
                    "assembly_accession": "GCF_TEST.1", "asset_role": "reference_fasta",
                    "asset_kind": "fasta", "bundle_path": "reference.fna", "canonical_path": "",
                    "object_path": "assemblies/GCF_TEST.1/reference/reference.fna",
                    "byte_size": str(public_source.stat().st_size), "sha256": _sha256(public_source),
                    "mime_type": "text/plain", "supports_range": "false",
                    "redistribution_status": "verified_redistributable", "is_public": "true",
                },
                {
                    "asset_id": "excluded-bed", "release_version": "v0.2.0", "source_id": "S1",
                    "assembly_accession": "GCF_TEST.1", "asset_role": "canonical_endpoints",
                    "asset_kind": "bed", "bundle_path": "", "canonical_path": "records/S1/endpoints.bed",
                    "object_path": "records/S1/endpoints.bed", "byte_size": str(excluded_source.stat().st_size),
                    "sha256": _sha256(excluded_source), "mime_type": "text/plain", "supports_range": "false",
                    "redistribution_status": "external_link_only", "is_public": "false",
                },
            ]
            inventory = root / "inventory.tsv"
            with inventory.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            output = root / "output"
            manifest = module.prepare_public_asset_objects(
                inventory_path=inventory,
                bundle=bundle,
                release_root=release,
                output_dir=output,
            )
            destination = output / "assemblies/GCF_TEST.1/reference/reference.fna"
            self.assertEqual(destination.read_bytes(), public_source.read_bytes())
            self.assertFalse((output / "records/S1/endpoints.bed").exists())
            self.assertEqual(manifest["selection"]["selected_count"], 1)
            sums = (output / "SHA256SUMS.txt").read_text(encoding="utf-8")
            self.assertIn("ASSET_OBJECTS.json", sums)
            self.assertIn("assemblies/GCF_TEST.1/reference/reference.fna", sums)
            with self.assertRaises(module.AssetPreparationError):
                module.prepare_public_asset_objects(
                    inventory_path=inventory,
                    bundle=bundle,
                    release_root=release,
                    output_dir=output,
                )


if __name__ == "__main__":
    unittest.main()
