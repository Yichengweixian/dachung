from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from scripts.diagnose_u11r04_serialization import read_mps, decimal_residuals


class ForensicParserTests(unittest.TestCase):
    def test_rhs_data_is_not_a_section_header(self):
        data = ('NAME MODEL\nROWS\n N OBJ\n E ROW0\n G ROW1\nCOLUMNS\n'
                ' X0 OBJ 1\n X0 ROW0 1\n X0 ROW1 2\nRHS\n'
                ' RHS ROW0 3.650000000000e+02\n RHS ROW1 7.000000000000e+02\n'
                'BOUNDS\n LO BND X0 1\n UP BND X0 400\nENDATA\n')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fixture.mps'
            path.write_text(data, encoding='utf-8')
            rows, rhs, senses, bounds = read_mps(path)
        self.assertEqual(rhs['ROW0'], Decimal(365))
        self.assertEqual(rhs['ROW1'], Decimal(700))
        residuals = decimal_residuals(rows, rhs, senses, {'X0':Decimal(365)}, bounds)
        self.assertTrue(all(Decimal(r['violation']) == 0 for r in residuals))

    def test_decimal_residual_preserves_tiny_violation(self):
        result = decimal_residuals({'r':{'x':Decimal(1)}}, {'r':Decimal(1)}, {'r':'L'},
                                   {'x':Decimal('1.00000000001')}, {'x':[Decimal(0), None]})
        self.assertEqual(Decimal(result[0]['violation']), Decimal('1e-11'))

    def test_unrecognized_bounds_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fixture.mps'
            path.write_text('NAME M\nROWS\n N OBJ\nCOLUMNS\n X OBJ 1\nBOUNDS\n FR B X\nENDATA\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                read_mps(path)
