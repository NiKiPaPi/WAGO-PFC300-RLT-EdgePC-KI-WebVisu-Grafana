import json
from pathlib import Path
from contracts.core import TAGS
query='''from(bucket: "rlt")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "rlt" and r._field == "value")
  |> filter(fn: (r) => r.tag == "TAG_ID" and r.tag =~ /^${tags:regex}$/)
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: true)
  |> yield(name: "mean")'''
overrides=[]
targets=[]
units={'°C':'celsius','%':'percent','Pa':'pressurepa'}
for k,t in TAGS.items():
    if t['type']=='number' and t['history']:
        ref='N'+str(len(targets))
        targets.append({'refId':ref,'query':query.replace('TAG_ID',k)})
        overrides.append({'matcher':{'id':'byFrameRefID','options':ref},'properties':[
            {'id':'displayName','value':t['label']},
            {'id':'unit','value':units.get(t['unit'],'none')},
            {'id':'custom.axisLabel','value':t['unit']},
            {'id':'custom.axisPlacement','value':'right' if t['unit']!='°C' else 'left'}]})
options=[{'text':t['label'],'value':k,'selected':k in ['temperature.supply','temperature.accepted','temperature.outdoor']} for k,t in TAGS.items() if t['history'] and t['type']=='number']
overrides.append({'matcher':{'id':'byType','options':'time'},'properties':[
    {'id':'unit','value':'dateTimeAsIso'},{'id':'displayName','value':'Zeit'},{'id':'custom.axisLabel','value':'Zeit'}]})
numeric={'id':1,'type':'timeseries','title':'Messwerte & akzeptierte Sollwerte · Datenlücken bleiben offen','gridPos':{'x':0,'y':0,'w':24,'h':13},
         'datasource':{'type':'influxdb','uid':'rlt-influx'},'targets':targets,
         'fieldConfig':{'defaults':{'custom':{'spanNulls':False,'axisPlacement':'auto'},'unit':'none'},'overrides':overrides},
         'options':{'legend':{'displayMode':'table','placement':'bottom','calcs':['lastNotNull','min','max']},'tooltip':{'mode':'multi'}}}
state_ids=['plant.state','mode.accepted','interlock.active']
state_query='''from(bucket: "rlt") |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
 |> filter(fn: (r) => r._measurement == "rlt_state" and r._field == "value")
 |> filter(fn: (r) => r.tag == "TAG_ID")
 |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: true)
'''
states={'id':2,'type':'state-timeline','title':'Anlagenzustand / Betriebsart / Verriegelung','gridPos':{'x':0,'y':13,'w':24,'h':7},
        'datasource':{'type':'influxdb','uid':'rlt-influx'},'targets':[{'refId':'S'+str(i),'query':state_query.replace('TAG_ID',k)} for i,k in enumerate(state_ids)],
        'fieldConfig':{'defaults':{'custom':{'spanNulls':False},'mappings':[{'type':'value','options':{
        'OFF':{'text':'Aus'},'RUNNING':{'text':'Betrieb'},'STARTING':{'text':'Anfahren'},'STOPPING':{'text':'Abfahren'},'LOCKED':{'text':'Verriegelt'},
        'auto':{'text':'Auto'},'manual':{'text':'Hand'},'off':{'text':'Aus'},'true':{'text':'Aktiv'},'false':{'text':'Normal'}}}]},
        'overrides':[{'matcher':{'id':'byFrameRefID','options':'S'+str(i)},'properties':[{'id':'displayName','value':TAGS[k]['label']}]} for i,k in enumerate(state_ids)]}}
dashboard={'uid':'rlt','title':'RLT · Simulationsanlage 01','schemaVersion':40,'version':1,'refresh':'5s','timezone':'browser',
           'time':{'from':'now-1h','to':'now'},'timepicker':{'refresh_intervals':['5s','10s','30s'],'time_options':['1h','6h','24h','7d']},
           'tags':['simulation'],'templating':{'list':[{'name':'tags','label':'Datenpunkte','type':'custom','multi':True,'includeAll':True,
           'query':','.join(t['text']+' : '+t['value'] for t in options),'options':options,
           'current':{'text':[x['text'] for x in options if x['selected']],'value':[x['value'] for x in options if x['selected']]}}]},'panels':[numeric,states]}
Path('grafana/dashboards').mkdir(parents=True,exist_ok=True)
Path('grafana/dashboards/rlt.json').write_text(json.dumps(dashboard,ensure_ascii=False,indent=2),encoding='utf-8')
