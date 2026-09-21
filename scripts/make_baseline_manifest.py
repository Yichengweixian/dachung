"""Non-mutating U00 supporting inventory. Never commits or changes old runs."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE = {'.venv', '.cache', '__pycache__', '.claude', '.git'}

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')

def snapshot(root, generated=None):
    paths = []
    for folder, directories, names in os.walk(root, followlinks=False):
        parent = Path(folder)
        directories[:] = sorted(n for n in directories if n not in EXCLUDE and parent/n != generated)
        for n in directories:
            path = parent/n
            if path.is_symlink() or path.is_junction():
                raise ValueError(f'Link requires explicit scope review: {path.relative_to(root)}')
        for name in sorted(names):
            path = parent/name
            if name == '.env' or name.startswith('.env.') or path.suffix.lower() in {'.pem', '.key', '.pfx'}:
                raise ValueError(f'Sensitive-file candidate requires scope review: {path.relative_to(root)}')
            paths.append(path)
    def item(path):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f'Link requires explicit scope review: {path.relative_to(root)}')
        return path.relative_to(root).as_posix(), sha(path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        files = dict(pool.map(item, paths))
    return dict(sorted(files.items()))

def differences(expected, actual):
    return dict(added=sorted(actual.keys()-expected.keys()), missing=sorted(expected.keys()-actual.keys()),
                changed=sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k]))

def clean(diff):
    return not any(diff.values())

def command(args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace',
                            env={**os.environ, 'PYTHONIOENCODING':'utf-8'}, timeout=300)
    return dict(command=args, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)

def git_status(output):
    return command(['git','status','--porcelain=v1','-z','--untracked-files=all','--','.',
                    ':(exclude)'+output.relative_to(ROOT).as_posix()])

def unit_metadata(root):
    units = {}
    for path in sorted((root/'instructions/studies').glob('*/findings.md')):
        header = path.read_text(encoding='utf-8').split('---')[1]
        fields = dict(line.split(':', 1) for line in header.splitlines() if ':' in line)
        fields = {k.strip():v.strip() for k,v in fields.items()}
        if fields.get('unit'):
            units[fields['unit']] = dict(findings=path.relative_to(root).as_posix(),
                                        findings_status=fields.get('status'),findings_verdict=fields.get('verdict'))
    return units

def artifact_rows(root, files):
    units = unit_metadata(root)
    runs = {}
    for rel in files:
        if rel.startswith('results/') and rel.endswith('/run_manifest.json'):
            record = json.loads((root/rel).read_text(encoding='utf-8'))
            unit = record.get('unit') or record.get('freeze', {}).get('unit')
            unit = unit.split('-')[0] if isinstance(unit,str) else None
            runs[str(Path(rel).parent).replace('\\','/')] = dict(unit=unit, run_manifest=rel,
                run_id=record.get('run_id'), recorded_status=record.get('status'), recorded_verdict=record.get('verdict'))
    groups = {'optimization':'U06','validation':'U07R01','penetration':'U08','grid_search':'U09R01',
              'real_data':'U10','annual':'U11R02','ga':'U12R01','prototype':'U13R01','materials':'U14',
              'capacity_sensitivity':'U04','economics':'U05','no_storage':'U02','storage':'U03',
              'master_revalidation_v01':'U00','baseline':'U00'}
    standalone = {'results/no_storage_hourly.csv':'U02','results/no_storage_summary.csv':'U02',
                  'results/storage_baseline_hourly.csv':'U03','results/storage_comparison.csv':'U03',
                  'results/storage_hourly.csv':'U03','results/storage_summary.csv':'U03',
                  'results/annual_independent_audit_v02.json':'U11R02'}
    rows = []
    for rel, digest in files.items():
        if not rel.startswith('results/'):continue
        matches = [prefix for prefix in runs if rel.startswith(prefix+'/')]
        meta = runs[max(matches,key=len)].copy() if matches else {}
        basis='nearest_run_manifest' if meta.get('unit') else None
        if not meta.get('unit'):
            candidate = re.match(r'^(U\d+(?:R\d+)?)',rel.split('/')[2]) if len(rel.split('/'))>2 else None
            if candidate and candidate.group(1) in units:
                meta['unit']=candidate.group(1);basis='directory_run_id'
            elif rel in standalone:
                meta['unit']=standalone[rel];basis='verified_legacy_entrypoint_or_audit'
            elif rel.startswith('results/artifact_audit_'):
                meta['unit']='cross_unit';basis='cross_unit_audit'
            elif rel=='results/.gitkeep':
                meta['unit']='infrastructure';basis='empty_directory_placeholder'
            else:
                meta['unit']=groups.get(rel.split('/')[1]);basis='result_group' if meta['unit'] else 'unassigned'
        unit = meta.get('unit')
        rows.append(dict(path=rel,sha256=digest,**meta,**units.get(unit,{}),
                         ownership_basis=basis))
    return rows

def capture(run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',run_id):raise ValueError('Invalid run ID')
    out = ROOT/'results/baseline'/run_id
    if out.exists():raise FileExistsError(out)
    freeze_path=ROOT/'instructions/studies/U00-baseline-freeze/freeze.json'
    freeze=json.loads(freeze_path.read_text(encoding='utf-8'))
    for rel,expected in freeze['sha256'].items():
        if sha(ROOT/rel)!=expected:raise ValueError(f'Frozen file changed: {rel}')
    start=perf_counter();before=snapshot(ROOT)
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/'baseline_manifest.json',dict(scope='Existing project files at capture; not a Git commit',
        excluded_directories=sorted(EXCLUDE),generated_output=out.relative_to(ROOT).as_posix(),sha256=before))
    print('First snapshot:',len(before),'files',flush=True)
    try:
        env={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
             'pip_list':command([sys.executable,'-m','pip','list','--format=json']),
             'git':command(['git','--version']),'head':command(['git','rev-parse','HEAD']),
             'initial_commits':command(['git','rev-list','--max-parents=0','HEAD']),
             'git_status':git_status(out)}
        git_path=Path(shutil.which('git')).resolve()
        bash=git_path.parent.parent/'bin/bash.exe'
        env['git_bash']=command([str(bash),'--noprofile','--norc','-c','git --version && git rev-parse HEAD']) if bash.exists() else dict(returncode=None,error='Git Bash not found beside Git')
        write_json(out/'environment.json',env)
        test=command([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py','-v'])
        with (out/'tests.txt').open('x',encoding='utf-8') as f:f.write(test['stdout']+test['stderr'])
        rows=artifact_rows(ROOT,before);write_json(out/'artifacts.json',rows)
        keys=['path','sha256','unit','run_id','run_manifest','recorded_status','recorded_verdict','findings','findings_status','findings_verdict','ownership_basis']
        with (out/'artifacts.csv').open('x',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
        after=snapshot(ROOT,out);diff=differences(before,after)
        write_json(out/'repeat_comparison.json',diff)
        checks=dict(repeat_identical=clean(diff),tests_passed=test['returncode']==0,
            git_available=env['git']['returncode']==0,git_bash_passed=env['git_bash']['returncode']==0,
            environment_saved=env['pip_list']['returncode']==0,
            head_unchanged=command(['git','rev-parse','HEAD'])['stdout']==env['head']['stdout'],
            git_index_worktree_unchanged_except_output=env['git_status']['returncode']==0 and env['git_status']==git_status(out))
        record=dict(run_id=run_id,unit='U00',recorded_at=datetime.now(timezone.utc).isoformat(),status='partial',verdict=None,
            supporting_checks_passed=all(checks.values()),checks=checks,project_file_count=len(before),result_file_count=len(rows),
            unassigned_result_files=sum(not x.get('unit') for x in rows),elapsed_seconds=perf_counter()-start,
            freeze_sha256=sha(freeze_path),source_sha256=sha(Path(__file__)),test_command=test['command'],
            test_returncode=test['returncode'],base_commit=env['head']['stdout'].strip(),
            remaining=['Working-tree baseline commit not authorized','444.docx inclusion confirmation not independently established',
                       'Original self-containing inventory/output-path acceptance requires scope confirmation'],
            output_sha256={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()})
        write_json(out/'run_manifest.json',record)
        print(json.dumps({k:v for k,v in record.items() if k not in ('output_sha256','test_command')},ensure_ascii=False,indent=2))
        if not record['supporting_checks_passed']:raise RuntimeError('Supporting checks failed; retained evidence')
    except Exception as exc:
        write_json(out/'failure.json',dict(error=repr(exc)));raise

def verify(path):
    path=path.resolve()
    if not path.is_relative_to(ROOT/'results/baseline'):raise ValueError('Expected baseline output under project results')
    record=json.loads(path.read_text(encoding='utf-8'))
    diff=differences(record['sha256'],snapshot(ROOT,ROOT/record['generated_output']))
    print(json.dumps(diff,ensure_ascii=False,indent=2))
    if not clean(diff):raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--run-id');g.add_argument('--verify',type=Path);a=p.parse_args()
    if a.verify:verify(a.verify)
    else:capture(a.run_id)
