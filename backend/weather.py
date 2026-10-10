"""Independent weather collector. No PLC/MQTT dependencies or control outputs."""
import asyncio
import datetime as dt
import json
import math
import os
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

INTERVAL=max(300,int(os.getenv('WEATHER_INTERVAL_SECONDS','1800')))
RETENTION=max(1,int(os.getenv('WEATHER_RETENTION_DAYS','365')))
db=sqlite3.connect(os.getenv('WEATHER_DB_PATH','/data/weather.sqlite'),check_same_thread=False)
db.row_factory=sqlite3.Row
db.executescript('''PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS config(id INTEGER PRIMARY KEY CHECK(id=1), location TEXT);
CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY, location_id TEXT, acquired REAL, payload TEXT, archived INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS searches(id INTEGER PRIMARY KEY, payload TEXT, expires REAL);
''')
last_error=None
archive_error=None
last_attempt=None

def location():
    row=db.execute('SELECT location FROM config WHERE id=1').fetchone()
    return json.loads(row[0]) if row else None

def normalize(raw,loc,acquired=None):
    h=raw['hourly']; times=h['time']; temperatures=h['temperature_2m']; humidity=h['relative_humidity_2m']
    if not len(times)==len(temperatures)==len(humidity) or not 1<=len(times)<=200: raise ValueError('Invalid hourly arrays')
    units=raw['hourly_units']
    if units['temperature_2m']!='°C' or units['relative_humidity_2m']!='%': raise ValueError('Invalid units')
    zone=ZoneInfo(loc['timezone']); hourly=[]; days={}; previous=None
    for stamp,t,rh in zip(times,temperatures,humidity):
        stamp=int(stamp)
        if previous is not None and stamp-previous!=3600: raise ValueError('Invalid timestamps')
        previous=stamp
        valid_t=isinstance(t,(int,float)) and not isinstance(t,bool) and math.isfinite(t) and -100<=t<=70
        valid_rh=isinstance(rh,(int,float)) and not isinstance(rh,bool) and math.isfinite(rh) and 0<=rh<=100
        item={'time':dt.datetime.fromtimestamp(stamp,dt.timezone.utc).isoformat(),'temperature':float(t) if valid_t else None,'humidity':float(rh) if valid_rh else None,'valid':valid_t and valid_rh}
        hourly.append(item); day=dt.datetime.fromtimestamp(stamp,zone).date().isoformat(); days.setdefault(day,[]).append(item)
    if not any(x['valid'] for x in hourly): raise ValueError('No valid values')
    daily=[]
    for day,items in days.items():
        ts=[x['temperature'] for x in items if x['temperature'] is not None]; hs=[x['humidity'] for x in items if x['humidity'] is not None]
        daily.append({'date':day,'minimum':min(ts) if ts else None,'maximum':max(ts) if ts else None,'humidity_mean':round(sum(hs)/len(hs),1) if hs else None,'hours':len(items),'valid_hours':sum(x['valid'] for x in items)})
    return {'version':str(uuid.uuid4()),'provider':'Open-Meteo','acquired_at':dt.datetime.fromtimestamp(acquired or time.time(),dt.timezone.utc).isoformat(),'location':loc,'hourly':hourly,'daily':daily[:7],'quality':'good' if all(x['valid'] for x in hourly) else 'partial'}

async def external(url,params):
    # Fixed endpoints only; never include URLs, keys or response bodies in errors.
    async with httpx.AsyncClient(timeout=12,follow_redirects=False) as http:
        for attempt in range(3):
            try:
                response=await http.get(url,params=params)
                if response.status_code==429: raise HTTPException(503,'Wetterdienst: Aufruflimit erreicht')
                response.raise_for_status(); return response.json()
            except HTTPException: raise
            except (httpx.HTTPError,ValueError):
                if attempt==2: raise HTTPException(503,'Wetterdienst nicht erreichbar oder Antwort ungültig')
                await asyncio.sleep(2**attempt)

async def archive():
    token=os.getenv('INFLUX_TOKEN','')
    async with httpx.AsyncClient(timeout=10) as http:
        bucket=os.getenv('WEATHER_BUCKET','weather')
        orgs=await http.get(os.getenv('INFLUX_URL','http://influxdb:8086')+'/api/v2/orgs',params={'org':'rlt'},headers={'Authorization':'Token '+token})
        orgs.raise_for_status(); org_id=orgs.json()['orgs'][0]['id']
        base=os.getenv('INFLUX_URL','http://influxdb:8086'); headers={'Authorization':'Token '+token}
        buckets=await http.get(base+'/api/v2/buckets',params={'orgID':org_id,'name':bucket},headers=headers)
        if buckets.status_code!=404: buckets.raise_for_status()
        if buckets.status_code==404 or not buckets.json()['buckets']:
            created=await http.post(base+'/api/v2/buckets',headers=headers,json={'orgID':org_id,'name':bucket,'retentionRules':[{'type':'expire','everySeconds':RETENTION*86400}]}); created.raise_for_status()
        for row in db.execute('SELECT * FROM versions WHERE archived=0 ORDER BY acquired LIMIT 8').fetchall():
            p=json.loads(row['payload']); lines=[]
            for item in p['hourly']:
                fields=['valid='+str(item['valid']).lower(),'acquired_at='+json.dumps(p['acquired_at']),'latitude='+str(p['location']['latitude']),'longitude='+str(p['location']['longitude'])]
                for key in ['temperature','humidity']:
                    if item[key] is not None: fields.append(key+'='+str(float(item[key])))
                ns=int(dt.datetime.fromisoformat(item['time']).timestamp())*1000000000
                lines.append(f"weather_forecast,location_id={row['location_id']},provider=open_meteo,version={row['id']} "+','.join(fields)+f' {ns}')
            r=await http.post(base+'/api/v2/write',params={'org':'rlt','bucket':bucket,'precision':'ns'},headers=headers,content='\n'.join(lines)); r.raise_for_status()
            db.execute('UPDATE versions SET archived=1 WHERE id=?',(row['id'],)); db.commit()

async def cycle():
    global last_error,last_attempt,archive_error
    while True:
        try:
            loc=location()
            latest=db.execute('SELECT MAX(acquired) FROM versions WHERE location_id=?',(str(loc['id']),)).fetchone()[0] if loc else None
            if loc and (latest is None or time.time()-latest>=INTERVAL) and (last_attempt is None or time.time()-last_attempt>=300):
                last_attempt=time.time()
                key=os.getenv('WEATHER_API_KEY','')
                host='https://customer-api.open-meteo.com' if key else 'https://api.open-meteo.com'
                params={'latitude':loc['latitude'],'longitude':loc['longitude'],'timezone':loc['timezone'],'forecast_days':7,'timeformat':'unixtime','hourly':'temperature_2m,relative_humidity_2m'}
                if key: params['apikey']=key
                raw=await external(host+'/v1/forecast',params); acquired=time.time(); payload=normalize(raw,loc,acquired)
                db.execute('INSERT INTO versions(id,location_id,acquired,payload) VALUES(?,?,?,?)',(payload['version'],str(loc['id']),acquired,json.dumps(payload))); db.commit(); last_error=None
            try:
                await archive(); archive_error=None
            except Exception:
                archive_error='Wetterarchivierung ausstehend; lokale Daten bleiben erhalten'
            db.execute('DELETE FROM versions WHERE acquired<? AND archived=1',(time.time()-RETENTION*86400,)); db.execute('DELETE FROM searches WHERE expires<?',(time.time(),)); db.commit()
        except Exception as e:
            last_error=e.detail if isinstance(e,HTTPException) else 'Wetterabruf oder Archivierung fehlgeschlagen'
        await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(app):
    task=asyncio.create_task(cycle())
    yield
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass

app=FastAPI(lifespan=lifespan)
class Choice(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:int

@app.get('/health')
def health(): return {'ok':True}

@app.get('/search')
async def search(q:str):
    q=q.strip()
    if not 2<=len(q)<=100: raise HTTPException(422,'Bitte 2 bis 100 Zeichen eingeben')
    key=os.getenv('WEATHER_API_KEY','')
    params={'name':q,'count':10,'language':'de','format':'json'}
    if key: params['apikey']=key
    host='https://customer-geocoding-api.open-meteo.com' if key else 'https://geocoding-api.open-meteo.com'
    raw=await external(host+'/v1/search',params)
    results=[]
    for x in raw.get('results',[]):
        try:
            ZoneInfo(x['timezone'])
            loc={k:x[k] for k in ['id','name','latitude','longitude','timezone']}; loc.update(country=x.get('country',''),region=x.get('admin1',''))
            if not -90<=loc['latitude']<=90 or not -180<=loc['longitude']<=180: continue
            results.append(loc); db.execute('INSERT OR REPLACE INTO searches VALUES(?,?,?)',(loc['id'],json.dumps(loc),time.time()+1800))
        except (KeyError,ValueError): continue
    db.commit(); return results

@app.put('/location')
async def choose(body:Choice):
    global last_attempt,last_error
    row=db.execute('SELECT payload FROM searches WHERE id=? AND expires>?',(body.id,time.time())).fetchone()
    if not row: raise HTTPException(422,'Bitte den Ort erneut suchen und auswählen')
    loc=json.loads(row[0]); db.execute('INSERT OR REPLACE INTO config VALUES(1,?)',(json.dumps(loc),)); db.commit(); last_attempt=None; last_error=None
    return loc

@app.get('/forecast')
async def forecast():
    loc=location(); row=db.execute('SELECT * FROM versions WHERE location_id=? ORDER BY acquired DESC LIMIT 1',(str(loc['id']),)).fetchone() if loc else None
    payload=json.loads(row['payload']) if row else None
    stale=bool(row and time.time()-row['acquired']>max(INTERVAL*2,3600))
    return {'location':loc,'forecast':payload,'status':'Kein Standort' if not loc else 'Keine Daten verfügbar' if not row else 'Daten veraltet' if stale else 'Teilweise Daten' if payload['quality']=='partial' else 'Aktuell','error':last_error or archive_error,'archived':bool(row and row['archived']),'interval_seconds':INTERVAL}

@app.get('/history')
async def history(location_id:int,as_of:str):
    try: at=dt.datetime.fromisoformat(as_of.replace('Z','+00:00')); assert at.tzinfo is not None
    except (ValueError,AssertionError): raise HTTPException(422,'UTC-Zeitpunkt mit Zeitzone erforderlich')
    row=db.execute('SELECT payload FROM versions WHERE location_id=? AND acquired<=? ORDER BY acquired DESC LIMIT 1',(str(location_id),at.timestamp())).fetchone()
    if not row: raise HTTPException(404,'Keine damals bekannte Vorhersage vorhanden')
    return json.loads(row[0])
