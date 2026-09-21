"""Freeze a study's specifications, current input files and configuration."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser()
    p.add_argument("unit")
    p.add_argument("--input", action="append", default=["data/input_24h.csv"])
    a = p.parse_args()
    unit = ROOT / "instructions/studies" / a.unit
    files = sorted(p for p in unit.glob("*.md") if p.name != "findings.md")
    files += sorted((ROOT / "config").glob("*.json"))
    files += [ROOT / n for n in a.input]
    record = {"frozen_at":datetime.now(timezone.utc).isoformat(), "unit":a.unit,
              "git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip(),
              "sha256":{f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
              "config":{f.name:json.loads(f.read_text(encoding="utf-8")) for f in (ROOT/"config").glob("*.json")}}
    with (unit / "freeze.json").open("x",encoding="utf-8") as f:
        json.dump(record,f,ensure_ascii=False,indent=2)
    print("Frozen", a.unit)

if __name__ == "__main__":
    main()
