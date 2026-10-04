from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts.audit_u11r08_feasibility import certificate, classify
from src.input_energy_feasibility import check_solution, solve_lp
from src.proxy_energy_feasibility import amounts, build_model, cbc, decision


class ProxyEnergyFeasibilityTests(unittest.TestCase):
    def model(self):
        return build_model([[10,20],[0,0],[0,0],[1,2]],[5475,0,0,547.5],[180,185])

    def test_proxy_is_clipped_input_not_dispatch(self):
        data = pd.DataFrame(dict(hour=[0,1],load=[150,100],wind=[10,10],solar=[5,5]))
        self.assertEqual(amounts(data,120),[250,20,10,15])
        for ceiling in (0,-1,np.nan):
            with self.assertRaises(ValueError): amounts(data,ceiling)

    def test_four_channels_and_count_point(self):
        model = self.model()
        self.assertEqual(len(model['A_ub']),4)
        result = check_solution(model,[180,185],25/5475)
        self.assertTrue(result['passed'])
        self.assertAlmostEqual(result['absolute_relative_errors'][3],25/5475)

    def test_invalid_dimensions_counts_and_zero_target(self):
        for counts in ([0,365],[180,180],[180.5,184.5]):
            with self.assertRaises(ValueError): build_model(np.zeros((4,2)),[0]*4,counts)
        for energy,target in ((np.zeros((3,2)),[0]*4),([[1,2]]*4,[0]*4),([[np.nan,2]]*4,[365]*4),([[-1,2]]*4,[365]*4)):
            with self.assertRaises(ValueError): build_model(energy,target,[180,185])

    def test_highs_and_native_cbc_synthetic_only(self):
        model = self.model()
        primary = solve_lp(model)
        self.assertTrue(primary['success'])
        with tempfile.TemporaryDirectory() as folder:
            cross = cbc(model,Path(folder)/'cbc')
            self.assertEqual(cross['status'],'Optimal')
            self.assertAlmostEqual(primary['t'],cross['t'],places=8)
            self.assertTrue((Path(folder)/'cbc/native/solution.bin').exists())

    def test_exact_four_channel_certificate_and_boundary(self):
        energy = [[F(1),F(1)]]*4
        proof = certificate(energy,[F(365)]*4,[180,185],[180.,185.],[0.]*8,[0.])
        self.assertEqual(proof['gap'],'0')
        self.assertEqual(classify(0.,proof),'reachable')
        self.assertEqual(classify(.02,proof),'uncertain')

    def test_verdict_matrix_and_incomplete_rejected(self):
        rows = [dict(seed=s,classification='reachable') for s in (42,7,2026)]
        self.assertEqual(decision(rows),'supported')
        rows[1]['classification'] = 'uncertain'
        self.assertEqual(decision(rows),'inconclusive')
        rows[0]['classification'] = 'unreachable'
        self.assertEqual(decision(rows),'refuted')
        for bad in (rows[:2],[rows[0]]*3,[dict(seed=s,classification='unknown') for s in (42,7,2026)]):
            with self.assertRaises(ValueError): decision(bad)

    def test_cbc_nonoptimal_retains_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'cbc'
            with patch('pulp.LpProblem.solve',return_value=-1):
                with self.assertRaises(RuntimeError): cbc(self.model(),out)
            saved = json.loads((out/'solution.json').read_text())
            self.assertIn('error',saved)
            self.assertTrue((out/'model.lp').exists())
            self.assertNotIn('weights',saved)

    def test_certificate_rejects_large_primal_repair(self):
        with self.assertRaises(ValueError):
            certificate([[F(1),F(1)]]*4,[F(365)]*4,[180,185],[180.,186.],[0.]*8,[0.])

    def test_independent_native_evidence_and_no_solve_trap(self):
        from scripts.audit_proxy_energy_feasibility import native, ROOT
        counts = [8]*29+[7]*19
        model = build_model([[1.]*48]*4,[365.]*4,counts)
        frozen = json.loads((ROOT/'instructions/studies/U11R14-proxy-energy-feasibility/freeze.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'cbc'
            solution = cbc(model,out)
            with patch('subprocess.run',side_effect=AssertionError('No solve in native audit')):
                self.assertLessEqual(native(out/'native',model,solution,frozen),1e-6)


if __name__ == '__main__': unittest.main()
