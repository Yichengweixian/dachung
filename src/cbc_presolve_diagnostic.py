"""Bounded U11R05 diagnostic; all model evidence stays in per-call directories."""
from decimal import Decimal
import json
from pathlib import Path
import re
import struct
import subprocess
from time import perf_counter
import numpy as np
import pandas as pd
from scripts.diagnose_u11r04_serialization import read_mps, decimal_residuals
from .energy_calibrated_weights import check_stage
from .study_runtime import ROOT, dump, sha

MODEL = ROOT/'results/annual/U11R04-diagnosis-v02/reconstructed.mps'
MAPPING = ROOT/'results/annual/U11R04-diagnosis-v02/diagnosis.json'
CBC = ROOT/'.venv/Lib/site-packages/pulp/solverdir/cbc/win/i64/cbc.exe'


def command():
    return [str(CBC), 'model.mps', '-primalTolerance', '1e-9', '-integerTolerance', '1e-9',
            '-ratioGap', '0', '-allowableGap', '0', '-threads', '0', '-presolve', 'off',
            '-branch', '-printingOptions', 'all', '-solution', 'solution.txt',
            '-saveSolution', 'solution.bin', '-quit']


def decode_native(raw, expected_rows, names):
    if len(raw) < 16:
        raise ValueError('Truncated native solution')
    rows, cols = struct.unpack_from('=ii', raw)
    if rows != expected_rows or cols != len(names) or len(raw) != 16+16*(rows+cols):
        raise ValueError('Native solution dimensions/layout mismatch')
    objective = struct.unpack_from('=d', raw, 8)[0]
    primal = struct.unpack_from(f'={cols}d', raw, 16+16*rows)
    if not np.isfinite([objective, *primal]).all():
        raise ValueError('Nonfinite native solution')
    return float(objective), dict(zip(names, primal))


def status_gate(folder):
    meta = json.loads((folder/'process.json').read_text(encoding='utf-8'))
    log = (folder/'stdout.txt').read_text(encoding='utf-8')
    text = (folder/'solution.txt').read_text(encoding='utf-8') if (folder/'solution.txt').exists() else ''
    header = text.splitlines()[0] if text else ''
    if meta['returncode'] != 0 or not header.startswith('Optimal'):
        raise ValueError('CBC did not prove Optimal: '+header)
    if ('Optimal objective' not in log and 'Optimal - objective' not in log) or 'Linear relaxation infeasible' in log:
        raise ValueError('CBC status/log disagreement')
    if meta['command'] != command() or 'Option for presolve changed from on to off' not in log:
        raise ValueError('Presolve-off command/log mismatch')
    return text


def read_and_validate(folder):
    text = status_gate(folder)
    if sha(folder/'model.mps') != sha(MODEL):
        raise ValueError('Model changed')
    rows, rhs, senses, bounds = read_mps(folder/'model.mps')
    names = list(bounds)
    native_obj, values = decode_native((folder/'solution.bin').read_bytes(),
                                       sum(v != 'N' for v in senses.values()), names)
    mapping = json.loads(MAPPING.read_text(encoding='utf-8'))['original_to_mps_variables']
    if set(mapping.values()) != set(values):
        raise ValueError('Native variable mapping mismatch')
    original = {name:values[encoded] for name, encoded in mapping.items()}
    objective_rows = [name for name, sense in senses.items() if sense == 'N']
    if len(objective_rows) != 1:
        raise ValueError('Expected one objective')
    decimal_values = {name:Decimal.from_float(v) for name, v in values.items()}
    objective = float(sum((coef*decimal_values[name] for name, coef in rows[objective_rows[0]].items()), Decimal(0)))
    if abs(objective-native_obj) >= 1e-6:
        raise ValueError('Native objective mismatch')
    residuals = decimal_residuals(rows, rhs, senses, decimal_values, bounds)
    inputs = pd.read_csv(ROOT/'results/annual/U11R04-v01/N48_seed42_inputs.csv', float_precision='round_trip')
    annual = pd.read_csv(ROOT/'results/annual/U11R02-v01/input_8760h.csv', float_precision='round_trip')
    reps = pd.read_csv(ROOT/'results/annual/U11R03-v01/N48_seed42_representatives.csv', float_precision='round_trip')
    a = np.array([[inputs.loc[inputs.cluster == i, c].sum() for i in range(48)] for c in ['load','wind','solar']])
    b = annual[['load','wind','solar']].sum().to_numpy()
    prior = json.loads((ROOT/'results/annual/U11R04-v01/N48_seed42_main_lex_035.json').read_text(encoding='utf-8'))
    prior.update(weights=[original[f'w_{i:03d}'] for i in range(48)],
                 deviations=[original[f'd_{i:03d}'] for i in range(48)], t=original['worst_relative_error'])
    checks = check_stage(a, b, reps.days.to_numpy(), prior)
    rounded = {}
    for line in text.splitlines()[1:]:
        fields = line.split()
        if fields and fields[0] == '**':
            fields = fields[1:]
        if len(fields) >= 3 and fields[1] in values:
            rounded[fields[1]] = float(fields[2])
    if set(rounded) != set(values):
        raise ValueError('Incomplete text/native comparison')
    match = re.search(r'objective value\s+([-+0-9.eE]+)', text.splitlines()[0])
    if not match:
        raise ValueError('Missing text objective')
    return dict(status='Optimal', native_objective=native_obj, recomputed_objective=objective,
                text_objective=float(match.group(1)),
                text_objective_difference=abs(float(match.group(1))-native_obj),
                max_text_rounding=max(abs(values[n]-rounded[n]) for n in names),
                values=values, original_values=original, original_unit_checks=checks,
                mps_residuals=residuals, max_mps_violation=residuals[0]['violation'],
                exactly_feasible=all(Decimal(r['violation']) == 0 for r in residuals))


def execute_once(folder):
    folder.mkdir(parents=True, exist_ok=False)
    (folder/'model.mps').write_bytes(MODEL.read_bytes())
    cmd = command()
    started = perf_counter()
    try:
        result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True, timeout=60,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired as exc:
        (folder/'stdout.txt').write_bytes(exc.stdout if isinstance(exc.stdout, bytes) else (exc.stdout or '').encode())
        (folder/'stderr.txt').write_bytes(exc.stderr if isinstance(exc.stderr, bytes) else (exc.stderr or '').encode())
        dump(folder/'process.json', dict(command=cmd, returncode=None, timeout=True, seconds=perf_counter()-started))
        raise
    (folder/'stdout.txt').write_text(result.stdout, encoding='utf-8')
    (folder/'stderr.txt').write_text(result.stderr, encoding='utf-8')
    dump(folder/'process.json', dict(command=cmd, returncode=result.returncode, seconds=perf_counter()-started))
    validated = read_and_validate(folder)
    dump(folder/'validated.json', validated)
    return validated


def execute_pair(out, on_attempt):
    completed = []
    for name in ['first', 'repeat']:
        on_attempt(name)
        completed.append(execute_once(out/name))
    diff = max(abs(completed[0]['values'][k]-completed[1]['values'][k]) for k in completed[0]['values'])
    objective_diff = abs(completed[0]['native_objective']-completed[1]['native_objective'])
    return dict(verdict='supported' if diff <= 1e-6 and objective_diff <= 1e-6 else 'inconclusive',
                max_variable_difference=diff, objective_difference=objective_diff)
