import unittest
import numpy as np
from src.genetic_search import run_ga,mutate,sbx,LOW,HIGH

class GATests(unittest.TestCase):
    def test_bounds(self):
        rng=np.random.default_rng(42)
        for _ in range(200):
            a,b=sbx(LOW,HIGH,rng)
            for x in (mutate(a,rng),mutate(b,rng)):
                self.assertTrue(((LOW<=x)&(x<=HIGH)).all())
    def test_count_repeat_and_incumbent(self):
        p=dict(population=30,generations=50,eta_c=15,eta_m=20,crossover_probability=.9,mutation_probability=.5)
        calls=[]
        def evaluate(xs,generation):
            calls.extend(xs.tolist());return ((xs-[60,20])**2).sum(axis=1)
        a,c,h=run_ga(evaluate,p,42)
        self.assertEqual(len(calls),1480);self.assertEqual(len(h),1480)
        self.assertTrue((np.diff([r['best_cost'] for r in h])<=0).all())
        b,d,j=run_ga(evaluate,p,42);np.testing.assert_array_equal(a,b);self.assertEqual(c,d);self.assertEqual(h,j)
        self.assertTrue(all(x[1]==0 for x in calls if x[0]==0))
