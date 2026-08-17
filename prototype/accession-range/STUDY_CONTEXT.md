# Pilot study-context provenance

This file records why the user-facing pilot attributes the `GCF_000739105.1` data to particular studies and institutions. It is presentation metadata only: no endpoint coordinate, evidence class, or BED record is changed.

## Shared organism and raw-data relationship

- Organism: *Streptomyces lividans* TK24.
- Reference assembly: `GCF_000739105.1`; chromosome `CP009124.1`.
- `BATTER_S1_007` and `BATTER_S1_013` both cite ENA project `PRJEB31507` for the *S. lividans* data.
- The database therefore presents two published endpoint datasets on one reference and one shared raw-data project. It does not describe them as two independent sequencing experiments.

## BATTER_S1_007 — Lee et al. 2019

- Paper: [The Transcription Unit Architecture of *Streptomyces lividans* TK24](https://pmc.ncbi.nlm.nih.gov/articles/PMC6742748/).
- Lead affiliation: Systems and Synthetic Biology Laboratory, Department of Biological Sciences and KI for the BioCentury, Korea Advanced Institute of Science and Technology (KAIST), Daejeon, South Korea.
- Corresponding author: Byung-Kwan Cho.
- Culture and sampling: R5− medium at 30 °C; samples at 9.5, 14, 16 and 20 hours, representing four growth phases; biological duplicates.
- Term-seq sequencing: Illumina HiSeq 2500, single-end 50 bp.
- Published endpoint set: 1,640 transcription end positions (TEPs).

## BATTER_S1_013 — Lee et al. 2020

- Paper: [Comparative transcriptomic analysis of seven actinobacterial species](https://pmc.ncbi.nlm.nih.gov/articles/PMC7738537/).
- Lead affiliation and corresponding author: KAIST Systems and Synthetic Biology Laboratory; Byung-Kwan Cho.
- For *S. lividans* TK24, the descriptor reports the same R5− / 30 °C time course and links the raw reads to `PRJEB31507`.
- Published endpoint set shown in BTED: 1,208 Term-seq transcription termination sites (TTSs) from the seven-species comparison.

## Attribution rules

- “Lead institution” means the primary paper affiliation, not necessarily the physical sequencing facility.
- “ENA submitting center” is taken from the ENA project metadata (`KAIST`).
- No separate sequencing facility is named in the reviewed paper or ENA record, so the page says “Not separately reported”. It must not infer that KAIST itself operated the sequencer.
- Study-context claims must remain source-specific. Shared assembly or raw-data accessions do not merge the two endpoint tables into a consensus.
