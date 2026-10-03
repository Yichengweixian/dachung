"""Short Windows freeze entry point; pin the preceding evidence closure."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.freeze_study import main


if __name__ == "__main__":
    folder = ROOT/"results/annual/U11R11-v01"
    m = json.loads((folder/"run_manifest.json").read_text(encoding="utf-8"))
    paths = set(m["freeze"]["sha256"]) | set(m["source_sha256"])
    paths |= {(folder/name).relative_to(ROOT).as_posix() for name in m["artifacts"]}
    paths |= {"results/annual/U11R11-v01/run_manifest.json",
              "instructions/studies/U11R11-cost-unserved-attribution/freeze.json",
              "results/annual/U11R12-predecessor-audit-v01.json",
              "scripts/freeze_input_shortage_proxy.py"}
    sys.argv = [sys.argv[0], "U11R12-input-shortage-proxy"]
    for path in sorted(paths):
        sys.argv.extend(["--input", path])
    main()
