"""U11R14: three HiGHS and three native CBC LPs, with zero new dispatch."""
import argparse
from fractions import Fraction as F
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import numpy as np
import pandas as pd

from scripts.audit_u11r08_feasibility import certificate, classify, read_csv
from src.annual_clustering import annual_metrics
from src.fixed_weights_capacity_transfer import fixed_days
from src.input_energy_feasibility import solve_lp, check_solution
from src.proxy_energy_feasibility import CHANNELS, SEEDS, amounts, build_model, cbc, decision
from src.study_runtime import ROOT, StudyRun, configuration, dump, sha


def exact_amounts(rows, ceiling):
    return [sum(F(r[ch]) for r in rows) for ch in CHANNELS[:3]]+[sum(max(F(r["load"])-F(r["wind"])-F(r["solar"])-ceiling,F(0)) for r in rows)]


def worker(model_path, out):
    command = [sys.executable,str(Path(__file__).resolve()),"--worker",str(model_path),"--solution",str(out/"solution.json")]
    record = dict(command=command,timeout_seconds=90)
    started = perf_counter()
    try:
        process = subprocess.run(command,capture_output=True,text=True,encoding="utf-8",timeout=90,
                                 creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        (out/"solver.log").write_text(process.stdout+process.stderr,encoding="utf-8")
        record.update(returncode=process.returncode,seconds=perf_counter()-started)
        process.check_returncode()
        solution = json.loads((out/"solution.json").read_text(encoding="utf-8"))
        if solution.get("success") is not True or solution.get("status") != 0: raise RuntimeError("HiGHS did not prove Optimal")
        return solution
    except subprocess.TimeoutExpired as exc:
        (out/"solver.log").write_text(str(exc.stdout or "")+str(exc.stderr or ""),encoding="utf-8")
        record.update(error=repr(exc),seconds=perf_counter()-started)
        raise
    finally:
        dump(out/"process.json",record)


def run(run_id):
    run = StudyRun("U11R14-proxy-energy-feasibility","annual",run_id)
    started = perf_counter()
    calls = 0
    try:
        cfg,st,th,e = configuration()
        expected = dict(numpy="2.5.3",pandas="3.0.5",scipy="1.18.1",pulp="3.3.0")
        versions = {name:importlib.metadata.version(name) for name in expected}
        if versions != expected or th["thermal_max_MW"] != 120: raise ValueError("Frozen runtime/ceiling mismatch")
        run.manifest["packages"].update(versions)
        run.manifest["parameters"] = dict(N=48,seeds=list(SEEDS),channels=CHANNELS,thermal_max_MW=120,threshold=.02,
                                          primary_lp_budget=3,cross_lp_budget=3,dispatch_budget=0,secondary_objectives=0)
        run.manifest["source_sha256"]["tests/test_proxy_energy_feasibility.py"] = sha(ROOT/"tests/test_proxy_energy_feasibility.py")
        preflight = json.loads((ROOT/"results/annual/U11R14-predecessor-audit-v01.json").read_text(encoding="utf-8"))
        if not preflight["passed"] or preflight["run_manifest_sha256"] != sha(ROOT/"results/annual/U11R13-v01/run_manifest.json"): raise ValueError("Predecessor audit mismatch")
        data = pd.read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv",float_precision="round_trip")
        raw = read_csv(ROOT/"results/annual/U11R02-v01/input_8760h.csv")
        exact_target = exact_amounts(raw,F(120))
        target = amounts(data,120.)
        full = pd.read_csv(ROOT/"results/annual/U11R02-v01/full_annual.csv",float_precision="round_trip").iloc[0]
        source = ROOT/"results/annual/U11R12-v01"
        comparisons,diagnostics = [],[]
        for seed in SEEDS:
            prefix = f"N48_seed{seed}"
            reps = pd.read_csv(source/(prefix+"_representatives.csv"),float_precision="round_trip")
            labels = pd.read_csv(ROOT/"results/annual/U11R08B-v01"/(prefix+"_labels.csv"))
            days,_,_ = fixed_days(data,reps,labels)
            energy = np.asarray([amounts(day,120.) for day in days]).T
            model = build_model(energy,target,reps.days)
            model.update(seed=seed,N=48,days=reps.day.tolist(),dates=reps.date_UTC.tolist(),unit="MWh")
            group = run.out/prefix
            group.mkdir()
            dump(group/"model.json",model)
            original_t = max(abs(math.fsum(a*c for a,c in zip(row,model["counts"]))/b-1) if b else 0. for row,b in zip(model["energy"],target))
            dump(group/"count_feasible_point.json",dict(weights=model["counts"],t=original_t,checks=check_solution(model,model["counts"],original_t)))
            exact_energy = [exact_amounts(raw[int(d)*24:(int(d)+1)*24],F(120)) for d in reps.day]
            exact_energy = list(map(list,zip(*exact_energy)))
            primary_dir = group/"highs"
            primary_dir.mkdir()
            calls += 1
            run.manifest["lp_calls"] = calls
            dump(run.out/"run_manifest.json",run.manifest)
            primary = worker(group/"model.json",primary_dir)
            checks = check_solution(model,primary["weights"],primary["t"])
            dump(primary_dir/"checks.json",checks)
            calls += 1
            run.manifest["lp_calls"] = calls
            dump(run.out/"run_manifest.json",run.manifest)
            cross = cbc(model,group/"cbc")
            if abs(primary["objective"]-cross["objective"]) > 1e-8: raise ValueError("Solver objectives differ")
            proof = certificate(exact_energy,exact_target,model["counts"],primary["weights"],primary["inequality_marginals"],primary["equality_marginals"])
            dump(group/"certificate.json",proof)
            if F(proof["gap"]) > F("1e-8"): raise ValueError("Exact certificate gap exceeds frozen guard")
            state = classify(primary["t"],proof)
            comparisons.append(dict(N=48,seed=seed,primary_t=primary["t"],cbc_t=cross["t"],
                                    exact_lower=proof["lower_float"],exact_upper=proof["upper_float"],classification=state))
            summary = pd.read_csv(source/(prefix+"_summary.csv"),float_precision="round_trip")
            if list(summary.scenario) != [prefix+f"_cluster{k}" for k in range(48)]: raise ValueError("Saved dispatch inventory mismatch")
            for label,q in (("highs",primary),("cbc",cross)):
                pd.DataFrame(dict(cluster=np.arange(48),day=reps.day,date_UTC=reps.date_UTC,c=reps.days,w=q["weights"])).to_csv(group/(label+"_weights.csv"),index=False,float_format="%.17g")
                exported = pd.read_csv(group/(label+"_weights.csv"),float_precision="round_trip")
                if exported.w.tolist() != q["weights"]: raise ValueError("Weight CSV lost precision")
                checked = check_solution(model,exported.w,q["t"])
                metrics = annual_metrics(summary.to_dict("records"),exported.w)
                E = max(abs(metrics[k]-full[k]) for k in ("renewable_utilization_pct","curtailment_rate_pct"))
                diagnostic = dict(seed=seed,solver=label,**metrics,worst_error_pp=E,
                                  max_input_relative_error=max(checked["absolute_relative_errors"][:3]),
                                  proxy_relative_error=checked["absolute_relative_errors"][3],
                                  cost_error_CNY=metrics["total_cost_CNY"]-full["total_cost_CNY"],
                                  unserved_error_MWh=metrics["unserved_MWh"]-full["unserved_MWh"])
                diagnostic["passes_ED"] = E <= 1 and diagnostic["max_input_relative_error"] <= .02
                diagnostics.append(diagnostic)
            print(seed,"t",primary["t"],"exact bounds",proof["lower_float"],proof["upper_float"],state,flush=True)
        verdict = decision(comparisons)
        pd.DataFrame(comparisons).to_csv(run.out/"comparison.csv",index=False,float_format="%.17g")
        pd.DataFrame(diagnostics).to_csv(run.out/"diagnostics.csv",index=False,float_format="%.17g")
        if calls != 6 or run.manifest["cases"]: raise ValueError("Frozen solve budget mismatch")
        for path,digest in run.manifest["source_sha256"].items():
            if sha(ROOT/path) != digest: raise ValueError("Source drift: "+path)
        run.manifest.update(lp_calls=calls,dispatch_calls=0)
        run.finish(verdict,dict(primary_lp_calls=3,cross_lp_calls=3,dispatch_calls=0,groups=3,
                               classification=[q["classification"] for q in comparisons],elapsed_seconds=perf_counter()-started))
    except Exception as exc:
        run.manifest.update(status="blocked",verdict="invalid",error=repr(exc),lp_calls=calls,dispatch_calls=0)
        dump(run.out/"failure.json",dict(error=repr(exc),lp_calls=calls,dispatch_calls=0))
        raise
    finally:
        run.manifest["artifacts"] = {p.relative_to(run.out).as_posix():sha(p) for p in run.out.rglob("*") if p.is_file() and p.name != "run_manifest.json"}
        dump(run.out/"run_manifest.json",run.manifest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id",default="U11R14-v01")
    parser.add_argument("--worker",type=Path)
    parser.add_argument("--solution",type=Path)
    args = parser.parse_args()
    if args.worker:
        if args.solution is None: parser.error("--solution is required")
        if args.solution.exists(): raise FileExistsError(args.solution)
        dump(args.solution,solve_lp(json.loads(args.worker.read_text(encoding="utf-8"))))
    else: run(args.run_id)


if __name__ == "__main__": main()
