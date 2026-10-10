"""Actual loopback MQTT/HTTP/WebSocket integration, with an explicit Influx HTTP test double.
Not an Influx/Grafana/Compose acceptance. Optional --serve holds fixture for UI QA.
"""
import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import httpx
from amqtt.broker import Broker
from websockets.asyncio.client import connect

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'/'mqtt-probe';DATA.mkdir(parents=True,exist_ok=True)
def freeport():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
lines=[]
class Recorder(BaseHTTPRequestHandler):
    def do_POST(self):
        lines.extend(self.rfile.read(int(self.headers['Content-Length'])).decode().splitlines())
        self.send_response(204);self.end_headers()
    def log_message(self,*args):pass
async def main(serve):
    stopfile=DATA/'stop'
    if stopfile.exists():stopfile.unlink()
    mqttport=freeport();apiport=8000 if serve else freeport();influxport=freeport()
    credentials=dict(x.split('=',1) for x in (ROOT/'.env').read_text().splitlines() if x and not x.startswith('#') and '=' in x)
    env=os.environ|credentials|{'MQTT_HOST':'127.0.0.1','MQTT_PORT':str(mqttport),'DB_PATH':str(DATA/'backend.sqlite'),
       'SIM_JOURNAL':str(DATA/'commands.json'),'SIM_HEARTBEAT':str(DATA/'heartbeat'),'INFLUX_URL':f'http://127.0.0.1:{influxport}','HISTORY_TEST_DOUBLE':'true'}
    broker=Broker({'listeners':{'default':{'type':'tcp','bind':f'127.0.0.1:{mqttport}'}},
                   'plugins':{'amqtt.plugins.authentication.AnonymousAuthPlugin':{'allow_anonymous':True}}})
    recorder=ThreadingHTTPServer(('127.0.0.1',influxport),Recorder)
    threading.Thread(target=recorder.serve_forever,daemon=True).start()
    await broker.start();children=[];logs=[]
    evidence={'mode':'loopback MQTT with Influx HTTP test double','checks':[],'timestamp':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    def check(name,condition):
        evidence['checks'].append({'name':name,'passed':bool(condition)})
        if not condition:raise AssertionError(name)
    try:
        for name,args in [('simulation',['-m','simulation.main']),('backend',['-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(apiport)])]:
            log=(DATA/(name+'.log')).open('w');logs.append(log)
            children.append(subprocess.Popen([sys.executable,*args],cwd=ROOT,env=env,stdout=log,stderr=log))
        async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{apiport}',timeout=5) as c:
            for _ in range(60):
                await asyncio.sleep(.25)
                try:
                    if (await c.get('/api/ready')).status_code==200:break
                except httpx.HTTPError:pass
            else:raise AssertionError('Readiness failed; see data/mqtt-probe/*.log')
            check('backend ready over real MQTT',True)
            (await c.post('/api/login',json={'name':'operator','password':credentials['INITIAL_OPERATOR_PASSWORD']})).raise_for_status()
            async def send(tag,value):
                old=(await c.get('/api/state')).json()['snapshot']['values'][tag]
                body=dict(tag=tag,value=value,expected=old,command_id=str(uuid.uuid4()))
                (await c.post('/api/commands',json=body)).raise_for_status()
                for _ in range(30):
                    await asyncio.sleep(.2)
                    commands=(await c.get('/api/state')).json()['commands']
                    result=next(x for x in commands if x['id']==body['command_id'])
                    if result['status'] in ['executed','rejected','timeout']:return body,result
                raise AssertionError('Command never completed')
            await send('fault.inject',False);await send('mode.requested','auto');await send('temperature.requested',20)
            await asyncio.sleep(10)
            before=(await c.get('/api/state')).json()['snapshot']['values']['temperature.supply']
            body,result=await send('temperature.requested',22)
            check('20 to 22 command executes via actual MQTT',result['status']=='executed')
            evidence['command_id']=body['command_id']
            now=(await c.get('/api/state')).json()['snapshot']['values']
            check('actual value differs from accepted setpoint',now['temperature.supply']!=22 and now['temperature.accepted']==22)
            (await c.post('/api/commands',json=body)).raise_for_status()
            audit=(await c.get('/api/audit')).json()
            check('audit contains correlated command',any(x['command_id']==body['command_id'] and x['result'].startswith('executed') for x in audit))
            check('duplicate API call yields one pending record',sum(x['command_id']==body['command_id'] and x['result']=='pending' for x in audit)==1)
            cookie=c.cookies.get('rlt_session')
            async with connect(f'ws://127.0.0.1:{apiport}/api/ws',origin='http://localhost:8080',additional_headers={'Cookie':'rlt_session='+cookie}) as ws:
                initial=json.loads(await ws.recv());next_state=json.loads(await ws.recv())
                check('authenticated initial WebSocket snapshot',initial['fresh'])
                check('WebSocket subsequent update',next_state['snapshot']['sequence']>initial['snapshot']['sequence'])
            await asyncio.sleep(12)
            after=(await c.get('/api/state')).json()['snapshot']['values']['temperature.supply']
            evidence['actual_before']=before;evidence['actual_after']=after
            check('dynamic temperature response',after>before+.1)
            check('numeric and state measurements separated',any(x.startswith('rlt,tag=temperature.supply') for x in lines) and any(x.startswith('rlt_state,tag=plant.state') for x in lines))
            await send('fault.inject',True)
            _,reject=await send('temperature.requested',23)
            check('interlock rejection over MQTT',reject['status']=='rejected')
            await send('alarm.ack',True);await send('fault.inject',False)
            check('alarm return distinct from acknowledgement',(await c.get('/api/state')).json()['alarm']['returned'])
            await c.post('/api/logout')
            (await c.post('/api/login',json={'name':'viewer','password':credentials['INITIAL_VIEWER_PASSWORD']})).raise_for_status()
            check('viewer cannot write via actual HTTP',(await c.post('/api/commands',json=body|{'command_id':str(uuid.uuid4())})).status_code==403)
            evidence['recorded_lines']=len(lines)
            if serve:
                print('UI TEST FIXTURE READY: API localhost:8000. Influx is an HTTP test double. No Grafana.',flush=True)
                while not stopfile.exists():await asyncio.sleep(.25)
            # Stop simulation; backend must mark stale and reject writes.
            children[0].terminate();await asyncio.sleep(6)
            check('stopped simulation makes telemetry stale',not (await c.get('/api/state')).json()['fresh'])
    finally:
        for child in children:
            if child.poll() is None:child.terminate()
            child.wait(timeout=10)
        for log in logs:log.close()
        recorder.shutdown();recorder.server_close();await broker.shutdown()
        (ROOT/'docs'/'mqtt-integration-results.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'checks':len(evidence['checks']),'passed':all(x['passed'] for x in evidence['checks'])}))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--serve',action='store_true');args=parser.parse_args()
    asyncio.run(main(args.serve))
