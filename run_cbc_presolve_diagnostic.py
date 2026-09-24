"""U11R05: at most two presolve-off calls, first failure stops the unit."""
import argparse
import platform
from time import perf_counter
from src.cbc_presolve_diagnostic import execute_pair
from src.study_runtime import ROOT, StudyRun, dump, sha


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-id', default='U11R05-v01')
    args = p.parse_args()
    run = StudyRun('U11R05-cbc-presolve-diagnostic', 'annual', args.run_id)
    calls = []
    started = perf_counter()
    def attempted(name):
        calls.append(name)
        run.manifest['solver_attempts'] = calls.copy()
        dump(run.out/'run_manifest.json', run.manifest)
    try:
        if platform.python_version() != '3.13.14' or run.manifest['packages']['pulp'] != '3.3.0':
            raise ValueError('Frozen environment changed')
        result = execute_pair(run.out, attempted)
        run.finish(result['verdict'], result)
    except Exception as exc:
        run.manifest.update(status='blocked', verdict='invalid', error=repr(exc))
        dump(run.out/'failure.json', dict(error=repr(exc), solver_attempts=calls))
        raise
    finally:
        run.manifest.update(solver_attempts=calls, elapsed_seconds=perf_counter()-started)
        run.manifest['artifacts'] = {p.relative_to(run.out).as_posix():sha(p) for p in run.out.rglob('*') if p.is_file() and p.name != 'run_manifest.json'}
        dump(run.out/'run_manifest.json', run.manifest)


if __name__ == '__main__':
    main()
