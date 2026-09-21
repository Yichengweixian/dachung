"""Separate-process CSV audit using only the standard library, no src imports."""
import csv
import math
import json
from pathlib import Path
import sys

def audit_file(path, storage, thermal, dt=1., terminal=True):
    with Path(path).open(encoding="utf-8",newline="") as f:
        rows=[{k:float(v) if v else math.nan for k,v in row.items()} for row in csv.DictReader(f)]
    if not rows: raise ValueError("Empty dispatch")
    errors=[]
    def eq(a,b): errors.append(abs(a-b))
    def bound(v,lo,hi):
        if not math.isfinite(v): raise ValueError("Nonfinite dispatch")
        errors.append(max(0,lo-v,v-hi))
    previous=storage['energy_capacity_MWh']*storage['soc_initial']
    for i,r in enumerate(rows):
        for k in ('thermal','wind_used','wind_curt','solar_used','solar_curt','charge','discharge','unserved'):
            bound(r[k],0,math.inf)
        eq(r['wind_used']+r['solar_used']+r['thermal']+r['discharge']+r['unserved'],r['load']+r['charge'])
        eq(r['wind_used']+r['wind_curt'],r['wind_available']); eq(r['solar_used']+r['solar_curt'],r['solar_available'])
        bound(r['thermal'],thermal['thermal_min_MW'],thermal['thermal_max_MW'])
        if i and thermal['thermal_ramp_MW_per_h'] is not None:
            bound(r['thermal']-rows[i-1]['thermal'],-thermal['thermal_ramp_MW_per_h']*dt,thermal['thermal_ramp_MW_per_h']*dt)
        bound(r['unserved'],0,r['load'])
        for k in ('charge','discharge'): bound(r[k],0,storage['power_capacity_MW'])
        if min(r['charge'],r['discharge'])>1e-6: raise ValueError("Simultaneous charging")
        eq(r['energy_start_MWh'],previous)
        eq(r['energy_MWh'],previous+storage['eta_charge']*r['charge']*dt-r['discharge']*dt/storage['eta_discharge'])
        for k in ('energy_start_MWh','energy_MWh'):
            bound(r[k],storage['soc_min']*storage['energy_capacity_MWh'],storage['soc_max']*storage['energy_capacity_MWh'])
        if storage['energy_capacity_MWh']:
            eq(r['soc'],r['energy_MWh']/storage['energy_capacity_MWh'])
        elif not math.isnan(r['soc']): raise ValueError("Zero capacity SOC must be undefined")
        previous=r['energy_MWh']
    if terminal: eq(previous,storage['energy_capacity_MWh']*storage['soc_initial'])
    if max(errors)>=1e-6: raise ValueError(f"Residual {max(errors)}")
    return max(errors)

if __name__=='__main__':
    folder=Path(sys.argv[1]); m=json.loads((folder/'run_manifest.json').read_text(encoding='utf-8'))
    residuals={name:audit_file(folder/(name+'_hourly.csv'),c['storage'],c['thermal'],c['dt'],c['terminal']) for name,c in m['cases'].items()}
    print(json.dumps(residuals,indent=2))
