"""Freeze U08 scenario matrix and upstream evidence before implementation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
UNIT=ROOT/'instructions/studies/U08-penetration-matrix'
DEST=UNIT/'freeze.json'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

if DEST.exists(): raise SystemExit('Existing U08 freeze must not be overwritten')
test=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py'],cwd=ROOT,capture_output=True,text=True)
assert test.returncode==0 and 'Ran 34 tests' in test.stderr,test.stderr
files=[ROOT/'data/input_24h.csv',ROOT/'data/scenarios/penetration_scenarios.csv',
       *(UNIT/n for n in ['design.md','decision-rule.md','plan.md','prerequisite-amendment.md']),
       *sorted((ROOT/'config').glob('*.json')),ROOT/'src/optimization_model.py',ROOT/'src/optimization_validation.py',
       ROOT/'src/cbc_precision.py',ROOT/'scripts/audit_u07.py',
       ROOT/'instructions/studies/U06-optimization-model/findings.md',
       ROOT/'instructions/studies/U07-optimization-validation/findings.md',
       ROOT/'instructions/studies/U07R-factorial-attribution/findings.md']
obj={'run_id':'U08-20260913-01','base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
     'preflight_tests':test.stdout+test.stderr,'sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in files},
     'config':{p.name:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'config').glob('*.json')}}
DEST.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(DEST)
