# BTED Handoff

Use this file to transfer work between Kimi, OpenAI, or collaborators. Replace the filled handoff for each transfer; keep the durable decision in the relevant source processing record.

## Handoff — 2026-08-18 — BTED v0.2 GitHub Pages 静态发布

### Objective

将 `feature/research-user-dataset-context-v0.1` 上已收敛的核心字段 accession 页面迁移到 GitHub Pages 可用的纯静态实现，完成个人仓库部署和线上验证。

### 已完成

- 本地代码、数据、测试全部通过（21/21 测试，全部校验脚本 PASS）。
- `integration/bted-v0.2-site-release` 已推送到 `seu-yolo/BATTER-Transcription-Terminator-Database`。
- PR #2 已创建并合并到 `seu-yolo/main`：merge commit `f9b3205926b8223f7427d1f7e8758ab0b267bc92`。
- GitHub Actions `Deploy BTED Pages` run `32054805656` 已完成并成功部署。
- 线上地址：https://seu-yolo.github.io/BATTER-Transcription-Terminator-Database/

### 主要改动文件

- `scripts/build_v0_2_site.py`：新增 `build_assemblies_json()` 生成 `site/data/assemblies.json`。
- `site/assets/accession-range-demo.js`：改为静态 JSON 查找；移除 `/api/assemblies` 和 localhost。
- `site/css/style.css`：新增 `.source-status-badge` 状态标签样式。
- `site/data/assemblies.json`：新增静态 accession 数据（自动生成）。
- `scripts/validate-site.py`：新增 localhost/API 依赖扫描。
- `scripts/validate_repo_layout.py`：允许 `prototype/` 顶层目录。
- `tests/test_bted_v0_2.py`：新增 `test_static_assemblies_json_powers_accession_search`。

### 数据边界

- 22 个来源 / 20 个组装 / 28,399 条核心记录未变。
- S1_002 仍为 `audit_only`；Rend-seq 来源为 `signal_endpoints`；其余为 `endpoints_only`。
- 未修改任何端点坐标、BED、证据类别或记录数。

### Release/JBrowse 资产

- Release tag：`preview-v0.2.0`
- 资产：`BTED-v0.2.0-jbrowse-assets.tar.gz`（2026-08-17 18:24 UTC 替换为包含 `.gff3` 等完整资产的版本）
- 替换原因：GitHub 上原有 asset 为 2026-08-10 版本，缺少本地 dist 中已验证的 `BATTER_S1_001__ecoli_geneproximal.combined.browser.gff3`，导致 Pages 部署时 `validate_jbrowse_release.py` 失败。
- 校验文件：`BTED-v0.2.0-jbrowse-assets.tar.gz.sha256` 已同步更新。

### 线上验证清单（HTTP 200 已确认）

- 首页：https://seu-yolo.github.io/BATTER-Transcription-Terminator-Database/
- Genomes 目录：https://seu-yolo.github.io/BATTER-Transcription-Terminator-Database/sources.html
- accession 查询（EN）：https://seu-yolo.github.io/BATTER-Transcription-Terminator-Database/accession-range-demo.html?accession=GCF_000739105.1&lang=en
- accession 查询（ZH）：https://seu-yolo.github.io/BATTER-Transcription-Terminator-Database/accession-range-demo.html?accession=GCF_000739105.1&lang=zh
- `GCF_000739105.1` assembly 页：https://seu-yolo.github.io/BATTER-Transcription-Terminator-Database/assemblies/GCF_000739105.1.html
- `BATTER_S1_003` Rend-seq 记录页：https://seu-yolo.github.io/BATTER-Transcription-Terminator-Database/records/BATTER_S1_003.html
- JBrowse 配置：https://seu-yolo.github.io/BATTER-Transcription-Terminator-Database/jbrowse/assemblies/GCF_000739105.1.config.json
- BED 下载：https://seu-yolo.github.io/BATTER-Transcription-Terminator-Database/downloads/assemblies/GCF_000739105.1/endpoints.bed
- metadata 下载：https://seu-yolo.github.io/BATTER-Transcription-Terminator-Database/downloads/assemblies/GCF_000739105.1/metadata.json

### 建议的下一步

1. 在真实浏览器中打开线上 accession 页面，确认：
   - 默认加载 `GCF_000739105.1` 后显示 2 个来源、2,848 条记录；
   - 中英文切换正常；
   - JBrowse 按钮打开后能看到 1 个共享参考 + 2 条独立来源 track；
   - Rend-seq 页面（如 S1_003）能看到 BigWig peak；
   - S1_002 页面没有 JBrowse 按钮；
   - 浏览器控制台无 404/CORS/JS 错误。
2. 如需更新数据，修改来源 manifest/registry 后重跑：
   ```bash
   python3 scripts/build_v0_2_site.py
   python3 scripts/build_assembly_downloads.py --output-dir dist/assembly-downloads
   python3 scripts/validate-site.py site
   python3 -m unittest -v tests/test_bted_ingestion.py tests/test_bted_v0_2.py tests/test_accession_range_prototype.py
   ```
3. 如需更新 JBrowse 大型资产：
   - 重新生成 `dist/BTED-v0.2.0-jbrowse`；
   - 建议创建新 Release tag（如 `preview-v0.2.1`）并更新 `.github/workflows/pages.yml` 中的 `RELEASE_TAG`；
   - 不要静默覆盖已发布版本而不记录。
4. 个人仓库 `main` 已部署；上游 `LIMwhatnameisavailable` 仓库未动，如需同步需单独提 PR。
