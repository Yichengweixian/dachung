"""Create completion evidence only after verifying the independent audit links."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re

if __package__:
    from .audit_u11r09_fixed_weights import read_json, sha, require, verify_hashes, write_new, UNIT, decide
else:
    from audit_u11r09_fixed_weights import read_json, sha, require, verify_hashes, write_new, UNIT, decide


def finalize(root, run_id):
    require(re.fullmatch(r'U11R09-v\d+', run_id) is not None, 'Invalid run ID')
    root = Path(root)
    out = root / 'results/annual' / run_id
    manifest_path = out / 'run_manifest.json'
    audit_path = out.with_name(run_id + '-independent-audit.json')
    completion = out / 'completion.json'
    require(not completion.exists(), 'Completion already exists')
    manifest, report = read_json(manifest_path), read_json(audit_path)
    require(report['main_manifest_sha256'] == sha(manifest_path), 'Audit/main manifest hash mismatch')
    require(manifest['status'] == 'awaiting_independent_audit' and manifest['verdict'] is None,
            'Main manifest is not awaiting audit')
    require(report['passed'] is True and report['status'] == 'complete' and
            report['verdict'] in ('supported', 'inconclusive'), 'Independent audit did not pass')
    require(report['audit_source_sha256'] == sha(root / 'scripts/audit_u11r09_fixed_weights.py'), 'Audit source changed')
    require(report['physical_audit_source_sha256'] == sha(root / 'scripts/independent_dispatch_audit.py'),
            'Physical audit source changed')
    freeze = root / 'instructions/studies' / UNIT / 'freeze.json'
    require(manifest['freeze_sha256'] == report['freeze_sha256'] == sha(freeze), 'Freeze changed')
    require(read_json(freeze) == manifest['freeze'], 'Embedded freeze differs')
    verify_hashes(root, manifest['freeze']['sha256'])
    verify_hashes(root, manifest['source_sha256'])
    verify_hashes(out, manifest['artifacts'])
    verdict, passing = decide(report['groups'])
    require(verdict == report['verdict'] == manifest['details']['provisional_verdict'] and
            passing == report['passing_N'] == manifest['details']['passing_N'], 'Verdict conflict')
    require(len(report['physical_residuals']) == 261 and len(report['baseline']['physical_residuals']) == 365
            and len(report['repeatability']) == 9 and report['audit_solver_calls'] == 0, 'Incomplete independent audit')
    result = {'status': 'complete', 'verdict': verdict, 'passing_N': passing,
              'selected_N': min(passing) if passing else None, 'run_id': run_id,
              'manifest_sha256': sha(manifest_path), 'audit_sha256': sha(audit_path),
              'audit_path': audit_path.relative_to(root).as_posix(), 'freeze_sha256': sha(freeze),
              'timestamp': datetime.now(timezone.utc).isoformat()}
    write_new(completion, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    print(finalize(Path(__file__).resolve().parents[1], parser.parse_args().run_id))
