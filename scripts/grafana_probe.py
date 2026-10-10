"""Verify the provisioned panel queries through actual Grafana datasource API."""
import json
import re
import time
from pathlib import Path
import httpx
config=dict(line.split('=',1) for line in Path('.env').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
evidence={'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'mode':'real provisioned Grafana queries','checks':[]}
with httpx.Client(base_url='http://localhost:3000',auth=('admin',config['GRAFANA_PASSWORD']),timeout=30) as c:
    r=c.get('/api/dashboards/uid/rlt');r.raise_for_status();dashboard=r.json()['dashboard']
    for panel in dashboard['panels']:
        queries=[{'refId':t['refId'],'datasource':{'uid':'rlt-influx','type':'influxdb'},'query':t['query'].replace('${tags:regex}','temperature\\.(supply|accepted|outdoor)')} for t in panel['targets']]
        r=c.post('/api/ds/query',json={'from':str(int(time.time()*1000)-600000),'to':str(int(time.time()*1000)),
                 'queries':queries})
        result=r.json();outputs=list(result.get('results',{}).values());frames=[f for out in outputs for f in out.get('frames',[]) if any(field['type']!='time' and any(v is not None for v in values) for field,values in zip(f['schema']['fields'],f['data']['values']))];errors=[out['error'] for out in outputs if out.get('error')]
        evidence['checks'].append({'panel':panel['title'],'passed':r.status_code==200 and not errors and len(frames)==3,'error':errors,'frames':frames})
Path('docs/grafana-query-results.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{'panel':x['panel'],'passed':x['passed'],'error':x['error'],'frames':len(x['frames'])} for x in evidence['checks']],ensure_ascii=False))
if not all(x['passed'] for x in evidence['checks']):raise SystemExit(1)
