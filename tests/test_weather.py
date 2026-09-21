import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from src.convert_weather import convert_weather,read_weather,unique_pairs,SOLAR,WIND

class WeatherTests(unittest.TestCase):
    def test_curve_boundaries_and_night(self):
        w=pd.DataFrame({WIND:np.resize([0,3,12,25,25.01,6],24),SOLAR:np.resize([0,1000],24)})
        q=convert_weather(w,np.ones(24)*100)
        np.testing.assert_allclose(q.wind.iloc[:5],[0,0,100,100,0]);self.assertEqual(q.solar.iloc[0],0)
        self.assertEqual(q.load.iloc[0],95);self.assertEqual(q.solar.max(),150)
        self.assertEqual(q.wind.iloc[5],round(100*(6**3-3**3)/(12**3-3**3),2))
    def test_cap_is_explicit(self):
        w=pd.DataFrame({WIND:np.zeros(24),SOLAR:np.ones(24)*1200})
        self.assertEqual(convert_weather(w,np.ones(24)).solar.max(),180)
        self.assertEqual(convert_weather(w,np.ones(24),150).solar.max(),150)
    def test_bad_values(self):
        for value in [-1,np.nan,np.inf]:
            with self.assertRaises(ValueError):convert_weather(pd.DataFrame({WIND:[value]*24,SOLAR:[0]*24}),np.ones(24))
        with self.assertRaises(ValueError):unique_pairs([('x',1),('x',2)])
    def test_metadata_and_missing_rejected(self):
        times=pd.date_range('2023-01-01',periods=24,freq='h').strftime('%Y%m%d%H')
        d={'header':dict(time_standard='UTC',start='20230101',end='20230101',fill_value=-999),
           'parameters':{WIND:dict(units='m/s'),SOLAR:dict(units='Wh/m^2')},
           'properties':{'parameter':{x:dict.fromkeys(times,0) for x in [WIND,SOLAR]}}}
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'raw.json';p.write_text(json.dumps(d),encoding='utf-8');self.assertEqual(len(read_weather(p,'20230101','20230101')[0]),24)
            d['properties']['parameter'][WIND].pop(times[0]);p.write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaises(ValueError):read_weather(p,'20230101','20230101')
            d['header']['time_standard']='LST';p.write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaises(ValueError):read_weather(p,'20230101','20230101')
