"""Live weather test, temporarily selects Berlin; weather UI test runs before cleanup."""
import json
import time
from pathlib import Path
import httpx

env=dict(line.split('=',1) for line in Path('.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
evidence={'timestamp':time.time(),'mode':'real Open-Meteo / Docker / InfluxDB','checks':[]}
def check(name,ok):
    evidence['checks'].append({'name':name,'passed':bool(ok)})
    assert ok,name
with httpx.Client(base_url='http://localhost:8080',timeout=50) as c:
    r=c.post('/api/login',json={'name':'operator','password':env['INITIAL_OPERATOR_PASSWORD']});r.raise_for_status()
    before=c.get('/api/state').json()['snapshot']['values']['temperature.requested']
    check('no hardcoded default location',c.get('/api/weather').json()['location'] is None)
    r=c.get('/api/weather/search',params={'q':'Berlin, Deutschland'});r.raise_for_status(); locations=r.json()
    berlin=next(x for x in locations if x['country']=='Deutschland' and x['name']=='Berlin')
    r=c.put('/api/weather/location',json={'id':berlin['id']});r.raise_for_status()
    deadline=time.time()+100
    while time.time()<deadline:
        data=c.get('/api/weather').json()
        if data['forecast'] and data['archived']:break
        time.sleep(2)
    check('real 7 local days',len(data['forecast']['daily'])==7)
    check('hourly temperature and humidity',all(x['valid'] for x in data['forecast']['hourly']))
    check('Influx write acknowledged',data['archived'])
    check('location audited',any(x['target']=='weather.location' for x in c.get('/api/audit').json()))
    r=c.get('/api/weather/history',params={'location_id':berlin['id'],'as_of':data['forecast']['acquired_at']});r.raise_for_status()
    check('as-of prediction returns correct version',r.json()['version']==data['forecast']['version'])
    check('control setpoint unchanged',c.get('/api/state').json()['snapshot']['values']['temperature.requested']==before)
    evidence['location']=berlin;evidence['version']=data['forecast']['version'];evidence['hours']=len(data['forecast']['hourly'])
Path('docs/weather-live-results.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
print(json.dumps(evidence,indent=2))
