import datetime as dt
import json
import os
import subprocess
from pathlib import Path
docker=os.getenv('RLT_DOCKER','docker')
def run(*args):return subprocess.check_output([docker,*args],text=True)
engine=json.loads(run('info','--format','{"version":"{{.ServerVersion}}","os":"{{.OSType}}","architecture":"{{.Architecture}}"}'))
services=[]
for line in run('compose','ps','--format','json').splitlines():
    r=json.loads(line)
    services.append({k:r[k] for k in ['Name','Service','State','Health','Image','Ports']})
    services[-1]['image_id']=run('inspect',r['Name'],'--format','{{.Image}}').strip()
evidence={'timestamp':dt.datetime.now(dt.timezone.utc).isoformat(),'engine':engine,'services':services,'all_healthy':{x['Service'] for x in services}=={'mqtt','influxdb','simulation','backend','frontend','grafana','weather'} and all(x['Health']=='healthy' for x in services)}
Path('docs/container-state.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'engine':engine,'services':len(services),'all_healthy':evidence['all_healthy']}))
