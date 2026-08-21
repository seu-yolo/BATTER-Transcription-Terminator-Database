# BTED v0.3 canonical release 校验器

**状态：** v0.3.0 第二里程碑（只读校验 + 确定性导入计划）  
**实现：** `backend/importer/canonical.py`  
**入口：** `scripts/import_bted_v03.py`

这一阶段还没有连接 PostgreSQL，也不会把文件写入数据库。校验器只读取一个已经冻结
的 canonical release，检查将来导入数据库时最容易出错的边界，并输出一个可以复核的
import plan。数据库仍然只是 canonical release 的派生查询层；校验通过不等同于已经
部署或已经写入 Neon。

## 运行

在仓库根目录执行：

```bash
python3 scripts/import_bted_v03.py validate \
  --release-root data/public/v0.2.0
```

命令在标准输出打印 JSON。`ok=true` 表示校验通过；`issues` 的每一项都带有
`source_id`、`file`、`line` 和具体问题，便于直接定位原始文件。非零退出码表示存在
问题，不会生成部分导入结果。

如需保存确定性计划：

```bash
python3 scripts/import_bted_v03.py validate \
  --release-root data/public/v0.2.0 \
  --plan-json /tmp/bted-v03-import-plan.json
```

测试 fixture 或复制出的 release 可以用 `--repo-root` 指定 registry 和来源 manifest
所在的仓库根目录：

```bash
python3 scripts/import_bted_v03.py validate \
  --repo-root /path/to/fixture \
  --release-root /path/to/fixture/data/public/v0.2.0
```

## 校验边界

校验器会读取：

1. `release_manifest.json`、22 个来源 entry 和
   `data/registry/batter_s1_source_registry.tsv`；
   根 `release_version` 必须符合 `vMAJOR.MINOR.PATCH`，例如 `v0.2.0`；
2. 每个 entry **声明并通过 checksum 校验的**
   `data/public/v0.2.0/records/BATTER_S1_NNN/manifest.json`（且 `record_root` 不能
   指向 registry 或 release 外部目录）。这是导入时的 canonical
   source manifest；`data/registry/manifests/BATTER_S1_NNN.json` 只是旧 registry
   audit 副本，用来交叉核对，不能替代 record 内的 manifest。canonical manifest 的
   `release_version` 也必须与根 release 一致；
3. 每个 source 至少声明并实际提供 `manifest.json`、`fields.json`、
   `SHA256SUMS.txt`。`published_standardized` 还必须有 `endpoints.tsv` 和
   `endpoints.bed`；`source_annotations_status=published` 还必须有
   `source_annotations.tsv`。状态为 `withheld_external_link_only` 的来源不因为缺少
   附表而失败；
4. 每个 source 的 `SHA256SUMS.txt`。文件名必须在 release entry 中声明，摘要必须同时
   与实际文件和 release entry 中的 SHA-256 相同；除 checksum 文件自身外，所有声明的
   发布文件都必须出现在该清单中；
5. 已发布 source 的 24 列 `endpoints.tsv` 与 `endpoints.bed`。

每个 endpoint 行检查：

- `source_id`、非空 `sample_id`、带来源前缀的 `end_id` 和重复键；
- `strand` 必须为 `+`/`-`；
- 1-based 位置与 BED 的严格关系：`start = position - 1`、`end = position`；
- endpoint evidence 必须属于 `observed_signal`、`called_endpoint`、
  `author_called_endpoint`、`curated_record`，并与来源 evidence 一致；
- endpoint 中的 PMID/DOI 必须与 registry 中的来源论文一致；
- BED6 行必须与同一行 TSV 的 contig、坐标、ID 和链方向一致；不跨 contig 合并。

`source_annotations.tsv` 只用稳定 `end_id` 做外键检查；它可以有来源特异列，但不能把
预测或混合证据提升为 endpoint evidence。`BATTER_S1_002` 保持 `audit_only`：必须是
零记录、无 endpoints 文件、无 JBrowse 配置；即使它的审计 metadata 存在，也不能在本
阶段生成伪端点。

此外，release 与 registry 的 source 集合必须完全相同。相同 PMID 的 canonical/audit
manifest 必须保持 DOI、标题和年份一致；相同带版本 assembly 也必须保持 species 一致。
这些比较是审计约束，不会根据某一份冲突文件猜测正确值。

## 当前 v0.2.0 校验结果

校验器从真实文件得到以下数字（不是手工写入）：

| 项目 | 数量 |
| --- | ---: |
| 来源 | 22 |
| `published_standardized` 来源 | 21 |
| `audit_only` 来源 | 1（S1_002） |
| 公开 endpoint | 28,399 |
| augmentation `TRUE` / `FALSE` | 19 / 3 |
| publication | 13 |
| reference assembly | 20 |
| endpoint contig | 47 |
| sample context | 21 |
| source accession | 32 |
| source annotation 文件 / 行 | 17 / 24,887 |

endpoint 表中没有 contig 长度，因此 plan 会把 `length_bp` 标为 unresolved；校验器不从
坐标最大值猜测长度。未来正式导入前，应从每个引用的参考 FASTA/assembly metadata 核实
长度并保存来源和 checksum。

## import plan 的含义

`plan` 是将来写入 schema 的**行数与键摘要**，不是数据库快照，也不代表已经执行
INSERT。它包含 `release_versions`、`import_runs`、`publications`、`assemblies`、
`contigs`、`sources`、`source_accessions`、`samples`、`endpoints`、
`source_annotations`、`genes`、`endpoint_gene_context` 和 `assets` 的确定性统计；大型
endpoint/annotation 键集合以数量、首尾样本和集合 SHA-256 表示，避免把 28,399 条 ID
复制到一次命令输出中。`write_mode` 固定为 `not_written`。`canonical_validation_status`
单独表示 canonical 校验是否通过；`postgresql_ready` 则表示是否满足实际 schema 的
写库前提，不会因为校验通过就默认为 true。

`import_runs` 记录 release 版本和 release manifest SHA-256，状态为 `validated` 或
`failed`，但不会执行 INSERT。`assets` 只列出 release entry 已声明、实际存在、SHA-256
已验证且不超过 50 MiB 的小型 canonical 文件；每项含不带 `/` 的稳定 `asset_id`、逻辑
路径、来源、类型、摘要、字节数和 schema 对应的 `is_public` 标记，不生成 HF/origin URL。
`asset_kind` 使用数据库允许的枚举（如 `bed`、`metadata`、`checksum`、
`source_annotation`）；`endpoints.bed` 映射为 `bed`，`SHA256SUMS.txt` 映射为
`checksum`，其它当前 JSON/TSV 映射为 `metadata`。`genes` 和
`endpoint_gene_context` 在本里程碑明确为零行。

`source_accessions` 与 schema 对齐，使用 `accession_namespace`，同时保留 `accession` 和
`raw_value`，并记录 `accession_type=study` 与 ordinal。namespace 映射为：`GSE → GEO`、
`SR* / PRJNA → SRA`、`PRJEB → ENA`、`E-MTAB → BioStudies`（另记录 `ArrayExpress`
别名放在 plan metadata 中，不作为物理列）。未知前缀只进入 `unresolved`，不会猜测数据库。

当前真实 v0.2.0 的 `canonical_validation_status=validated`，但
`postgresql_ready=false`：47 个 contig 的 `length_bp` 尚未从参考 FASTA/assembly metadata
核实，不能把校验通过误认为已经满足 PostgreSQL 的 NOT NULL 约束。

未来的 PostgreSQL importer 必须把该 plan 作为 staging 预检，然后按
`release -> publication/assembly -> source/accession/sample -> endpoint/annotation ->
asset` 顺序写入一个新的 release，并在事务内切换 published 状态。当前实现刻意不做
psycopg、Neon、Render 或生产写库。

## 测试

```bash
python3 -m unittest -v tests/test_bted_v03_importer.py
python3 -m unittest -v tests/test_bted_ingestion.py
python3 -m unittest discover -s tests -p 'test*.py' -v
git diff --check
```

测试包含真实 v0.2.0 happy path，以及只复制少量文件到临时目录后模拟的坐标错误、
annotation orphan、audit-only 错误 endpoint、release row-count mismatch、canonical
manifest 篡改、必要文件缺失/未声明、SHA256SUMS 不一致、registry extra source、相同
PMID 元数据冲突、未声明 checksum 条目、错误 release version 和 CLI plan 输出；不会复制
整个大型 release，也不会修改仓库内的原始数据。
