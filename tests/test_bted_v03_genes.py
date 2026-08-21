"""Focused tests for the v0.3 GFF-derived gene query layer."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from backend.importer.materialize import materialize_release
from backend.importer.postgres import (
    BundleVerification,
    _load_assets,
    _load_genes,
    _preflight,
)

from tests.test_bted_v03_postgres import _tiny_preflight_verification


REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASE_ROOT = REPO_ROOT / "data/public/v0.2.0"
INVENTORY = REPO_ROOT / "data/registry/jbrowse_assets.v0.2.0.tsv"
DEFAULT_BUNDLE = (
    REPO_ROOT.parent / "bted-v0.2" / "dist" / "BTED-v0.2.0-jbrowse"
)
BUNDLE_ROOT = Path(
    os.environ.get("BTED_V02_JBROWSE_BUNDLE", str(DEFAULT_BUNDLE))
)


class RecordingCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def executemany(self, sql: str, params: list[tuple[Any, ...]]) -> None:
        self.calls.append((sql, len(params)))


def _gene_rows(rows: dict[str, list[dict[str, Any]]]) -> None:
    rows["assets"].append(
        {
            "asset_id": "v0.2.0--assembly-GCF_000000001.1--gff3",
            "release_version": "v0.2.0",
            "asset_kind": "gff3",
            "logical_path": "assemblies/GCF_000000001.1/reference/genes.gff3.gz",
            "origin_url": "https://example.test/gff3",
            "origin_host": "example.test",
            "byte_size": 10,
            "sha256": "b" * 64,
            "mime_type": "application/gzip",
            "supports_range": False,
            "redistribution_status": "external_link_only",
            "is_public": False,
            "assembly_id_ref": "GCF_000000001.1",
        }
    )
    rows["genes"].append(
        {
            "release_version": "v0.2.0",
            "assembly_id_ref": "GCF_000000001.1",
            "contig_id_ref": {
                "assembly_accession": "GCF_000000001.1",
                "contig_accession": "NC_000001.1",
            },
            "gene_id": "GCF_000000001.1:gene-test",
            "locus_tag": "TEST_0001",
            "gene_name": "test",
            "feature_type": "gene",
            "start_1based": 10,
            "end_1based": 20,
            "strand": "+",
            "annotation_asset_id": "v0.2.0--assembly-GCF_000000001.1--gff3",
            "annotation_sha256": "b" * 64,
            "attributes_json": {
                "ID": "gene-test",
                "Name": "test",
                "locus_tag": "TEST_0001",
            },
        }
    )


class TestBtedV03Genes(unittest.TestCase):
    def test_fake_preflight_accepts_gene_and_writer_loads_assets_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            verification = _tiny_preflight_verification(
                Path(directory) / "bundle",
                mutate=_gene_rows,
            )
            state = _preflight(verification)
            self.assertEqual(len(state.genes), 1)
            cursor = RecordingCursor()
            _load_assets(
                cursor,
                verification,
                {"S": 11},
                {"GCF_000000001.1": 22},
                batch_size=10,
            )
            _load_genes(
                cursor,
                verification,
                {"GCF_000000001.1": 22},
                {("GCF_000000001.1", "NC_000001.1"): 33},
                batch_size=10,
            )
            self.assertEqual(len(cursor.calls), 2)
            self.assertIn("INSERT INTO assets", cursor.calls[0][0])
            self.assertIn("INSERT INTO genes", cursor.calls[1][0])
            self.assertEqual(cursor.calls[1][1], 1)

    @unittest.skipUnless(
        BUNDLE_ROOT.is_dir() and INVENTORY.is_file(),
        "local v0.2 JBrowse bundle is not available on this runner",
    )
    def test_real_gff_import_counts_and_circular_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = materialize_release(
                RELEASE_ROOT,
                repo_root=REPO_ROOT,
                output_dir=Path(directory) / "bundle",
                asset_origin_base="https://example.test/assets",
                generated_at_utc="2026-08-22T00:00:00Z",
                jbrowse_asset_inventory=INVENTORY,
                jbrowse_bundle_root=BUNDLE_ROOT,
            )
            self.assertEqual(result.table_counts["contigs"], 49)
            self.assertEqual(result.table_counts["genes"], 95_437)
            self.assertEqual(result.table_counts["endpoint_gene_context"], 0)
            with (result.output_dir / "genes.jsonl").open(encoding="utf-8") as handle:
                genes = [json.loads(line) for line in handle]
            boundary = [
                row
                for row in genes
                if "_bted_coordinate_note" in row["attributes_json"]
            ]
            self.assertEqual(len(boundary), 5)
            self.assertTrue(
                all(
                    row["end_1based"]
                    > int(row["attributes_json"]["_bted_contig_length"])
                    for row in boundary
                )
            )
            with (result.output_dir / "contigs.jsonl").open(encoding="utf-8") as handle:
                contigs = [json.loads(line) for line in handle]
            extras = {
                (row["assembly_accession"], row["contig_accession"])
                for row in contigs
                if row["provenance_json"].get("source") == "jbrowse_reference_fai"
            }
            self.assertEqual(
                extras,
                {
                    ("GCF_000008685.2", "NC_000957.1"),
                    ("GCF_000008685.2", "NC_001904.1"),
                },
            )
