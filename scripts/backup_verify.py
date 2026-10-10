"""Exercise backup/restore scripts with separate recovery volumes; retain production backup."""
import datetime as dt
import json
import os
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
docker=os.getenv('RLT_DOCKER','docker')
env=os.environ.copy();env['PATH']=str(Path(docker).parent)+os.pathsep+env['PATH']
prefix='rlt-simulation-restore-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')
volumes=['backend_data','simulation_data','broker_config','broker_data','influx_data','influx_config','grafana_data']
test_container=prefix+'-influx'
evidence={'timestamp':dt.datetime.now(dt.timezone.utc).isoformat(),'checks':[],'mode':'real stopped-volume backup and separate-volume recovery'}
config=dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
tokenfile=ROOT/'.install'/f'{prefix}.env'
def run(args,timeout=180):
    p=subprocess.run(args,env=env,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError('Operation failed: '+str(args[0])+' / '+p.stderr[:300])
    return p.stdout
def d(*args):return run([docker,*args])
def check(name,ok,detail=None):
    evidence['checks'].append({'name':name,'passed':bool(ok),'detail':detail})
    if not ok:raise AssertionError(name)
def query(service,flux):
    if service=='source':return d('compose','exec','-T','influxdb','sh','-c','INFLUX_TOKEN="$DOCKER_INFLUXDB_INIT_ADMIN_TOKEN" influx query --raw --org rlt "$1"','_',flux)
    return d('exec',service,'influx','query','--raw','--org','rlt',flux)
try:
    end=dt.datetime.now(dt.timezone.utc).isoformat();start=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=10)).isoformat()
    flux=f'from(bucket: "rlt") |> range(start: time(v: "{start}"), stop: time(v: "{end}")) |> filter(fn:(r)=>r._measurement == "rlt" and r.tag == "temperature.supply")'
    run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File','scripts/backup.ps1'])
    backup=max((ROOT/'backups').glob('rlt-*'),key=lambda p:p.stat().st_mtime)
    evidence['backup_directory']=str(backup)
    check('seven persistent volumes archived',all((backup/(v+'.tar.gz')).stat().st_size>0 for v in volumes))
    run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File','scripts/restore.ps1','-BackupDirectory',str(backup),'-VolumePrefix',prefix,'-NoStart'])
    check('restore script completes into isolated volumes',True)
    sql="import sqlite3,json;c=sqlite3.connect('file:/data/backend.sqlite?mode=ro',uri=True);print(json.dumps({t:c.execute('select count(*) from '+t).fetchone()[0] for t in ['users','audit','commands','settings']}))"
    source=json.loads(d('compose','exec','-T','backend','python','-c',sql))
    # A stopped backup has a checkpointed WAL-mode DB without -wal/-shm. Read-only
    # verification needs immutable=1 to avoid attempting to create these sidecars.
    restored_sql=sql.replace('mode=ro','mode=ro&immutable=1')
    restored=json.loads(d('run','--rm','--network','none','--mount',f'type=volume,src={prefix}_backend_data,dst=/data,readonly','rlt-simulation-backend:1.0.1','python','-c',restored_sql))
    check('restored users/audit/commands/settings match source',source==restored,source)
    journal="import json;x=json.load(open('/data/commands.json'));print(json.dumps({'commands':len(x['seen']),'accepted_setpoint':x['values']['temperature.accepted']}))"
    orig=json.loads(d('compose','exec','-T','simulation','python','-c',journal))
    copy=json.loads(d('run','--rm','--network','none','--mount',f'type=volume,src={prefix}_simulation_data,dst=/data,readonly','rlt-simulation-simulation:1.0.1','python','-c',journal))
    check('restored accepted setpoint and idempotency journal match',orig==copy,copy)
    tokenfile.write_text('INFLUX_TOKEN='+config['INFLUX_TOKEN']+'\n',encoding='utf-8')
    d('run','-d','--name',test_container,'--network','none','--env-file',str(tokenfile),
      '--mount',f'type=volume,src={prefix}_influx_data,dst=/var/lib/influxdb2',
      '--mount',f'type=volume,src={prefix}_influx_config,dst=/etc/influxdb2','influxdb:2.7.11')
    for _ in range(100):
        try:d('exec',test_container,'influx','ping');break
        except RuntimeError:time.sleep(.5)
    else:raise AssertionError('Restored Influx not ready')
    for _ in range(100):
        try:before=query('source',flux);break
        except RuntimeError:time.sleep(.5)
    else:raise AssertionError('Source Influx not ready')
    after=query(test_container,flux)
    check('recovered exact Influx history matches source',before==after and 'temperature.supply' in after,{'start':start,'stop':end,'bytes':len(after)})
    gf="import json;x=json.load(open('/var/lib/grafana/dashboards/rlt.json'));print(x['uid'])"
    # Persistent Grafana DB is present; provisioned dashboard source remains a read-only project mount.
    recovered_files=d('run','--rm','--network','none','--mount',f'type=volume,src={prefix}_grafana_data,dst=/verify,readonly','alpine:3.21.3','test','-s','/verify/grafana.db')
    check('Grafana persistent database recovered',True)
finally:
    subprocess.run([docker,'rm','-f',test_container],capture_output=True,env=env)
    for volume in volumes:subprocess.run([docker,'volume','rm',prefix+'_'+volume],capture_output=True,env=env)
    if tokenfile.exists():tokenfile.unlink()
    (ROOT/'docs'/'backup-restore-results.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(evidence['checks']),'passed':all(x['passed'] for x in evidence['checks'])}))
