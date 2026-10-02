"""CBC presolve-off weight LPs with native precision and retained solve evidence."""
from contextlib import nullcontext
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from time import perf_counter

import numpy as np
import pulp


class EvidenceCBC(pulp.PULP_CBC_CMD):
    def __init__(self, artifact_directory=None, **kwargs):
        super().__init__(**kwargs)
        self.artifact_directory = None if artifact_directory is None else Path(artifact_directory)

    def actualSolve(self, lp, **kwargs):
        if self.artifact_directory is None:
            context = tempfile.TemporaryDirectory(prefix='cbc-native-')
        else:
            self.artifact_directory.mkdir(parents=True, exist_ok=False)
            context = nullcontext(str(self.artifact_directory.resolve()))
        with context as folder:
            root = Path(folder)
            mps, text, binary = [root / n for n in ('model.mps', 'solution.txt', 'solution.bin')]
            variables, names, constraints, _ = lp.writeMPS(str(mps), rename=1)
            mapping = dict(variables=names, constraints=constraints,
                           original_variable_order=[v.name for v in variables], rows=len(lp.constraints),
                           columns=len(variables))
            (root / 'mapping.json').write_text(json.dumps(mapping, indent=2), encoding='utf-8')
            args = [self.path, mps.name, '-primalTolerance', '1e-9', '-integerTolerance', '1e-9',
                    '-ratioGap', '0', '-allowableGap', '0', '-threads', '0', '-presolve', 'off', '-branch',
                    '-printingOptions', 'all', '-solution', text.name, '-saveSolution', binary.name, '-quit']
            start = perf_counter()
            try:
                process = subprocess.run(args, cwd=root, capture_output=True, text=True, check=False, timeout=60,
                                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except subprocess.TimeoutExpired as exc:
                (root / 'process.json').write_text(json.dumps(dict(command=args, timeout_seconds=60,
                    elapsed_seconds=perf_counter()-start, error=repr(exc)), indent=2), encoding='utf-8')
                raise
            self.log = process.stdout
            (root / 'stdout.txt').write_text(process.stdout, encoding='utf-8')
            (root / 'stderr.txt').write_text(process.stderr, encoding='utf-8')
            (root / 'process.json').write_text(json.dumps(dict(command=args, returncode=process.returncode,
                timeout_seconds=60, elapsed_seconds=perf_counter()-start), indent=2), encoding='utf-8')
            process.check_returncode()
            status, values, dj, pi, slacks, sol_status = self.readsol_MPS(str(text), lp, variables, names, constraints)
            lp.assignStatus(status, sol_status)
            if status != pulp.LpStatusOptimal or sol_status != pulp.LpSolutionOptimal:
                return status
            raw = binary.read_bytes()
            rows, columns = struct.unpack_from('=ii', raw)
            if rows != len(lp.constraints) or columns != len(variables) or len(raw) != 16 + 16 * (rows + columns):
                raise ValueError('CBC native solution layout does not match model')
            native_objective = struct.unpack_from('=d', raw, 8)[0]
            primal = struct.unpack_from(f'={columns}d', raw, 16 + 16 * rows)
            if not np.isfinite(primal).all():
                raise ValueError('Nonfinite native solution')
            lp.assignVarsVals({v.name: value for v, value in zip(variables, primal)})
            lp.assignVarsDj(dj)
            lp.assignConsPi(pi)
            lp.assignConsSlack(slacks, activity=True)
            if abs(pulp.value(lp.objective) - native_objective) >= 1e-6:
                raise ValueError('Native solution objective mismatch')
            self.precision = dict(native_objective=native_objective,
                max_text_rounding=max(abs(values[v.name]-x) for v, x in zip(variables, primal)))
            return status
