# BTED v0.3 Cloudflare preview deployment

当前可执行部署路线是一个 Cloudflare Worker + D1 + Worker Static Assets
deployment。它复用仓库现有的 `site/` 静态 UX，Worker 负责 `/api/*` 查询、动态
JBrowse config 和登记资产的同源 GET/HEAD/单 Range 代理。现有 FastAPI/PostgreSQL/Next.js
实现保留为 future/alternative，不是本路线的依赖；Render/Neon/Vercel 不在当前任务中创建。

## 已验证的输入

- canonical `release_version` 保持 `v0.2.0`；D1 行的 `status=preview` 只是查询投影，
  不是 promotion 或新的 `v0.3.0` data release。
- verified bundle 来源为固定 Hugging Face revision：
  `https://huggingface.co/datasets/seu-yolo/BTED-v0.3-assets/resolve/d12190e434057edaf2c2bdbf19132f1e41873c38`。
- bundle materializes 22 sources、20 release assemblies、49 contigs、32 accessions、
  211 registered assets（164 public）、22 tracks 和 28,399 endpoints；19 sources
  qualify for source-level augmentation。source annotations 保留在 HF/metadata asset，
  genes 未进入 D1，因为当前 catalogue 页面/API 不查询它们。
- 164 public objects 已由固定 revision 的真实 audit 通过 HEAD 200 + 单 Range 206；
  private/external 47 项只留 D1 登记和不可代理状态。

## Worker 配置

`prototype/accession-range/wrangler.jsonc` 是唯一当前部署配置：

- `assets.directory` 指向仓库既有 `site/`，不重做页面；
- D1 binding 名为 `BTED_DB`，数据库名为 `bted-catalogue-v03-preview`；
- `HF_RESOLVE_BASE` 已固定到上述 revision，`ALLOWED_ORIGIN_HOST` 为
  `huggingface.co`；
- `database_id` 在远程 D1 创建后才填入，不把 token、密码或个人 URL 写进 Git。

## 生成并导入 D1

生成器只读取 verified bundle，并把可重建 SQL 批次写到仓库外的明确临时目录；不会在 Git
中写入巨型 seed：

```bash
python3 scripts/generate_bted_d1.py \
  --bundle-dir /path/to/verified-bundle \
  --output-dir /private/tmp/bted-v03-d1-import \
  --batch-size 1000
```

生成 `schema.sql`、`00_release.sql` 到 `07_tracks.sql`、分片的
`08_endpoints_*.sql` 和 `IMPORT_SUMMARY.json`。首次创建本地 D1 后按文件名顺序执行：

```bash
npx wrangler d1 execute bted-catalogue-v03-preview --local \
  --file /private/tmp/bted-v03-d1-import/schema.sql \
  --config prototype/accession-range/wrangler.jsonc

for f in /private/tmp/bted-v03-d1-import/[0-8][0-9]*.sql; do
  npx wrangler d1 execute bted-catalogue-v03-preview --local \
    --file "$f" --config prototype/accession-range/wrangler.jsonc || exit 1
done
```

Wrangler 4.125 的 local D1 executor 不接受 SQL 文件中的显式 `BEGIN/COMMIT`；生成器让
D1 自己处理 statement batching。实际 smoke 的最终计数为 1 release、13 publications、
20 assemblies、49 contigs、22 sources、32 accessions、211 assets、22 tracks 和 28,399
endpoints。生成批次和 `.wrangler/` local state 都是临时物，不应提交。

## Local Worker smoke

以有界进程运行，不要将 `wrangler dev` 作为交互式后台服务遗留：

```bash
npx wrangler dev --local \
  --config prototype/accession-range/wrangler.jsonc \
  --port 8787 --ip 127.0.0.1
```

至少检查：

```text
/api/health
/api/stats
/api/catalogue?page_size=1
/api/sources
/api/sources/{source_id}
/api/assemblies
/api/assemblies/{accession}
/api/endpoints?page_size=1
/api/endpoints/{end_id}
/api/augmentation
/api/assemblies/{accession}/jbrowse-config
/api/assets/{registered_public_asset_key}       HEAD and Range: bytes=0-0
/api/remote-data/{registered_public_asset_key}  alias
```

`/api/assets/*` 只接受 D1 中登记、active、public 的 key；`?url=`、private asset、未知
key 和未列入 allowlist 的 origin 必须被拒绝。实际本地 smoke 结果：health/stats/catalogue/
sources/assemblies/endpoints/augmentation/JBrowse 均 200；FASTA 与 BED HEAD 为 200、单字节
Range 为 206；任意 origin 尝试为 400；缺 public FASTA+FAI 的 assembly 返回 404。

## Remote Cloudflare gate

本轮只做了短的非交互检查：

```bash
CI=1 npx wrangler whoami
```

当前结果是 `You are not authenticated`，因此没有创建远程 D1、没有部署 Worker，也没有
产生线上 URL。最短人工步骤是用户在自己的终端运行一次 `npx wrangler login` 完成浏览器
授权，然后重新运行 `npx wrangler whoami`。登录后才可以在免费/preview 范围内：

1. `npx wrangler d1 create bted-catalogue-v03-preview`；将返回的 database id 写入本地
   未提交配置（或用部署环境注入），再运行上面的远程 schema/import；
2. `npx wrangler deploy --config prototype/accession-range/wrangler.jsonc`；
3. 用部署输出的 Worker URL 重跑同一组 HTTP、JBrowse 和 Range smoke，并把 URL、导入计数
   和审计结果补入 `WORKLOG.md`/`HANDOFF.md`。

不要在 Git、shell history、日志或聊天中粘贴 API token、密码或带凭据的 URL；不要使用
`--remote`，直到 D1 id 已由登录用户明确创建并核对为目标 preview 数据库。
