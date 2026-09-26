"""No-solve forensic replay of U11R06's failed lexicographic LP stage."""
import argparse
from decimal import Decimal, localcontext
import json
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np
import pandas as pd
import pulp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.energy_calibrated_weights_presolve_off import calibrate
from src.study_runtime import sha


class ReplayStopped(Exception):
    pass


def decimal_residuals(rows, rhs, senses, values, bounds):
    result = []
    with localcontext() as ctx:
        ctx.prec = 70
        for name, terms in rows.items():
            if senses[name] == 'N':
                continue
            lhs = sum((coef*values[var] for var, coef in terms.items()), Decimal(0))
            residual = lhs-rhs.get(name, Decimal(0))
            violation = abs(residual) if senses[name] == 'E' else max(Decimal(0), residual if senses[name] == 'L' else -residual)
            result.append(dict(row=name, sense=senses[name], violation=str(violation), signed_residual=str(residual)))
        for name, (lower, upper) in bounds.items():
            v = values[name]
            violation = max(Decimal(0), lower-v if lower is not None else Decimal(0), v-upper if upper is not None else Decimal(0))
            result.append(dict(row='bound:'+name, sense='bounds', violation=str(violation)))
    return sorted(result, key=lambda row: Decimal(row['violation']), reverse=True)


def read_mps(path):
    """Read the continuous, free MPS subset emitted by this local PuLP writer."""
    senses, rows, rhs, bounds = {}, {}, {}, {}
    section = None
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('*'):
            continue
        fields = line.split()
        if fields[0] == 'NAME' or (len(fields) == 1 and fields[0] in ['ROWS', 'COLUMNS', 'RHS', 'BOUNDS', 'ENDATA']):
            section = fields[0]
            continue
        if section == 'ROWS':
            senses[fields[1]] = fields[0]
            rows[fields[1]] = {}
        elif section == 'COLUMNS':
            var = fields[0]
            bounds.setdefault(var, [Decimal(0), None])
            for i in range(1, len(fields), 2):
                row = fields[i]
                rows[row][var] = rows[row].get(var, Decimal(0)) + Decimal(fields[i+1])
        elif section == 'RHS':
            for i in range(1, len(fields), 2):
                rhs[fields[i]] = Decimal(fields[i+1])
        elif section == 'BOUNDS':
            kind, var = fields[0], fields[2]
            if kind == 'LO':
                bounds[var][0] = Decimal(fields[3])
            elif kind == 'UP':
                bounds[var][1] = Decimal(fields[3])
            elif kind == 'FX':
                bounds[var] = [Decimal(fields[3])]*2
            else:
                raise ValueError('Unsupported MPS bound: '+kind)
        elif section != 'NAME':
            raise ValueError('Unexpected MPS section: '+str(section))
    return rows, rhs, senses, bounds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = ROOT/args.output
    if out.exists():
        if any(out.iterdir()):
            raise FileExistsError('Nonempty diagnosis output directory: '+str(out))
    else:
        out.mkdir(parents=True)
    run = ROOT/'results/annual/U11R06-v01'
    manifest = json.loads((run/'run_manifest.json').read_text(encoding='utf-8'))
    for rel, expected in manifest['source_sha256'].items():
        if sha(ROOT/rel) != expected:
            raise ValueError('Computation source drift: '+rel)
    for rel, expected in manifest['artifacts'].items():
        if sha(run/rel) != expected:
            raise ValueError('Artifact drift: '+rel)
    prefix = 'N24_seed42'
    reps = pd.read_csv(ROOT/'results/annual/U11R03-v01'/(prefix+'_representatives.csv'), float_precision='round_trip')
    inputs = pd.read_csv(run/(prefix+'_inputs.csv'), float_precision='round_trip')
    full = pd.read_csv(ROOT/'results/annual/U11R02-v01/input_8760h.csv', float_precision='round_trip')
    channels = ['load', 'wind', 'solar']
    a = np.array([[inputs.loc[inputs.cluster == i, col].sum() for i in range(24)] for col in channels])
    b = full[channels].sum().to_numpy()
    stage_names = ['primary', 'secondary']+[f'lex_{i:03d}' for i in sorted(range(len(reps)), key=lambda i: reps.date_UTC.iloc[i])]
    records = []
    for name in stage_names:
        r = json.loads((run/(prefix+'_main_'+name+'.json')).read_text(encoding='utf-8'))
        records.append(r)
        if r.get('error'):
            break
    replayed = out/'replayed_models'
    replayed.mkdir()
    captured = {}
    cursor = 0

    class RecordedSolution:
        def __init__(self, **kwargs):
            self.log = 'Forensic replay of stored solution; no subprocess or optimizer.'

        def actualSolve(self, model, **kwargs):
            nonlocal cursor
            record = records[cursor]
            cursor += 1
            if record.get('error'):
                captured['model'] = model.copy()
                raise ReplayStopped(record['stage'])
            values = {f'w_{i:03d}': v for i, v in enumerate(record['weights'])}
            values.update({f'd_{i:03d}': v for i, v in enumerate(record['deviations'])})
            values['worst_relative_error'] = record['t']
            model.assignVarsVals(values)
            model.assignStatus(pulp.LpStatusOptimal, pulp.LpSolutionOptimal)
            return pulp.LpStatusOptimal

    # A hard trap makes an accidental real optimizer/subprocess call an error.
    with patch('src.energy_calibrated_weights_presolve_off.FullPrecisionCBC', RecordedSolution), \
            patch('subprocess.run', side_effect=AssertionError('No subprocess allowed in diagnosis')):
        try:
            calibrate(a, b, reps.days.to_numpy(), reps.date_UTC.tolist(), model_directory=replayed)
        except ReplayStopped:
            pass
    if cursor != len(records) or 'model' not in captured:
        raise ValueError('Replay did not stop at the recorded failure')
    model = captured['model']
    matches = {}
    for record in records:
        name = record['stage']+'.lp'
        matches[name] = sha(replayed/name) == sha(run/(prefix+'_main_models')/name)
    if not all(matches.values()):
        raise ValueError('Replayed model differs from the saved LP')
    variables, names, constraints, objective = model.writeMPS(str(out/'reconstructed.mps'), rename=1)
    previous = records[-2]
    values = {f'w_{i:03d}': Decimal.from_float(v) for i, v in enumerate(previous['weights'])}
    values.update({f'd_{i:03d}': Decimal.from_float(v) for i, v in enumerate(previous['deviations'])})
    values['worst_relative_error'] = Decimal.from_float(previous['t'])
    rows = {name: {v.name: Decimal.from_float(float(coef)) for v, coef in row.items()} for name, row in model.constraints.items()}
    rhs = {name: Decimal.from_float(float(-row.constant)) for name, row in model.constraints.items()}
    senses = {name: {-1:'L', 0:'E', 1:'G'}[row.sense] for name, row in model.constraints.items()}
    bounds = {v.name: [None if x is None else Decimal.from_float(float(x)) for x in [v.lowBound, v.upBound]] for v in variables}
    memory_residuals = decimal_residuals(rows, rhs, senses, values, bounds)
    mr, mh, ms, mb = read_mps(out/'reconstructed.mps')
    mps_values = {names[name]: value for name, value in values.items()}
    mps_residuals = decimal_residuals(mr, mh, ms, mps_values, mb)
    max_coefficient_delta = Decimal(0)
    max_rhs_delta = Decimal(0)
    for row, terms in rows.items():
        for var, coef in terms.items():
            max_coefficient_delta = max(max_coefficient_delta, abs(coef-mr[constraints[row]][names[var]]))
        max_rhs_delta = max(max_rhs_delta, abs(rhs[row]-mh[constraints[row]]))
    counts = reps.days.to_numpy()
    lower, upper = .5*counts, 2.*counts
    for pin in records[-1]['pins']:
        i = pin['index']
        lower[i] = max(lower[i], pin['lower'])
        upper[i] = min(upper[i], pin['upper'])
    findings = dict(new_solver_calls=0, replayed_stages=cursor, all_lp_files_byte_equal=True,
                    previous_stage=previous['stage'], failed_stage=records[-1]['stage'],
                    frozen_band=1e-9, cbc_primal_tolerance=1e-9,
                    pin_count=len(records[-1]['pins']), min_pin_width=min(p['upper']-p['lower'] for p in records[-1]['pins']),
                    min_intersected_width=float(np.min(upper-lower)),
                    weight_sum_lower=float(lower.sum()), weight_sum_upper=float(upper.sum()),
                    simple_weight_bounds_feasible=bool((lower <= upper).all() and lower.sum() <= 365 <= upper.sum()),
                    in_memory_max_previous_solution_violation=memory_residuals[0]['violation'],
                    mps_max_previous_solution_violation=mps_residuals[0]['violation'],
                    max_mps_coefficient_delta=str(max_coefficient_delta), max_mps_rhs_delta=str(max_rhs_delta),
                    strictly_feasible_previous_witness=all(Decimal(r['violation']) == 0 for r in mps_residuals),
                    mathematical_infeasibility_proven=False, numerical_root_cause_proven=False,
                    notes=['Reconstructed MPS, not retained original solver MPS.',
                           'A small residual is not exact feasibility or an infeasibility certificate.',
                           'No changes to frozen criteria, model source, saved solutions or CBC status.'])
    evidence = dict(findings=findings, model_matches=matches, in_memory_residuals=memory_residuals,
                    mps_residuals=mps_residuals, original_to_mps_variables=names,
                    original_to_mps_constraints=constraints,
                    source_sha256={p:sha(ROOT/p) for p in ['scripts/diagnose_u11r06_serialization.py', 'src/energy_calibrated_weights_presolve_off.py', 'src/cbc_presolve_off.py']},
                    run_manifest_sha256=sha(run/'run_manifest.json'))
    evidence['output_sha256'] = {p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    with (out/'diagnosis.json').open('x', encoding='utf-8') as stream:
        json.dump(evidence, stream, ensure_ascii=False, indent=2)
    print(json.dumps(findings, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
