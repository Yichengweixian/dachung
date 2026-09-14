"""U00 evidence capture; standard library only. Run from any directory."""
import argparse
import hashlib
import json
import pathlib
import platform
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXCLUDE = {'.git', '.venv', '.cache', '__pycache__', '.claude'}
OUT = ROOT / 'instructions/baseline_manifest.json'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def command(*args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, check=True).stdout

def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def inventory():
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes())
            for p in sorted(ROOT.rglob('*')) if p.is_file() and p != OUT
            and not any(x in EXCLUDE for x in p.relative_to(ROOT).parts)}

def freeze():
    dest = ROOT / 'instructions/baseline_freeze.json'
    if dest.exists():
        raise SystemExit('Freeze already exists; refusing to overwrite.')
    names = command('git', 'ls-files', '-z').decode().split('\0')
    tracked = {n: sha((ROOT / n).read_bytes()) for n in names if n}
    rules = ['current-environment-amendment.md', 'decision-rule.md', 'plan.md', 'design.md']
    folder = ROOT / 'instructions/studies/U00-baseline-freeze'
    patch = command('git', 'diff', '--binary', 'HEAD')
    (ROOT / 'instructions/baseline_preexisting_changes.patch').write_bytes(patch)
    write_json(dest, {'run_id': 'U00-baseline-20260913-01',
        'base_commit': command('git', 'rev-parse', 'HEAD').decode().strip(),
        'rule_sha256': {n: sha((folder / n).read_bytes()) for n in rules},
        'tracked_start_sha256': tracked, 'preexisting_patch_sha256': sha(patch),
        'excluded_directories': sorted(EXCLUDE), 'excluded_file': OUT.relative_to(ROOT).as_posix()})
    print('Frozen:', dest)

def audit():
    frozen = json.loads((ROOT / 'instructions/baseline_freeze.json').read_text(encoding='utf-8'))
    folder = ROOT / 'instructions/studies/U00-baseline-freeze'
    for n, digest in frozen['rule_sha256'].items():
        assert sha((folder / n).read_bytes()) == digest, n
    allowed = {'instructions/STATUS.md', 'instructions/RUNLOG.md', 'instructions/specs/roadmap.md',
               'instructions/README.md', 'instructions/studies/U00-baseline-freeze/findings.md',
               'instructions/studies/U00-baseline-freeze/question.md'}
    for n, digest in frozen['tracked_start_sha256'].items():
        if n not in allowed:
            assert sha((ROOT / n).read_bytes()) == digest, n
    environment = [sys.version, sys.executable, platform.platform(),
                   command('git', '--version').decode(),
                   command(sys.executable, '-m', 'pip', 'list', '--format=json').decode()]
    (ROOT / 'instructions/baseline_environment.txt').write_text('\n'.join(environment), encoding='utf-8')
    proc = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                           '-p', 'test_*.py', '-v'], cwd=ROOT, capture_output=True, text=True)
    log = proc.stdout + proc.stderr
    (ROOT / 'instructions/baseline_tests.txt').write_text(log, encoding='utf-8')
    assert proc.returncode == 0 and 'Ran 25 tests' in log and '\nOK\n' in log, log
    # Tests must not mutate protected files either.
    for n, digest in frozen['tracked_start_sha256'].items():
        if n not in allowed:
            assert sha((ROOT / n).read_bytes()) == digest, n
    print(log)
    print('Frozen rules and protected files unchanged; environment captured.')

def manifest():
    first = inventory()
    write_json(OUT, first)
    before = sha(OUT.read_bytes())
    write_json(OUT, inventory())
    assert before == sha(OUT.read_bytes()), 'Manifest not stable'
    loaded = json.loads(OUT.read_text(encoding='utf-8'))
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
              if p.is_file() and p != OUT
              and not set(p.relative_to(ROOT).parts).intersection(EXCLUDE)}
    assert set(loaded) == actual, 'Coverage mismatch'
    for name, digest in loaded.items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    print(json.dumps({'files': len(loaded), 'manifest_sha256': before,
                      'coverage_verified': True, 'two_runs_identical': True}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'audit', 'manifest'])
    {'freeze': freeze, 'audit': audit, 'manifest': manifest}[parser.parse_args().action]()
