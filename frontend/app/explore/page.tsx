import Link from "next/link";
import { getEndpoints, ApiClientError } from "@/lib/api";
import { EmptyState, ErrorState, PageIntro, ReleaseNote, StatusBadge } from "@/components/PageFrame";
import { Pagination } from "@/components/Pagination";

type ExploreParams = { page?: string; source_id?: string; assembly_accession?: string; contig_accession?: string; gene_or_locus?: string; strand?: string; evidence_class?: string; position_min?: string; position_max?: string };

export default async function ExplorePage({ searchParams }: { searchParams?: ExploreParams }) {
  const page = Math.max(1, Number(searchParams?.page ?? "1") || 1);
  const params = {
    page, page_size: 25, source_id: searchParams?.source_id, assembly_accession: searchParams?.assembly_accession,
    contig_accession: searchParams?.contig_accession, gene_or_locus: searchParams?.gene_or_locus, strand: searchParams?.strand, evidence_class: searchParams?.evidence_class,
    position_min: searchParams?.position_min ? Number(searchParams.position_min) : undefined,
    position_max: searchParams?.position_max ? Number(searchParams.position_max) : undefined,
  };
  try {
    const result = await getEndpoints(params);
    const makeHref = (nextPage: number) => {
      const query = new URLSearchParams();
      Object.entries({ ...searchParams, page: String(nextPage) }).forEach(([key, value]) => { if (value) query.set(key, value); });
      return `/explore?${query.toString()}`;
    };
    return <>
      <PageIntro eyebrow="Catalogue / endpoints" title="Explore endpoint records"><span>Filter the public endpoint table without collapsing source, sample, contig, strand, or evidence identity. Open a record for its original fields and reference context.</span></PageIntro>
      <ReleaseNote release={result.release} />
      <form className="filter-bar" action="/explore" method="get">
        <div><label htmlFor="source_id">Source</label><input id="source_id" name="source_id" defaultValue={searchParams?.source_id} placeholder="BATTER_S1_007" /></div>
        <div><label htmlFor="assembly_accession">Assembly</label><input id="assembly_accession" name="assembly_accession" defaultValue={searchParams?.assembly_accession} placeholder="GCF_..." /></div>
        <div><label htmlFor="contig_accession">Contig</label><input id="contig_accession" name="contig_accession" defaultValue={searchParams?.contig_accession} placeholder="CP..." /></div>
        <div><label htmlFor="gene_or_locus">Gene / locus</label><input id="gene_or_locus" name="gene_or_locus" defaultValue={searchParams?.gene_or_locus} placeholder="locus tag" /></div>
        <div><label htmlFor="strand">Strand</label><select id="strand" name="strand" defaultValue={searchParams?.strand ?? ""}><option value="">Both strands</option><option value="+">+ plus</option><option value="-">− minus</option></select></div>
        <div><label htmlFor="evidence_class">Evidence</label><select id="evidence_class" name="evidence_class" defaultValue={searchParams?.evidence_class ?? ""}><option value="">All public evidence</option><option value="author_called_endpoint">Author-called endpoint</option><option value="curated_record">Curated record</option><option value="observed_signal">Observed signal</option><option value="called_endpoint">Called endpoint</option></select></div>
        <div><label>&nbsp;</label><button className="button primary" type="submit">Filter records</button></div>
      </form>
      {result.data.length === 0 ? <EmptyState>No endpoint records match these filters.</EmptyState> : <>
        <div className="section-heading"><div><h2>{result.pagination.total.toLocaleString()} matching records</h2><p>Showing page {result.pagination.page}; positions remain 1-based in the record view.</p></div></div>
        <div className="table-wrap"><table><thead><tr><th>Endpoint</th><th>Source</th><th>Assembly / contig</th><th>Position</th><th>Strand</th><th>Evidence</th><th>Associated locus</th><th>Context</th></tr></thead><tbody>{result.data.map((endpoint) => <tr key={endpoint.end_id}><td><Link href={`/endpoints/${encodeURIComponent(endpoint.end_id)}`}><strong>{endpoint.end_id}</strong></Link></td><td><Link href={`/sources/${encodeURIComponent(endpoint.source_id)}`}>{endpoint.source_id}</Link></td><td>{endpoint.reference_assembly}<br /><span className="muted">{endpoint.reference_name}</span></td><td>{endpoint.biological_coordinate_1based.toLocaleString()}</td><td>{endpoint.strand}</td><td><StatusBadge value={endpoint.evidence_class} /></td><td>{endpoint.associated_gene_or_locus ?? "—"}</td><td><Link href={`/assemblies/${encodeURIComponent(endpoint.reference_assembly)}#${encodeURIComponent(`${endpoint.reference_name}:${endpoint.biological_coordinate_1based}`)}`}>Assembly view</Link></td></tr>)}</tbody></table></div>
        <Pagination page={result.pagination.page} hasNext={result.pagination.has_next} makeHref={makeHref} />
      </>}
    </>;
  } catch (reason) { return <><PageIntro eyebrow="Catalogue / endpoints" title="Explore endpoint records" /><ErrorState message={reason instanceof ApiClientError ? reason.message : "The endpoint table could not be loaded."} /></>; }
}
