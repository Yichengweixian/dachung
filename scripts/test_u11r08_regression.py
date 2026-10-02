"""Run regression tests with actual solver process counts, never overwrite logs."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import scipy.optimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=False)
    counts = {'cbc_processes': 0, 'scipy_linprog_calls': 0}
    original_popen, original_lp = subprocess.Popen, scipy.optimize.linprog

    def counted_popen(command, *pos, **kw):
        if isinstance(command, (list, tuple)) and Path(str(command[0])).stem.lower() == 'cbc':
            counts['cbc_processes'] += 1
        return original_popen(command, *pos, **kw)

    def counted_lp(*pos, **kw):
        counts['scipy_linprog_calls'] += 1
        return original_lp(*pos, **kw)

    with patch('subprocess.Popen', counted_popen), patch('scipy.optimize.linprog', counted_lp):
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
        with (out / 'unittest.log').open('x', encoding='utf-8') as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = dict(passed=result.wasSuccessful(), tests=result.testsRun, failures=len(result.failures),
                  errors=len(result.errors), skipped=len(result.skipped), solver_calls=counts,
                  timestamp=datetime.now(timezone.utc).isoformat(), python=sys.version,
                  packages={name: importlib.metadata.version(name) for name in
                            ['numpy', 'pandas', 'scipy', 'pulp', 'scikit-learn']},
                  source_sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for pattern in ['src/*.py', 'tests/*.py', 'scripts/*u11r08*.py', 'run_u11r08_feasibility.py']
                                 for p in ROOT.glob(pattern)},
                  log_sha256=hashlib.sha256((out / 'unittest.log').read_bytes()).hexdigest())
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['passed', 'tests', 'failures', 'errors', 'solver_calls']}))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
