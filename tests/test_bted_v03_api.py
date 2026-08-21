"""Offline contract tests for the BTED v0.3 read API.

The service and repository tests do not require FastAPI, psycopg3, or a real
database.  The final test is skipped when the optional web runtime is absent;
that absence must not be reported as a successful FastAPI smoke test.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from typing import Any, Mapping

from backend.app.contracts import ReleaseContext, RepositoryNotFound
from backend.app.errors import ApiError
from backend.app.repository import PostgresReadRepository
from backend.app.service import PUBLIC_EVIDENCE, ReadService
from backend.importer.canonical import V02_ENDPOINT_COLUMNS


RELEASE = ReleaseContext("v0.3.0", "published", "a" * 64, 17)
ASSEMBLY = "GCF_000739105.1"
CONTIG = "CP009124.1"
END_ID = "BTED_S1_007_CP009124_plus_67368"


def _source(source_id: str, *, audit: bool = False) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "release_status": "audit_only" if audit else "published_standardized",
        "species": "Escherichia coli str. K-12",
        "phylum": "Proteobacteria",
        "assay_family": "Term-seq",
        "evidence_class": "NA" if audit else "author_called_endpoint",
        "record_count": 0 if audit else 1,
        "used_for_batter_augmentation": False,
        "has_jbrowse": False if audit else True,
        "manifest_sha256": "b" * 64,
        "manifest_path": f"records/{source_id}/manifest.json",
        "redistribution_status": "audit_only" if audit else "external_link_only",
        "accessibility_status": "public",
        "coordinate_status": "verified",
        "processing_status": "standardized",
        "source_note": "audit source" if audit else "",
        "publication": {
            "pmid": "12345678", "doi": "10.1000/test", "pmc": "PMC1234567",
            "year": 2020, "journal": "Test journal", "title": "Test paper",
        },
        "assembly": {"accession": ASSEMBLY, "name": "test", "organism_name": "Escherichia coli", "strain": "K-12"},
        "accessions": [{"namespace": "GEO", "accession": "GSE123", "type": "study"}],
        "assets": [
            {"asset_id": f"{source_id}--manifest", "asset_kind": "metadata", "logical_path": f"records/{source_id}/manifest.json"},
            {"asset_id": f"{source_id}--config", "asset_kind": "config", "logical_path": f"jbrowse/{source_id}.json"},
        ] if not audit else [],
    }


def _endpoint() -> dict[str, Any]:
    row = {column: "NA" for column in V02_ENDPOINT_COLUMNS}
    row.update({
        "end_id": END_ID,
        "source_id": "BATTER_S1_007",
        "sample_id": "sample-1",
        "assay": "Term-seq",
        "evidence_class": "author_called_endpoint",
        "author_endpoint_id": "AUTHOR-1",
        "published_reference_accession": CONTIG,
        "reference_assembly": ASSEMBLY,
        "reference_name": CONTIG,
        "replicon_label": CONTIG,
        "biological_coordinate_1based": 67368,
        "bed_start_0based": 67367,
        "bed_end_0based": 67368,
        "strand": "+",
        "signal_or_score": "-1.2",
        "author_category": "P",
        "associated_gene_or_locus": "SLIV_00320",
        "pmid": "12345678",
        "doi": "10.1000/test",
        "source_table_or_file": "supp.tsv",
        "coordinate_interpretation": "1-based",
        "original_row_reference": "supp.tsv:row=2",
        "qc_status": "pass",
        "note": "author-called endpoint",
        "raw_accessions": [{"namespace": "GEO", "accession": "GSE123", "type": "study"}],
        "provenance": {"source_manifest_sha256": "b" * 64, "assembly_accession": ASSEMBLY, "contig_accession": CONTIG},
    })
    return row


class FakeRepository:
    def __init__(self) -> None:
        self.sources = {
            "BATTER_S1_007": _source("BATTER_S1_007"),
            "BATTER_S1_002": _source("BATTER_S1_002", audit=True),
        }
        self.endpoints = [ _endpoint() ]
        self.release_calls: list[str | None] = []

    def resolve_release(self, release_version: str | None = None) -> ReleaseContext:
        self.release_calls.append(release_version)
        if release_version not in (None, RELEASE.release_version):
            raise RepositoryNotFound("release not found")
        return RELEASE

    def health(self) -> Mapping[str, Any]:
        return {"status": "ok", "database": "fake"}

    def stats(self, release: ReleaseContext) -> Mapping[str, Any]:
        return {
            "sources": {"total": 2, "published_standardized": 1, "audit_only": 1},
            "endpoints": {"total": 1, "by_evidence_class": {"author_called_endpoint": 1}},
            "assemblies": {"total": 1},
            "augmentation": {"eligible_sources": 0, "scope": "source"},
        }

    @staticmethod
    def _filter(rows: list[Mapping[str, Any]], filters: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        result = rows
        for key in ("source_id", "species", "assay_family", "release_status", "evidence_class"):
            if filters.get(key):
                result = [row for row in result if row.get(key) == filters[key]]
        if filters.get("augmentation_eligible") is not None:
            result = [row for row in result if bool(row.get("used_for_batter_augmentation")) == bool(filters["augmentation_eligible"])]
        if filters.get("assembly_accession"):
            result = [row for row in result if row.get("assembly", {}).get("accession") == filters["assembly_accession"]]
        if filters.get("q"):
            q = str(filters["q"]).lower()
            result = [row for row in result if q in str(row).lower()]
        return result

    def list_sources(self, release: ReleaseContext, filters: Mapping[str, Any], *, offset: int, limit: int, sort: str, descending: bool):
        rows = sorted(self._filter(list(self.sources.values()), filters), key=lambda row: row["source_id"], reverse=descending)
        return rows[offset:offset + limit], len(rows)

    def get_source(self, release: ReleaseContext, source_id: str):
        return self.sources.get(source_id)

    def list_assemblies(self, release: ReleaseContext, filters: Mapping[str, Any], *, offset: int, limit: int, sort: str, descending: bool):
        rows = [{
            "assembly_accession": ASSEMBLY, "assembly_name": "test", "organism_name": "Escherichia coli",
            "strain": "K-12", "contigs": [{"accession": CONTIG, "name": CONTIG, "length_bp": 100000}],
            "source_tracks": [{"source_id": "BATTER_S1_007", "record_count": 1}], "endpoint_count": 1,
        }]
        return rows, len(rows)

    def get_assembly(self, release: ReleaseContext, assembly_accession: str):
        return self.list_assemblies(release, {}, offset=0, limit=1, sort="assembly_accession", descending=False)[0][0] if assembly_accession == ASSEMBLY else None

    def list_endpoints(self, release: ReleaseContext, filters: Mapping[str, Any], *, offset: int, limit: int, sort: str, descending: bool):
        rows = list(self.endpoints)
        if filters.get("source_ids"):
            rows = [row for row in rows if row["source_id"] in filters["source_ids"]]
        for key in ("assembly_accession", "contig_accession", "sample_id", "strand", "evidence_class", "author_category", "gene_or_locus"):
            if filters.get(key):
                lookup = "associated_gene_or_locus" if key == "gene_or_locus" else ("reference_assembly" if key == "assembly_accession" else ("reference_name" if key == "contig_accession" else key))
                rows = [row for row in rows if row[lookup] == filters[key]]
        return rows[offset:offset + limit], len(rows)

    def get_endpoint(self, release: ReleaseContext, end_id: str):
        return next((row for row in self.endpoints if row["end_id"] == end_id), None)

    def list_genes(self, release: ReleaseContext, filters: Mapping[str, Any], *, offset: int, limit: int, sort: str, descending: bool):
        return [], 0

    def get_gene(self, release: ReleaseContext, gene_id: str):
        return None

    def list_augmentation(self, release: ReleaseContext, *, offset: int, limit: int):
        rows = [row for row in self.sources.values() if row["used_for_batter_augmentation"]]
        return rows[offset:offset + limit], len(rows)

    def validate_source_ids(self, release: ReleaseContext, source_ids: list[str], *, published_only: bool = False) -> None:
        missing = [source_id for source_id in source_ids if source_id not in self.sources]
        if published_only:
            missing.extend(
                source_id
                for source_id in source_ids
                if source_id in self.sources
                and self.sources[source_id]["release_status"] != "published_standardized"
            )
        if missing:
            raise RepositoryNotFound(missing[0])

    def validate_assembly(self, release: ReleaseContext, assembly_accession: str) -> None:
        if assembly_accession != ASSEMBLY:
            raise RepositoryNotFound(assembly_accession)

    def validate_contig(self, release: ReleaseContext, assembly_accession: str, contig_accession: str) -> None:
        if assembly_accession != ASSEMBLY or contig_accession != CONTIG:
            raise RepositoryNotFound(contig_accession)

    def iter_endpoint_rows(self, release: ReleaseContext, filters: Mapping[str, Any]):
        for row in self.endpoints:
            yield row


class TestBtedV03ApiService(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeRepository()
        self.service = ReadService(self.repository)

    def test_release_and_stats_are_explicit(self) -> None:
        result = self.service.stats(None)
        self.assertEqual(result["release"]["release_version"], "v0.3.0")
        self.assertEqual(result["endpoints"]["total"], 1)
        with self.assertRaises(ApiError) as error:
            self.service.stats("v9.9.9")
        self.assertEqual(error.exception.status_code, 404)

    def test_sources_and_audit_only_links(self) -> None:
        result = self.service.source_detail(None, "BATTER_S1_007")
        self.assertIn("endpoints_download", result["links"])
        self.assertIn("%2Fapi%2Fv1%2Fassets%2FBATTER_S1_007--config", result["links"]["jbrowse"])
        self.assertIn("config=", result["links"]["jbrowse"])
        audit = self.service.source_detail(None, "BATTER_S1_002")
        self.assertEqual(audit["record_count"], 0)
        self.assertNotIn("endpoints_download", audit["links"])
        self.assertNotIn("jbrowse", audit["links"])

    def test_pagination_sort_and_endpoint_24_columns(self) -> None:
        result = self.service.list_endpoints(None, filters={}, page=1, page_size=1, sort="end_id", order="asc")
        self.assertEqual(result["pagination"], {"page": 1, "page_size": 1, "returned": 1, "total": 1, "has_next": False})
        self.assertEqual(set(V02_ENDPOINT_COLUMNS), set(result["data"][0]) - {"provenance"})
        with self.assertRaises(ApiError) as error:
            self.service.list_endpoints(None, filters={"evidence_class": "prediction_only"}, page=1, page_size=50, sort="end_id", order="asc")
        self.assertEqual(error.exception.status_code, 422)
        with self.assertRaises(ApiError):
            self.service.list_endpoints(None, filters={"contig_accession": CONTIG}, page=1, page_size=50, sort="end_id", order="asc")
        with self.assertRaises(ApiError):
            self.service.list_endpoints(None, filters={}, page=1, page_size=101, sort="end_id", order="asc")

    def test_download_preserves_tsv_values_and_bed_coordinates(self) -> None:
        tsv = self.service.download_endpoints(None, filters={"source_ids": ["BATTER_S1_007"]}, output_format="tsv")
        lines = list(tsv.body)
        self.assertEqual(lines[0].rstrip("\n").split("\t"), V02_ENDPOINT_COLUMNS)
        self.assertIn("-1.2", lines[1])
        bed = self.service.download_endpoints(None, filters={"source_ids": ["BATTER_S1_007"]}, output_format="bed6")
        self.assertEqual(lines := list(bed.body)[1].rstrip("\n").split("\t"), [CONTIG, "67367", "67368", END_ID, "0", "+"])

    def test_audit_only_source_cannot_be_download_filter(self) -> None:
        with self.assertRaises(ApiError) as error:
            self.service.download_endpoints(
                None,
                filters={"source_ids": ["BATTER_S1_002"]},
                output_format="tsv",
            )
        self.assertEqual(error.exception.status_code, 404)

    def test_augmentation_is_source_level(self) -> None:
        result = self.service.augmentation(None, page=1, page_size=50)
        self.assertEqual(result["scope"], "source")
        self.assertEqual(result["training_claim"], "none; source-level eligibility only")


class RecordingCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.closed = False

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        self.calls.append((sql, params))

    def fetchone(self) -> tuple[Any, ...]:
        return ("v0.3.0", "published", "a" * 64, 17)

    def close(self) -> None:
        self.closed = True


class RecordingConnection:
    def __init__(self) -> None:
        self.cursor_instance = RecordingCursor()
        self.closed = False

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance

    def close(self) -> None:
        self.closed = True


class NotFoundCursor(RecordingCursor):
    def fetchone(self) -> None:
        return None


class NotFoundConnection(RecordingConnection):
    def __init__(self) -> None:
        self.cursor_instance = NotFoundCursor()
        self.closed = False


class TestBtedV03PostgresReadRepository(unittest.TestCase):
    def test_release_query_is_parameterized_and_connection_is_closed(self) -> None:
        connection = RecordingConnection()
        repository = PostgresReadRepository(lambda: connection)
        release = repository.resolve_release("v0.3.0")
        self.assertEqual(release.release_version, "v0.3.0")
        sql, params = connection.cursor_instance.calls[0]
        self.assertIn("%s", sql)
        self.assertEqual(params, ("v0.3.0",))
        self.assertTrue(connection.cursor_instance.closed)
        self.assertTrue(connection.closed)

    def test_not_found_validation_is_not_wrapped_as_repository_unavailable(self) -> None:
        repository = PostgresReadRepository(lambda: NotFoundConnection())
        with self.assertRaises(RepositoryNotFound):
            repository.validate_assembly(RELEASE, "GCF_999999999.1")
        with self.assertRaises(RepositoryNotFound):
            repository.validate_contig(RELEASE, ASSEMBLY, "missing-contig")


@unittest.skipUnless(importlib.util.find_spec("fastapi"), "FastAPI optional dependency is not installed")
class TestBtedV03FastApiRuntime(unittest.TestCase):
    def test_app_factory_with_fake_repository(self) -> None:
        from fastapi.testclient import TestClient
        from backend.app.main import create_app

        client = TestClient(create_app(FakeRepository()))
        response = client.get("/api/v1/sources?page_size=101")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "invalid_pagination")

    def test_http_release_evidence_download_and_24_columns(self) -> None:
        from fastapi.testclient import TestClient
        from backend.app.main import create_app

        client = TestClient(create_app(FakeRepository()))
        unknown = client.get("/api/v1/stats?release_version=v9.9.9")
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.json()["error"]["code"], "release_not_found")

        invalid_evidence = client.get("/api/v1/endpoints?evidence_class=prediction_only")
        self.assertEqual(invalid_evidence.status_code, 422)
        self.assertEqual(invalid_evidence.json()["error"]["code"], "invalid_filter")

        audit_download = client.get("/api/v1/downloads/endpoints?source_id=BATTER_S1_002")
        self.assertEqual(audit_download.status_code, 404)

        endpoint_response = client.get("/api/v1/endpoints?page_size=1")
        self.assertEqual(endpoint_response.status_code, 200)
        self.assertEqual(
            set(V02_ENDPOINT_COLUMNS),
            set(endpoint_response.json()["data"][0]) - {"provenance"},
        )


if __name__ == "__main__":
    unittest.main()
