import datetime as dt
import hashlib
import importlib
import json
import time
import uuid
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from simulation.model import Model
from contracts.core import PREFIX,VERSION,utc

@pytest.fixture
def api(tmp_path,monkeypatch):
    monkeypatch.setenv('DB_PATH',str(tmp_path/'db.sqlite'))
    for role in ['VIEWER','OPERATOR','ADMINISTRATOR']:monkeypatch.setenv('INITIAL_'+role+'_PASSWORD','test-only-pass-12345')
    import backend.app as mod
    mod=importlib.reload(mod);mod.bootstrap()
    mod.state.update(snapshot=Model().snapshot(),connected=True,online=True,history_ok=False)
    monkeypatch.setattr(mod.client,'is_connected',lambda:True)
    sent=[]
    monkeypatch.setattr(mod.client,'publish',lambda topic,payload,**kw: (sent.append((topic,json.loads(payload),kw)) or SimpleNamespace(rc=0)))
    client=TestClient(mod.app)
    yield client,mod,sent
    mod.db.close()
def login(client,role='operator'):
    assert client.post('/api/login',json={'name':role,'password':'test-only-pass-12345'}).status_code==200

def test_weather_permissions_and_audit(api,monkeypatch):
    c,m,s=api
    assert c.get('/api/weather').status_code==401
    login(c,'viewer')
    assert c.put('/api/weather/location',json={'id':1}).status_code==403
    assert c.get('/api/weather/search?q=Berlin').status_code==403
    async def proxy(path,method='GET',params=None,body=None):return {'location':None} if path=='/forecast' else {'id':1,'name':'Berlin'}
    monkeypatch.setattr(m,'weather_request',proxy)
    assert c.get('/api/weather').status_code==200
    login(c)
    assert c.put('/api/weather/location',json={'id':1}).status_code==200
    assert c.get('/api/audit').json()[0]['target']=='weather.location'
    assert not s
def body(**extra):return dict(tag='temperature.requested',value=22,expected=20,command_id=str(uuid.uuid4()))|extra
def test_anonymous_and_viewer_write_denied(api):
    c,m,s=api;assert c.get('/api/state').status_code==401
    login(c,'viewer');assert c.post('/api/commands',json=body()).status_code==403
    assert not s
def test_identity_audit_and_idempotent(api):
    c,m,s=api;login(c);b=body()
    assert c.post('/api/commands',json=b).status_code==202
    assert c.post('/api/commands',json=b).status_code==202
    assert len(s)==1 and s[0][1]['user']=='operator' and not s[0][2]['retain']
    result=Model().command(s[0][1])
    msg=SimpleNamespace(topic=PREFIX+'/results',payload=json.dumps(result).encode())
    m.on_message(None,None,msg);m.on_message(None,None,msg)
    rows=c.get('/api/audit').json()
    assert len(rows)==2 and rows[0]['result'].startswith('executed')
    assert rows[0]['command_id']==b['command_id'] and rows[0]['old']=='20.0' and rows[0]['new']=='22.0'
def test_invalid_conflicting_stale(api):
    c,m,s=api;login(c)
    assert c.post('/api/commands',json=body(value=50)).status_code==422
    assert c.post('/api/commands',json=body(expected=19)).status_code==409
    assert c.post('/api/commands',json=body()).status_code==202
    assert c.post('/api/commands',json=body()).status_code==409
    m.state['connected']=False
    assert not c.get('/api/state').json()['fresh']
def test_no_client_role_or_identity(api):
    c,m,s=api;login(c)
    assert c.post('/api/commands',json=body(user='admin')).status_code==422
    assert c.put('/api/settings',json={'timezone':'UTC','stale_seconds':5,'history_interval_seconds':2}).status_code==403
def test_cross_origin(api):
    c,m,s=api;login(c)
    assert c.post('/api/commands',json=body(),headers={'Origin':'http://foreign.invalid'}).status_code==403
def test_admin_revokes_existing_sessions(api):
    c,m,s=api;login(c,'administrator')
    assert c.put('/api/users',json={'name':'viewer','password':'replacement-pass-123','role':'viewer','enabled':False}).status_code==200
    assert 'password' not in str(c.get('/api/users').json())
def test_expired_result_is_timeout(api):
    c,m,s=api;login(c);b=body();c.post('/api/commands',json=b)
    m.db.execute("UPDATE commands SET expires='2020-01-01T00:00:00+00:00' WHERE id=?",(b['command_id'],));m.db.commit()
    r=dict(schema_version=VERSION,command_id=b['command_id'],tag=b['tag'],status='executed',reason='',timestamp=utc())
    m.on_message(None,None,SimpleNamespace(topic=PREFIX+'/results',payload=json.dumps(r).encode()))
    assert c.get('/api/state').json()['commands'][0]['status']=='timeout'
def test_restart_marks_timeout_without_replay(api):
    c,m,s=api;login(c);c.post('/api/commands',json=body());m.bootstrap()
    assert c.get('/api/state').json()['commands'][0]['status']=='timeout' and len(s)==1
def test_websocket_requires_auth_and_origin(api):
    c,m,s=api
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect('/api/ws',headers={'Origin':'http://localhost:8080'}):pass
    login(c)
    with c.websocket_connect('/api/ws',headers={'Origin':'http://localhost:8080'}) as ws:
        data=ws.receive_json();assert data['snapshot']['values']['temperature.accepted']==20
