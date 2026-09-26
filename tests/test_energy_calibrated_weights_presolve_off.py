"""U11R06 checks that the copied calibration changes only CBC presolve."""
from pathlib import Path
import unittest

import pulp

from src.cbc_presolve_off import FullPrecisionCBC


ROOT = Path(__file__).resolve().parents[1]


class PresolveOffTests(unittest.TestCase):
    def test_solver_source_delta(self):
        old = (ROOT / 'src/cbc_full_precision.py').read_text(encoding='utf-8')
        new = (ROOT / 'src/cbc_presolve_off.py').read_text(encoding='utf-8')
        self.assertEqual(new.replace('"-presolve", "off", ', '').rstrip('\n'), old.rstrip('\n'))

    def test_calibration_source_delta(self):
        old = (ROOT / 'src/energy_calibrated_weights.py').read_text(encoding='utf-8')
        new = (ROOT / 'src/energy_calibrated_weights_presolve_off.py').read_text(encoding='utf-8')
        self.assertEqual(new.replace('from .cbc_presolve_off import FullPrecisionCBC',
                                     'from .cbc_full_precision import FullPrecisionCBC').replace(
                                         "'U11R06_energy_weights'", "'U11R04_energy_weights'").rstrip('\n'),
                         old.rstrip('\n'))

    def test_real_cbc_off_and_optimal(self):
        problem = pulp.LpProblem('presolve_off_smoke', pulp.LpMinimize)
        x = pulp.LpVariable('x', lowBound=0)
        problem += x
        problem += x >= 1
        solver = FullPrecisionCBC(msg=False)
        problem.solve(solver)
        self.assertEqual(problem.status, pulp.LpStatusOptimal)
        self.assertEqual(problem.sol_status, pulp.LpSolutionOptimal)
        self.assertAlmostEqual(pulp.value(x), 1.)
        self.assertIn('Option for presolve changed from on to off', solver.log)


if __name__ == '__main__':
    unittest.main()
