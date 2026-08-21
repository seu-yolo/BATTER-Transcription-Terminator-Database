# BTED 当前交接

**更新：** 2026-08-22

**当前分支：** `feature/bted-v0.3-dynamic-service`

**当前里程碑：** v0.3.0 已完成架构契约、PostgreSQL schema 骨架、只读 canonical
release 校验/导入计划、B1 确定性 JSONL 物化、B2 离线事务 writer，以及基于既有 v0.2
JBrowse bundle 的 47 个参考 contig 长度/provenance 注册；C1 只读 FastAPI 查询层已实现并
通过纯 Python contract tests，但没有连接真实 PostgreSQL，也没有实现 assets/Range、前端
或部署。

## 2026-08-21 v0.3 第三阶段 A：参考 contig registry

- `scripts/build_reference_contig_registry.py` 从只读的既有
  `BTED-v0.2.0-jbrowse` bundle 解析 21 个 published source 的 config、
  `IndexedFastaAdapter`、FAI 和根 `SHA256SUMS.txt`；不下载新参考序列，不修改 v0.2
  release，也不使用端点最大坐标推测长度。
- `data/registry/reference_contigs.v0.2.0.tsv`（47 行）与 `.json` provenance 已生成。
  每行保留 assembly/contig、FAI `length_bp`、最大 endpoint 位置、支持 source、FASTA/FAI
  basename 和摘要、bundle 清单摘要、生成器版本/UTC 时间。共享 contig 只有在长度和摘要
  一致时才接受；S1_007/S1_013 共享 CP009124.1，但 source endpoint 仍独立。
- canonical importer 默认读取该 TSV，也可用 `--contig-registry` 指定副本；它要求与
  endpoint `(reference_assembly, reference_name)` 集合精确相同、长度覆盖所有 endpoint、
  source/provenance/checksum 字段有效；长度边界为
  `length_bp >= max_endpoint_position_1based`，允许 endpoint 正好在 contig 末位。真实 v0.2.0 现为
  `canonical_validation_status=validated`、`postgresql_ready=true`、unresolved 为空。
  缺少 registry 时保持 canonical validated 但 ready=false；这两个状态仍不能解释为已经
  写入 PostgreSQL。
- 参考 FASTA/FAI 不进入 Git，也不加入当前 127 项 canonical assets；registry 只是既有
  JBrowse 发布资产的查询层 provenance。专项 importer/builder 测试为 24/24 PASS。

## 2026-08-21 v0.3 架构与数据库骨架

- 阅读并以 v0.2 SOP、证据边界、发布接口、release manifest、registry 和 S1_007/S1_002
  记录为输入；v0.2 canonical release 保持不变。
- `docs/v0.3/architecture.md` 冻结 canonical release→PostgreSQL 派生查询层关系、
  v0.2/v0.3 并行策略和 Vercel/Render/Neon/Hugging Face/同源 Range 代理边界。
- `docs/v0.3/browser-ui-contract.md` 冻结已批准的搜索/augmentation 入口、论文与
  accession 可点击详情、基因/端点多级缩放、raw plus/minus BigWig 和 GFF3/TBI 展示规则。
- `docs/v0.3/database-schema.md` 与 `backend/database/schema.sql` 覆盖
  `release_versions`、`import_runs`、`publications`、`assemblies`、`contigs`、
  `sources`、`source_accessions`、`samples`、`endpoints`、`source_annotations`、
  `genes`、`endpoint_gene_context`、`assets`；endpoint 保留 v0.2 全 24 列和 provenance。
- source-level 边界保持：22 个 source 中 21 个 published、S1_002 audit-only；Table S1
  `used_for_batter_augmentation` 为 19 TRUE/3 FALSE。预测/不可拆分混合证据不进入公开
  endpoint，gene clusters/Rfam 不纳入。
- `docs/v0.3/api-contract.md` 定义 `/api/v1/stats`、sources、assemblies、endpoints、
  genes、四类详情路由、augmentation、downloads/endpoints 和 assets Range 206/416 行为；
  page_size 上限为 100，S1_002 不生成下载/JBrowse 入口。
- `backend/database/README.md` 规定 staging、校验、atomic switch；禁止对生产数据库
  直接 DROP/TRUNCATE 或覆盖既有 release。
- `tests/test_bted_v03_schema.py`：11/11 PASS；与 `tests/test_bted_ingestion.py` 合计
  15/15 PASS；完整 `unittest discover` 为 32/32 PASS；`git diff --check` PASS。

## 2026-08-21 v0.3 canonical release 校验器

- `backend/importer/canonical.py` 是无 PostgreSQL 依赖的只读校验器；先解析并验证 release
  entry 声明的 `records/<source>/manifest.json` 作为 canonical source manifest，
  `data/registry/manifests` 只作 audit 交叉核对；随后检查 24 列 endpoints、BED 坐标、
  证据、PMID/DOI、annotation 外键、必要文件、逐项 `SHA256SUMS.txt` 与 S1_002 audit-only
  边界。
- `scripts/import_bted_v03.py validate --release-root data/public/v0.2.0` 输出 JSON；
  `--plan-json` 保存确定性行数/键摘要。它不执行 INSERT，`write_mode` 固定为
  `not_written`；plan 另有 `canonical_validation_status` 和
  `postgresql_ready` 两个状态，避免把校验通过误认为可以直接写库。
- 第二里程碑当时的真实 v0.2.0 预检结果：22 source / 21 published / 1 audit-only / 28,399 endpoint；
  19/3 augmentation；13 publication、20 assembly、47 contig、21 sample、32 accession、
  17 个 source annotation 文件（24,887 行），并生成 127 个已验证小型 canonical assets。
  计划另含 1 个 `import_runs`、零行 `genes`/`endpoint_gene_context`；当时 47 个 contig
  长度仍标为 unresolved，未用端点最大坐标猜测（第三阶段 A 已补齐 registry）。
- `tests/test_bted_v03_importer.py`：第三阶段后 24/24 PASS；schema/ingestion 合计
  15/15 PASS，完整 `unittest discover` 为 56/56 PASS；plan 的 127 个 asset 使用不含
  `/` 的稳定 asset_id、schema asset_kind 和 `is_public`；accession 使用
  `accession_namespace`/accession/raw_value。

### 接手后的下一步

1. 在目标 PostgreSQL 版本执行 DDL smoke test，补充 importer 的 staging/atomic switch
   和 release checksum 校验；不要先连接生产或改写 v0.2 文件。
2. 根据 API 契约实现 FastAPI 只读查询和同源 asset Range 代理，先用本地 fixture 验证
   404/422、provenance、JBrowse deep link 与单 Range 206/416。
3. 只有契约和 importer 评审通过后，才安排 Render/Neon/Vercel/Hugging Face 部署；
   gene context、外部协作者数据、NCBI 新数据和训练集仍需单独任务。

## 2026-08-17 核心字段页面

- 页面先显示 *Streptomyces lividans* TK24、精确 assembly/contig、来源数据集和端点总数。
- 每个来源只显示此前已经整理的论文、实验方法、原始 accession、证据类型和记录数；研究单位、详细培养/采样和测序机构不进入当前页面。
- S1_007/013 继续保持两条独立 source track；相同 `PRJEB31507` 会分别出现在两张来源卡中，不将端点静默合并。
- 22 个来源的核心字段来自现有 manifest、release registry 和 processing record；S1_002 继续保持 `audit_only`。
- 本地入口：`http://127.0.0.1:8017/accession-range-demo.html?accession=GCF_000739105.1&lang=zh`。

## 2026-08-16 用户化双语检索页

- 页面入口仍为 `http://127.0.0.1:8016/accession-range-demo.html`，但可见内容已从开发架构说明改为“检索—研究概览—浏览/下载”的科研用户流程。
- 顶部 EN/中文按钮即时切换导航、表单、动态状态、统计、研究表、证据标签、下载区与页脚；选择写入 URL 和 localStorage。
- 用户页不显示 D1、API route、对象存储路径或 Range 检查。技术实现仍保留在 `prototype/accession-range/`，自动测试仍直接验证 API 和 Range。
- 页面解释收录范围、单条记录含义和证据边界，并列出适合用途与不可直接推断的结论。
- S1_007/013 分别展示论文标题、2019/2020、实验方法、证据类别、记录数、PubMed、PRJEB31507、来源详情和来源特异解读，继续保持独立 track。

## 2026-08-15 accession/Range 架构试点

- 入口：`http://127.0.0.1:8016/accession-range-demo.html`；必须用 `scripts/run_accession_range_demo.py`，普通静态服务器不提供 `/api`。
- 试点 assembly：`GCF_000739105.1 / CP009124.1`；S1_007（1,640）和 S1_013（1,208）仍是两条独立 `author_called_endpoint` track。
- 参考 FASTA/FAI/GFF3/TBI 在两个旧来源资产中 SHA-256 完全一致；原型只解析一组共享对象，避免重复 8,628,614 bytes。
- D1 schema、seed、Worker 和说明位于 `prototype/accession-range/`；本地等价API位于 `scripts/run_accession_range_demo.py`。
- 生产 Worker 不接受任意远程 URL，只允许 D1 中登记的 asset key，并校验 origin host。
- 本分支只验证部署架构，没有上传外部服务、创建Cloudflare资源或改变公开科学数据。

## 2026-08-14 Genomes 科研目录改版

- 主表只保留 `Genome / Experimental data / Evidence / 3′ ends / Access`，不再让内部 Source ID、track 数和重复状态占据主视图。
- 物种/菌株是第一视觉层级；assembly accession 位于其下并链接 NCBI Datasets。
- 可按物种、实验方法和证据类别筛选，搜索仍覆盖 assembly、source ID 与原始数据 accession。
- `Select visible` 按当前筛选结果选择 assembly；批量 ZIP 为每个 assembly 保留独立目录，并包含 BED 与合并 metadata。
- 多篇研究使用同一精确 assembly 时，在同一个 genome 详情/JBrowse 中保留独立来源轨道，不把研究结果静默合并。
- 完整本地演示地址：`http://127.0.0.1:8015/sources.html`（需在仓库根目录运行 `.pages-preview` 的本地服务器）。

## 2026-08-14 JBrowse 可读性补强

- 四个 Rend-seq 默认窗口均自动选择同时含 `+`/`-` 候选的约 3 kb 区域，打开即可验证箭头方向。
- 轨道标题直接写明蓝色/正链/向右与橙色/负链/向左；来源页和 assembly 页另有一张英文读图卡。
- 合并候选轨道使用浏览器专用富属性 GFF3；点击端点可查看稳定 ID、1-based 坐标、strand、raw support、上下文和证据警告。公开标准 BED 不变。
- signed-log BigWig 使用 `bedGraphToBigWig -unc`，规避 JBrowse 2.17 对本机生成的压缩 BigWig 的 range 索引错误；这是 display-only 资产，原始 BigWig 未变。
- S1_003 实际浏览器检查 0 alert；完整校验与 15 项回归通过。

## 2026-08-13 JBrowse 正负链紧凑视图

- S1_001/003/004/005 默认仅打开基因、正负链配对信号、正负链合并候选端点三条轨道。
- 默认配对信号使用 display-only `sign(strand) × log10(1 + raw signal)`：正链在零线上方，负链在零线下方；原始 BigWig 不变，并保留在 `Full evidence view`。
- 合并端点 BED 保留原 BED6 坐标和 strand；候选仍是 `called_endpoint`，不改述为终止子。
- 构建时发现旧 E. coli viewer BED 被 B. subtilis 同名文件覆盖；现改从各来源 canonical `processed/` 目录复制，并增加 contig/strand 硬检查。核心公开表未受影响。
- JBrowse、Pages、15 项回归和实际浏览器检查全部通过；控制台无 warning/error。

## 2026-08-13 英文与 accession 更新

- 全站当前只输出英文，不显示尚未审校的中文副本或语言按钮；生成标签保留 `data-i18n-key` 供后续语言切换。
- 22 个来源详情页均有 **Raw data accessions** 区域；多个 accession 分别链接到 GEO、SRA、BioProject、ENA 或 BioStudies。
- 参考 assembly accession 可点击跳转 NCBI Datasets；assembly 页面也展示各来源的原始数据入口。
- genome 搜索支持 accession number。
- 完整 Pages 预览、站点校验、14 项回归测试和浏览器检查均通过。

## 2026-08-12 网站改版

- 20 个精确 assembly 作为主目录，22 个来源作为独立 track 和追溯记录；
- `GCF_000739105.1` 与 `GCF_005519465.1` 各有一套自动打开的双来源 JBrowse 视图；
- 下载页可全选/多选，输出按 assembly 分目录的 ZIP；
- 主要公开文件收敛为 BED + metadata，后台 24 列表、字段字典、manifest 与 checksum 不删除；
- 组会教程：[`demo/BTED_组会展示教程_2026-08-12.md`](demo/BTED_组会展示教程_2026-08-12.md)。
- feature 分支 Pages build 已成功，部署环境按策略拒绝非 `main` 分支；合并后 `push: main` 会触发正式部署。

## 已交付

- 22 个来源均有 manifest 和详情页；21 个来源公开标准数据，S1_002 为 `audit_only`。
- 21 个来源共 28,399 条 24 列核心记录；17 个许可允许的来源另有来源特异表。
- 每个公开来源有 BED6、字段清单、manifest 和 checksum。
- 21 套独立 JBrowse 配置；S1_005 的 CP009977.1/CP009978.1 位于同一 assembly。
- 双语静态网站包含首页、筛选目录、下载页、方法页、关于页和 22 个来源页。
- 数据/JBrowse Release 资产、CI、Pages workflow 和本地 Pages staging 已具备。
- S1_005、S1_020、S1_022 的工程审计和处理记录已补齐。
- 外部链接审计已保存为 `data/audit/v0.2.0/external_link_audit.tsv`，无失败或缺失必填入口。
- PR #3 的根目录清理已同步：旧报告和登录号快照归档，重复的 `docs/legacy/original-directories/`、read-starts 与 `__MACOSX` 已退出当前 Git 树；历史未改写。

## 接手前阅读

1. [`docs/releases/v0.2.0.md`](releases/v0.2.0.md)
2. [`docs/standards/BTED_数据入库标准流程_v0.2.md`](standards/BTED_数据入库标准流程_v0.2.md)
3. [`docs/standards/BTED_数据发布接口_v0.2.md`](standards/BTED_数据发布接口_v0.2.md)
4. [`data/public/v0.2.0/release_manifest.json`](../data/public/v0.2.0/release_manifest.json)
5. [`data/registry/batter_s1_publication_status.v0.2.0.tsv`](../data/registry/batter_s1_publication_status.v0.2.0.tsv)

## 重新构建

```bash
python3 scripts/build_v0_2_release.py --input-root /path/to/BGIRNA
python3 scripts/audit_v0_2_priority_sources.py
python3 scripts/build_release_archives.py
python3 scripts/build_jbrowse_release.py --input-root /path/to/BGIRNA
python3 scripts/build_v0_2_site.py
python3 scripts/stage_pages.py --jbrowse-dir dist/BTED-v0.2.0-jbrowse --output-dir .pages-preview
```

## 完整验证

```bash
python3 scripts/validate_bted_templates.py
python3 scripts/validate_bted_release.py
python3 scripts/validate_repo_layout.py
python3 scripts/validate_bted_v0_2.py
python3 scripts/audit_v0_2_priority_sources.py
python3 scripts/validate_jbrowse_release.py dist/BTED-v0.2.0-jbrowse
python3 scripts/validate-site.py site
python3 scripts/validate-site.py .pages-preview
python3 -m unittest -v tests/test_bted_ingestion.py tests/test_bted_v0_2.py
git diff --check
```

## 待完成

1. 审阅已同步 PR #3 结构清理的 Draft PR #4，保持串联 PR 的改动范围清晰。
2. 按 #1 → #2 → #3 → #4 顺序处理 PR 基线，避免直接把全部历史一次展开到 `main`。
3. 评审通过后发布 `v0.2.0` Release，再合并包含 Pages workflow 的分支。
4. 在 Settings → Pages 选择 GitHub Actions，运行部署并检查稳定链接。
5. S1_002 只有在未来能可靠拆出纯实验端点时才改变 `audit_only`。

## 远端发布状态

- 实现提交：`142e371 feat: build BTED v0.2 public demo`。
- 分支：`agent/bted-v0.2-public-demo`，已通过 SSH 推送。
- Draft PR：`https://github.com/LIMwhatnameisavailable/BATTER-Transcription-Terminator-Database/pull/4`，CI 已通过。
- PR #3 结构清理提交：`61318db refactor: clean repository root and legacy assets`。
- `v0.2.0` Release 草稿包含四个发布资产；保持草稿，直至评审和 Pages 发布顺序确认。
- Pages workflow 仅允许手动触发；正式发布 Release 且管理员启用 Pages 后再运行，避免合并时产生预期失败。
- HTTPS OAuth 令牌仍缺少 `workflow` scope；继续推送本分支可使用已验证的 SSH 地址，无需重新构建数据。

## 不要做

- 不把协作者外部文献合入本分支；
- 不把混合证据或纯预测放进公开端点表/JBrowse；
- 不把作者预测注释解释为新的实验结果；
- 不把原始测序、出版商工作簿、大型 JBrowse 文件或凭据提交到 Git；
- 不在未确认参考、坐标、contig、strand 或许可时猜测补齐。

## v0.3 第三阶段 B1 接手说明（2026-08-21）

当前 `feature/bted-v0.3-dynamic-service` 已增加确定性 PostgreSQL 行物化中间层，但仍未
提交或推送。实现入口为 `backend/importer/materialize.py`，CLI 为：

```bash
python3 scripts/import_bted_v03.py materialize \
  --release-root data/public/v0.2.0 \
  --output-dir /tmp/bted-v03-staging \
  --asset-origin-base https://example.test/assets \
  --generated-at-utc 2026-08-21T00:00:00Z
```

真实 v0.2.0 输出的表计数为 1/1/13/20/47/22/32/21/28,399/81,477/0/0/127，顺序对应
release_versions/import_runs/publications/assemblies/contigs/sources/source_accessions/
samples/endpoints/source_annotations/genes/endpoint_gene_context/assets。`BATTER_S1_002`
只生成审计关联行，不生成 endpoint、source annotation 或 JBrowse 资产入口。JSONL 的
`*_ref` 是给未来 writer 解析 PostgreSQL identity 的自然键辅助列，不是 schema 新物理列；
origin URL 仅是 `planned_not_verified` 计划值。

已完成测试：`tests/test_bted_v03_importer.py` 32/32 PASS；包括真实行数、24 列保留、自然
键闭包、附表字段覆盖、预测分层、asset_kind 枚举、非法 origin、非空目录保护、固定时间
重复 checksum、provenance 体积回归和失败校验不生成输出。另有全量
`unittest discover` 64/64、`tests/test_bted_ingestion.py` 4/4、真实 validate 与
`git diff --check` 通过。不要把 `/tmp` bundle 或参考 FASTA/FAI 放入 Git；本任务不实现
writer、psycopg、API 或部署。

### B1 provenance 体积修正

主审反馈后，行级 annotation provenance 已改为紧凑形式：不再在 81,477 行中重复完整
`field_roles`/`field_definitions`，只保留定位、未映射列、endpoint evidence 和必要边界；
作者端点角色映射只记录 `original_evidence_roles`。完整字段字典及
`fields.json`/`source_annotations.tsv` 的 checksum/行数按 source 各写一条到物化 manifest
的 `annotation_field_provenance`，所有路径均相对 release，不含本机绝对路径。真实 bundle
当前约为 77 MiB（附表 JSONL）/115 MiB（总目录），新增 100/150 MiB 体积回归测试；原始
字段联合覆盖和 81,477 行计数不变。旧测试中曾允许的 schema 外 `source_annotation`
asset_kind 已删除。由于 origin 仍是 `planned_not_verified`，所有物化 asset 行的
`supports_range` 均为 `false`；未来通过 HTTP 206 审计后再由资产注册阶段改为 `true`。

## v0.3 第三阶段 B2 接手说明（2026-08-22）

B2 新增 `backend/importer/postgres.py` 和 `tests/test_bted_v03_postgres.py`，并在
`scripts/import_bted_v03.py` 增加三个命令：

```bash
python3 scripts/import_bted_v03.py verify-bundle --bundle-dir /tmp/bted-v03-staging
python3 scripts/import_bted_v03.py load-postgres --bundle-dir /tmp/bted-v03-staging --confirm-write
python3 scripts/import_bted_v03.py promote-postgres --bundle-dir /tmp/bted-v03-staging --confirm-promote
```

第一个命令只做本地 bundle 验证。后两个命令默认不会执行，必须显式确认并从
`BTED_DATABASE_URL`（或 `--database-url-env` 指定的变量）取得 URL；没有 psycopg3、环境变量
或确认参数时安全失败，不打印 URL。`requirements-v03.txt` 只声明
`psycopg[binary]>=3.2,<4`，本轮不安装。

writer 的关键安全边界：

- 事务前流式验证 manifest、SHA256SUMS、每表 checksum/row count、允许/必填字段和自然键
  闭包；拒绝 bundle 根目录额外文件、目录、符号链接及预期文件 symlink；JSON 拒绝 NaN/
  Infinity。
- `assets.origin_url` 必须 HTTPS 且 hostname 与 `origin_host` 一致；
  `planned_not_verified` 时 `supports_range` 必须为 false，不把计划远端能力当作事实。
- 事务顺序固定为 release/import → publication/assembly → contig → source → accession/
  sample → endpoint → annotation → asset → global/per-source count audit；使用 SERIALIZABLE、
  advisory lock、参数化 SQL、批量 endpoint/annotation，异常 rollback，无 DROP/TRUNCATE/
  无条件 DELETE。
- 已有 publication/assembly/contig 只有完整自然键字段兼容时复用；已有 release 整批拒绝。
  非 published source 不能有 endpoint/sample，S1_002 必须零 endpoint/annotation/JBrowse。
- `load-postgres` 的目标 release 保持 staged/validated 且 `is_current=false`。promotion
  还需 bundle 与最新 committed import run 的 `asset_origin_status=verified`，并重复计数审计；
  当前 v0.2 B1 bundle 是 `planned_not_verified`，不能 promotion。

### B2 验证与下一步

`tests/test_bted_v03_postgres.py` 当前 12/12 通过，涵盖真实 bundle 计数、批量边界、fake
transaction commit/rollback、自然键兼容/冲突、重复 release、tamper/extra/symlink、origin/
Range、严格 JSON 和 promotion 拒绝。另需运行：

```bash
python3 -m unittest discover -s tests -p 'test*.py' -q
python3 -m unittest -v tests/test_bted_ingestion.py
python3 scripts/import_bted_v03.py validate --release-root data/public/v0.2.0
python3 scripts/import_bted_v03.py verify-bundle --bundle-dir /tmp/bted-b1-range-final
git diff --check
```

以上离线测试不等同于真实数据库 smoke test。下一步应在隔离 PostgreSQL 实例执行
`backend/database/schema.sql`，用测试凭据验证完整 load、重复 release 拒绝、已有自然键
兼容/冲突、事务回滚、global/per-source count audit；在远程资产完成 HTTP 206 审计前不应
标记 verified 或发布当前 release。不要提交 `/tmp` bundle、FASTA/FAI、数据库 URL 或凭据。

## C1 只读 API 接手说明（2026-08-22）

新增文件：

- `backend/app/contracts.py`：无框架的 release/page/repository contracts；
- `backend/app/errors.py`：统一 404/422 API error；
- `backend/app/repository.py`：参数化 PostgreSQL read repository，每个操作独立清理连接；
- `backend/app/service.py`：release、分页、排序、证据边界、下载和 audit-only 规则；
- `backend/app/main.py`：可注入 fake repository 的 FastAPI `create_app()`；
- `tests/test_bted_v03_api.py`：service/repository 离线测试和可选 HTTP contract tests。

当前路由为 `/api/v1/health`、`stats`、`sources`、`assemblies`、`endpoints`、`genes`、
`augmentation`、`downloads/endpoints`。列表/详情返回 release provenance；endpoint 保留
24 列；TSV 是原值下载，BED6 的 score 是 `0` 格式占位，不能解释为 coverage。endpoint
SQL 和 download source 校验只接受 `published_standardized`，S1_002 会 404，不生成空下载。
endpoint 详情保留 24 列中的 PMID/DOI，并提供 source-annotation 行数/kind 摘要；完整
publication 信息从 source detail 获取，没有摘要的 fake 结果会明确标记 `not_loaded_in_c1`。

C1 暂不实现 `/api/v1/assets/{asset_id}`、HEAD/Range、Next.js/JBrowse 资产服务、附表下载、
真实 PostgreSQL smoke test 或部署。由于 asset route 尚未存在，source 详情中已登记 JBrowse
config 返回 null 与 pending note，不产生裸 asset ID 死链接；下一阶段实现同源 asset route
后再恢复可点击 JBrowse URL。FastAPI/uvicorn/httpx/psycopg3 仅在
`requirements-v03.txt` 声明，当前环境未安装。

验证命令：

```bash
python3 -m unittest -q tests/test_bted_v03_api.py
python3 -m unittest discover -s tests -p 'test*.py' -q
python3 -m unittest -q tests/test_bted_ingestion.py
git diff --check
```

缺少 FastAPI 时 API runtime tests 会 skipped；这是预期，不得写成 HTTP smoke test 已通过。
安装依赖后再用 `TestClient(create_app(fake_repository))`，最后在隔离 PostgreSQL 中以显式
`BTED_DATABASE_URL` 运行只读查询和 schema smoke test。不要在本任务安装依赖、连接生产库、
修改 v0.2 canonical 数据或提交凭据。
