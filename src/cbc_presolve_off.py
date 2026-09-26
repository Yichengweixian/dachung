"""Retain CBC native solution precision instead of rounded text-column values."""
from pathlib import Path
import struct
import subprocess
import tempfile

import numpy as np
import pulp


class FullPrecisionCBC(pulp.PULP_CBC_CMD):
    def actualSolve(self, lp, **kwargs):
        with tempfile.TemporaryDirectory(prefix="cbc-native-") as folder:
            root = Path(folder)
            mps, text, binary = [root / n for n in ("model.mps", "solution.txt", "solution.bin")]
            variables, names, constraints, _ = lp.writeMPS(str(mps), rename=1)
            args = [self.path, mps.name, "-primalTolerance", "1e-9", "-integerTolerance", "1e-9",
                    "-ratioGap", "0", "-allowableGap", "0", "-threads", "0", "-presolve", "off", "-branch",
                    "-printingOptions", "all", "-solution", text.name, "-saveSolution", binary.name, "-quit"]
            process = subprocess.run(args, cwd=root, capture_output=True, text=True, check=True, timeout=60,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.log = process.stdout
            status, values, dj, pi, slacks, sol_status = self.readsol_MPS(str(text), lp, variables, names, constraints)
            lp.assignStatus(status, sol_status)
            if status != pulp.LpStatusOptimal or sol_status != pulp.LpSolutionOptimal:
                return status
            raw = binary.read_bytes()
            rows, columns = struct.unpack_from("=ii", raw)
            if rows != len(lp.constraints) or columns != len(variables) or len(raw) != 16 + 16 * (rows + columns):
                raise ValueError("CBC native solution layout does not match model")
            native_objective = struct.unpack_from("=d", raw, 8)[0]
            primal = struct.unpack_from(f"={columns}d", raw, 16 + 16 * rows)
            if not np.isfinite(primal).all():
                raise ValueError("Nonfinite native solution")
            lp.assignVarsVals({v.name: value for v, value in zip(variables, primal)})
            lp.assignVarsDj(dj)
            lp.assignConsPi(pi)
            lp.assignConsSlack(slacks, activity=True)
            if abs(pulp.value(lp.objective) - native_objective) >= 1e-6:
                raise ValueError("Native solution objective mismatch")
            self.precision = {"native_objective":native_objective,
                              "max_text_rounding":max(abs(values[v.name]-x) for v,x in zip(variables,primal))}
            return status

