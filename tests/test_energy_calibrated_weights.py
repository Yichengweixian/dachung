import unittest
from unittest.mock import patch
import numpy as np
from src.energy_calibrated_weights import calibrate, validate_inputs, check_stage


class CalibratedWeightsTests(unittest.TestCase):
    def test_exact_energy_and_repeat(self):
        c = [120, 120, 125]
        a = np.array([[10, 20, 40], [5, 30, 10], [0, 0, 0.]])
        b = a @ np.array([110, 130, 125])
        w, records = calibrate(a, b, c, ['01', '02', '03'])
        repeated, again = calibrate(a, b, c, ['01', '02', '03'])
        np.testing.assert_allclose(w, repeated, atol=1e-6, rtol=0)
        np.testing.assert_allclose(a @ w, b, atol=1e-4, rtol=0)
        self.assertEqual(len(records), 5)
        self.assertEqual(len(again), 5)
        self.assertLessEqual(abs(w.sum()-365), 1e-6)

    def test_unreachable_energy_is_valid_bounded_solution(self):
        a = np.array([[10, 20], [0, 0], [0, 0.]])
        w, records = calibrate(a, [100000, 0, 0], [180, 185], ['02', '01'])
        self.assertGreater(records[0]['objective'], .02)
        self.assertGreaterEqual(w[0], 90-1e-6)
        self.assertEqual([r['stage'] for r in records], ['primary', 'secondary', 'lex_001', 'lex_000'])

    def test_zero_channels_and_tie(self):
        w, records = calibrate(np.zeros((3, 2)), np.zeros(3), [180, 185], ['01', '02'])
        np.testing.assert_allclose(w, [180, 185], atol=1e-6, rtol=0)
        self.assertEqual(records[0]['objective'], 0)

    def test_invalid_inputs(self):
        for c in ([0, 365], [180, 180], [180.5, 184.5]):
            with self.assertRaises(ValueError):
                validate_inputs(np.zeros((3, 2)), np.ones(3), c, ['01', '02'])
        with self.assertRaises(ValueError):
            validate_inputs(np.ones((3, 2)), np.zeros(3), [180, 185], ['01', '02'])
        with self.assertRaises(ValueError):
            validate_inputs(np.zeros((3, 2)), [np.nan, 0, 0], [180, 185], ['01', '02'])

    def test_solve_failure_is_recorded_and_stops(self):
        records = []
        with patch('src.energy_calibrated_weights.FullPrecisionCBC.actualSolve', return_value=-1):
            with self.assertRaises(RuntimeError):
                calibrate(np.zeros((3, 2)), np.zeros(3), [180, 185], ['01', '02'], records.append)
        self.assertEqual(len(records), 1)
        self.assertIn('error', records[0])

    def test_exported_invalid_weights_rejected(self):
        record = dict(weights=[0, 365], t=0, deviations=[1, 1], t_limit=None, l_limit=None, pins=[])
        with self.assertRaises(ValueError):
            check_stage(np.zeros((3, 2)), np.zeros(3), np.array([180, 185]), record)
