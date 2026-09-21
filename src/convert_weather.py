"""Strict UTC NASA POWER conversion; load is constructed, not measured."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .data_loader import validate_input_data

SOLAR='ALLSKY_SFC_SW_DWN'
WIND='WS50M'

def unique_pairs(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise ValueError(f'Duplicate JSON key: {key}')
        out[key]=value
    return out

def read_weather(path,start,end):
    d=json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique_pairs)
    if d['header']['time_standard']!='UTC':raise ValueError('Expected UTC')
    if d['header']['start']!=start or d['header']['end']!=end:raise ValueError('Wrong date range')
    units=d['parameters']
    if units[WIND]['units']!='m/s' or units[SOLAR]['units'] not in ('Wh/m^2','W/m^2'):
        raise ValueError(f'Unsupported units: {units}')
    times=pd.date_range(pd.to_datetime(start,format='%Y%m%d'),pd.to_datetime(end,format='%Y%m%d')+pd.Timedelta(days=1),freq='h',inclusive='left',tz='UTC')
    keys=times.strftime('%Y%m%d%H').tolist();values=d['properties']['parameter']
    for name in (SOLAR,WIND):
        if set(values[name])!=set(keys):raise ValueError(f'Missing/extra hours: {name}')
    result=pd.DataFrame({'timestamp_UTC':times,SOLAR:[values[SOLAR][k] for k in keys],WIND:[values[WIND][k] for k in keys]})
    array=result[[SOLAR,WIND]].to_numpy(dtype=float)
    if not np.isfinite(array).all() or (array<0).any() or (array==d['header']['fill_value']).any():
        raise ValueError('Missing, negative or nonfinite weather')
    return result,d

def convert_weather(weather,load_shape,solar_cap=None):
    shape=np.asarray(load_shape,dtype=float)
    if shape.shape!=(24,) or not np.isfinite(shape).all() or (shape<0).any():raise ValueError('Invalid 24h load shape')
    n=len(weather)
    if n==0 or n%24:raise ValueError('Expected whole days')
    v=weather[WIND].to_numpy(dtype=float);g=weather[SOLAR].to_numpy(dtype=float)
    if not np.isfinite(v).all() or not np.isfinite(g).all() or (v<0).any() or (g<0).any():raise ValueError('Invalid weather')
    wind=np.where(v<3,0,np.where(v<=12,(v**3-3**3)/(12**3-3**3),np.where(v<=25,1,0)))*100
    solar=g/1000*150
    if solar_cap is not None:solar=np.minimum(solar,solar_cap)
    load=np.tile(shape,n//24)*np.repeat(np.resize([.95,1.,1.05],n//24),24)
    result=pd.DataFrame(dict(hour=np.arange(n),load=load,wind=wind,solar=solar)).round(2)
    validate_input_data(result,n)
    if not (result.loc[g==0,'solar']==0).all():raise ValueError('Night output')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',required=True);p.add_argument('--start',required=True);p.add_argument('--end',required=True)
    p.add_argument('--load',default='data/input_24h.csv');p.add_argument('--output',required=True)
    a=p.parse_args();w,_=read_weather(a.raw,a.start,a.end)
    convert_weather(w,pd.read_csv(a.load).load).to_csv(a.output,index=False,encoding='utf-8',float_format='%.2f',mode='x')
