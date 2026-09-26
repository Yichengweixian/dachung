"""Regression checks for the read-only U11R07 diagnosis artifacts."""
from decimal import Decimal
import json
from pathlib import Path
import unittest

from scripts.diagnose_u11r06_serialization import decimal_residuals, read_mps


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/annual/U11R07-v01'


class U11R07ForensicsTests(unittest.TestCase):
    def test_replay_matches_saved_lp_hashes(self):
        report = json.loads((OUT / 'diagnosis.json').read_text(encoding='utf-8'))
        self.assertEqual(len(report['model_matches']), 16)
        self.assertTrue(all(report['model_matches'].values()))
        self.assertEqual(report['findings']['new_solver_calls'], 0)
        self.assertEqual(report['findings']['failed_stage'], 'lex_014')

    def test_mps_residuals_recompute(self):
        report = json.loads((OUT / 'diagnosis.json').read_text(encoding='utf-8'))
        previous = json.loads((ROOT / 'results/annual/U11R06-v01/N24_seed42_main_lex_006.json').read_text(encoding='utf-8'))
        values = {f'w_{i:03d}': Decimal.from_float(v) for i, v in enumerate(previous['weights'])}
        values.update({f'd_{i:03d}': Decimal.from_float(v) for i, v in enumerate(previous['deviations'])})
        values['worst_relative_error'] = Decimal.from_float(previous['t'])
        mapped = {report['original_to_mps_variables'][name]: value for name, value in values.items()}
        rows, rhs, senses, bounds = read_mps(OUT / 'reconstructed.mps')
        self.assertEqual(decimal_residuals(rows, rhs, senses, mapped, bounds), report['mps_residuals'])


if __name__ == '__main__':
    unittest.main()
