import asyncio
from types import SimpleNamespace
from tests.test_api import body,login

# Reuse only the existing fixture, no application semantics are mocked here.
from tests.test_api import api

def test_missing_ack_times_out_without_success(api):
    c,m,s=api;login(c);command=body();c.post('/api/commands',json=command)
    m.db.execute("UPDATE commands SET expires='2020-01-01T00:00:00+00:00' WHERE id=?",(command['command_id'],));m.db.commit()
    m.state['connected']=False
    async def tick():
        try:await asyncio.wait_for(m.background(),timeout=2)
        except asyncio.TimeoutError:pass
    asyncio.run(tick())
    state=c.get('/api/state').json()
    assert state['commands'][0]['status']=='timeout'
    assert len(s)==1 and s[0][2]['qos']==0 and not s[0][2]['retain']
    assert c.get('/api/audit').json()[0]['result']=='timeout'
