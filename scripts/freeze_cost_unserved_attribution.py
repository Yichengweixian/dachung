"""Avoid Windows command-line limits while using the existing study freezer."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.freeze_study import main as freeze_main


def main():
    files = ["results/annual/U11R11-predecessor-audit-v01.json",
             "results/annual/U11R11-freeze-attempt-v01.json",
             "results/annual/U11R02-v01/input_8760h.csv", "results/annual/U11R02-v01/full_annual.csv",
             "results/annual/U11R02-v01/daily_summary.csv", "results/annual/U11R02-v01/run_manifest.json",
             "results/annual/U11R08B-v01/run_manifest.json", "results/annual/U11R08B-v01/comparison.csv",
             "results/annual/U11R10-v01/run_manifest.json", "results/annual/U11R10-v01/comparison.csv",
             "results/annual/U11R10-v01/full_annual.csv", "src/optimization_validation.py",
             "src/economic_model.py", "src/fixed_weights_capacity_transfer.py",
             "scripts/independent_dispatch_audit.py", "scripts/audit_fixed_weights_capacity_transfer.py",
             "scripts/freeze_cost_unserved_attribution.py", "scripts/freeze_study.py", "requirements.txt"]
    for seed in (42, 7, 2026):
        for suffix in ("representatives", "labels", "summary"):
            files.append(f"results/annual/U11R08B-v01/N48_seed{seed}_{suffix}.csv")
        for scenario in ("E0_P0", "E80_P20"):
            files.append(f"results/annual/U11R10-v01/{scenario}_N48_seed{seed}_summary.csv")
    for scenario in ("E0_P0", "E80_P20"):
        files.append(f"results/annual/U11R10-v01/{scenario}_daily_summary.csv")
    for folder, prefix, expected in (("U11R02-v01", "day_*", 365),
                                      ("U11R08B-v01", "N48_seed*_cluster*", 144),
                                      ("U11R10-v01", "E*_day_*", 730),
                                      ("U11R10-v01", "E*_N48_seed*_cluster*", 288)):
        for suffix in ("hourly.csv", "cbc.log"):
            found = sorted((ROOT/"results/annual"/folder).glob(prefix+"_"+suffix))
            if len(found) != expected:
                raise ValueError("Incomplete source inventory: "+folder+" "+prefix)
            files.extend(p.relative_to(ROOT).as_posix() for p in found)
    sys.argv = ["freeze_study.py", "U11R11-cost-unserved-attribution"]
    for filename in sorted(set(files)):
        sys.argv.extend(["--input", filename])
    freeze_main()


if __name__ == "__main__":
    main()
