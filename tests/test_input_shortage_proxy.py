import unittest

import numpy as np
import pandas as pd

from src.input_shortage_proxy import decision, member_index, select_days


class InputShortageProxyTests(unittest.TestCase):
    def table(self):
        return pd.DataFrame(dict(N=[48]*3, seed=[42,7,2026], worst_error_pp=[1.]*3,
                                 max_input_relative_error=[.02]*3, cost_absolute_improvement_CNY=[2.]*3,
                                 unserved_absolute_improvement_MWh=[3.]*3))

    def inputs(self):
        data = pd.DataFrame(dict(hour=np.arange(8760), load=np.full(8760, 150.),
                                 wind=np.full(8760, 10.), solar=np.full(8760, 5.)))
        labs = np.arange(365) % 48
        labels = pd.DataFrame(dict(day=np.arange(365), cluster=labs))
        old = pd.DataFrame(dict(cluster=np.arange(48), days=np.bincount(labs), day=np.arange(48)))
        return data, labels, old

    def test_mean_nearest_not_extreme(self):
        result = member_index(np.array([0.,4.,5.]), np.zeros((3,72)), np.arange(3))
        self.assertEqual(result[0], 1)
        self.assertEqual(result[1], 3.)

    def test_shape_then_earliest_tie(self):
        features = np.array([[3.], [1.], [1.]])
        result = member_index(np.zeros(3), features, np.array([2,0,1]))
        self.assertEqual(result[0], 1)
        self.assertEqual(result[3:], (3,2))

    def test_actual_member_reset_and_proxy(self):
        data, labels, old = self.inputs()
        days, reps, proxies = select_days(data, labels, old, 120.)
        self.assertEqual(len(days), 48)
        self.assertEqual(len(proxies), 365)
        self.assertTrue((proxies.proxy_MWh == 360.).all())
        self.assertEqual(reps.day.tolist(), list(range(48)))
        self.assertEqual(reps.days.sum(), 365)
        self.assertEqual(reps.date_UTC.iloc[1], "2023-01-02")
        for day in days:
            self.assertEqual(day.hour.tolist(), list(range(24)))
        self.assertFalse(reps.changed.any())

    def test_bad_inputs_and_membership(self):
        for failure in ("count", "fractional", "missing", "negative", "nonfinite", "ceiling"):
            with self.subTest(failure=failure):
                data, labels, old = self.inputs()
                ceiling = 120.
                if failure == "count": old.loc[0,"days"] += 1
                elif failure == "fractional": labels["cluster"] = labels.cluster.astype(float); labels.loc[0,"cluster"] = .5
                elif failure == "missing": labels.loc[labels.cluster == 47,"cluster"] = 46
                elif failure == "negative": data.loc[0,"wind"] = -1.
                elif failure == "nonfinite": data.loc[0,"load"] = np.nan
                else: ceiling = np.nan
                with self.assertRaises(ValueError): select_days(data, labels, old, ceiling)

    def test_supported_exact_ED_boundary(self):
        self.assertEqual(decision(self.table()), ("supported", [True]*3))

    def test_worse_is_refuted_even_if_ED_fails(self):
        table = self.table()
        table.loc[1,"cost_absolute_improvement_CNY"] = -2e-6
        table.loc[1,"worst_error_pp"] = 2.
        self.assertEqual(decision(table)[0], "refuted")

    def test_tie_or_ED_failure_inconclusive(self):
        for column,value in (("cost_absolute_improvement_CNY",1e-6), ("unserved_absolute_improvement_MWh",-1e-6),
                             ("worst_error_pp",1.000001), ("max_input_relative_error",.020001)):
            table = self.table()
            table.loc[0,column] = value
            self.assertEqual(decision(table)[0], "inconclusive")

    def test_invalid_matrix_and_nonfinite(self):
        table = self.table()
        with self.assertRaises(ValueError): decision(table.iloc[:2])
        table.loc[0,"seed"] = 7
        with self.assertRaises(ValueError): decision(table)
        table = self.table()
        table.loc[0,"worst_error_pp"] = np.nan
        with self.assertRaises(ValueError): decision(table)


if __name__ == "__main__":
    unittest.main()
