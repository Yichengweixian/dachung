"""Record the existing master files and run the pre-U06 regression suite."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results/master_revalidation_v01"


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    paths = [p for p in paths if p]

    def snapshot():
        return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}

    before = snapshot()
    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace",
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    (OUT / "baseline_tests.txt").write_text(tests.stdout + tests.stderr, encoding="utf-8")
    after = snapshot()
    manifest = {
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
        "packages": {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "matplotlib", "pulp")},
        "sha256": before, "repeat_snapshot_equal": before == after,
        "test_returncode": tests.returncode,
        "scope": "Existing master tracked-file baseline, before U06 implementation; not a solver verdict.",
    }
    (OUT / "baseline_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(tests.stdout + tests.stderr)
    print("Tracked files unchanged:", before == after)
    if tests.returncode or before != after:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
