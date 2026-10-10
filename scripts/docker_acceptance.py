"""Extended acceptance against real Compose services. No credentials in evidence."""
import datetime as dt
import json
import os
import subprocess
import time
import uuid
from pathlib import Path
import httpx

config=dict(line.split('=',1) for line in Path('.env').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
docker=os.getenv('RLT_DOCKER','docker')
evidence={'timestamp':dt.datetime.now(dt.timezone.utc).isoformat(),'mode':'real Docker Compose / Mosquitto / InfluxDB / Grafana','checks':[]}
def check(name,ok,detail=None):
    evidence['checks'].append({'name':name,'passed':bool(ok),'detail':detail})
    if not ok:raise AssertionError(name)
def compose(*args):
    p=subprocess.run([docker,'compose',*args],capture_output=True,text=True)
    if p.returncode:raise RuntimeError('Compose operation failed: '+args[0])
    return p.stdout
def influx(query):
    return compose('exec','-T','influxdb','sh','-c','INFLUX_TOKEN="$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" influx query --raw --org rlt "$1"','_',query)
def login(c,role):
    c.post('/api/login',json={'name':role,'password':config['INITIAL_'+role.upper()+'_PASSWORD']}).raise_for_status()
def wait_result(c,cid):
    end=time.monotonic()+15
    while time.monotonic()<end:
        result=next(x for x in c.get('/api/state').json()['commands'] if x['id']==cid)
        if result['status'] in ['executed','rejected','timeout']:return result
        time.sleep(.3)
    raise AssertionError('Command terminal state missing')
def send(c,tag,value):
    old=c.get('/api/state').json()['snapshot']['values'][tag]
    body={'tag':tag,'value':value,'expected':old,'command_id':str(uuid.uuid4())}
    c.post('/api/commands',json=body).raise_for_status()
    return body,wait_result(c,body['command_id'])
def wait_ready(c):
    for _ in range(80):
        try:
            if c.get('/api/ready').status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.5)
    raise AssertionError('Services not ready after restart')
try:
    with httpx.Client(base_url=config['PUBLIC_ORIGIN'],timeout=10) as c:
        login(c,'operator');wait_ready(c)
        check('invalid value rejected at API',c.post('/api/commands',json={'tag':'temperature.requested','value':31,'expected':22,'command_id':str(uuid.uuid4())}).status_code==422)
        check('operator cannot edit settings',c.put('/api/settings',json={'timezone':'UTC','stale_seconds':5,'history_interval_seconds':2}).status_code==403)
        send(c,'fault.inject',True)
        _,r=send(c,'temperature.requested',23)
        check('interlock rejection',r['status']=='rejected',r['command_id'] if 'command_id' in r else r['id'])
        send(c,'alarm.ack',True)
        alarm=c.get('/api/state').json()['alarm'];check('alarm active and acknowledged',alarm['active'] and alarm['acknowledged'])
        send(c,'fault.inject',False)
        alarm=c.get('/api/state').json()['alarm'];check('alarm returned and acknowledged',not alarm['active'] and alarm['returned'] and alarm['acknowledged'])
        body,r=send(c,'temperature.requested',22)
        c.post('/api/commands',json=body).raise_for_status()
        entries=c.get('/api/audit').json()
        check('duplicate command does not execute twice',sum(x['command_id']==body['command_id'] and x['result'].startswith('executed') for x in entries)==1)
        # Suspend gateway briefly: accepted HTTP write then missing MQTT result -> timeout.
        compose('pause','simulation')
        try:
            old=c.get('/api/state').json()['snapshot']['values']['temperature.requested']
            timeout_body={'tag':'temperature.requested','value':24,'expected':old,'command_id':str(uuid.uuid4())}
            response=c.post('/api/commands',json=timeout_body)
            check('command queued before telemetry stale',response.status_code==202)
            r=wait_result(c,timeout_body['command_id']);check('missing acknowledgement produces timeout',r['status']=='timeout')
            s=c.get('/api/state').json();check('stale telemetry during gateway outage',not s['fresh'])
        finally:compose('unpause','simulation')
        wait_ready(c);time.sleep(2)
        check('expired command not executed on reconnect',c.get('/api/state').json()['snapshot']['values']['temperature.accepted']==22)
        # Prove an exact old UTC window survives restart, independent of new points.
        end=dt.datetime.now(dt.timezone.utc).isoformat();start=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=10)).isoformat()
        q=f'from(bucket: "rlt") |> range(start: time(v: "{start}"), stop: time(v: "{end}")) |> filter(fn:(r)=>r._measurement == "rlt" and r.tag == "temperature.supply")'
        before=influx(q)
        check('historical window contains data before restart','temperature.supply' in before)
        compose('restart','influxdb','grafana');wait_ready(c)
        after=influx(q)
        check('historical exact window retained after restart',before==after,{'start':start,'stop':end,'bytes':len(before)})
        with httpx.Client(base_url='http://localhost:3000',auth=('admin',config['GRAFANA_PASSWORD']),timeout=20) as g:
            for _ in range(60):
                try:
                    if g.get('/api/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.5)
            dashboard=g.get('/api/dashboards/uid/rlt');check('dashboard retained after restart',dashboard.status_code==200)
            query='from(bucket: "rlt") |> range(start: -10m) |> filter(fn:(r)=>r._measurement == "rlt" and r._field == "value" and (r.tag == "temperature.supply" or r.tag == "temperature.accepted" or r.tag == "temperature.outdoor")) |> aggregateWindow(every: 5s, fn: mean, createEmpty: true)'
            response=g.post('/api/ds/query',json={'from':str(int(time.time()*1000)-600000),'to':str(int(time.time()*1000)),
                             'queries':[{'refId':'A','datasource':{'uid':'rlt-influx','type':'influxdb'},'query':query}]})
            results=response.json();frames=results.get('results',{}).get('A',{}).get('frames',[])
            data_tags=set()
            for f in frames:
                for field in f.get('schema',{}).get('fields',[]):
                    if 'tag' in field.get('labels',{}):data_tags.add(field['labels']['tag'])
            check('Grafana queries three actual Influx data points',response.status_code==200 and {'temperature.supply','temperature.accepted','temperature.outdoor'}<=data_tags,sorted(data_tags))
            evidence['grafana_frames']=frames
finally:
    Path('docs/docker-acceptance-results.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(evidence['checks']),'passed':all(x['passed'] for x in evidence['checks'])}))
