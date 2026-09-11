#!/usr/bin/env python3
"""Regenerate SHA256SUMS.txt and release_manifest.json using git-object content (LF line endings).
This ensures checksums match what CI (Linux) would compute, bypassing local CRLF conversion."""
import hashlib, subprocess, json, os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RELEASE = REPO / "data/public/v0.2.0"
MANIFEST_PATH = RELEASE / "release_manifest.json"

def git_obj_sha256(git_path):
    """Compute SHA-256 of a file as stored in git (always LF line endings)."""
    try:
        content = subprocess.check_output(["git", "show", "HEAD:" + git_path], cwd=REPO, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        # File not in HEAD yet, read from working tree
        content = (REPO / git_path).read_bytes()
    return hashlib.sha256(content).hexdigest()

def git_read_text(git_path):
    """Read a text file from git object (always LF)."""
    try:
        return subprocess.check_output(["git", "show", "HEAD:" + git_path], cwd=REPO, stderr=subprocess.DEVNULL).decode("utf-8")
    except subprocess.CalledProcessError:
        return (REPO / git_path).read_text(encoding="utf-8")

def sha256_of_file(path):
    """Compute SHA-256 of a file on disk, normalizing CRLF to LF."""
    content = path.read_bytes()
    content = content.replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


# ── 1. Regenerate per-source SHA256SUMS.txt ──────────────────────────
source_dirs = sorted([d for d in (RELEASE / "records").iterdir() if d.is_dir() and d.name.startswith("BATTER_S1_")])
updated_sums = 0

for sdir in source_dirs:
    sid = sdir.name
    git_dir = "data/public/v0.2.0/records/" + sid
    checksum_path = sdir / "SHA256SUMS.txt"

    # List all files in the directory (except SHA256SUMS.txt itself)
    files = sorted(f.name for f in sdir.iterdir() if f.is_file() and f.name != "SHA256SUMS.txt")

    lines = []
    for fname in files:
        chk = git_obj_sha256(git_dir + "/" + fname)
        lines.append(chk + "  " + fname)

    new_content = "\n".join(lines) + "\n"
    old_content = checksum_path.read_text(encoding="utf-8") if checksum_path.exists() else ""

    if new_content != old_content:
        checksum_path.write_text(new_content, encoding="utf-8", newline="")
        print(f"Updated {sid}/SHA256SUMS.txt")
        updated_sums += 1

# ── 2. Regenerate release_manifest.json checksums ───────────────────
manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
updated_manifest = 0

for sid, src in manifest["sources"].items():
    rec_root_rel = src["record_root"].replace("data/public/v0.2.0/", "")
    for f in src["files"]:
        fp_rel = src["record_root"] + "/" + f["path"]
        actual = git_obj_sha256(fp_rel)
        if actual != f["sha256"]:
            print(f"  manifest {sid}: {f['path']} {f['sha256'][:12]} -> {actual[:12]}")
            f["sha256"] = actual
            updated_manifest += 1

# Release-root checksum
if "release_root_checksum" in manifest:
    actual = sha256_of_file(RELEASE / "SHA256SUMS.txt")
    if actual != manifest["release_root_checksum"]:
        print(f"  release-root: {manifest['release_root_checksum'][:12]} -> {actual[:12]}")
        manifest["release_root_checksum"] = actual
        updated_manifest += 1

if updated_manifest:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="")

# ── 3. Regenerate release-root SHA256SUMS.txt ───────────────────────
root_chk = sha256_of_file(RELEASE / "release_manifest.json")
root_content = root_chk + "  release_manifest.json\n"
root_path = RELEASE / "SHA256SUMS.txt"
if root_path.read_text(encoding="utf-8") != root_content:
    root_path.write_text(root_content, encoding="utf-8", newline="")
    print("Updated release-root SHA256SUMS.txt")

print(f"\nDone: {updated_sums} source sums, {updated_manifest} manifest entries updated")