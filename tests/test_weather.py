import asyncio
import datetime as dt
import importlib
import json
import time
import pytest
from fastapi import HTTPException

@pytest.fixture
def weather(tmp_path,monkeypatch):
    monkeypatch.setenv('WEATHER_DB_PATH',str(tmp_path/'weather.sqlite'))
    import backend.weather as w
    w=importlib.reload(w)
    yield w
    w.db.close()

def raw(start=1792886400,count=168):
    return {'hourly_units':{'temperature_2m':'°C','relative_humidity_2m':'%'},'hourly':{'time':[start+i*3600 for i in range(count)],'temperature_2m':[10.]*count,'relative_humidity_2m':[60.]*count}}

LOC={'id':1,'name':'Berlin','region':'Berlin','country':'Deutschland','latitude':52.52,'longitude':13.41,'timezone':'Europe/Berlin'}

def test_partial_and_invalid_units(weather):
    r=raw();r['hourly']['relative_humidity_2m'][0]=None
    p=weather.normalize(r,LOC);assert p['quality']=='partial' and p['hourly'][0]['humidity'] is None
    assert p['daily'][0]['humidity_mean']==60
    r['hourly_units']['temperature_2m']='°F'
    with pytest.raises(ValueError):weather.normalize(r,LOC)

def test_dst_grouping_and_utc(weather):
    p=weather.normalize(raw(int(dt.datetime(2026,10,24,tzinfo=dt.timezone.utc).timestamp())),LOC)
    assert all(dt.datetime.fromisoformat(x['time']).utcoffset()==dt.timedelta(0) for x in p['hourly'])
    assert any(d['hours']==25 for d in p['daily'])

def test_location_selection_and_history_versions(weather):
    async def run():
        with pytest.raises(HTTPException): await weather.choose(weather.Choice(id=999))
        weather.db.execute('INSERT INTO searches VALUES(?,?,?)',(1,json.dumps(LOC),time.time()+100));weather.db.commit()
        await weather.choose(weather.Choice(id=1)); assert weather.location()==LOC
        for acquired in [1000,2000]:
            p=weather.normalize(raw(),LOC,acquired)
            weather.db.execute('INSERT INTO versions(id,location_id,acquired,payload) VALUES(?,?,?,?)',(p['version'],'1',acquired,json.dumps(p)))
        weather.db.commit()
        p=await weather.history(1,'1970-01-01T00:25:00+00:00');assert dt.datetime.fromisoformat(p['acquired_at']).timestamp()==1000
        assert (await weather.forecast())['status']=='Daten veraltet'
        assert weather.db.execute('SELECT COUNT(*) FROM versions').fetchone()[0]==2
    asyncio.run(run())

def test_outage_retains_cache(weather,monkeypatch):
    p=weather.normalize(raw(),LOC)
    weather.db.execute('INSERT INTO config VALUES(1,?)',(json.dumps(LOC),));weather.db.execute('INSERT INTO versions(id,location_id,acquired,payload) VALUES(?,?,?,?)',(p['version'],'1',time.time(),json.dumps(p)));weather.db.commit()
    weather.last_error='Wetterdienst nicht erreichbar'
    result=asyncio.run(weather.forecast());assert result['forecast']['version']==p['version'] and result['error']

def test_retry_and_limit(weather,monkeypatch):
    import httpx
    calls=[]
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,params):calls.append(url);return httpx.Response(429,request=httpx.Request('GET',url))
    monkeypatch.setattr(weather.httpx,'AsyncClient',Client)
    with pytest.raises(HTTPException):asyncio.run(weather.external('https://api.open-meteo.com/v1/forecast',{}))
    assert len(calls)==1

def test_timeout_retries_bounded(weather,monkeypatch):
    import httpx
    calls=[]
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,params):calls.append(url);raise httpx.ReadTimeout('test')
    async def sleep(seconds):pass
    monkeypatch.setattr(weather.httpx,'AsyncClient',Client);monkeypatch.setattr(weather.asyncio,'sleep',sleep)
    with pytest.raises(HTTPException):asyncio.run(weather.external('https://api.open-meteo.com/v1/forecast',{}))
    assert len(calls)==3

def test_archive_creates_missing_bucket_and_keeps_version(weather,monkeypatch):
    import httpx
    p=weather.normalize(raw(),LOC)
    weather.db.execute('INSERT INTO versions(id,location_id,acquired,payload) VALUES(?,?,?,?)',(p['version'],'1',time.time(),json.dumps(p)));weather.db.commit()
    writes=[]
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,**kwargs):return httpx.Response(200,json={'orgs':[{'id':'org'}]},request=httpx.Request('GET',url)) if url.endswith('/orgs') else httpx.Response(404,request=httpx.Request('GET',url))
        async def post(self,url,**kwargs):
            writes.append((url,kwargs));return httpx.Response(204,request=httpx.Request('POST',url))
    monkeypatch.setattr(weather.httpx,'AsyncClient',Client)
    asyncio.run(weather.archive())
    assert weather.db.execute('SELECT archived FROM versions').fetchone()[0]==1
    line=writes[-1][1]['content'];assert len(line.splitlines())==168 and 'version='+p['version'] in line
    assert writes[0][0].endswith('/buckets')
