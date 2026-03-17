#!/usr/bin/env python3
"""
One-time script: strip credential references and replace hardcoded IPs from n8n workflow JSONs.
Run from project root. Reads from paths given as args, writes to n8n/workflows/.
"""
import json
import re
import sys
from pathlib import Path

def sanitize(obj):
    """Remove credentials from nodes; replace private IP with placeholder."""
    if isinstance(obj, dict):
        if "nodes" in obj:
            for node in obj["nodes"]:
                node.pop("credentials", None)
                node.pop("webhookId", None)
            return obj
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(i) for i in obj]
    return obj

def main():
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "n8n" / "workflows"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Map: (source path, output filename). Pass paths as args or use defaults.
    if len(sys.argv) >= 2:
        # Usage: python sanitize_workflows.py "C:\path\to\file1.json" "out1.json" ...
        args = sys.argv[1:]
        inputs = [(Path(args[i]), Path(args[i + 1]).name) for i in range(0, len(args) - 1, 2)]
        if len(args) % 2 != 0:
            inputs.append((Path(args[-1]), Path(args[-1]).name))
    else:
        inputs = [
            (Path(r"c:\Users\alamo\Downloads\Feed Playlist (Youtube API) (2).json"), "Feed Playlist (Youtube API).json"),
            (Path(r"c:\Users\alamo\Downloads\Daily Upload Count Reset.json"), "Daily Upload Count Reset.json"),
            (Path(r"c:\Users\alamo\Downloads\Upload Shorts (Schedule, Postgres, YouTube) cursor v2 (1).json"), "Upload Shorts (Schedule, Postgres, YouTube).json"),
            (Path(r"c:\Users\alamo\Downloads\Index Shorts (Transcribe, Classify, to DB) (1).json"), "Index Shorts (Transcribe, Classify, to DB).json"),
            (Path(r"c:\Users\alamo\Downloads\Create Shorts (Playlist, Create Clips, Render Clips).json"), "Create Shorts (Playlist, Create Clips, Render Clips).json"),
        ]

    for src, out_name in inputs:
        if isinstance(out_name, Path):
            out_name = out_name.name
        src = src.resolve()
        if not src.exists():
            print(f"Skip (not found): {src}")
            continue
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = sanitize(data)
        raw = json.dumps(data, indent=2, ensure_ascii=False)
        raw = raw.replace("http://10.0.0.145:9010", "http://whisper-asr:9010")
        out_path = out_dir / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(raw)
        print(f"Wrote: {out_path}")

if __name__ == "__main__":
    main()
