#!/usr/bin/env python3
"""Modify BTED v0.2 production overlay JBrowse configs to add dual signal tracks.

Existing single signal track (uses signed-log10 BigWigs) is preserved as
the "log" optional track (default_off: true). A new "linear (raw)" track
is added (default_off: false), referencing the untransformed .bw files.

This is the production counterpart of add_dual_tracks.py (which only touched
the local preview site). Both raw and log BigWig assets already exist in the
preview-v0.2.0 release bundle — only the config overlays need updating.
"""

import json
import copy
from pathlib import Path

OVERLAY_DIR = Path(__file__).resolve().parent.parent / "data/public/v0.2.0/jbrowse-config-overlays"
SOURCES = ["BATTER_S1_001", "BATTER_S1_003", "BATTER_S1_004", "BATTER_S1_005"]


def rewrite_config(source_id: str) -> None:
    config_path = OVERLAY_DIR / f"{source_id}.config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    tracks = config.get("tracks", [])
    signal_track_index = None
    signal_track = None
    for i, t in enumerate(tracks):
        if t.get("type") == "MultiQuantitativeTrack" and t.get("trackId", "").endswith("strand_aware_3prime_signal"):
            signal_track_index = i
            signal_track = t
            break

    if signal_track is None:
        print(f"  WARN: no signal track found, skipping")
        return

    prefix = signal_track["trackId"]

    # --- Track A: Log (existing track, modified) ---
    log_track = copy.deepcopy(signal_track)
    log_track["trackId"] = f"{prefix}_log"
    log_track["name"] = "Signal · log display"
    log_track["description"] = (
        "Paired strand-specific signal, displayed as sign × log10(1 + raw value) "
        "to compress dynamic range. Blue values above zero denote the + strand; "
        "orange values below zero denote the − strand. Raw untransformed strand tracks "
        "remain available in Full evidence view."
    )
    for disp in log_track.get("displays", []):
        old_id = disp.get("displayId", "")
        if old_id.endswith(f"{prefix}-MultiLinearWiggleDisplay"):
            disp["displayId"] = f"{prefix}_log-MultiLinearWiggleDisplay"

    if "metadata" not in log_track:
        log_track["metadata"] = {}
    log_track["metadata"]["display_transform"] = "sign(strand) * log10(1 + raw_signal)"
    log_track["metadata"]["default_off"] = True

    # --- Track B: Linear (raw) — cloned from log, but URIs point to raw .bw ---
    raw_track = copy.deepcopy(log_track)
    raw_track["trackId"] = f"{prefix}_raw"
    raw_track["name"] = "Signal · linear (raw)"
    raw_track["description"] = (
        "Paired strand-specific signal from one experiment, displayed as raw values (1:1). "
        "Blue values above zero denote the + strand; orange values below zero denote "
        "the − strand. Negative values encode strand only, not negative experimental abundance."
    )
    for disp in raw_track.get("displays", []):
        old_id = disp.get("displayId", "")
        if old_id.endswith(f"{prefix}_log-MultiLinearWiggleDisplay"):
            disp["displayId"] = f"{prefix}_raw-MultiLinearWiggleDisplay"

    # Point subadapter URIs to raw .bw (strip signed-log10-ui-v4 suffix)
    for sa in raw_track["adapter"]["subadapters"]:
        uri = sa["bigWigLocation"]["uri"]
        new_uri = uri.replace(".signed-log10-ui-v4.bw", ".bw")
        sa["bigWigLocation"]["uri"] = new_uri

    raw_track["metadata"]["display_transform"] = "raw (1:1)"
    raw_track["metadata"]["default_off"] = False

    # --- Replace the original signal track with both ---
    tracks[signal_track_index] = log_track
    tracks.insert(signal_track_index + 1, raw_track)

    # --- Update default session ---
    default_session = config.get("defaultSession")
    if default_session:
        for view in default_session.get("views", []):
            view_tracks = view.get("tracks", [])
            new_view_tracks = []
            for vt in view_tracks:
                vt_conf = vt.get("configuration", "")
                if vt_conf == prefix:
                    # Log track (default minimized in session)
                    new_view_tracks.append({
                        "id": vt["id"] + "_log",
                        "type": vt["type"],
                        "configuration": f"{prefix}_log",
                        "minimized": True,
                        "displays": [
                            {
                                "id": vt["displays"][0]["id"] + "_log" if vt.get("displays") else f"{prefix}_log_display",
                                "type": vt["displays"][0]["type"] if vt.get("displays") else "MultiLinearWiggleDisplay",
                                "configuration": f"{prefix}_log-MultiLinearWiggleDisplay"
                            }
                        ]
                    })
                    # Raw track (default visible in session)
                    new_view_tracks.append({
                        "id": vt["id"] + "_raw",
                        "type": vt["type"],
                        "configuration": f"{prefix}_raw",
                        "minimized": False,
                        "displays": [
                            {
                                "id": vt["displays"][0]["id"] + "_raw" if vt.get("displays") else f"{prefix}_raw_display",
                                "type": vt["displays"][0]["type"] if vt.get("displays") else "MultiLinearWiggleDisplay",
                                "configuration": f"{prefix}_raw-MultiLinearWiggleDisplay"
                            }
                        ]
                    })
                else:
                    new_view_tracks.append(vt)
            view["tracks"] = new_view_tracks

    config["tracks"] = tracks
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  OK — log track: {log_track['trackId']}, raw track: {raw_track['trackId']} ")


def main():
    for sid in SOURCES:
        print(f"\n{sid}:")
        rewrite_config(sid)


if __name__ == "__main__":
    main()