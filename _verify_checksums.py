#!/usr/bin/env python3
"""Verify SHA256SUMS.txt entries match git-object content (LF)."""
import hashlib, subprocess, glob

records = sorted(glob.glob("data/public/v0.2.0/records/BATTER_S1_*"))
all_ok = True

for rdir in records:
    sid = rdir.split("/")[-1]
    spath = rdir + "/SHA256SUMS.txt"
    lines = open(spath, "rb").read().decode("utf-8").strip().split("\n")
    for line in lines:
        expected, fname = line.split("  ", 1)
        git_path = rdir.replace("\\", "/") + "/" + fname
        try:
            content = subprocess.check_output(["git", "show", "HEAD:" + git_path])
            actual = hashlib.sha256(content).hexdigest()
        except Exception as e:
            print(f"ERROR {sid}/{fname}: {e}")
            all_ok = False
            continue
        if actual != expected:
            print(f"FAIL {sid}/{fname}: expected={expected[:16]} actual={actual[:16]}")
            all_ok = False

if all_ok:
    print("All checksums match git-object content (LF)!")

# Also check release_manifest.json
print("\nChecking release_manifest.json...")
try:
    mf_content = subprocess.check_output(["git", "show", "HEAD:data/public/v0.2.0/release_manifest.json"])
    mf_actual = hashlib.sha256(mf_content).hexdigest()
    root_sum = open("data/public/v0.2.0/SHA256SUMS.txt", "rb").read().decode("utf-8").strip()
    mf_expected = root_sum.split("  ", 1)[0]
    if mf_actual == mf_expected:
        print("release_manifest.json checksum: OK")
    else:
        print(f"FAIL release_manifest.json: expected={mf_expected[:16]} actual={mf_actual[:16]}")
except Exception as e:
    print(f"ERROR: {e}")