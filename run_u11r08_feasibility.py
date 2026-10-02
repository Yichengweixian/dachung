"""Run U11R08 only; saved representative days and no dispatch solves."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import platform
import subprocess
import sys
import traceback

import pandas as pd

from src.input_energy_feasibility import (
    ROOT, sha, dump, create_run_directory, load_saved_groups, execute_case,
    saved_dispatch_diagnostic, solve_lp,
)


def run(run_id):
    out = create_run_directory(ROOT / 'results/annual', run_id)
    study = ROOT / 'instructions/studies/U11R08-input-energy-feasibility'
    manifest = dict(run_id=run_id, unit=study.name, started_at=datetime.now(timezone.utc).isoformat(),
                    status='in_progress', verdict=None, lp_calls=0, dispatch_calls=0,
                    python=sys.version, executable=sys.executable, platform=platform.platform(),
                    base_git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                    source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in
                                   [ROOT / 'run_u11r08_feasibility.py', ROOT / 'src/input_energy_feasibility.py']},
                    packages={k: importlib.metadata.version(k) for k in ['numpy', 'pandas', 'scipy', 'pulp']},
                    cases={})
    stage, group = 'preflight', None
    try:
        freeze = json.loads((study / 'freeze.json').read_text('utf-8'))
        manifest.update(freeze=freeze, freeze_sha256=sha(study / 'freeze.json'))
        dump(out / 'run_manifest.json', manifest)
        for path, expected in freeze['sha256'].items():
            if sha(ROOT / path) != expected:
                raise ValueError('Frozen file changed: ' + path)
        old_counts = {}
        for name in ['U11R02', 'U11R03']:
            folder = ROOT / 'results/annual' / f'{name}-v01'
            old = json.loads((folder / 'run_manifest.json').read_text('utf-8'))
            for path, expected in old['artifacts'].items():
                if sha(folder / path) != expected:
                    raise ValueError('Original artifact hash mismatch: ' + str(folder / path))
            old_counts[name] = len(old['artifacts'])
        models = load_saved_groups()
        dump(out / 'input_audit.json', dict(passed=True, original_artifact_hashes=old_counts,
             freeze_hashes=len(freeze['sha256']), groups=len(models), representative_days=252,
             annual_hours=8760, time_step_hours=1, power_unit='MW', energy_unit='MWh',
             clustering_calls=0, saved_curves_exact_match=True, annual_target_MWh=models[0]['target']))
        rows = []
        for model in models:
            group = f"N{model['N']}_seed{model['seed']}"
            stage = 'primary_lp'
            manifest['lp_calls'] += 1
            manifest['current_group'] = group
            dump(out / 'run_manifest.json', manifest)
            solution, checks = execute_case(model, out / group)
            stage = 'saved_dispatch_diagnostic'
            diagnostic = saved_dispatch_diagnostic(model, solution['weights'])
            dump(out / group / 'supplementary_dispatch.json', diagnostic)
            t = solution['t']
            provisional = 'uncertain' if abs(t - .02) <= 1e-8 else ('reachable' if t <= .02 else 'unreachable')
            row = dict(N=model['N'], seed=model['seed'], D_min=t, distance_to_2pct=t - .02,
                       max_input_relative_error=checks['max_input_relative_error'], provisional_status=provisional,
                       renewable_utilization_pct=diagnostic['renewable_utilization_pct'],
                       curtailment_rate_pct=diagnostic['curtailment_rate_pct'], worst_error_pp=diagnostic['worst_error_pp'])
            rows.append(row)
            manifest['cases'][group] = dict(status='Optimal', **row)
            print(group, 'D_min=', repr(t), 'distance=', repr(t - .02), flush=True)
        pd.DataFrame(rows).to_csv(out / 'comparison.csv', index=False, float_format='%.17g', lineterminator='\n')
        for path, expected in freeze['sha256'].items():
            if sha(ROOT / path) != expected:
                raise ValueError('Frozen file changed during run: ' + path)
        manifest.update(status='awaiting_independent_audit', verdict=None,
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        note='Final scientific decision belongs to independent_audit/report.json; no dispatch solves.')
    except Exception as exc:
        manifest.update(status='blocked', verdict='invalid', error=repr(exc))
        dump(out / 'failure.json', dict(category='numerical_or_implementation_problem', stage=stage,
              group=group, error=repr(exc), traceback=traceback.format_exc(),
              mathematical_unreachability_claim=False, lp_calls=manifest['lp_calls']))
        raise
    finally:
        manifest['artifacts'] = {p.relative_to(out).as_posix(): sha(p) for p in sorted(out.rglob('*'))
                                 if p.is_file() and p.name != 'run_manifest.json'}
        dump(out / 'run_manifest.json', manifest)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='U11R08-v01')
    parser.add_argument('--worker', type=str, help=argparse.SUPPRESS)
    parser.add_argument('--solution', type=str, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if not args.solution:
            parser.error('--worker requires --solution')
        from pathlib import Path
        if Path(args.solution).exists():
            raise FileExistsError(args.solution)
        dump(args.solution, solve_lp(json.loads(Path(args.worker).read_text('utf-8'))))
    else:
        print(run(args.run_id))


if __name__ == '__main__':
    main()
