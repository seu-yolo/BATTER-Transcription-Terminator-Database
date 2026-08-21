# v0.3 public asset handoff

This is the shortest maintainer sequence for handing the registered public
objects (browser assets plus API-facing release files) to an external HTTPS
object store. The repository does not implement an uploader, does not contain
credentials, and this procedure must not be treated as completed until the
remote audit has passed.

## Current facts

- The tracked browser inventory has 105 rows spanning 19 unique assemblies.
- The planned materialized bundle has 211 asset rows. The preparation policy
  selects all 164 rows with `is_public=true` and
  `redistribution_status=verified_redistributable`, and excludes 47 private or
  external rows. The 77 inventory rows with the same public status are only a
  browser provenance cross-check; they are not the complete upload set.
- The current local GFF/FAI materialization contains 95,437 genes and keeps
  `endpoint_gene_context` at zero.
- No object has been uploaded or verified against a remote origin yet.

## Maintainer sequence

1. Materialize the release with the tracked browser inventory, then prepare the
   exact object set from its `assets.jsonl`. The output directory must be new or
   empty; the command verifies local byte size and SHA-256 before copying
   anything. It resolves browser paths from the frozen JBrowse bundle and
   canonical `records/` paths from the release root.

   ```bash
   python3 scripts/import_bted_v03.py materialize \
     --release-root data/public/v0.2.0 \
     --repo-root . \
     --output-dir /path/to/bted-v03-staging-with-browser \
     --asset-origin-base https://assets.example.org/bted/v0.2.0 \
     --generated-at-utc 2026-08-22T00:00:00Z \
     --jbrowse-asset-inventory data/registry/jbrowse_assets.v0.2.0.tsv \
     --jbrowse-bundle-root /path/to/BTED-v0.2.0-jbrowse
   ```

   ```bash
   python3 scripts/prepare_v03_public_asset_objects.py \
     --materialized-bundle /path/to/bted-v03-staging-with-browser \
     --inventory data/registry/jbrowse_assets.v0.2.0.tsv \
     --jbrowse-bundle /path/to/BTED-v0.2.0-jbrowse \
     --release-root data/public/v0.2.0 \
     --output-dir /path/to/bted-v03-public-objects
   ```

   This produces `ASSET_OBJECTS.json`, `SHA256SUMS.txt`, and the 164-object
   `object_path` tree. `ASSET_OBJECTS.json` is selected from the materialized
   211-row asset table and records `asset_id`, `object_path`, `byte_size`, and
   `sha256` for every object. `--manifest-only` is useful for a dry preparation
   check; it does not create upload payload files.

2. Upload the copied object tree with the project-approved external/manual
   uploader. Preserve every `object_path` exactly, use the explicit HTTPS
   origin base that will be given to the audit command, and do not upload the
   47 excluded objects. The repository has no upload command and no upload
   credentials.

3. Audit the remote objects with one HEAD and one single-byte Range request per
   registered object. The auditor constructs URLs only from `object_path` and
   the explicit HTTPS origin; it does not accept arbitrary manifest URLs,
   retry, cache, upload, or hash full remote files.

   ```bash
   python3 scripts/audit_v03_remote_assets.py \
     --asset-objects /path/to/bted-v03-public-objects/ASSET_OBJECTS.json \
     --origin-base https://assets.example.org/bted/v0.2.0 \
     --output /path/to/bted-v03-public-objects/REMOTE_ASSET_AUDIT.json
   ```

   A successful full audit reports 164/164 objects. Each row must have the
   registered size and SHA-256, HEAD `200` with matching `Content-Length`,
   Range `206`, `Content-Range: bytes 0-0/<size>`, one returned byte, and
   `supports_range=true`/`ok=true`. A non-zero exit still writes the audit
   report; fix the external object and rerun the audit.

   The 77 browser rows remain visible in the preparation manifest as an
   inventory cross-check; the other 87 public rows are canonical metadata,
   checksums, endpoint/annotation files and related small API assets selected by
   the same materialized table.

4. Apply the completed 164-object report to a `planned_not_verified` materialized bundle
   in a new output directory. This step is offline: it compares every required
   public asset's `asset_id`, `object_path`, byte size and SHA-256, and
   requires recorded HEAD `200` plus Range `206` before setting
   `supports_range=true`.

   ```bash
   python3 scripts/apply_v03_remote_asset_audit.py \
     --bundle-dir /path/to/bted-v03-staging-with-browser \
     --remote-audit /path/to/bted-v03-public-objects/REMOTE_ASSET_AUDIT.json \
     --jbrowse-asset-inventory data/registry/jbrowse_assets.v0.2.0.tsv \
     --output-dir /path/to/bted-v03-verified-bundle
   ```

   The command refuses an incomplete or mismatched report. It derives the
   required set from every materialized row with `is_public=true` and
   `redistribution_status=verified_redistributable` (currently 164); the tracked
   inventory separately verifies the 77-object browser subset. It marks the
   origin `verified` only when all 164 required assets pass; the 47
   `external_link_only`/private assets remain `supports_range=false`. It then
   rebuilds bundle checksums and runs the existing offline bundle verifier.
   This still does not write PostgreSQL or perform promotion.

The audit script's injected transport and focused tests are for offline code
verification only. They are not evidence that any remote origin is reachable.
