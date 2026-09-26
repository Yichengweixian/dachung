"""Separate-process, read-only consistency audit of U11R07 evidence."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diagnose_u11r06_serialization import decimal_residuals, read_mps
from src.study_runtime import sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run = ROOT / 'results/annual/U11R06-v01'
    diagnosis = ROOT / 'results/annual/U11R07-v01'
    manifest = json.loads((run / 'run_manifest.json').read_text(encoding='utf-8'))
    freeze = json.loads((ROOT / 'instructions/studies/U11R07-u11r06-band-diagnosis/freeze.json').read_text(encoding='utf-8'))
    evidence = json.loads((diagnosis / 'diagnosis.json').read_text(encoding='utf-8'))
    for rel, expected in freeze['sha256'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError('Frozen input drift: ' + rel)
    for rel, expected in manifest['source_sha256'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError('U11R06 source drift: ' + rel)
    for rel, expected in manifest['artifacts'].items():
        if sha(run / rel) != expected:
            raise ValueError('U11R06 artifact drift: ' + rel)
    for rel, expected in evidence['source_sha256'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError('Diagnosis source drift: ' + rel)
    for rel, expected in evidence['output_sha256'].items():
        if sha(diagnosis / rel) != expected:
            raise ValueError('Diagnosis output drift: ' + rel)
    for name, matched in evidence['model_matches'].items():
        if not matched or sha(diagnosis / 'replayed_models' / name) != sha(run / 'N24_seed42_main_models' / name):
            raise ValueError('LP replay mismatch: ' + name)
    findings = evidence['findings']
    if findings['new_solver_calls'] != 0 or findings['replayed_stages'] != 16 or len(evidence['model_matches']) != 16:
        raise ValueError('Wrong replay count')
    if findings['previous_stage'] != 'lex_006' or findings['failed_stage'] != 'lex_014':
        raise ValueError('Wrong failure sequence')
    rows, rhs, senses, bounds = read_mps(diagnosis / 'reconstructed.mps')
    previous = json.loads((run / 'N24_seed42_main_lex_006.json').read_text(encoding='utf-8'))
    values = {f'w_{i:03d}': Decimal.from_float(v) for i, v in enumerate(previous['weights'])}
    values.update({f'd_{i:03d}': Decimal.from_float(v) for i, v in enumerate(previous['deviations'])})
    values['worst_relative_error'] = Decimal.from_float(previous['t'])
    mapped = {evidence['original_to_mps_variables'][name]: value for name, value in values.items()}
    residuals = decimal_residuals(rows, rhs, senses, mapped, bounds)
    if residuals != evidence['mps_residuals'] or str(residuals[0]['violation']) != findings['mps_max_previous_solution_violation']:
        raise ValueError('Decimal MPS residual mismatch')
    if findings['strictly_feasible_previous_witness'] or findings['mathematical_infeasibility_proven'] or findings['numerical_root_cause_proven']:
        raise ValueError('Unsupported certainty in diagnosis')
    result = dict(passed=True, new_solver_calls=0, frozen_hashes=len(freeze['sha256']),
                  run_artifact_hashes=len(manifest['artifacts']), matched_lp_files=len(evidence['model_matches']),
                  top_mps_residual=residuals[0], run_manifest_sha256=sha(run / 'run_manifest.json'),
                  diagnosis_sha256=sha(diagnosis / 'diagnosis.json'), audit_source_sha256=sha(Path(__file__)))
    with (ROOT / args.output).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
