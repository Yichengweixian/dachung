"""Hand-derived allocations test the accounting independently of dispatch."""
import unittest
import numpy as np
from run_factorial_attribution import allocation, METRICS, NAMES

class FactorialTests(unittest.TestCase):
    def test_additive_factors_recover_exact_contributions(self):
        values={m:np.full(4,17.+sum((i+1)*10 for i in range(3) if m & (1<<i))) for m in range(8)}
        q=allocation(values)
        for i,name in enumerate(NAMES):
            np.testing.assert_allclose(q[q.factor==name].shapley,(i+1)*10,rtol=0,atol=1e-12)

    def test_pair_interaction_splits_equally_and_dummy_gets_zero(self):
        values={m:np.full(4,6. if m & 3 == 3 else 0.) for m in range(8)}
        q=allocation(values)
        for name,target in zip(NAMES,[3.,3.,0.]):
            np.testing.assert_allclose(q[q.factor==name].shapley,target,rtol=0,atol=1e-12)
