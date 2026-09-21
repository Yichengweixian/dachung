"""Read-only checksum and solver-state audit of completed experiment manifests."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(path):
    path=ROOT/path;record=json.loads(path.read_text(encoding='utf-8'));errors=[];checked=0;source_drift=[]
    for rel,expected in record['freeze']['sha256'].items():
        checked+=1
        if digest(ROOT/rel)!=expected:errors.append('frozen:'+rel)
    for name,expected in record.get('artifacts',{}).items():
        checked+=1
        if digest(path.parent/name)!=expected:errors.append('artifact:'+name)
    for rel,expected in record.get('source_sha256',{}).items():
        if digest(ROOT/rel)!=expected:source_drift.append(rel)
    for case,info in record.get('cases',{}).items():
        if info['solver_status']!='Optimal' or info['max_residual']>=1e-6:errors.append('case:'+case)
    if record['status']!='complete':errors.append('not_complete')
    return dict(run_id=record['run_id'],checked_hashes=checked,cases=len(record.get('cases',{})),errors=errors,source_drift_since_run=source_drift,passed=not errors)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifests',nargs='+');p.add_argument('--output');a=p.parse_args()
    rows=[audit(Path(x)) for x in a.manifests];text=json.dumps(rows,ensure_ascii=False,indent=2)
    if a.output:
        with (ROOT/a.output).open('x',encoding='utf-8') as f:f.write(text+'\n')
    print(text)
    if not all(r['passed'] for r in rows):raise SystemExit(1)
