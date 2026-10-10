import json
from pathlib import Path
from contracts.core import TAGS, VERSION
p=Path('contracts')
def save(name,value): (p/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
save('tags.json',{'schema_version':VERSION,'tags':TAGS})
base={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','additionalProperties':False}
stamp={'type':'string','format':'date-time','pattern':'(Z|\\+00:00)$'}
common={'schema_version':{'const':VERSION},'command_id':{'type':'string','format':'uuid'},'tag':{'enum':[k for k,v in TAGS.items() if v['writable']]}}
command=common|{'value':{'type':['number','string','boolean']},'expected':{'type':['number','string','boolean']},'user':{'type':'string','minLength':1},'created_at':stamp,'expires_at':stamp}
save('command.schema.json',base|{'properties':command,'required':list(command)})
result=common|{'status':{'enum':['received','accepted','rejected','executed']},'reason':{'type':'string'},'timestamp':stamp}
save('result.schema.json',base|{'properties':result,'required':list(result)})
props={}
for k,v in TAGS.items():
    props[k]={'type':v['type']}
    if v['minimum'] is not None: props[k].update(minimum=v['minimum'],maximum=v['maximum'])
    if v['choices']: props[k]['enum']=v['choices']
tele={'schema_version':{'const':VERSION},'timestamp':stamp,'sequence':{'type':'integer','minimum':0},'quality':{'enum':['good','bad']},'values':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}}
save('telemetry.schema.json',base|{'properties':tele,'required':list(tele)})
status={'schema_version':{'const':VERSION},'online':{'type':'boolean'},'timestamp':stamp}
save('status.schema.json',base|{'properties':status,'required':list(status)})
alarm={'schema_version':{'const':VERSION},'id':{'const':'SIM_INTERLOCK'},'active':{'type':'boolean'},'acknowledged':{'type':'boolean'},'returned':{'type':'boolean'},'timestamp':stamp}
save('alarm.schema.json',base|{'properties':alarm,'required':list(alarm)})
