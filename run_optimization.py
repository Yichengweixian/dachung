"""Run frozen U06 cases; fail closed and retain diagnostics on any failure."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import numpy as np
import pandas as pd
import pulp
from src.optimization_model import solve_dispatch
from src.optimization_validation import validate, summarize

ROOT = Path(__file__).resolve().parent

def dump(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def main():
    out = ROOT/'results/optimization/U06-20260913-02'
    out.mkdir(parents=True, exist_ok=False)
    try:
        frozen = json.loads((ROOT/'instructions/studies/U06-optimization-model/freeze.json').read_text(encoding='utf-8'))
        for p, digest in frozen['sha256'].items():
            assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest, p
        cfg = frozen['config']
        s = cfg['storage.json']; cost = cfg['economics.json']['parameters']; dt = cfg['simulation.json']['time_step_hours']
        o = cfg['optimization.json']
        th = {'min': o['thermal_min_MW'], 'max': cfg['no_storage.json']['thermal_max_MW'], 'ramp': o['thermal_ramp_MW_per_h']}
        data = pd.read_csv(ROOT/'data/input_24h.csv')
        assert len(data) == cfg['simulation.json']['num_steps']
        manifest = {'run_id': 'U06-20260913-02', 'frozen': frozen, 'python':sys.version,
                    'platform':platform.platform(), 'pulp':pulp.__version__, 'cases':{}}
        def run(name, d, st, t, step, terminal=True):
            q, info = solve_dispatch(d, st, t, cost, step, terminal)
            checks = validate(q, d, st, t, step, terminal)
            summary = summarize(q, cost, step)
            assert abs(summary['operating_cost_CNY']-info['objective_CNY']) < 1e-6
            path = out/(name+'_hourly.csv')
            q.to_csv(path, index=False, float_format='%.17g')
            validate(pd.read_csv(path), d, st, t, step, terminal)
            manifest['cases'][name] = {**info, 'summary':summary, 'max_residual':max(checks.values()), 'checks':checks,
                                        'dt':step, 'storage':st, 'thermal':t, 'terminal':terminal}
            return summary
        primary = run('dispatch', data, s, th, dt)
        rows = []
        old = pd.read_csv(ROOT/'results/economics/dispatch_summary.csv').query('energy_capacity_MWh == 40').iloc[0]
        rows.append({'case':'rule', 'operating_cost_CNY':float(old.thermal_generation_MWh*cost['thermal_cost_CNY_per_MWh']+
            old.curtailment_MWh*cost['curtailment_penalty_CNY_per_MWh']+old.load_shedding_MWh*cost['load_shedding_penalty_CNY_per_MWh']+
            old.storage_discharge_MWh*cost['storage_variable_om_CNY_per_MWh_discharged']),
            'renewable_utilization_pct':float(old.renewable_utilization_pct), 'curtailment_MWh':float(old.curtailment_MWh),
            'thermal_generation_MWh':float(old.thermal_generation_MWh)})
        for name,t,end in [('method',dict(th,min=0,ramp=None),False), ('minimum',dict(th,ramp=None),False), ('ramp',th,False)]:
            rows.append({'case':name, **run(name,data,s,t,dt,end)})
        rows.append({'case':'terminal', **primary})
        table = pd.DataFrame(rows)
        for col in ['operating_cost_CNY','renewable_utilization_pct','curtailment_MWh','thermal_generation_MWh']:
            table['delta_'+col] = table[col].diff()
            assert abs(table['delta_'+col].sum()-(table[col].iloc[-1]-table[col].iloc[0])) < 1e-6
        table.to_csv(out/'attribution.csv',index=False)
        half = data.loc[data.index.repeat(2)].reset_index(drop=True)
        half['hour'] = np.arange(len(half))*dt/2
        run('half_hour',half,s,th,dt/2)
        run('zero_storage',data,dict(s,energy_capacity_MWh=0,power_capacity_MW=0),th,dt)
        zero = data.copy(); zero[['wind','solar']] = 0.
        run('zero_renewables',zero,s,th,dt)
        manifest['cbc_version'] = subprocess.check_output([pulp.PULP_CBC_CMD().path,'-version']).decode()
        manifest['source_sha256'] = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ['src/optimization_model.py','src/optimization_validation.py','src/cbc_precision.py','run_optimization.py','requirements.txt']}
        dump(out/'run_manifest.json',manifest)
        pd.DataFrame([primary]).to_csv(out/'summary.csv',index=False)
        print(table.to_string(index=False))
        print('All cases passed; maximum residual:', max(x['max_residual'] for x in manifest['cases'].values()))
    except Exception as exc:
        dump(out/'failure.json', {'status':'invalid', 'error':repr(exc), 'note':'No successful U06 conclusion. Existing diagnostics preserved.'})
        raise

if __name__ == '__main__':
    main()
