"""Independent exact-certificate tests; deliberately no optimization calls."""
import unittest
from fractions import Fraction as F
from scripts.audit_u11r08_feasibility import certificate, classify, residuals

class IndependentAuditTests(unittest.TestCase):
    def test_exact_unreachable_certificate(self):
        cert = certificate([[F(2)]], [F(365)], [365], [365.0], [-1., 0.], [2/365])
        self.assertLessEqual(F(cert['lower']), 1)
        self.assertLess(1-F(cert['lower']), F('1e-15'))
        self.assertEqual(F(cert['upper']), 1)
        self.assertEqual(classify(1., cert), 'unreachable')

    def test_exact_reachable_and_repair(self):
        cert = certificate([[F(1), F(1)]], [F(365)], [100,265], [100.0,265.00000000000006], [0.,0.], [0.])
        self.assertEqual(F(cert['upper']), 0)
        self.assertEqual(sum(map(F,cert['proof_weights'])), 365)
        self.assertGreater(float(F(cert['max_repair'])),0)
        self.assertEqual(classify(0., cert),'reachable')

    def test_strict_threshold_and_near_band(self):
        self.assertEqual(classify(.020000005, {'lower':'.020000005','upper':'.020000005'}),'uncertain')
        self.assertEqual(classify(.021, {'lower':'.02','upper':'.021'}),'uncertain')

    def test_loose_certificate_is_uncertain(self):
        self.assertEqual(classify(.001, {'lower':'0','upper':'.001'}),'uncertain')

    def test_invalid_zero_channel(self):
        with self.assertRaises(ValueError):
            certificate([[F(1)]],[F(0)],[365],[365.],[0.,0.],[0.])

    def test_reject_large_weight_repair(self):
        with self.assertRaises(ValueError):
            certificate([[F(1)]],[F(365)],[365],[364.],[0.,0.],[0.])

    def test_residuals_detect_infeasible(self):
        r=residuals([[F(2)]],[F(365)],[365],[365.],0.)
        self.assertEqual(r['energy'],1.)
        self.assertEqual(r['sum'],0.)

if __name__=='__main__': unittest.main()
