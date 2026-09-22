import unittest
import numpy as np
import pandas as pd
from src.representative_days import cluster_real_days, nearest_member, input_energy_errors, passing_sizes


class RepresentativeDaysTests(unittest.TestCase):
    def test_real_days_preserve_amplitude_membership_and_weights(self):
        levels = np.repeat([10., 20., 40.], [120, 120, 125])
        data = pd.DataFrame(dict(hour=np.arange(8760), load=np.repeat(levels, 24),
                                 wind=np.repeat(levels/2, 24), solar=np.zeros(8760)))
        days, representatives, labels = cluster_real_days(data, 3, 42)
        self.assertEqual(sorted(representatives.days), [120, 120, 125])
        self.assertEqual(set(representatives.day), {0, 120, 240})
        for day, row in zip(days, representatives.itertuples()):
            self.assertEqual(labels[row.day], row.cluster)
            np.testing.assert_array_equal(day[['load', 'wind', 'solar']],
                                          data.iloc[row.day*24:(row.day+1)*24][['load', 'wind', 'solar']])
        self.assertEqual(input_energy_errors(data, days, representatives.days)['max_input_relative_error'], 0)

    def test_nearest_tie_uses_earliest_date(self):
        features = np.array([[0.], [2.], [4.]])
        selected, distance = nearest_member(features, np.array([1, 0]), np.array([1.]))
        self.assertEqual(selected, 0)
        self.assertEqual(distance, 1.)

    def test_weighted_energy_and_zero_channel(self):
        a = pd.DataFrame(dict(load=[10., 10.], wind=[5., 5.], solar=[0., 0.]))
        b = a*2
        data = pd.concat([a, a, b])
        errors = input_energy_errors(data, [a, b], [2, 1])
        self.assertEqual(errors['max_input_relative_error'], 0)
        self.assertEqual(errors['load_input_MWh'], 80)
        self.assertGreater(input_energy_errors(data, [a, b], [1, 2])['max_input_relative_error'], .02)

    def test_requires_common_size_and_all_seeds(self):
        rows = [dict(N=n, seed=s, worst_error_pp=2., max_input_relative_error=.01)
                for n in [12, 24, 48] for s in [42, 7, 2026]]
        for index in [0, 4, 8]:
            rows[index]['worst_error_pp'] = .1
        self.assertEqual(passing_sizes(pd.DataFrame(rows)), [])
        for row in rows[3:6]:
            row['worst_error_pp'] = 1.
            row['max_input_relative_error'] = .02
        self.assertEqual(passing_sizes(pd.DataFrame(rows)), [24])
        rows[4]['max_input_relative_error'] = .02001
        self.assertEqual(passing_sizes(pd.DataFrame(rows)), [])
        with self.assertRaises(ValueError):
            passing_sizes(pd.DataFrame(rows[:-1]))
