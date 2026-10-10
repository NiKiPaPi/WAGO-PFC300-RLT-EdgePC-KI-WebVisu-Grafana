import datetime as dt
import json
import uuid
import pytest
from contracts.core import VERSION, TAGS, utc, schema_validate, validate
from simulation.model import Model

def cmd(m,tag,value,**extra):
    c=dict(schema_version=VERSION,command_id=str(uuid.uuid4()),tag=tag,value=value,expected=m.current(tag),user='operator',created_at=utc(),expires_at=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=10)).isoformat())
    return c|extra
def apply(m,tag,value): return m.command(cmd(m,tag,value))

def test_contract_snapshot_complete():
    m=Model(); schema_validate('telemetry',m.step(1))
    assert set(m.snapshot()['values'])==set(TAGS)
@pytest.mark.parametrize('value',[31,15,float('nan'),float('inf'),True,'22'])
def test_invalid_values(value):
    with pytest.raises(ValueError): validate('temperature.requested',value)
def test_unknown_or_readonly():
    with pytest.raises(ValueError): validate('temperature.supply',22)
def test_dynamic_step_not_assignment():
    m=Model(); apply(m,'mode.requested','auto')
    for _ in range(600): m.step(1)
    old=m.v['temperature.supply']
    assert apply(m,'temperature.requested',22)['status']=='executed'
    assert m.v['temperature.supply']==old
    for _ in range(600): m.step(1)
    assert m.v['temperature.supply']>old+1
    assert abs(m.v['temperature.supply']-22)<.5
def test_sequence_dampers_before_fans():
    m=Model();apply(m,'mode.requested','auto')
    m.step(1)
    assert m.v['fan.supply.feedback']==0
    for _ in range(15): m.step(1)
    assert m.v['plant.state']=='RUNNING'
    apply(m,'mode.requested','off');m.step(1)
    assert m.v['actuator.outdoor.feedback']==100
    for _ in range(15):m.step(1)
    assert m.v['plant.state']=='OFF' and m.v['actuator.outdoor.feedback']==0
def test_manual_interlock_alarm_lifecycle():
    m=Model();apply(m,'mode.requested','manual')
    for _ in range(15):m.step(1)
    apply(m,'fault.inject',True)
    assert apply(m,'fan.supply.request',100)['status']=='rejected'
    apply(m,'alarm.ack',True)
    assert m.alarm['active'] and m.alarm['acknowledged']
    for _ in range(15):m.step(1)
    assert m.v['fan.supply.feedback']==0
    apply(m,'fault.inject',False)
    assert not m.alarm['active'] and m.alarm['returned'] and m.alarm['acknowledged']
def test_heat_cool_mutex():
    m=Model();apply(m,'mode.requested','manual')
    assert apply(m,'actuator.heat.request',50)['status']=='executed'
    assert apply(m,'actuator.cool.request',50)['status']=='rejected'
    for _ in range(20):m.step(1)
    apply(m,'actuator.heat.request',0);apply(m,'actuator.cool.request',50)
    for _ in range(20):
        m.step(1);assert not (m.v['actuator.heat.feedback']>.1 and m.v['actuator.cool.feedback']>.1)
def test_duplicate_persists_restart(tmp_path):
    path=tmp_path/'journal.json';m=Model(journal=path);c=cmd(m,'temperature.requested',22)
    first=m.command(c)
    assert m.command(c)==first
    again=Model(journal=path)
    assert again.command(c)==first and again.v['temperature.accepted']==22
    assert len(again.seen)==1
def test_expired_and_conflict():
    m=Model()
    assert m.command(cmd(m,'temperature.requested',22,expires_at='2020-01-01T00:00:00+00:00'))['status']=='rejected'
    assert m.command(cmd(m,'temperature.requested',22,expected=21))['status']=='rejected'
def test_manual_required():
    m=Model();assert apply(m,'fan.supply.request',50)['status']=='rejected'
def test_wrong_schema_rejected():
    m=Model()
    with pytest.raises(Exception): m.command(cmd(m,'temperature.requested',22,schema_version='9'))
