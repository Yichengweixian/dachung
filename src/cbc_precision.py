"""Read CBC's native double solution, avoiding rounded text column values."""
from pathlib import Path
import struct
import subprocess
import tempfile
import pulp


class PreciseCBC(pulp.PULP_CBC_CMD):
    def actualSolve(self, lp, **kwargs):
        with tempfile.TemporaryDirectory(prefix='u06-cbc-') as directory:
            root = Path(directory)
            mps, text, binary = (root/n for n in ['model.mps','solution.txt','solution.bin'])
            variables, names, constraints, _ = lp.writeMPS(str(mps), rename=1)
            args = [self.path, str(mps), '-primalTolerance','1e-9','-integerTolerance','1e-9',
                    '-ratioGap','0','-allowableGap','0','-threads','1','-branch',
                    '-printingOptions','all','-solution',str(text),'-saveSolution',str(binary),'-quit']
            process = subprocess.run(args, capture_output=True, text=True, check=True)
            status, values, dj, pi, slacks, sol_status = self.readsol_MPS(str(text),lp,variables,names,constraints)
            lp.assignStatus(status, sol_status)
            if status != pulp.LpStatusOptimal or sol_status != pulp.LpSolutionOptimal:
                return status
            raw = binary.read_bytes()
            rows, cols = struct.unpack_from('=ii', raw)
            assert rows == len(lp.constraints) and cols == len(variables), 'CBC binary dimensions mismatch'
            assert len(raw) == 16+16*(rows+cols), 'CBC binary size mismatch'
            objective = struct.unpack_from('=d',raw,8)[0]
            exact = struct.unpack_from(f'={cols}d',raw,16+16*rows)
            self.precision_evidence = {'text_max_rounding':max(abs(values[v.name]-x) for v,x in zip(variables,exact)),
                                      'binary_objective':objective, 'cbc_log':process.stdout,
                                      'text_solution':text.read_text(encoding='utf-8')}
            lp.assignVarsVals({v.name:x for v,x in zip(variables,exact)})
            lp.assignVarsDj(dj)
            lp.assignConsPi(pi)
            lp.assignConsSlack(slacks,activity=True)
            return status
