"""Independent arithmetic and fail-closed evidence tests; no solver calls."""
import importlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class IndependentAuditTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.audit_u11r09_fixed_weights'),
                             'Independent audit implementation is required')
        self.audit = importlib.import_module('scripts.audit_u11r09_fixed_weights')

    def test_weighted_energy_before_rates(self):
        result = self.audit.aggregate([
            {'renewable_available_MWh': 10., 'renewable_used_MWh': 10., 'curtailment_MWh': 0.},
            {'renewable_available_MWh': 100., 'renewable_used_MWh': 0., 'curtailment_MWh': 100.}], [2., 1.])
        self.assertEqual(result['renewable_available_MWh'], 120.)
        self.assertAlmostEqual(result['renewable_utilization_pct'], 100. / 6.)

    def test_complete_common_n_and_strict_boundaries(self):
        rows = [{'N': n, 'seed': s, 'D': .02, 'E_pp': 1.}
                for n in (12, 24, 48) for s in (42, 7, 2026)]
        self.assertEqual(self.audit.decide(rows), ('supported', [12, 24, 48]))
        rows[0]['D'] = math.nextafter(.02, math.inf)
        self.assertEqual(self.audit.decide(rows), ('invalid', []))
        rows[0]['D'] = .02
        rows[0]['E_pp'] = math.nextafter(1., math.inf)
        self.assertEqual(self.audit.decide(rows), ('supported', [24, 48]))
        self.assertEqual(self.audit.decide(rows[:-1]), ('invalid', []))
        self.assertEqual(self.audit.decide(rows + [rows[0]]), ('invalid', []))

    def test_cannot_mix_n_across_seeds(self):
        rows = [{'N': n, 'seed': s, 'D': 0., 'E_pp': (0. if n == chosen else 2.)}
                for s, chosen in ((42, 12), (7, 24), (2026, 48)) for n in (12, 24, 48)]
        self.assertEqual(self.audit.decide(rows), ('inconclusive', []))

    def test_zero_channel(self):
        self.assertEqual(self.audit.relative_error([0., 0.], [1., 364.], 0.), (0., 0.))
        with self.assertRaises(ValueError):
            self.audit.relative_error([1., 0.], [0., 365.], 0.)
        with self.assertRaises(ValueError):
            self.audit.aggregate([{'renewable_available_MWh': 0., 'renewable_used_MWh': 0.,
                                   'curtailment_MWh': 0.}], [365.])

    def test_hash_tampering_and_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'evidence.csv'
            path.write_text('original', encoding='utf-8')
            hashes = {'evidence.csv': self.audit.sha(path)}
            self.assertEqual(self.audit.verify_hashes(root, hashes), 1)
            path.write_text('altered', encoding='utf-8')
            with self.assertRaises(ValueError):
                self.audit.verify_hashes(root, hashes)
            with self.assertRaises(ValueError):
                self.audit.verify_hashes(root, {'../outside': 'bad'})

    def test_finalize_rejects_tampered_manifest_without_completion(self):
        finalize = importlib.import_module('scripts.finalize_u11r09')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / 'results/annual/U11R09-v01'
            out.mkdir(parents=True)
            (out / 'run_manifest.json').write_text(json.dumps({'status': 'awaiting_independent_audit',
                                                              'verdict': None}), encoding='utf-8')
            audit_path = out.with_name(out.name + '-independent-audit.json')
            audit_path.write_text(json.dumps({'passed': True, 'status': 'complete',
                'verdict': 'supported', 'passing_N': [12], 'main_manifest_sha256': 'tampered'}), encoding='utf-8')
            with patch('subprocess.Popen', side_effect=AssertionError('No external processes')):
                with self.assertRaises(ValueError):
                    finalize.finalize(root, 'U11R09-v01')
            self.assertFalse((out / 'completion.json').exists())


if __name__ == '__main__':
    unittest.main()
