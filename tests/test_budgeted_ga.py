import unittest
import numpy as np
import pandas as pd
from src.budgeted_ga import SEEDS, search, decision


class BudgetedGATests(unittest.TestCase):
    def test_budget_elite_repeat_and_no_cached_calls(self):
        calls = []
        def evaluate(xs, generation):
            calls.append((generation, len(xs)))
            return np.ones(len(xs))
        _, _, history = search(evaluate, 42)
        self.assertEqual(calls, [(0, 12)]+[(g, 11) for g in range(1, 8)])
        self.assertEqual(len(history), 89)
        _, _, repeat = search(evaluate, 42)
        self.assertEqual(history, repeat)

    def test_one_sided_quality_and_nine_seed_threshold(self):
        table = pd.DataFrame(dict(seed=SEEDS, evaluations=[89]*10, cost=[99.]*9+[110.]))
        q, verdict = decision(table, 100.)
        self.assertEqual(verdict, 'supported')
        self.assertEqual(q.quality_loss.iloc[0], 0.)
        table.loc[0, 'cost'] = 100.5
        self.assertEqual(decision(table, 100.)[1], 'inconclusive')
        table.loc[1, 'evaluations'] = 90
        with self.assertRaises(ValueError):
            decision(table, 100.)
