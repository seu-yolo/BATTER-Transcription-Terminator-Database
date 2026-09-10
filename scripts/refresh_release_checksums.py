#!/usr/bin/env python3
"""Update release_manifest.json SHA-256 checksums to match actual files."""
import hashlib, json
from pathlib import Path

MANIFEST = Path(r'D:\SEU\实习\BATTER数据整理\BTED\repo\data\public\v0.2.0\release_manifest.json')
ROOT = Path(r'D:\SEU\实习\BATTER数据整理\BTED\repo\data\public\v0.2.0')

def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

manifest = json.loads(MANIFEST.read_text('utf-8'))
problems = []
updated = 0

for sid, src in manifest['sources'].items():
    rec_root = ROOT / src['record_root'].replace('data/public/v0.2.0/', '')
    for f in src['files']:
        fp = rec_root / f['path']
        if not fp.exists():
            problems.append(f'{sid}: {f["path"]} missing')
            continue
        actual = sha256(fp)
        if actual != f['sha256']:
            print(f'  {sid}: {f["path"]} {f["sha256"][:12]} -> {actual[:12]}')
            f['sha256'] = actual
            updated += 1

# Release-root checksum
if 'release_root_checksum' in manifest:
    fp = ROOT / 'SHA256SUMS.txt'
    if fp.exists():
        actual = sha256(fp)
        if actual != manifest['release_root_checksum']:
            print(f'  release-root: {manifest["release_root_checksum"][:12]} -> {actual[:12]}')
            manifest['release_root_checksum'] = actual
            updated += 1

if not problems:
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'\nOK: {updated} checksum(s) updated across {len(manifest["sources"])} sources')
else:
    print(f'\n{len(problems)} problem(s):')
    for p in problems:
        print(f'  {p}')