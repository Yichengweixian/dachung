import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.input_energy_feasibility import (
    build_model, check_solution, solve_lp, save_weights, execute_case, create_run_directory,
    load_saved_groups, saved_dispatch_diagnostic,
)


class InputEnergyFeasibilityTests(unittest.TestCase):
    def model(self):
        return build_model([[10, 20], [0, 0], [0, 0]], [5475, 0, 0], [180, 185])

    def test_original_counts_are_feasible_with_nonzero_t(self):
        result = check_solution(self.model(), [180, 185], 25 / 5475)
        self.assertTrue(result['passed'])
        self.assertAlmostEqual(result['max_input_relative_error'], 25 / 5475)

    def test_exact_fit_and_zero_channels(self):
        result = solve_lp(self.model())
        self.assertTrue(result['success'])
        np.testing.assert_allclose(result['weights'], [182.5, 182.5], atol=1e-8)
        self.assertEqual(result['t'], 0)
        self.assertEqual(check_solution(self.model(), result['weights'], 0)['absolute_relative_errors'][1:], [0, 0])

    def test_unreachable_remains_feasible_lp(self):
        model = build_model([[10, 20], [0, 0], [0, 0]], [100000, 0, 0], [180, 185])
        result = solve_lp(model)
        self.assertTrue(result['success'])
        self.assertAlmostEqual(result['t'], 0.936)
        np.testing.assert_allclose(result['weights'], [90, 275], atol=1e-8)

    def test_all_zero_channels(self):
        model = build_model(np.zeros((3, 2)), [0, 0, 0], [180, 185])
        result = solve_lp(model)
        self.assertEqual(result['t'], 0)
        self.assertTrue(check_solution(model, result['weights'], 0)['passed'])

    def test_invalid_counts_and_zero_target(self):
        for counts in ([0, 365], [180, 180], [180.5, 184.5]):
            with self.assertRaises(ValueError):
                build_model(np.zeros((3, 2)), [0, 0, 0], counts)
        for target in ([0, 0, 0], [np.nan, 0, 0], [-1, 0, 0]):
            with self.assertRaises(ValueError):
                build_model([[1, 2], [0, 0], [0, 0]], target, [180, 185])

    def test_bounds_sum_and_error_violations_rejected(self):
        for weights, t in [([89, 276], 1), ([180, 186], 1), ([180, 185], 0), ([np.nan, 185], 1), ([180, 185], -1)]:
            with self.assertRaises(ValueError):
                check_solution(self.model(), weights, t)

    def test_native_precision_csv_round_trip(self):
        weights = [182.50000000000003, 182.49999999999997]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'weights.csv'
            saved = save_weights(path, [180, 185], weights, [0, 1], ['a', 'b'])
            np.testing.assert_array_equal(saved, weights)
            self.assertTrue(check_solution(self.model(), saved, 0)['passed'])

    def test_saved_dispatch_diagnostic_serializes_without_solver(self):
        model = load_saved_groups()[0]
        result = saved_dispatch_diagnostic(model, model['counts'])
        self.assertEqual(result['dispatch_solves'], 0)
        json.dumps(result, allow_nan=False)
        self.assertAlmostEqual(result['worst_error_pp'], 0.539816459, places=8)

    def test_nonoptimal_records_model_log_failure_and_stops(self):
        result = {'success': False, 'status': 2, 'message': 'Infeasible'}
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'case'
            with patch('src.input_energy_feasibility.invoke_worker', return_value=(result, 'solver infeasible')):
                with self.assertRaises(RuntimeError):
                    execute_case(self.model(), out)
            self.assertTrue((out / 'model.json').exists())
            self.assertEqual((out / 'solver.log').read_text(), 'solver infeasible')
            failure = json.loads((out / 'failure.json').read_text())
            self.assertEqual(failure['category'], 'numerical_or_implementation_problem')
            self.assertFalse((out / 'weights.csv').exists())

    def test_run_directory_does_not_overwrite_or_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            create_run_directory(base, 'U11R08-test')
            with self.assertRaises(FileExistsError):
                create_run_directory(base, 'U11R08-test')
            for value in ('../escape', 'C:/escape', 'other'):
                with self.assertRaises(ValueError):
                    create_run_directory(base, value)


if __name__ == '__main__':
    unittest.main()
