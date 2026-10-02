"""Check U11R08 feasibility guards, stopping, repeatability and retained CBC files."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pulp

from src.energy_calibrated_weights_resolved import BAND, calibrate, check_stage
from scripts.audit_energy_calibrated_days_resolved import audit_solver_evidence


class ResolvedWeightBandsTests(unittest.TestCase):
    def test_known_target_repeat_and_real_evidence(self):
        a = np.array([[10., 20., 40.], [5., 30., 10.], [0., 0., 0.]])
        counts = np.array([120., 120., 125.])
        target = a @ np.array([110., 130., 125.])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            w, records = calibrate(a, target, counts, ['01', '02', '03'], model_directory=root)
            repeated, _ = calibrate(a, target, counts, ['01', '02', '03'])
            np.testing.assert_allclose(w, repeated, atol=1e-6, rtol=0)
            self.assertEqual(len(records), 5)
            self.assertLessEqual(np.max(np.abs(a@w/np.where(target > 0, target, 1)-np.where(target > 0, 1, 0))), 1.1e-6)
            for record in records:
                self.assertEqual(record['status'], 'Optimal')
                self.assertEqual(record['band'], BAND)
                evidence = root/(record['stage']+'_cbc')
                self.assertTrue((evidence/'model.mps').is_file())
                self.assertTrue((evidence/'mapping.json').is_file())
                self.assertTrue((evidence/'solution.txt').read_text().startswith('Optimal'))
                raw = (evidence/'solution.bin').read_bytes()
                rows, columns = struct.unpack_from('=ii', raw)
                self.assertEqual(len(raw), 16+16*(rows+columns))
                process = json.loads((evidence/'process.json').read_text())
                self.assertEqual(process['returncode'], 0)
                self.assertIn('-presolve', process['command'])
                self.assertLessEqual(audit_solver_evidence(evidence, record), 1e-6)

    def test_infeasible_second_stage_stops_and_records(self):
        records = []
        def fake_solve(solver, model, **kwargs):
            if len(records) == 1:
                model.assignStatus(pulp.LpStatusInfeasible, pulp.LpSolutionInfeasible)
                return pulp.LpStatusInfeasible
            model.assignVarsVals({'w_000':180., 'w_001':185., 'd_000':0., 'd_001':0., 'worst_relative_error':0.})
            model.assignStatus(pulp.LpStatusOptimal, pulp.LpSolutionOptimal)
            return pulp.LpStatusOptimal
        with patch('src.energy_calibrated_weights_resolved.EvidenceCBC.actualSolve', fake_solve):
            with self.assertRaises(RuntimeError):
                calibrate(np.zeros((3, 2)), np.zeros(3), [180, 185], ['01', '02'], records.append)
        self.assertEqual([r['stage'] for r in records], ['primary', 'secondary'])
        self.assertEqual(records[-1]['status'], 'Infeasible')
        self.assertIn('error', records[-1])

    def test_band_does_not_relax_residual_guard(self):
        record = dict(weights=[180., 185.], t=2e-7, deviations=[0., 0.], t_limit=0., l_limit=None, pins=[])
        with self.assertRaises(ValueError):
            check_stage(np.zeros((3, 2)), np.zeros(3), np.array([180, 185]), record)


if __name__ == '__main__':
    unittest.main()
