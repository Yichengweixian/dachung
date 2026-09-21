"""Versioned experiment artifacts and shared, independently audited evaluation."""
from datetime import datetime, timezone
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import pandas as pd

from .economic_model import EconomicParameters, evaluate_system_costs, validate_cost_results
from .optimization_model import solve_dispatch
from .optimization_validation import audit_dispatch, summarize_dispatch

ROOT = Path(__file__).resolve().parent.parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")

def configuration():
    cfg={p.stem:json.loads(p.read_text(encoding="utf-8")) for p in (ROOT/"config").glob("*.json")}
    thermal={k:cfg["optimization"][k] for k in ("thermal_min_MW","thermal_ramp_MW_per_h")}
    thermal["thermal_max_MW"]=cfg["no_storage"]["thermal_max_MW"]
    return cfg, cfg["storage"], thermal, EconomicParameters(**cfg["economics"]["parameters"])

def evaluate_case(data, storage, thermal, economics, dt=1., terminal=True):
    q, info=solve_dispatch(data,storage,thermal,asdict(economics),dt,terminal,mutual_exclusion=True)
    checks=audit_dispatch(q,data,storage,thermal,dt,terminal)
    if not checks["passed"]:
        raise ValueError(str(checks))
    totals=summarize_dispatch(q,asdict(economics),dt).iloc[0].to_dict()
    row={**totals,"scenario":"case","energy_capacity_MWh":storage["energy_capacity_MWh"],
         "power_capacity_MW":storage["power_capacity_MW"],"num_steps":len(data),"time_step_hours":dt,
         "load_shedding_MWh":totals["unserved_MWh"],"storage_discharge_MWh":totals["discharge_MWh"],
         "initial_inventory_supply_MWh":max(0,float(q.energy_start_MWh.iloc[0]-q.energy_MWh.iloc[-1]))*storage["eta_discharge"]}
    costs=evaluate_system_costs(pd.DataFrame([row]),economics)
    validate_cost_results(costs,economics)
    row.update(costs.iloc[0].to_dict())
    row["storage_utilization_pct"]=float(((q.charge>1e-6)|(q.discharge>1e-6)).mean()*100) if storage["energy_capacity_MWh"] else np.nan
    row["solver_status"]=info["solver_status"]
    row["max_residual"]=checks["max_residual"]
    return q,row,info

class StudyRun:
    def __init__(self, unit, group, run_id):
        self.unit=ROOT/"instructions/studies"/unit
        freeze=json.loads((self.unit/"freeze.json").read_text(encoding="utf-8"))
        for path,digest in freeze["sha256"].items():
            if sha(ROOT/path)!=digest: raise ValueError(f"Frozen file changed: {path}")
        self.out=ROOT/"results"/group/run_id
        self.out.mkdir(parents=True,exist_ok=False)
        self.fig=ROOT/"figures"/group/run_id
        self.manifest={"run_id":run_id,"unit":unit,"started_at":datetime.now(timezone.utc).isoformat(),
                       "freeze":freeze,"freeze_sha256":sha(self.unit/"freeze.json"),"status":"in_progress","verdict":None,
                       "python":sys.version,"platform":platform.platform(),"cases":{},
                       "source_sha256":{p.relative_to(ROOT).as_posix():sha(p) for p in
                           list((ROOT/"src").glob("*.py"))+list((ROOT/"scripts").glob("*.py"))+list(ROOT.glob("run_*.py"))},
                       "packages":{p:importlib.metadata.version(p) for p in ("numpy","pandas","matplotlib","pulp")}}
        dump(self.out/"run_manifest.json",self.manifest)
    def case(self,name,data,storage,thermal,economics,dt=1.,terminal=True):
        try:
            q,row,info=evaluate_case(data,storage,thermal,economics,dt,terminal)
            q.to_csv(self.out/(name+"_hourly.csv"),index=False,float_format="%.17g",encoding="utf-8")
            saved=pd.read_csv(self.out/(name+"_hourly.csv"))
            audit=audit_dispatch(saved,data,storage,thermal,dt,terminal)
            if not audit["passed"]: raise ValueError(str(audit))
            (self.out/(name+"_cbc.log")).write_text(info.pop("cbc_log"),encoding="utf-8")
            self.manifest["cases"][name]={**info,"max_residual":audit["max_residual"],"storage":storage,
                                           "thermal":thermal,"dt":dt,"terminal":terminal}
            row["scenario"]=name
            return saved,row
        except Exception as exc:
            self.manifest.update(status="blocked",verdict="invalid",failure_case=name,error=repr(exc))
            dump(self.out/"run_manifest.json",self.manifest)
            dump(self.out/"failure.json",{"case":name,"error":repr(exc)})
            raise
    def finish(self,verdict,details):
        for path,digest in self.manifest["freeze"]["sha256"].items():
            if sha(ROOT/path)!=digest: raise ValueError(f"Frozen file changed during run: {path}")
        self.manifest.update(status="complete",verdict=verdict,details=details)
        self.manifest["artifacts"]={p.name:sha(p) for p in self.out.iterdir() if p.is_file() and p.name!="run_manifest.json"}
        dump(self.out/"run_manifest.json",self.manifest)
        print(self.manifest["run_id"],verdict,details,flush=True)
