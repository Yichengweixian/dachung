"""Short Windows entry; freeze the complete preceding study evidence closure."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.freeze_study import main


if __name__ == "__main__":
    folder = ROOT/"results/annual/U11R12-v01"
    record = json.loads((folder/"run_manifest.json").read_text(encoding="utf-8"))
    paths = set(record["freeze"]["sha256"]) | set(record["source_sha256"])
    paths |= {(folder/name).relative_to(ROOT).as_posix() for name in record["artifacts"]}
    paths |= {"results/annual/U11R12-v01/run_manifest.json",
              "instructions/studies/U11R12-input-shortage-proxy/freeze.json",
              "results/annual/U11R13-predecessor-audit-v01.json",
              "scripts/freeze_day_weight_accounting.py"}
    sys.argv = [sys.argv[0], "U11R13-day-weight-accounting"]
    for path in sorted(paths):
        sys.argv.extend(["--input",path])
    main()
