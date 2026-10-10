"""Time dependent model; no physical I/O. Parameters are NOT real plant specifications."""
import json
import time
from pathlib import Path
from contracts.core import TAGS, VERSION, utc, age, validate, schema_validate

DEFAULTS = dict(outdoor=8., room=21., initial_supply=20., recovery_efficiency=.7,
               thermal_tau=45., actuator_rate=20., fan_rate=20., kp=8., ki=.12,
               nominal_pressure=600., filter_dp=90.)

class Model:
    def __init__(self, params=None, journal=None):
        self.p = DEFAULTS | (params or {})
        self.journal = Path(journal) if journal else None
        saved = json.loads(self.journal.read_text()) if self.journal and self.journal.exists() else {}
        self.seen = saved.get('seen',{})
        self.v = {k:0. for k,t in TAGS.items() if t['type']=='number'}
        self.v.update({'temperature.accepted':20.,'temperature.supply':self.p['initial_supply'],
                       'temperature.outdoor':self.p['outdoor'],'temperature.extract':self.p['room'],
                       'mode.accepted':'off','plant.state':'OFF','interlock.active':False})
        self.requests = {k:0. for k,t in TAGS.items() if t['writable'] and t['type']=='number'}
        self.requests.update({'fan.supply.request':60.,'fan.extract.request':60.,
                             'fan.supply.enable':True,'fan.extract.enable':True,
                             'actuator.outdoor.request':100.,'actuator.exhaust.request':100.,
                             'actuator.recovery.request':70.})
        self.integral = 0.
        self.alarm = {'schema_version':VERSION,'id':'SIM_INTERLOCK','active':False,'acknowledged':False,'returned':False,'timestamp':utc()}
        self.sequence=0
        if saved:
            self.v.update(saved['values']); self.requests.update(saved['requests'])
            self.alarm=saved['alarm'] | {'schema_version':VERSION}; self.integral=saved['integral']

    def command(self,c):
        schema_validate('command',c)
        cid=c['command_id']
        if cid in self.seen:
            return self.seen[cid]
        def result(status,reason=''):
            r={'schema_version':VERSION,'command_id':cid,'tag':c['tag'],'status':status,'reason':reason,'timestamp':utc()}
            self.seen[cid]=r
            if self.journal:
                self.journal.parent.mkdir(parents=True,exist_ok=True)
                tmp=self.journal.with_suffix('.tmp')
                tmp.write_text(json.dumps(dict(seen=self.seen,values=self.v,requests=self.requests,alarm=self.alarm,integral=self.integral)))
                tmp.replace(self.journal)
            return r
        try:
            if age(c['expires_at'])>=0 or age(c['created_at'])< -5:
                raise ValueError('Befehl abgelaufen oder Zeit ungültig')
            validate(c['tag'],c['value'])
            if c['expected'] != self.current(c['tag']):
                raise ValueError('Konflikt: Ausgangswert wurde geändert')
            tag,value=c['tag'],c['value']
            if self.v['interlock.active'] and tag not in ['fault.inject','alarm.ack'] and not (tag=='mode.requested' and value=='off'):
                raise ValueError('Simulierte Schutzverriegelung aktiv')
            if tag.startswith(('fan.','actuator.')) and self.v['mode.accepted']!='manual':
                raise ValueError('Einzelbedienung erfordert Handbetrieb')
            if tag in ['actuator.heat.request','actuator.cool.request'] and value>0:
                other='actuator.cool.request' if 'heat' in tag else 'actuator.heat.request'
                if self.requests[other]>0:
                    raise ValueError('Gleichzeitiges Heizen und Kühlen gesperrt')
            if tag=='temperature.requested': self.v['temperature.accepted']=value
            elif tag=='mode.requested': self.v['mode.accepted']=value
            elif tag=='fault.inject':
                self.v['interlock.active']=value
                self.alarm.update(active=value,returned=not value,acknowledged=False if value else self.alarm['acknowledged'],timestamp=utc())
            elif tag=='alarm.ack': self.alarm.update(acknowledged=True,timestamp=utc())
            else: self.requests[tag]=value
            return result('executed','Sollwert/Logik übernommen; Zielzustand über Telemetrie prüfen')
        except ValueError as e:
            return result('rejected',str(e))

    def current(self,tag):
        return {'temperature.requested':self.v['temperature.accepted'],'mode.requested':self.v['mode.accepted'],
                'fault.inject':self.v['interlock.active'],'alarm.ack':self.alarm['acknowledged']}.get(tag,self.requests.get(tag))

    def step(self,dt):
        dt=max(0.,min(dt,2.))
        mode=self.v['mode.accepted']; locked=self.v['interlock.active']
        run=mode!='off' and not locked
        for d in ['outdoor','exhaust']:
            target=(100. if mode=='auto' else self.requests[f'actuator.{d}.request']) if run else 0.
            # Abfahren: Ventilatoren zuerst auslaufen, Klappen danach schließen.
            if not run and max(self.v['fan.supply.feedback'],self.v['fan.extract.feedback'])>1: target=100.
            self.move(f'actuator.{d}',target,dt,self.p['actuator_rate'])
        ready=min(self.v['actuator.outdoor.feedback'],self.v['actuator.exhaust.feedback'])>=90
        for side in ['supply','extract']:
            target=(60 if mode=='auto' else self.requests[f'fan.{side}.request']) if run and ready and self.requests[f'fan.{side}.enable'] else 0
            self.move(f'fan.{side}',target,dt,self.p['fan_rate'])
            speed=self.v[f'fan.{side}.feedback']/100
            self.v[f'pressure.{side}']=self.p['nominal_pressure']*speed**2
            self.v[f'filter.{side}.dp']=self.p['filter_dp']*speed**2
        flowing=min(self.v['fan.supply.feedback'],self.v['fan.extract.feedback'])>5
        error=self.v['temperature.accepted']-self.v['temperature.supply']
        if mode=='auto' and run and flowing:
            self.integral=max(-100,min(100,self.integral+error*self.p['ki']*dt))
            output=max(-100,min(100,self.p['kp']*error+self.integral))
            heat=max(0,output); cool=max(0,-output)
        elif mode=='manual' and run and flowing:
            heat=self.requests['actuator.heat.request']; cool=self.requests['actuator.cool.request']
        else:
            heat=cool=0.; self.integral=0.
        # Break-before-make, including residual actuator feedback.
        if self.v['actuator.cool.feedback']>.1: heat=0.
        if self.v['actuator.heat.feedback']>.1: cool=0.
        self.move('actuator.heat',heat,dt,self.p['actuator_rate'])
        self.move('actuator.cool',cool,dt,self.p['actuator_rate'])
        recovery=(100. if mode=='auto' else self.requests['actuator.recovery.request']) if run else 0.
        self.move('actuator.recovery',recovery,dt,self.p['actuator_rate'])
        recovered=(self.p['room']-self.p['outdoor'])*self.p['recovery_efficiency']*self.v['actuator.recovery.feedback']/100
        target=self.p['outdoor']+recovered+18*self.v['actuator.heat.feedback']/100-12*self.v['actuator.cool.feedback']/100 if flowing else self.p['room']
        self.v['temperature.supply']+=(target-self.v['temperature.supply'])*dt/self.p['thermal_tau']
        self.v['temperature.exhaust']=self.p['room']-recovered
        self.v['plant.state']='LOCKED' if locked else ('RUNNING' if run and ready and flowing else 'STARTING' if run else 'STOPPING' if max(self.v['fan.supply.feedback'],self.v['fan.extract.feedback'])>1 else 'OFF')
        self.sequence+=1
        return self.snapshot()

    def move(self,base,target,dt,rate):
        self.v[base+'.command']=target
        k=base+'.feedback'; delta=target-self.v[k]
        self.v[k]+=max(-rate*dt,min(rate*dt,delta))

    def snapshot(self):
        return {'schema_version':VERSION,'timestamp':utc(),'sequence':self.sequence,'quality':'good',
                'values':self.v | self.requests | {'temperature.requested':self.v['temperature.accepted'],'mode.requested':self.v['mode.accepted'],'fault.inject':self.v['interlock.active'],'alarm.ack':self.alarm['acknowledged']}}
