import struct
from pathlib import Path
import unittest
from unittest.mock import patch
from src.cbc_presolve_diagnostic import decode_native, execute_pair, command


class PresolveDiagnosticTests(unittest.TestCase):
    def test_native_layout(self):
        raw = struct.pack('=iid', 1, 2, 3.) + struct.pack('=6d', 0, 0, 1, 2, 0, 0)
        objective, values = decode_native(raw, 1, ['a','b'])
        self.assertEqual((objective, values), (3., {'a':1., 'b':2.}))

    def test_truncated_dimensions_and_nonfinite(self):
        for raw in [b'', struct.pack('=iid', 1, 2, 0.),
                    struct.pack('=iid', 0, 1, 0.)+struct.pack('=2d', float('nan'), 0.)]:
            with self.assertRaises(ValueError):
                decode_native(raw, 0, ['a'])

    def test_failure_stops_before_repeat(self):
        calls = []
        with patch('src.cbc_presolve_diagnostic.execute_once', side_effect=ValueError('Infeasible')) as run:
            with self.assertRaises(ValueError):
                execute_pair(Path('unused'), calls.append)
        self.assertEqual(calls, ['first'])
        self.assertEqual(run.call_count, 1)

    def test_pair_and_repeat_threshold(self):
        first = dict(values={'a':1.}, native_objective=1.)
        with patch('src.cbc_presolve_diagnostic.execute_once', side_effect=[first, first]):
            self.assertEqual(execute_pair(Path('unused'), lambda _:None)['verdict'], 'supported')
        other = dict(values={'a':1.01}, native_objective=1.01)
        with patch('src.cbc_presolve_diagnostic.execute_once', side_effect=[first, other]):
            self.assertEqual(execute_pair(Path('unused'), lambda _:None)['verdict'], 'inconclusive')

    def test_only_frozen_solver_options(self):
        cmd = command()
        self.assertEqual(cmd[cmd.index('-presolve')+1], 'off')
        self.assertEqual(cmd[cmd.index('-primalTolerance')+1], '1e-9')
        self.assertEqual(cmd.count('-branch'), 1)
