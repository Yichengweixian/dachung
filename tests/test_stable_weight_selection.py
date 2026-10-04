"""U11R15 unit tests: hand-checkable hierarchy, pinning order, frozen gates and verdict rules.

The toy instance is the three-cluster problem
    c = [120, 120, 125],  sum c = 365
    active channel 0: a = [1, 2, 0], target 350  (counts give 360, so the counts point is infeasible)
    other three channels: zero amounts and zero targets
so that  w1 + 2 w2 = 350,  w1 + w2 + w3 = 365  and the L1 / L-infinity optima are hand-computable.
"""
import unittest

from src.stable_weight_selection import (BAND, E_GATE, build_model, h1_verdict, h2_verdict,
                                         highs_problem, identity_difference, require_stage,
                                         run_cbc_rule, run_highs_rule, solve_highs, stage_residuals,
                                         stage_specs)

TOY_ENERGY = [[1., 2., 0.], [0., 0., 0.], [0., 0., 0.], [0., 0., 0.]]
TOY_TARGET = [350., 0., 0., 0.]
TOY_COUNTS = [120, 120, 125]
TOY_DATES = ["2023-01-03", "2023-01-01", "2023-01-02"]


def toy_model(rule="l1"):
    return build_model(TOY_ENERGY, TOY_TARGET, TOY_COUNTS, rule, seed=42, N=3,
                       days=[0, 1, 2], dates=TOY_DATES)


class ModelTests(unittest.TestCase):
    def test_stage_specs_and_date_order(self):
        specs = stage_specs(toy_model())
        self.assertEqual([s["objective"] for s in specs], ["t", "l1", "w", "w", "w"])
        self.assertEqual([s["index"] for s in specs], [None, None, 1, 2, 0])

    def test_validation_rejects_bad_instances(self):
        with self.assertRaises(ValueError):
            build_model(TOY_ENERGY, TOY_TARGET, [120, 120, 124], "l1", dates=TOY_DATES)
        with self.assertRaises(ValueError):
            build_model(TOY_ENERGY, TOY_TARGET, TOY_COUNTS, "l2", dates=TOY_DATES)
        with self.assertRaises(ValueError):
            build_model([[-1., 2., 0.], [0., 0., 0.], [0., 0., 0.], [0., 0., 0.]], TOY_TARGET,
                        TOY_COUNTS, "l1", dates=TOY_DATES)
        with self.assertRaises(ValueError):
            build_model(TOY_ENERGY, [350., -1., 0., 0.], TOY_COUNTS, "l1", dates=TOY_DATES)
        with self.assertRaises(ValueError):
            build_model([[1., 2., 0.], [1., 1., 1.], [0., 0., 0.], [0., 0., 0.]], TOY_TARGET,
                        TOY_COUNTS, "l1", dates=TOY_DATES)

    def test_highs_problem_layout(self):
        model = toy_model()
        problem = highs_problem(model, stage_specs(model)[0], dict(t_limit=None, s_limit=None, pins=[]))
        self.assertEqual(problem["layout"]["nv"], 4)
        self.assertEqual(len(problem["A_ub"]), 2)
        self.assertEqual(problem["bounds"], [[60., 240.], [60., 240.], [62.5, 250.], [0., None]])


class HierarchyTests(unittest.TestCase):
    def test_hand_computed_l1_solution(self):
        # Hand optimum on the exact-equality face is 49/600 = 1/24 + 1/25 at w = [120, 115, 130];
        # the frozen BAND = 1e-6 lets the LP buy ~2.9e-6 of objective, so compare within 1e-5.
        record = run_highs_rule(toy_model())
        self.assertEqual(len(record["stages"]), 5)
        self.assertLessEqual(record["primary"]["t"], 1e-9)
        self.assertAlmostEqual(record["stages"][1]["objective"], 49. / 600., places=5)
        weights = record["final"]["weights"]
        # BAND = 1e-6 is worth ~1e-4 of weight movement, so the hand values hold to ~1e-3.
        self.assertAlmostEqual(weights[0], 120., delta=1e-3)
        self.assertAlmostEqual(weights[1], 115., delta=1e-3)
        self.assertAlmostEqual(weights[2], 130., delta=1e-3)

    def test_hand_computed_linf_solution(self):
        # Hand optimum on the exact-equality face: min max_i |w_i-c_i|/c_i = 2/49 at
        # w = [5870/49, 5640/49, 6375/49]; the BAND shifts it by less than 2e-6.
        record = run_highs_rule(toy_model("linf"))
        self.assertAlmostEqual(record["stages"][1]["objective"], 2. / 49., places=5)
        weights = record["final"]["weights"]
        self.assertAlmostEqual(weights[0], 5870. / 49., delta=1e-3)
        self.assertAlmostEqual(weights[1], 5640. / 49., delta=1e-3)
        self.assertAlmostEqual(weights[2], 6375. / 49., delta=1e-3)

    def test_primary_objective_is_shared_by_both_rules(self):
        l1 = run_highs_rule(toy_model("l1"))
        linf = run_highs_rule(toy_model("linf"))
        self.assertAlmostEqual(l1["primary"]["objective"], linf["primary"]["objective"], places=12)

    def test_pinning_order_follows_dates(self):
        record = run_highs_rule(toy_model())
        self.assertEqual([stage["index"] for stage in record["stages"][2:]], [1, 2, 0])
        self.assertEqual([pin[0] for pin in record["pins"]], [1, 2, 0])
        for _, lower, upper in record["pins"]:
            self.assertLessEqual(upper - lower, 2. * BAND + 1e-12)

    def test_cbc_cross_path_matches_highs_on_toy(self):
        highs = run_highs_rule(toy_model())
        cbc = run_cbc_rule(toy_model(), "l1", True, None)
        self.assertEqual(len(cbc["stages"]), 5)
        for left, right in zip(highs["stages"], cbc["stages"]):
            self.assertLessEqual(abs(left["objective"] - right["objective"]), 1e-8)
        self.assertLessEqual(identity_difference(highs["final"]["weights"], cbc["final"]["weights"]), 1e-4)

    def test_cbc_top_level_only_stops_after_secondary(self):
        cbc = run_cbc_rule(toy_model(), "linf", False, None)
        self.assertEqual([stage["stage"] for stage in cbc["stages"]], ["primary", "secondary"])
        self.assertFalse(cbc["stages"][1]["native_artifacts"])


class GateTests(unittest.TestCase):
    def test_require_stage_accepts_feasible_and_rejects_violations(self):
        model = toy_model()
        feasible = require_stage(model, [120., 115., 130.], 1e-12, 49. / 600.,
                                 dict(t_limit=None, s_limit=None, pins=[]))
        self.assertLessEqual(feasible["bounds"], 1e-7)
        with self.assertRaises(ValueError):
            require_stage(model, [50., 115., 200.], 1e-12, None, dict(t_limit=None, s_limit=None, pins=[]))
        with self.assertRaises(ValueError):
            require_stage(model, [120., 115., 130.], 1e-3, None, dict(t_limit=1e-6, s_limit=None, pins=[]))
        with self.assertRaises(ValueError):
            require_stage(model, [120., 115., 130.], 1e-12, None,
                          dict(t_limit=None, s_limit=1e-9, pins=[]))
        with self.assertRaises(ValueError):
            require_stage(model, [120., 115., 130.], 1e-12, None,
                          dict(t_limit=None, s_limit=None, pins=[(1, 116., 124.)]))

    def test_stage_residuals_are_reported(self):
        residuals = stage_residuals(toy_model(), [120., 115., 130.], 1e-12, None,
                                    dict(t_limit=None, s_limit=None, pins=[]))
        self.assertEqual(len(residuals["channel_errors"]), 1)
        self.assertAlmostEqual(residuals["channel_errors"][0], 0., places=12)
        self.assertLessEqual(residuals["bounds"], 1e-12)

    def test_solve_highs_reports_marginals(self):
        model = toy_model()
        problem = highs_problem(model, stage_specs(model)[0], dict(t_limit=None, s_limit=None, pins=[]))
        record = solve_highs(problem)
        self.assertEqual(record["status"], 0)
        self.assertEqual(len(record["inequality_marginals"]), len(problem["A_ub"]))
        self.assertEqual(len(record["equality_marginals"]), 1)


class VerdictTests(unittest.TestCase):
    @staticmethod
    def rows(**overrides):
        base = [dict(seed=seed, classification="reachable", cross_solver_ok=True, E=0.5,
                     max_input_relative_error=1e-4) for seed in (42, 7, 2026)]
        for item in base:
            item.update(overrides)
        return base

    def test_h1_supported_refuted_and_inconclusive(self):
        self.assertEqual(h1_verdict(self.rows()), "supported")
        self.assertEqual(h1_verdict(self.rows(E=1.2)), "refuted")
        self.assertEqual(h1_verdict(self.rows(E=E_GATE)), "inconclusive")
        self.assertEqual(h1_verdict(self.rows(classification="uncertain")), "inconclusive")
        self.assertEqual(h1_verdict(self.rows(classification="unreachable")), "refuted")
        self.assertEqual(h1_verdict(self.rows(cross_solver_ok=False)), "inconclusive")
        self.assertEqual(h1_verdict(self.rows(max_input_relative_error=0.05)), "refuted")

    def test_h1_rejects_incomplete_matrix(self):
        with self.assertRaises(ValueError):
            h1_verdict(self.rows()[:2])

    def test_h2_compares_absolute_errors_to_baseline(self):
        rows = [dict(seed=seed, cost_error_CNY=-1.0e6, unserved_error_MWh=-300.,
                     base_cost_error_CNY=-1.2e6, base_unserved_error_MWh=-310.) for seed in (42, 7, 2026)]
        self.assertEqual(h2_verdict(rows), "supported")
        worse = [dict(item) for item in rows]
        worse[2]["unserved_error_MWh"] = -400.
        self.assertEqual(h2_verdict(worse), "refuted")
        equal = [dict(item) for item in rows]
        equal[0]["cost_error_CNY"] = equal[0]["base_cost_error_CNY"]
        self.assertEqual(h2_verdict(equal), "inconclusive")


if __name__ == "__main__":
    unittest.main()
