"""Reconstruct manifest-exact historical files in an isolated audit directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=False)
    snapshot = Path(tempfile.mkdtemp(prefix='dachuang-u11-audit-'))
    required, restored = {}, []
    manifests = ['results/annual/U11R02-v01/run_manifest.json',
                 'results/annual/U11R03-v01/run_manifest.json']
    for rel in manifests:
        record = json.loads((ROOT / rel).read_text(encoding='utf-8'))
        entries = {**record['freeze']['sha256'], **record['source_sha256']}
        entries[rel] = digest((ROOT / rel).read_bytes())
        entries.update({str((Path(rel).parent / p).as_posix()): h
                        for p, h in record['artifacts'].items()})
        for p, h in entries.items():
            if p in required and required[p] != h:
                raise ValueError('Conflicting historical versions: ' + p)
            required[p] = h
    prior_audit = json.loads((ROOT / 'results/annual/U11R03-v01-independent-audit.json').read_text(encoding='utf-8'))
    required['scripts/audit_representative_days.py'] = prior_audit['audit_source_sha256']
    for rel, expected in required.items():
        data = (ROOT / rel).read_bytes()
        if digest(data) != expected:
            # Only retrieve recorded source from Git; never rewrite live files.
            if rel != 'scripts/check_materials_numbers.py':
                raise ValueError('Unexpected drift: ' + rel)
            ref = '5a1cbbbe752eb4df9d65718f035d157f975c3ac0'
            blob = subprocess.check_output(['git', 'show', ref + ':' + rel], cwd=ROOT)
            candidates = [blob, blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')]
            data = next((b for b in candidates if digest(b) == expected), None)
            if data is None:
                raise ValueError('Git source does not match recorded SHA-256')
            restored.append(dict(path=rel, git_ref=ref, sha256=expected))
        target = snapshot / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
    def execute(name, command):
        result = subprocess.run([sys.executable, '-X', 'utf8', *command], cwd=snapshot,
                                capture_output=True, encoding='utf-8')
        (output / (name + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
        (output / (name + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(name + ' failed; see retained logs')
        return json.loads(result.stdout)
    evidence = dict(snapshot=str(snapshot), required_sha256=required, restored=restored,
                    script_sha256=digest(Path(__file__).read_bytes()), new_solver_calls=0)
    try:
        evidence['representatives'] = execute('representatives', [
            'scripts/audit_representative_days.py', 'U11R03-v01', '--output', 'isolated_audit.json'])
        evidence['baseline'] = execute('baseline', ['-c',
            "import json; from run_representative_days import check_baseline; "
            "from src.study_runtime import configuration,ROOT; from src.data_loader import load_input_data; "
            "cfg,s,t,e=configuration(); data=load_input_data(ROOT/'results/annual/U11R02-v01/input_8760h.csv',8760); "
            "full,report=check_baseline(data,cfg,s,t,e); print(json.dumps(dict(full=full,audit=report)))"])
        # Independently rebuild costs as well as energy for all U11R03 saved days.
        evidence['costs'] = execute('costs', ['-c',
            "import json; from dataclasses import asdict; import pandas as pd; "
            "from src.study_runtime import ROOT,configuration; "
            "from src.optimization_validation import summarize_dispatch; "
            "from src.economic_model import evaluate_system_costs,validate_cost_results; "
            "cfg,s,t,e=configuration(); folder=ROOT/'results/annual/U11R03-v01'; diffs=[]; "
            "\nfor p in sorted(folder.glob('N*_summary.csv')):\n"
            " rows=pd.read_csv(p)\n for row in rows.to_dict('records'):\n"
            "  q=pd.read_csv(folder/(row['scenario']+'_hourly.csv')); r=summarize_dispatch(q,asdict(e)).iloc[0].to_dict(); "
            "r.update(scenario=row['scenario'],energy_capacity_MWh=s['energy_capacity_MWh'],power_capacity_MW=s['power_capacity_MW'],num_steps=24,time_step_hours=1.,load_shedding_MWh=r['unserved_MWh'],storage_discharge_MWh=r['discharge_MWh'],initial_inventory_supply_MWh=max(0.,float(q.energy_start_MWh.iloc[0]-q.energy_MWh.iloc[-1]))*s['eta_discharge']); "
            "cost=evaluate_system_costs(pd.DataFrame([r]),e); validate_cost_results(cost,e); diffs.append(abs(float(cost.total_cost_CNY.iloc[0])-row['total_cost_CNY']))\n"
            "assert len(diffs)==252 and max(diffs)<1e-6; print(json.dumps(dict(days=len(diffs),max_cost_difference=max(diffs))))"])
        for rel, expected in required.items():
            if digest((snapshot / rel).read_bytes()) != expected:
                raise ValueError('Snapshot modified during audit: ' + rel)
            if rel not in {r['path'] for r in restored} and digest((ROOT / rel).read_bytes()) != expected:
                raise ValueError('Live source/artifact changed during audit: ' + rel)
        evidence['passed'] = True
    except Exception as exc:
        evidence.update(passed=False, error=repr(exc))
        raise
    finally:
        with (output / 'audit.json').open('x', encoding='utf-8') as stream:
            json.dump(evidence, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in evidence.items() if k != 'required_sha256'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
