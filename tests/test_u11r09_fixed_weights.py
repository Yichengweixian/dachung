import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.fixed_weight_dispatch import (
    energy_check, aggregate, decision, recover_weights, create_output, run_case,
    ROOT, read_csv, configuration,
)


class FixedWeightDispatchTests(unittest.TestCase):
    def test_weights_recovered_without_adjustment(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p/'solution.json').write_text(json.dumps({'weights': [182.50000000000003, 182.49999999999997], 'status': 0, 'success': True}))
            (p/'weights.csv').write_text('cluster,day,date_UTC,c,w\n0,0,2023-01-01,180,182.50000000000003\n1,1,2023-01-02,185,182.49999999999997\n')
            w = recover_weights(p, [180,185], [0,1], ['2023-01-01','2023-01-02'])
            np.testing.assert_array_equal(w, [182.50000000000003,182.49999999999997])
            (p/'weights.csv').write_text('cluster,day,date_UTC,c,w\n0,0,2023-01-01,180,182.5\n1,1,2023-01-02,185,182.5\n')
            with self.assertRaises(ValueError):
                recover_weights(p, [180,185], [0,1], ['2023-01-01','2023-01-02'])

    def test_missing_formal_weights_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                recover_weights(Path(tmp), [365], [0], ['2023-01-01'])

    def test_energy_bounds_sum_and_zero_channels(self):
        check = energy_check([[10,20],[0,0],[0,0]], [5475,0,0], [180,185], [182.5,182.5])
        self.assertEqual(check['D'], 0.)
        self.assertEqual(check['relative_errors'], [0.,0.,0.])
        for weights in ([89,276], [180,186], [float('nan'),185]):
            with self.assertRaises(ValueError):
                energy_check([[10,20],[0,0],[0,0]], [5475,0,0], [180,185], weights)
        with self.assertRaises(ValueError):
            energy_check([[1,1],[0,0],[0,0]], [0,0,0], [180,185], [180,185])

    def test_energy_threshold_not_relaxed(self):
        with self.assertRaises(ValueError):
            energy_check([[1.021],[0],[0]], [365,0,0], [365], [365])

    def test_aggregate_energy_before_ratio(self):
        rows = [{'renewable_available_MWh':10.,'renewable_used_MWh':5.,'curtailment_MWh':5.},
                {'renewable_available_MWh':100.,'renewable_used_MWh':100.,'curtailment_MWh':0.}]
        result = aggregate(rows, [1,3])
        self.assertAlmostEqual(result['renewable_utilization_pct'], 305/310*100)
        self.assertAlmostEqual(result['curtailment_rate_pct'], 5/310*100)
        with self.assertRaises(ValueError): aggregate(rows, [1])
        with self.assertRaises(ValueError): aggregate([{'renewable_available_MWh':0.,'renewable_used_MWh':0.,'curtailment_MWh':0.}], [1])

    def test_decision_requires_complete_common_n(self):
        rows=[{'N':n,'seed':s,'D':.01,'E_pp':.5} for n in [12,24,48] for s in [42,7,2026]]
        self.assertEqual(decision(rows), ('supported',[12,24,48]))
        rows[0]['E_pp']=1.0000000001
        rows[3]['D']=.0200000001
        rows[7]['E_pp']=1.5
        self.assertEqual(decision(rows), ('invalid',[]))
        rows[3]['D']=.02
        rows[3]['E_pp']=1.0000000001
        self.assertEqual(decision(rows), ('inconclusive',[]))
        self.assertEqual(decision(rows[:-1]), ('invalid',[]))
        self.assertEqual(decision(rows[:-1]+[rows[0]]), ('invalid',[]))

    def test_run_directory_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_output(Path(tmp),'U11R09-test')
            with self.assertRaises(FileExistsError): create_output(Path(tmp),'U11R09-test')
            with self.assertRaises(ValueError): create_output(Path(tmp),'../escape')

    def test_failed_dispatch_preserves_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('src.fixed_weight_dispatch.evaluate_case', side_effect=RuntimeError('solver failure')):
                with self.assertRaises(RuntimeError): run_case(Path(tmp),'case',None,{}, {},None, {'dispatch_calls':0})
            fail=json.loads((Path(tmp)/'failure.json').read_text())
            self.assertEqual(fail['verdict'],'invalid')
            self.assertEqual(fail['case'],'case')
            self.assertTrue((Path(tmp)/'case_cbc.log').exists())

    def test_real_dispatch_roundtrip_and_evidence(self):
        freeze=json.loads((ROOT/'instructions/studies/U11R09-fixed-weight-dual-threshold/freeze.json').read_text('utf-8'))
        s,t,e=configuration(freeze)
        source=read_csv(ROOT/'results/annual/U11R03-v01/N12_seed42_inputs.csv')
        day=source.loc[source.cluster==0,['hour','load','wind','solar']].reset_index(drop=True)
        counter={'dispatch_calls':0}
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            q,row,info=run_case(out,'case',day,s,t,e,counter)
            self.assertEqual(counter['dispatch_calls'],1)
            self.assertEqual(len(q),24)
            self.assertEqual(info['solver_status'],'Optimal')
            self.assertEqual(info['integer_variable_count'],24)
            self.assertAlmostEqual(row['renewable_available_MWh'],1099.77,places=8)
            self.assertTrue((out/'case_model.mps').exists())
            self.assertIn('Optimal',(out/'case_cbc.log').read_text())
            self.assertTrue(json.loads((out/'case_checks.json').read_text())['passed'])


if __name__=='__main__': unittest.main()
