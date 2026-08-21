import Link from "next/link";
import { notFound } from "next/navigation";
import { getEndpoint, ApiClientError, Endpoint, Release } from "@/lib/api";
import { ErrorState, ExternalLink, PageIntro, ReleaseNote, StatusBadge } from "@/components/PageFrame";

const DISPLAY_FIELDS = [
  "end_id", "source_id", "sample_id", "assay", "evidence_class", "author_endpoint_id",
  "published_reference_accession", "reference_assembly", "reference_name", "replicon_label",
  "biological_coordinate_1based", "bed_start_0based", "bed_end_0based", "strand", "signal_or_score",
  "author_category", "associated_gene_or_locus", "pmid", "doi", "source_table_or_file",
  "coordinate_interpretation", "original_row_reference", "qc_status", "note",
];

function valueText(value: unknown): string { return value === null || value === undefined || value === "" ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value); }

export default async function EndpointDetailPage({ params }: { params: { endId: string } }) {
  let endpoint: { release: Release } & Endpoint;
  try { endpoint = await getEndpoint(decodeURIComponent(params.endId)); }
  catch (reason) { if (reason instanceof ApiClientError && reason.status === 404) notFound(); return <ErrorState message="The endpoint record could not be loaded." />; }
  const location = `${endpoint.reference_name}:${endpoint.biological_coordinate_1based}`;
  return <>
    <PageIntro eyebrow="Endpoint record" title={endpoint.end_id}><span>{location} · {endpoint.strand} strand · {endpoint.evidence_class.replaceAll("_", " ")}</span></PageIntro>
    <ReleaseNote release={endpoint.release} />
    <div className="detail-grid"><div>
      <section className="panel"><div className="source-card-top"><h2>Endpoint data</h2><StatusBadge value={endpoint.evidence_class} /></div><div className="table-wrap"><table className="json-table"><tbody>{DISPLAY_FIELDS.map((field) => <tr key={field}><td>{field}</td><td>{valueText(endpoint[field])}</td></tr>)}</tbody></table></div></section>
      {Boolean(endpoint.source_annotations_summary) && <section className="panel"><h2>Source annotations</h2><p className="muted">{valueText(endpoint.source_annotations_summary)}</p></section>}
    </div><aside>
      <section className="panel"><h2>Record context</h2><ul className="link-list"><li><Link href={`/sources/${encodeURIComponent(endpoint.source_id)}`}>View source study</Link></li><li><Link href={`/assemblies/${encodeURIComponent(endpoint.reference_assembly)}#${encodeURIComponent(location)}`}>View assembly context</Link></li><li><Link href={`/explore?assembly_accession=${encodeURIComponent(endpoint.reference_assembly)}&contig_accession=${encodeURIComponent(endpoint.reference_name)}&position_min=${endpoint.biological_coordinate_1based}&position_max=${endpoint.biological_coordinate_1based}`}>Explore nearby records</Link></li></ul></section>
      <section className="panel"><h2>Publication</h2><p className="muted">The endpoint keeps the original PMID/DOI and source row reference.</p><ul className="link-list"><li><ExternalLink href={endpoint.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${endpoint.pmid}/` : null}>PMID {endpoint.pmid ?? "not recorded"}</ExternalLink></li><li><ExternalLink href={endpoint.doi ? `https://doi.org/${endpoint.doi}` : null}>{endpoint.doi ?? "DOI not recorded"}</ExternalLink></li></ul></section>
    </aside></div>
  </>;
}
