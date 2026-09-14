"""Capture approved U06 specification and immutable inputs before solving."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
dest = root / 'instructions/studies/U06-optimization-model/freeze.json'
if dest.exists():
    raise SystemExit('Existing freeze must not be overwritten')
test = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'],
                      cwd=root, capture_output=True, text=True)
assert test.returncode == 0 and 'Ran 25 tests' in test.stderr, test.stderr
paths = [root / 'data/input_24h.csv', *sorted((root / 'config').glob('*.json'))]
paths += [dest.parent / n for n in ['milp-amendment.md', 'design.md', 'decision-rule.md', 'plan.md']]
record = {'run_id': 'U06-20260913-01', 'base_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=root).decode().strip(),
          'preflight_tests': test.stdout + test.stderr,
          'sha256': {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
          'config': {p.name: json.loads(p.read_text(encoding='utf-8')) for p in paths if p.suffix == '.json'}}
dest.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(dest)
