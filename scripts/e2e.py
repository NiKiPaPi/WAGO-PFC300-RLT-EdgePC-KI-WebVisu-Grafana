"""Run against the actual Compose stack; writes evidence, not credentials."""
import json
import os
import time
import uuid
from pathlib import Path
import httpx

def env():
    return dict(line.split('=',1) for line in Path('.env').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
e=env(); url=e.get('PUBLIC_ORIGIN','http://localhost:8080')
evidence={'run_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'base_url':url,'checks':[]}
def check(name,condition):
    evidence['checks'].append({'name':name,'passed':bool(condition)})
    if not condition: raise AssertionError(name)
def wait(c,cid):
    end=time.monotonic()+15
    while time.monotonic()<end:
        for command in c.get('/api/state').json()['commands']:
            if command['id']==cid and command['status'] in ['executed','rejected','timeout']: return command
        time.sleep(.5)
    raise AssertionError('No terminal command result')
def send(c,tag,value):
    old=c.get('/api/state').json()['snapshot']['values'][tag]
    b=dict(tag=tag,value=value,expected=old,command_id=str(uuid.uuid4()))
    r=c.post('/api/commands',json=b);r.raise_for_status()
    return b,wait(c,b['command_id'])
try:
    with httpx.Client(base_url=url,timeout=10) as c:
        c.post('/api/login',json={'name':'operator','password':e['INITIAL_OPERATOR_PASSWORD']}).raise_for_status()
        check('initial telemetry fresh',c.get('/api/state').json()['fresh'])
        for tag,value in [('fault.inject',False),('mode.requested','auto'),('temperature.requested',20)]:
            _,r=send(c,tag,value);check(tag+' accepted',r['status']=='executed')
        time.sleep(15)
        before=c.get('/api/state').json()['snapshot']['values']['temperature.supply']
        b,r=send(c,'temperature.requested',22)
        check('22 °C command executed',r['status']=='executed')
        evidence['command_id']=b['command_id']
        after=c.get('/api/state').json()['snapshot']['values']
        check('accepted setpoint 22',after['temperature.accepted']==22)
        check('actual temperature not assigned to setpoint',abs(after['temperature.supply']-22)>.1)
        c.post('/api/commands',json=b).raise_for_status()
        audit=c.get('/api/audit').json()
        check('audit contains operator command',any(x['command_id']==b['command_id'] and x['name']=='operator' and x['result'].startswith('executed') for x in audit))
        samples=[]
        for _ in range(24):
            time.sleep(5);samples.append(c.get('/api/state').json()['snapshot'])
        evidence['samples']=samples
        check('time dependent response',samples[-1]['values']['temperature.supply']>before+.2)
        check('historian reports healthy',c.get('/api/state').json()['history_ok'])
        # Query actual Influx via container exec, never expose token on host command line.
        import subprocess
        flux='from(bucket: "rlt") |> range(start: -10m) |> filter(fn:(r)=>r._measurement == "rlt" and (r.tag == "temperature.supply" or r.tag == "temperature.accepted" or r.tag == "temperature.outdoor")) |> last()'
        query=subprocess.run(['docker','compose','exec','-T','influxdb','sh','-c','INFLUX_TOKEN="$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" influx query --org rlt "$1"','_',flux],capture_output=True,text=True)
        check('actual Influx contains three selected points',query.returncode==0 and all(x in query.stdout for x in ['temperature.supply','temperature.accepted','temperature.outdoor']))
        with httpx.Client(base_url='http://localhost:3000',auth=('admin',e['GRAFANA_PASSWORD'])) as g:
            dashboard=g.get('/api/dashboards/uid/rlt');check('Grafana dashboard provisioned',dashboard.status_code==200)
        c.post('/api/logout')
        c.post('/api/login',json={'name':'viewer','password':e['INITIAL_VIEWER_PASSWORD']}).raise_for_status()
        check('viewer write forbidden',c.post('/api/commands',json=b|{'command_id':str(uuid.uuid4())}).status_code==403)
finally:
    Path('docs/e2e-results.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print('E2E evidence saved to docs/e2e-results.json')
