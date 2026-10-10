import asyncio
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict
from contracts.core import TAGS, PREFIX, VERSION, utc, age, validate, schema_validate

DB_PATH=os.getenv('DB_PATH','data/backend.sqlite')
Path(DB_PATH).parent.mkdir(parents=True,exist_ok=True)
db=sqlite3.connect(DB_PATH,check_same_thread=False)
db.row_factory=sqlite3.Row
mutex=threading.RLock()
db.executescript('''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY, password TEXT NOT NULL, role TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, name TEXT NOT NULL, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, name TEXT, tag TEXT, old TEXT, new TEXT, status TEXT, reason TEXT, created TEXT, expires TEXT);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, name TEXT, target TEXT, old TEXT, new TEXT, command_id TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
''')
def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),310000).hex()
def verify(password,stored): return hmac.compare_digest(password_hash(password,stored.split(':')[0]),stored)
def audit(name,target,old,new,cid,result):
    db.execute('INSERT INTO audit(timestamp,name,target,old,new,command_id,result) VALUES(?,?,?,?,?,?,?)',(utc(),name,target,json.dumps(old),json.dumps(new),cid,result))
    db.commit()
def setting(key,default):
    with mutex:
        row=db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
    return json.loads(row[0]) if row else default
def bootstrap():
    with mutex:
        for role in ['viewer','operator','administrator']:
            value=os.getenv('INITIAL_'+role.upper()+'_PASSWORD')
            if not db.execute('SELECT 1 FROM users WHERE name=?',(role,)).fetchone():
                if not value or len(value)<12: raise RuntimeError('Initial passwords of at least 12 characters required in .env')
                db.execute('INSERT INTO users(name,password,role) VALUES(?,?,?)',(role,password_hash(value),role))
        # Restart never republishes incomplete commands.
        for row in db.execute("SELECT * FROM commands WHERE status IN ('pending','received','accepted')").fetchall():
            db.execute("UPDATE commands SET status='timeout',reason='Backend-Neustart: Ergebnis unbekannt' WHERE id=?",(row['id'],))
            audit(row['name'],row['tag'],json.loads(row['old']),json.loads(row['new']),row['id'],'timeout: Backend-Neustart')
        db.commit()

state={'snapshot':None,'connected':False,'online':False,'alarm':None,'history_ok':False,'history_error':None}
client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='rlt-backend')
client.username_pw_set(os.getenv('MQTT_API_USER'),os.getenv('MQTT_API_PASSWORD'))
def on_connect(c,u,f,reason,p):
    state['connected']=reason==0
    if reason==0:
        c.subscribe([(PREFIX+'/'+s,1) for s in ['telemetry','results','alarms','status']])
def on_disconnect(c,u,f,reason,p):
    state['connected']=False; state['online']=False
def on_message(c,u,msg):
    try:
        data=json.loads(msg.payload); kind=msg.topic.rsplit('/',1)[1]
        with mutex:
            if kind=='telemetry':
                schema_validate('telemetry',data)
                if age(data['timestamp']) < -5 or age(data['timestamp'])>10: return
                old=state['snapshot']
                if old and data['timestamp']<=old['timestamp']: return
                state['snapshot']=data
            elif kind=='status':
                schema_validate('status',data)
                state['online']=bool(data['online']) and age(data['timestamp'])<10
            elif kind=='alarms':
                schema_validate('alarm',data)
                state['alarm']=data
            elif kind=='results':
                schema_validate('result',data)
                row=db.execute('SELECT * FROM commands WHERE id=?',(data['command_id'],)).fetchone()
                if not row or row['tag']!=data['tag']: return
                if row['status'] in ['executed','rejected','timeout']: return
                order={'pending':0,'received':1,'accepted':2,'executed':3,'rejected':3}
                if order[data['status']]<order[row['status']]: return
                if age(row['expires'])>=0:
                    status='timeout'; reason='Verspätete Bestätigung; Ergebnis unbekannt'
                else: status=data['status']; reason=data['reason']
                db.execute('UPDATE commands SET status=?,reason=? WHERE id=?',(status,reason,row['id']))
                audit(row['name'],row['tag'],json.loads(row['old']),json.loads(row['new']),row['id'],status+': '+reason)
    except Exception as e:
        print('MQTT input rejected:',type(e).__name__,flush=True)
client.on_connect=on_connect; client.on_disconnect=on_disconnect; client.on_message=on_message
client.reconnect_delay_set(1,15)

def snapshot():
    with mutex:
        s=state['snapshot']
        fresh=bool(s and s['quality']=='good' and state['connected'] and state['online'] and 0<=age(s['timestamp'])<setting('stale_seconds',5))
        return {'schema_version':VERSION,'snapshot':s,'fresh':fresh,'data_age_seconds':round(age(s['timestamp']),1) if s else None,
                'mqtt_connected':state['connected'],'simulation_online':state['online'],'alarm':state['alarm'],
                'history_ok':state['history_ok'],'history_error':state['history_error'],
                'history_test_double':os.getenv('HISTORY_TEST_DOUBLE','false')=='true',
                'stale_seconds':setting('stale_seconds',5),
                'commands':[dict(x) for x in db.execute('SELECT * FROM commands ORDER BY created DESC LIMIT 30')],
                'timezone':setting('timezone',os.getenv('DISPLAY_TIMEZONE','Europe/Berlin'))}

async def background():
    last_stamp=None; last_write=0.
    async with httpx.AsyncClient(timeout=3) as http:
        while True:
            await asyncio.sleep(.5)
            with mutex:
                for row in db.execute("SELECT * FROM commands WHERE status IN ('pending','received','accepted')").fetchall():
                    if age(row['expires'])>=0:
                        db.execute("UPDATE commands SET status='timeout',reason='Bestätigung fehlt; Ergebnis unbekannt' WHERE id=?",(row['id'],))
                        audit(row['name'],row['tag'],json.loads(row['old']),json.loads(row['new']),row['id'],'timeout')
            s=snapshot()
            if not s['fresh']: continue
            tele=s['snapshot']; interval=setting('history_interval_seconds',float(os.getenv('HISTORY_INTERVAL_SECONDS','2')))
            if tele['timestamp']==last_stamp or time.monotonic()-last_write<interval: continue
            lines=[]
            ns=int(dt.datetime.fromisoformat(tele['timestamp']).timestamp()*1e9)
            for tag_id,value in tele['values'].items():
                if not TAGS[tag_id]['history']: continue
                numeric=TAGS[tag_id]['type']=='number'
                encoded=str(float(value)) if numeric else json.dumps(str(value).lower() if isinstance(value,bool) else value)
                measurement='rlt' if numeric else 'rlt_state'
                lines.append(f'{measurement},tag={tag_id},quality=good value={encoded} {ns}')
            try:
                r=await http.post(os.getenv('INFLUX_URL','http://influxdb:8086')+'/api/v2/write',
                                 params={'org':'rlt','bucket':'rlt','precision':'ns'},
                                 headers={'Authorization':'Token '+os.getenv('INFLUX_TOKEN','')},content='\n'.join(lines))
                r.raise_for_status(); state['history_ok']=True; state['history_error']=None
                last_stamp=tele['timestamp']; last_write=time.monotonic()
            except Exception as e:
                state['history_ok']=False; state['history_error']=type(e).__name__

@asynccontextmanager
async def lifespan(app):
    bootstrap()
    client.connect_async(os.getenv('MQTT_HOST','mqtt'),int(os.getenv('MQTT_PORT','1883')),30); client.loop_start()
    task=asyncio.create_task(background())
    yield
    task.cancel(); client.disconnect(); client.loop_stop()
app=FastAPI(title='RLT Simulation API',version=VERSION,lifespan=lifespan)
class Strict(BaseModel): model_config=ConfigDict(extra='forbid')
class Login(Strict): name:str; password:str
class Command(Strict): tag:str; value:float|str|bool; expected:float|str|bool; command_id:str
class User(Strict): name:str; password:str; role:str; enabled:bool=True
class Settings(Strict): timezone:str; stale_seconds:float; history_interval_seconds:float

def identity(token):
    if not token: raise HTTPException(401,'Anmeldung erforderlich')
    with mutex:
        row=db.execute('SELECT u.name,u.role FROM sessions s JOIN users u ON s.name=u.name WHERE s.token=? AND s.expires>? AND u.enabled=1',
                       (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
    if not row: raise HTTPException(401,'Sitzung abgelaufen')
    return dict(row)
def user(request,roles=None):
    # Same-origin cookie; also protect all mutations against cross-site requests.
    origin=request.headers.get('origin')
    if request.method not in ['GET','HEAD'] and origin and origin!=os.getenv('PUBLIC_ORIGIN','http://localhost:8080'):
        raise HTTPException(403,'Fremder Origin gesperrt')
    who=identity(request.cookies.get('rlt_session'))
    if roles and who['role'] not in roles: raise HTTPException(403,'Berechtigung fehlt')
    return who
attempts={}
@app.post('/api/login')
def login(body:Login,request:Request,response:Response):
    if request.headers.get('origin') and request.headers['origin']!=os.getenv('PUBLIC_ORIGIN','http://localhost:8080'): raise HTTPException(403)
    key=request.client.host; now=time.time()
    with mutex:
        attempts[key]=[t for t in attempts.get(key,[]) if now-t<60]
        if len(attempts[key])>=10: raise HTTPException(429,'Zu viele Anmeldeversuche')
        attempts[key].append(now)
        row=db.execute('SELECT * FROM users WHERE name=?',(body.name,)).fetchone()
        if not row or not row['enabled'] or not verify(body.password,row['password']): raise HTTPException(401,'Anmeldung fehlgeschlagen')
        token=secrets.token_urlsafe(32)
        db.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),body.name,now+3600)); db.commit()
    response.set_cookie('rlt_session',token,httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE','false')=='true',max_age=3600,path='/')
    return {'name':row['name'],'role':row['role']}
@app.post('/api/logout')
def logout(request:Request,response:Response):
    user(request)
    with mutex:
        db.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(request.cookies['rlt_session'].encode()).hexdigest(),)); db.commit()
    response.delete_cookie('rlt_session'); return {'ok':True}
@app.get('/api/me')
def me(request:Request): return user(request)
@app.get('/api/tags')
def tags(request:Request): user(request); return TAGS
@app.get('/api/state')
def get_state(request:Request): user(request); return snapshot()
@app.get('/api/health')
def health(): return {'alive':True,'mode':'simulation','mqtt':state['connected'],'fresh':snapshot()['fresh'],'history':state['history_ok']}
@app.get('/api/ready')
def ready():
    if not snapshot()['fresh'] or not state['history_ok']: raise HTTPException(503,'MQTT/Simulation/Historie noch nicht bereit')
    return {'ready':True}
@app.post('/api/commands',status_code=202)
def command(body:Command,request:Request):
    who=user(request,['operator','administrator'])
    try: uuid.UUID(body.command_id); validate(body.tag,body.value)
    except (ValueError,TypeError) as e: raise HTTPException(422,str(e))
    with mutex:
        old=db.execute('SELECT * FROM commands WHERE id=?',(body.command_id,)).fetchone()
        if old:
            if old['name']!=who['name'] or old['tag']!=body.tag or json.loads(old['new'])!=body.value: raise HTTPException(409,'Command-ID bereits verwendet')
            return dict(old)
        snap=snapshot()
        if not snap['fresh']: raise HTTPException(503,'Keine frischen Simulationsdaten')
        old_value=snap['snapshot']['values'].get(body.tag)
        if old_value!=body.expected: raise HTTPException(409,'Ausgangswert wurde geändert; neu laden')
        if db.execute("SELECT 1 FROM commands WHERE tag=? AND status IN ('pending','received','accepted')",(body.tag,)).fetchone(): raise HTTPException(409,'Befehl für dieses Tag läuft bereits')
        created=utc(); expires=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=10)).isoformat()
        payload=dict(schema_version=VERSION,command_id=body.command_id,tag=body.tag,value=body.value,expected=body.expected,
                     user=who['name'],created_at=created,expires_at=expires)
        schema_validate('command',payload)
        db.execute('INSERT INTO commands VALUES(?,?,?,?,?,?,?,?,?)',(body.command_id,who['name'],body.tag,json.dumps(old_value),json.dumps(body.value),'pending','',created,expires))
        audit(who['name'],body.tag,old_value,body.value,body.command_id,'pending')
        # No offline queue or replay. Race/disconnect is resolved as timeout, never success.
        if not client.is_connected(): raise HTTPException(503,'Broker getrennt; gespeicherter Befehl wird nicht erneut gesendet')
        result=client.publish(PREFIX+'/commands',json.dumps(payload),qos=0,retain=False)
        if result.rc!=mqtt.MQTT_ERR_SUCCESS: raise HTTPException(503,'Veröffentlichung fehlgeschlagen; keine Wiederholung')
    return {'command_id':body.command_id,'status':'pending'}
@app.get('/api/audit')
def get_audit(request:Request):
    user(request)
    with mutex: return [dict(r) for r in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 200')]
@app.get('/api/users')
def get_users(request:Request):
    user(request,['administrator'])
    with mutex: return [dict(r) for r in db.execute('SELECT name,role,enabled FROM users')]
@app.put('/api/users')
def put_user(body:User,request:Request):
    who=user(request,['administrator'])
    if body.role not in ['viewer','operator','administrator'] or len(body.password)<12 or not body.name.isalnum(): raise HTTPException(422,'Rolle, Benutzername oder Passwort ungültig')
    if body.name==who['name'] and (not body.enabled or body.role!='administrator'): raise HTTPException(409,'Eigene Administratorberechtigung erhalten')
    with mutex:
        db.execute('INSERT INTO users VALUES(?,?,?,?) ON CONFLICT(name) DO UPDATE SET password=excluded.password,role=excluded.role,enabled=excluded.enabled',
                   (body.name,password_hash(body.password),body.role,int(body.enabled)))
        db.execute('DELETE FROM sessions WHERE name=?',(body.name,))
        audit(who['name'],'user:'+body.name,None,{'role':body.role,'enabled':body.enabled},None,'updated')
    return {'ok':True}
@app.put('/api/settings')
def put_settings(body:Settings,request:Request):
    from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
    who=user(request,['administrator'])
    try: ZoneInfo(body.timezone)
    except ZoneInfoNotFoundError: raise HTTPException(422,'Zeitzone ungültig')
    if not 2<=body.stale_seconds<=30 or not 1<=body.history_interval_seconds<=60: raise HTTPException(422,'Intervall außerhalb des Simulationsbereichs')
    with mutex:
        for k,v in body.model_dump().items():
            old=setting(k,None)
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(k,json.dumps(v)))
            audit(who['name'],k,old,v,None,'updated')
    return {'ok':True}
@app.websocket('/api/ws')
async def ws(socket:WebSocket):
    if socket.headers.get('origin')!=os.getenv('PUBLIC_ORIGIN','http://localhost:8080'):
        await socket.close(code=1008); return
    try: identity(socket.cookies.get('rlt_session'))
    except HTTPException: await socket.close(code=1008); return
    await socket.accept()
    try:
        while True:
            identity(socket.cookies.get('rlt_session'))
            await socket.send_json(snapshot())
            await asyncio.sleep(1)
    except (WebSocketDisconnect,RuntimeError,HTTPException):
        try: await socket.close(code=1008)
        except RuntimeError: pass
