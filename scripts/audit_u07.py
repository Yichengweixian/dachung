"""U07 freeze and independent audit. Does not import U06 validation code."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
UNIT = ROOT/'instructions/studies/U07-optimization-validation'
RUN = ROOT/'results/optimization/U06-20260913-02'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def check(q, s, t, dt, terminal=True):
    def close(a,b):
        assert np.max(np.abs(np.asarray(a)-np.asarray(b))) < 1e-6
    def bounds(x,lo,hi):
        assert np.isfinite(x).all() and (np.asarray(x)>=lo-1e-6).all() and (np.asarray(x)<=hi+1e-6).all()
    for c in ['thermal','wind_used','solar_used','wind_curt','solar_curt','charge','discharge','unserved','energy_start_MWh','energy_MWh']:
        bounds(q[c],0,np.inf)
    close(q.wind_used+q.solar_used+q.thermal+q.discharge+q.unserved,q.load+q.charge)
    close(q.wind_used+q.wind_curt,q.wind_available)
    close(q.solar_used+q.solar_curt,q.solar_available)
    bounds(q.thermal,t['min'],t['max'])
    if t['ramp'] is not None:
        bounds(np.diff(q.thermal),-t['ramp']*dt,t['ramp']*dt)
    for c in ['charge','discharge']:
        bounds(q[c],0,s['power_capacity_MW'])
    assert (np.minimum(q.charge,q.discharge)<1e-6).all()
    bounds(q.unserved,0,q.load.to_numpy())
    for c in ['energy_start_MWh','energy_MWh']:
        bounds(q[c],s['soc_min']*s['energy_capacity_MWh'],s['soc_max']*s['energy_capacity_MWh'])
    close(q.energy_start_MWh.iloc[0],s['energy_capacity_MWh']*s['soc_initial'])
    close(q.energy_start_MWh.to_numpy()[1:],q.energy_MWh.to_numpy()[:-1])
    close(q.energy_MWh,q.energy_start_MWh+s['eta_charge']*q.charge*dt-q.discharge*dt/s['eta_discharge'])
    if terminal:
        close(q.energy_MWh.iloc[-1],q.energy_start_MWh.iloc[0])
    if s['energy_capacity_MWh']:
        close(q.soc,q.energy_MWh/s['energy_capacity_MWh'])
    else:
        assert q.soc.isna().all()
    return True

def freeze():
    dest=UNIT/'freeze.json'
    assert not dest.exists(), 'Do not overwrite freeze'
    manifest=json.loads((RUN/'run_manifest.json').read_text(encoding='utf-8'))
    for p,h in manifest['source_sha256'].items():
        assert sha(ROOT/p)==h,p
    assert 'verdict: supported' in (ROOT/'instructions/studies/U06-optimization-model/findings.md').read_text(encoding='utf-8')
    files=[*RUN.glob('*'),*(UNIT/n for n in ['design.md','decision-rule.md','plan.md']),
           ROOT/'results/capacity_sensitivity/summary.csv',ROOT/'results/storage_hourly.csv',ROOT/'data/input_24h.csv',
           * (ROOT/'config').glob('*.json')]
    obj={'run_id':'U07-20260913-01','base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
         'sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in files},
         'scope':'Original U07 thresholds and attribution formulas retained. U06 approved MILP used. New Python processes, same Linux machine; no second-machine claim.'}
    dest.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('U07 frozen')

if __name__=='__main__':
    freeze()
