"""Download public NASA POWER bytes without changing them or replacing archives."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request

ENDPOINT = 'https://power.larc.nasa.gov/api/temporal/hourly/point'

def download(destination, start, end, latitude=30.59, longitude=114.30):
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    params=dict(parameters='ALLSKY_SFC_SW_DWN,WS50M',community='RE',latitude=latitude,
                longitude=longitude,start=start,end=end,format='JSON',**{'time-standard':'UTC'})
    record=dict(endpoint=ENDPOINT,parameters=params,requested_at=datetime.now(timezone.utc).isoformat())
    try:
        with urlopen(Request(ENDPOINT+'?'+urlencode(params),headers={'User-Agent':'dachuang-research/1.0'}),timeout=120) as response:
            raw=response.read()
            record.update(http_status=response.status,headers=dict(response.headers))
        (destination/'response.json').write_bytes(raw)
        record['sha256']=hashlib.sha256(raw).hexdigest()
    except Exception as exc:
        record['error']=repr(exc)
        raise
    finally:
        (destination/'request.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return destination/'response.json'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--start',required=True);p.add_argument('--end',required=True)
    p.add_argument('--latitude',type=float,default=30.59);p.add_argument('--longitude',type=float,default=114.30)
    a=p.parse_args();print(download(a.output,a.start,a.end,a.latitude,a.longitude))
