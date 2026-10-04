"""Freeze the U11R14 closure, the reused modules and the saved annual inputs for U11R15."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.freeze_study import main

SEEDS = (42, 7, 2026)


if __name__ == "__main__":
    folder = ROOT / "results/annual/U11R14-v01"
    m = json.loads((folder / "run_manifest.json").read_text(encoding="utf-8"))
    paths = set(m["freeze"]["sha256"]) | set(m["source_sha256"])
    paths |= {(folder / name).relative_to(ROOT).as_posix() for name in m["artifacts"]}
    paths |= {
        "results/annual/U11R14-v01/run_manifest.json",
        "instructions/studies/U11R14-proxy-energy-feasibility/freeze.json",
        "results/annual/U11R14-v01-independent-audit.json",
        "results/annual/U11R14-v01-independent-audit-v02.json",
        # reused, read-only modules
        "src/input_energy_feasibility.py",
        "src/cbc_weight_evidence.py",
        "src/annual_clustering.py",
        "src/fixed_weights_capacity_transfer.py",
        "src/study_runtime.py",
        "src/data_loader.py",
        "scripts/audit_u11r08_feasibility.py",
        "scripts/freeze_study.py",
        "scripts/freeze_stable_weight_selection.py",
        ".venv/Lib/site-packages/pulp/solverdir/cbc/win/i64/cbc.exe",
        # annual inputs and baselines read by the runner and the audit
        "results/annual/U11R02-v01/input_8760h.csv",
        "results/annual/U11R02-v01/full_annual.csv",
        "results/annual/U11R02-v01/daily_summary.csv",
        "results/annual/U11R08B-v01/run_manifest.json",
        "results/annual/U11R12-v01/run_manifest.json",
    }
    for seed in SEEDS:
        paths |= {p.relative_to(ROOT).as_posix()
                  for p in (ROOT / "results/annual/U11R12-v01").glob(f"N48_seed{seed}_*.csv")}
        paths |= {p.relative_to(ROOT).as_posix()
                  for p in (ROOT / "results/annual/U11R08B-v01").glob(f"N48_seed{seed}_labels.csv")}
    missing = sorted(p for p in paths if not (ROOT / p).exists())
    if missing:
        raise SystemExit("Missing frozen dependencies: " + repr(missing[:10]))
    sys.argv = [sys.argv[0], "U11R15-stable-weight-selection"]
    for path in sorted(paths):
        sys.argv.extend(["--input", path])
    main()
