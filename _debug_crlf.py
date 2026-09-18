#!/usr/bin/env python3
"""Compare working-tree SHA256 vs git-object SHA256 to detect CRLF/LF issues."""
import hashlib, subprocess, glob

def git_sha256(rel_path):
    rel = rel_path.replace("\\", "/")
    try:
        raw = subprocess.check_output(["git", "show", "HEAD:" + rel], stderr=subprocess.DEVNULL)
        return hashlib.sha256(raw).hexdigest()
    except:
        raw = open(rel_path, "rb").read()
        return hashlib.sha256(raw).hexdigest()

paths = ["data/public/v0.2.0/release_manifest.json"]
paths.append("data/public/v0.2.0/SHA256SUMS.txt")
for d in sorted(glob.glob("data/public/v0.2.0/records/BATTER_S1_*/SHA256SUMS.txt")):
    paths.append(d)

diffs = 0
for p in paths:
    ws = hashlib.sha256(open(p, "rb").read()).hexdigest()
    gs = git_sha256(p)
    if ws != gs:
        print(f"DIFF {p}: ws={ws[:16]} git={gs[:16]}")
        diffs += 1
if diffs == 0:
    print("All checksums match - no CRLF issue!")
else:
    print(f"{diffs} files differ - CRLF issues!")