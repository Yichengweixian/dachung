"""Independent U11R08 audit, using original decimal inputs and exact certificates."""
import argparse
import csv
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import sys
import subprocess
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pulp
from src.cbc_full_precision import FullPrecisionCBC

CHANNELS = ['load', 'wind', 'solar']

def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')

def require(condition, message):
    if not condition:
        raise ValueError(message)

def exact_rows(energy, target):
    rows, rhs = [], []
    for a, total in zip(energy, target):
        require(total >= 0 and all(x >= 0 for x in a), 'negative input')
        if total == 0:
            require(all(x == 0 for x in a), 'nonzero representative in zero channel')
        else:
            row = [x / total for x in a]
            rows.extend([row, [-x for x in row]])
            rhs.extend([F(1), F(-1)])
    return rows, rhs

def certificate(energy, target, counts, weights, inequality, equality):
    rows, rhs = exact_rows(energy, target)
    require(len(inequality) == len(rows) and len(equality) == 1, 'dual dimensions')
    native = [F.from_float(float(w)) for w in weights]
    lower = [F(c)/2 for c in counts]
    upper = [F(c)*2 for c in counts]
    proof = [min(hi,max(lo,w)) for w,lo,hi in zip(native,lower,upper)]
    require(max(abs(w-p) for w,p in zip(native,proof)) <= F('1e-7'), 'large bound repair')
    delta = F(365)-sum(proof)
    require(abs(delta)<=F('1e-7'), 'large sum repair')
    for i in range(len(proof)):
        change = min(delta,upper[i]-proof[i]) if delta>0 else max(delta,lower[i]-proof[i])
        proof[i] += change
        delta -= change
    require(delta == 0, 'cannot repair sum')
    y = [min(F(0),F.from_float(float(v))) for v in inequality]
    scale = max(F(1),-sum(y))
    y = [v/scale for v in y]
    z = F.from_float(float(equality[0]))
    r = [-sum(row[i]*v for row,v in zip(rows,y))-z for i in range(len(counts))]
    lb = max(F(0),sum(b*v for b,v in zip(rhs,y))+365*z+sum(min(v*lo,v*hi) for v,lo,hi in zip(r,lower,upper)))
    ub = max([F(0)]+[sum(x*w for x,w in zip(row,proof))-b for row,b in zip(rows,rhs)])
    require(lb<=ub, 'invalid exact bounds')
    return {'lower':str(lb),'upper':str(ub),'gap':str(ub-lb), 'lower_float':float(lb),'upper_float':float(ub),
            'proof_weights':list(map(str,proof)), 'max_repair':str(max(abs(w-p) for w,p in zip(native,proof))),
            'dual_y':list(map(str,y)), 'dual_z':str(z), 'dual_scale':str(scale)}

def classify(t, cert):
    if F(cert['upper'])-F(cert['lower'])>F('1e-8'):
        return 'uncertain'
    if abs(t-.02)<=1e-8:
        return 'uncertain'
    if F(cert['upper'])<=F('0.02') and t<=.02:
        return 'reachable'
    if F(cert['lower'])>F('0.02') and t>.02:
        return 'unreachable'
    return 'uncertain'

def residuals(energy,target,counts,weights,t):
    require(all(math.isfinite(v) for v in [*weights,t]), 'nonfinite solution')
    rows,rhs=exact_rows(energy,target)
    w=[F.from_float(float(x)) for x in weights]
    return {'sum':float(abs(sum(w)-365)),
            'bounds':float(max([F(0)]+[max(F(c)/2-x,x-2*c) for c,x in zip(counts,w)])),
            'energy':float(max([F(0)]+[sum(a*x for a,x in zip(row,w))-b-F.from_float(float(t)) for row,b in zip(rows,rhs)])),
            'nonnegative_t':max(0.,-t)}

def check_residuals(data):
    require(data['sum']<=1e-7 and data['bounds']<=1e-7 and data['energy']<=1e-8 and data['nonnegative_t']<=1e-8,'constraint residual failed')

def close(a,b,label,tol=1e-8):
    require(abs(float(a)-float(b))<=tol, label)

def original_data(n,seed,annual):
    prefix=ROOT/'results/annual/U11R03-v01'/f'N{n}_seed{seed}'
    reps=read_csv(str(prefix)+'_representatives.csv')
    labels=read_csv(str(prefix)+'_labels.csv')
    inputs=read_csv(str(prefix)+'_inputs.csv')
    require(len(reps)==n and len(labels)==365 and len(inputs)==24*n,'source dimensions')
    require([int(x['cluster']) for x in reps]==list(range(n)),'cluster order')
    require(sorted(int(x['day']) for x in labels)==list(range(365)),'label days')
    hist=Counter(int(x['cluster']) for x in labels)
    counts=[int(x['days']) for x in reps]
    require([hist[i] for i in range(n)]==counts and sum(counts)==365,'cluster counts')
    energy=[[] for _ in CHANNELS]
    for i,rep in enumerate(reps):
        day=int(rep['day'])
        block=[r for r in inputs if int(r['cluster'])==i]
        require(len(block)==24 and [int(r['hour']) for r in block]==list(range(24)),'input hours')
        for k,ch in enumerate(CHANNELS):
            source=[annual[day*24+h][ch] for h in range(24)]
            require(all(float(r[ch])==float(v) for r,v in zip(block,source)),'representative source mismatch')
            energy[k].append(sum(map(F,source)))
    return energy,counts,reps,prefix

def diagnostics(prefix, reps, weights):
    summary=read_csv(str(prefix)+'_summary.csv')
    require(len(summary)==len(reps),'summary dimensions')
    weighted={key:0. for key in ['renewable_available_MWh','renewable_used_MWh','curtailment_MWh']}
    mapping={'renewable_available_MWh':['wind_available','solar_available'], 'renewable_used_MWh':['wind_used','solar_used'], 'curtailment_MWh':['wind_curt','solar_curt']}
    for i,(rep,w) in enumerate(zip(reps,weights)):
        rows=read_csv(str(prefix)+f'_cluster{i}_hourly.csv')
        require(len(rows)==24,'dispatch hours')
        s=next(x for x in summary if x['scenario']==prefix.name+f'_cluster{i}')
        require(s['solver_status']=='Optimal','historical dispatch status')
        for key,cols in mapping.items():
            amount=math.fsum(float(row[col]) for row in rows for col in cols)
            close(amount,s[key],f'summary {key}',1e-7)
            weighted[key]+=w*amount
    available=weighted['renewable_available_MWh']
    weighted['renewable_utilization_pct']=100*weighted['renewable_used_MWh']/available
    weighted['curtailment_rate_pct']=100*weighted['curtailment_MWh']/available
    annual=read_csv(ROOT/'results/annual/U11R02-v01/full_annual.csv')[0]
    weighted['worst_error_pp']=max(abs(weighted[k]-float(annual[k])) for k in ['renewable_utilization_pct','curtailment_rate_pct'])
    return weighted

def solve_cbc(folder,energy,target,counts):
    rows,rhs=exact_rows(energy,target)
    problem=pulp.LpProblem('independent_energy_feasibility',pulp.LpMinimize)
    w=[pulp.LpVariable(f'w_{i:03}',lowBound=c/2,upBound=2*c) for i,c in enumerate(counts)]
    t=pulp.LpVariable('t',lowBound=0)
    problem+=t
    problem+=pulp.lpSum(w)==365
    for row,b in zip(rows,rhs):
        problem+=pulp.lpSum(float(a)*v for a,v in zip(row,w))-t<=float(b)
    problem.writeLP(str(folder/'model.lp'))
    problem.writeMPS(str(folder/'model.mps'))
    solver=FullPrecisionCBC(msg=False)
    try:
        status=problem.solve(solver)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        chunks=[getattr(exc,'stdout',None),getattr(exc,'stderr',None)]
        solver.log='\n'.join(x.decode('utf-8',errors='replace') if isinstance(x,bytes) else x for x in chunks if x)
        raise
    finally:
        (folder/'cbc.log').write_text(getattr(solver,'log','CBC failed before log capture'),encoding='utf-8')
    require(status==pulp.LpStatusOptimal and problem.sol_status==pulp.LpSolutionOptimal,'CBC nonOptimal')
    weights=[v.value() for v in w]
    value=t.value()
    np.save(folder/'weights_native.npy',np.array(weights,dtype=np.float64))
    with (folder/'weights.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle); writer.writerow(['cluster','w'])
        writer.writerows((i,format(x,'.17g')) for i,x in enumerate(weights))
    require(weights==[float(r['w']) for r in read_csv(folder/'weights.csv')],'CBC roundtrip')
    save(folder/'solution.json',{'status':'Optimal','t':value,'weights':weights,'precision':solver.precision})
    check_residuals(residuals(energy,target,counts,weights,value))
    return value

def audit(run_id):
    require(Path(run_id).name==run_id,'invalid run id')
    run=ROOT/'results/annual'/run_id
    output=run/'independent_audit'
    output.mkdir(exist_ok=False)
    calls=0
    stage='source hashes'
    try:
        frozen=ROOT/'instructions/studies/U11R08-input-energy-feasibility/freeze.json'
        freeze=json.loads(frozen.read_text(encoding='utf-8'))
        for path,sha in freeze['sha256'].items():
            require(digest(ROOT/path)==sha,f'frozen hash mismatch: {path}')
        manifest_path=run/'run_manifest.json'
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        for path,sha in manifest['artifacts'].items():
            require(digest(run/path)==sha,f'main artifact mismatch: {path}')
        require(manifest['freeze_sha256']==digest(frozen),'main freeze hash')
        for path,sha in manifest['source_sha256'].items():
            require(digest(ROOT/path)==sha,f'main source hash: {path}')
        for historical in ['U11R02-v01','U11R03-v01']:
            history=ROOT/'results/annual'/historical
            original_manifest=json.loads((history/'run_manifest.json').read_text(encoding='utf-8'))
            for path,sha in original_manifest['artifacts'].items():
                require(digest(history/path)==sha,f'original manifest hash: {historical}/{path}')
        annual=read_csv(ROOT/'results/annual/U11R02-v01/input_8760h.csv')
        require(len(annual)==8760 and [int(r['hour']) for r in annual]==list(range(8760)),'annual hours')
        require(all(F(r[ch])>=0 for r in annual for ch in CHANNELS),'negative annual input')
        target=[sum(F(r[ch]) for r in annual) for ch in CHANNELS]
        table=read_csv(run/'comparison.csv')
        require(len(table)==9,'comparison dimensions')
        reports=[]
        for n in [12,24,48]:
            for seed in [42,7,2026]:
                name=f'N{n}_seed{seed}'
                stage=name
                folder=output/name; folder.mkdir()
                energy,counts,reps,prefix=original_data(n,seed,annual)
                main=run/name
                model=json.loads((main/'model.json').read_text())
                require(model['counts']==counts and model['N']==n and model['seed']==seed and model['channels']==CHANNELS,'main model metadata')
                require(model['dates']==[r['date_UTC'] for r in reps] and model['days']==[int(r['day']) for r in reps],'main representative dates')
                require(len(model['energy'])==3 and all(len(row)==n for row in model['energy']) and len(model['target'])==3,'main coefficient dimensions')
                for actual,expected in zip(model['target'],target): close(actual,expected,'main target',1e-7)
                for a,b in zip(model['energy'],energy):
                    for actual,expected in zip(a,b): close(actual,expected,'main energy',1e-9)
                solution=json.loads((main/'solution.json').read_text())
                require(solution['status']==0 and solution['success'] is True,'main nonOptimal')
                weights=solution['weights']; t=solution['t']
                require(len(weights)==n,'main weights dimensions')
                native=np.asarray(weights,dtype=np.float64)
                require(native.tolist()==weights,'main native float64 mismatch')
                csv_weights=read_csv(main/'weights.csv')
                require([float(r['w']) for r in csv_weights]==weights,'main CSV roundtrip')
                require([int(r['c']) for r in csv_weights]==counts,'main CSV counts')
                for r,rep in zip(csv_weights,reps):
                    require(all(str(r[k])==str(rep[k]) for k in ['cluster','day','date_UTC']),'main CSV identity')
                original_t=max([0.]+[abs(float(sum(a*c for a,c in zip(row,counts))/total)-1) for row,total in zip(energy,target) if total])
                residual={'original':residuals(energy,target,counts,counts,original_t),'solution':residuals(energy,target,counts,weights,t),'readback':residuals(energy,target,counts,[float(r['w']) for r in csv_weights],t)}
                for r in residual.values(): check_residuals(r)
                saved_residuals=json.loads((main/'constraints.json').read_text())
                for kind,values in residual.items():
                    require(saved_residuals[kind]['passed'] is True,'saved constraints status')
                    for independent,saved_key in [('sum','sum_residual'),('bounds','bound_residual'),('energy','normalized_residual')]:
                        close(values[independent],saved_residuals[kind][saved_key],'saved residual mismatch',1e-10)
                errors=read_csv(main/'energy_errors.csv')
                require([r['channel'] for r in errors]==CHANNELS,'error channels')
                actual_errors=[]
                for row,total,err in zip(energy,target,errors):
                    amount=sum(a*F.from_float(float(w)) for a,w in zip(row,weights))
                    signed=float(amount/total-1) if total else 0.
                    actual_errors.append(abs(signed))
                    for key,value in [('target_MWh',total),('weighted_MWh',amount),('signed_relative_error',signed),('absolute_relative_error',abs(signed))]:
                        close(err[key],value,f'energy errors {key}',1e-7 if 'MWh' in key else 1e-10)
                cert=certificate(energy,target,counts,weights,solution['inequality_marginals'],solution['equality_marginals'])
                save(folder/'certificate.json',cert)
                cert['optimality_certified']=F(cert['gap'])<=F('1e-8')
                cert['evidence_note']=None if cert['optimality_certified'] else 'Exact bounds too wide for frozen optimality certificate'
                save(folder/'certificate.json',cert)
                require(float(F(cert['lower']))-1e-8<=t<=float(F(cert['upper']))+1e-8,'main t outside certificate')
                calls+=1
                cbc_t=solve_cbc(folder,energy,target,counts)
                close(cbc_t,t,'CBC objective mismatch')
                diagnostic=diagnostics(prefix,reps,weights)
                saved_diagnostic=json.loads((main/'supplementary_dispatch.json').read_text())
                for key in ['renewable_utilization_pct','curtailment_rate_pct','worst_error_pp']:
                    close(saved_diagnostic[key],diagnostic[key],'saved diagnostic mismatch')
                comp=next(r for r in table if int(r['N'])==n and int(r['seed'])==seed)
                for key,value in [('D_min',t),('distance_to_2pct',t-.02),('max_input_relative_error',max(actual_errors)),*[(k,diagnostic[k]) for k in ['renewable_utilization_pct','curtailment_rate_pct','worst_error_pp']]]:
                    close(comp[key],value,f'comparison {key}')
                report={'N':n,'seed':seed,'D_min':t,'CBC_t':cbc_t,'status':classify(t,cert),'certificate':cert,'residuals':residual,'diagnostics':diagnostic,'input_relative_errors':actual_errors}
                save(folder/'audit.json',report); reports.append(report)
        common=[n for n in [12,24,48] if all(r['status']=='reachable' for r in reports if r['N']==n)]
        verdict='supported' if common else ('refuted' if all(any(r['N']==n and r['status']=='unreachable' for r in reports) for n in [12,24,48]) else 'inconclusive')
        result={'verdict':verdict,'common_N':common,'groups':reports,'independent_lp_calls':calls,'dispatch_calls':0,'main_manifest_sha256':digest(manifest_path),'freeze_sha256':digest(frozen),'audit_source_sha256':digest(__file__),'artifacts':{str(p.relative_to(output)).replace('\\','/'):digest(p) for p in sorted(output.rglob('*')) if p.is_file()}}
        save(output/'report.json',result)
        print(json.dumps({'verdict':verdict,'common_N':common,'independent_lp_calls':calls}))
        return result
    except Exception as exc:
        save(output/'failure.json',{'verdict':'invalid','engineering_status':'blocked','stage':stage,'error':str(exc),'traceback':traceback.format_exc(),'independent_lp_calls':calls,'dispatch_calls':0})
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--run-id',default='U11R08-v01')
    audit(parser.parse_args().run_id)
