# BTED v0.3 数据库骨架

`schema.sql` 是 BTED v0.3 PostgreSQL 派生查询层的初始 DDL。它只定义表、约束、索引和
阻止非法公开 endpoint 的触发器，不导入数据，也不连接 Neon/Render。科研真源仍是
版本化 canonical release（manifest、24 列 `endpoints.tsv`、来源附表、BED、字段清单和
checksum）。数据库中的每个值都应该能沿 `release_version -> import_runs -> source /
endpoint / asset` 路径回到该 release。

## 表的用途

骨架覆盖：

- release/import provenance：`release_versions`、`import_runs`；
- 文献和参考：`publications`、`assemblies`、`contigs`；
- 来源和实验语境：`sources`、`source_accessions`、`samples`；
- 核心数据：保留 v0.2 全部 24 列的 `endpoints`，来源特异 JSONB 的
  `source_annotations`；
- 将来关联：`genes`、`endpoint_gene_context`（第一里程碑不计算 gene context）；
- 下载/浏览器对象：带 checksum、byte size、许可和 Range 标记的 `assets`。

endpoint 的 `evidence_class` 只接受 `observed_signal`、`called_endpoint`、
`author_called_endpoint`、`curated_record`。`author_integrated_mixed_evidence` 和
`prediction_only` 可以作为 source 审计状态或 JSONB 的预测注释被记录，但不能成为公开
endpoint 行。`BATTER_S1_002` 可有 source/manifest/accession 审计信息，但 audit-only
约束和触发器禁止它产生 endpoint、下载或 JBrowse 入口。

## 未来 importer 的安全流程

1. 读取 canonical release manifest，建立新的 `release_versions` 和 `import_runs`，
   将数据写入隔离的 staging schema/数据库；不要先修改当前 published release。
2. 按 publication → assembly/contig → source → accession/sample → endpoint/
   source_annotations → gene/asset 的顺序加载。每个输入文件保存路径、行引用、字节
   数、SHA-256 和许可状态；每个 endpoint 必须有 NOT NULL `sample_pk`，通过复合外键
   绑定同一 source 的 sample。
3. 在 staging 中运行 24 列表头/行数、坐标换算、strand、contig、evidence、
   `end_id`、source 状态、19/3 augmentation 计数和 assets checksum 校验。相同
   release/manifest 在 importer 修复后可以重新建立新的 `import_runs`，不能因历史
   失败 run 被唯一约束阻塞。任何
   失败都保留 `import_runs.run_status = failed` 与错误摘要，不删除审计记录。
4. 只有整批校验通过后，才在一个事务中把 run 标为 `committed`，并把新的 release
   置为可查询/当前版本；旧 release 保持只读。API 不应在事务中看到一半导入的数据。
5. 重新运行静态 schema 测试、`tests/test_bted_ingestion.py` 和 release/asset 校验，
   再允许应用层切换默认 release。

## 明确禁止

- 不在生产库执行 `DROP DATABASE`、`DROP TABLE`、`TRUNCATE` 或无 release 条件的
  `DELETE` 来“刷新”数据；
- 不在 v0.2.0 表/目录上原地覆盖值，修订必须生成新 release 并保留差异；
- 不用数据库中的手工修正覆盖 canonical release，不把预测输出补进实验 endpoint；
- 不接受任意 `?url=` 作为 asset origin。资产只能从 `assets` 中的登记和 checksum
  生成同源 `/api/v1/assets/{asset_id}` 代理。完整 SHA-256 在资产登记/import 阶段复算；
  每次 partial request 只校验 allowlist、登记 byte size、Content-Range 和返回长度；
- 不在第一里程碑导入 NCBI 新数据、外部协作者来源、gene clusters、Rfam 或训练
  endpoint 标签。

## 当前验证范围

本目录不要求本机安装 PostgreSQL。`schema.sql` 由静态 unittest 检查关键表、24 列
映射、release/source/contig/sample 外键、19/3 augmentation 边界和 prediction evidence
拒绝规则；未来连接 Neon 前还需要在目标 PostgreSQL 版本执行 DDL 并补充迁移 smoke test。

## v0.3 只读导入预检

第二里程碑新增 `backend/importer/canonical.py` 和
`scripts/import_bted_v03.py`。它们只读取 canonical release，先解析并 checksum 验证
每个 release entry 声明的 `records/<source>/manifest.json`，再验证 registry 交叉审计、
24 列 endpoint、BED 坐标、证据类别、论文 PMID/DOI、来源附表外键、所有发布文件的
`SHA256SUMS.txt` 以及 S1_002 的 audit-only 边界；不会连接 PostgreSQL，也不会写入任何
表。运行方式和错误定位见 [`docs/v0.3/importer.md`](../../docs/v0.3/importer.md)。

```bash
python3 scripts/import_bted_v03.py validate \
  --release-root data/public/v0.2.0 \
  --plan-json /tmp/bted-v03-import-plan.json
```

输出的 `plan` 只是一份确定性的未来写库行数/键摘要，`write_mode` 为
`not_written`；它不是 PostgreSQL 快照，且明确包含 `import_runs`、`assets`、零行的
`genes`/`endpoint_gene_context`。当前真实 v0.2.0 预检为 22 个 source、21 个
published、1 个 audit-only、28,399 条 endpoint，publication/assembly/contig/sample/
accession/source-annotation 数量分别为 13/20/47/21/32/17 个文件（24,887 行附表），
并规划 127 个已验证的小型 canonical assets。47 个 contig 的长度和 provenance 已由
现有 v0.2 JBrowse release bundle 中的 FAI、config 和根 `SHA256SUMS.txt` 交叉核实，并
保存为 `data/registry/reference_contigs.v0.2.0.tsv` 及其 JSON provenance；没有下载新
参考序列，也没有从 endpoint 最大坐标猜测长度。因此当前
`canonical_validation_status=validated` 且 `postgresql_ready=true`，但这仍只表示满足
写库前预检，不表示已经执行 INSERT。缺少或不通过该 registry 时，canonical 校验仍可
保持 validated，但 `postgresql_ready=false`。长度边界允许 endpoint 正好落在 contig
最后一个碱基上，即 `length_bp >= max_endpoint_position_1based`。

plan 中的 assets 使用无 `/` 的稳定 asset_id、schema 允许的 `asset_kind` 和 `is_public`
字段；source accession 使用 `accession_namespace`，不把别名当作物理列。参考 FASTA/FAI
不进入 Git 或当前 canonical asset 计划，registry 只记录可复核的 asset basename 和
checksum。builder 和检查命令见 [`docs/v0.3/importer.md`](../../docs/v0.3/importer.md)。
