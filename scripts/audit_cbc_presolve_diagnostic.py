"""Read-only audit for either a completed or a fail-closed U11R05 run."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_study_artifacts import audit
from src.cbc_presolve_diagnostic import read_and_validate, command
from src.study_runtime import sha


def main():
    p = argparse.ArgumentParser()
    p.add_argument('run_id')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    folder = ROOT/'results/annual'/args.run_id
    m = json.loads((folder/'run_manifest.json').read_text(encoding='utf-8'))
    hashes = audit(folder/'run_manifest.json')
    allowed = [] if m['status'] == 'complete' else ['not_complete']
    if hashes['errors'] != allowed or hashes['source_drift_since_run']:
        raise ValueError(str(hashes))
    attempts = m['solver_attempts']
    if attempts not in [['first'], ['first', 'repeat']]:
        raise ValueError('Invalid solve count/order')
    inspected = []
    for name in attempts:
        call = folder/name
        process = json.loads((call/'process.json').read_text(encoding='utf-8'))
        if process['command'] != command():
            raise ValueError('Command mismatch')
        try:
            validated = read_and_validate(call)
        except (ValueError, FileNotFoundError) as exc:
            if m['verdict'] != 'invalid' or name != attempts[-1] or not (folder/'failure.json').exists():
                raise
            inspected.append(dict(attempt=name, valid=False, error=repr(exc)))
            break
        saved = json.loads((call/'validated.json').read_text(encoding='utf-8'))
        if saved != validated:
            raise ValueError('Validation replay differs')
        inspected.append(dict(attempt=name, valid=True, objective=validated['native_objective'],
                              checks=validated['original_unit_checks'], max_mps_violation=validated['max_mps_violation']))
    if m['status'] == 'complete':
        if len(inspected) != 2 or not all(r['valid'] for r in inspected):
            raise ValueError('Incomplete supported run')
        a, b = [json.loads((folder/name/'validated.json').read_text(encoding='utf-8')) for name in attempts]
        delta = max(abs(a['values'][k]-b['values'][k]) for k in a['values'])
        obj_delta = abs(a['native_objective']-b['native_objective'])
        verdict = 'supported' if delta <= 1e-6 and obj_delta <= 1e-6 else 'inconclusive'
        if verdict != m['verdict']:
            raise ValueError('Decision mismatch')
    else:
        if not inspected or inspected[-1]['valid']:
            raise ValueError('Invalid run has no confirmed failure')
        if attempts == ['first'] and (folder/'repeat').exists():
            raise ValueError('Unexpected repeat after first failure')
    result = dict(evidence_integrity_passed=True, hashes=hashes, attempts=inspected, verdict=m['verdict'],
                  new_solver_calls=0, source_sha256=sha(Path(__file__)), manifest_sha256=sha(folder/'run_manifest.json'))
    with (ROOT/args.output).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
