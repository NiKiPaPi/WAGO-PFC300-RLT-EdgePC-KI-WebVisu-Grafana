import json
import os
import threading
import time
from pathlib import Path
from contracts.core import PREFIX, VERSION, utc, schema_validate
from simulation.model import Model
import paho.mqtt.client as mqtt

model=Model(json.loads(os.getenv('SIM_PARAMETERS','{}')),os.getenv('SIM_JOURNAL','/data/commands.json'))
lock=threading.Lock()
client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='rlt-simulation')
client.username_pw_set(os.environ['MQTT_SIM_USER'],os.environ['MQTT_SIM_PASSWORD'])
client.will_set(PREFIX+'/status',json.dumps({'schema_version':VERSION,'online':False,'timestamp':utc()}),qos=1,retain=True)
def publish(topic,payload,retain=False): client.publish(PREFIX+'/'+topic,json.dumps(payload),qos=1,retain=retain)
def connect(c,u,f,reason,p):
    if reason==0:
        c.subscribe(PREFIX+'/commands',qos=1)
        publish('status',{'schema_version':VERSION,'online':True,'timestamp':utc()},True)
        Path(os.getenv('SIM_HEARTBEAT','/data/heartbeat')).write_text(utc())
def receive(c,u,msg):
    if msg.retain: return
    try:
        command=json.loads(msg.payload); schema_validate('command',command)
        with lock:
            publish('results',dict(schema_version=VERSION,command_id=command['command_id'],tag=command['tag'],status='received',reason='',timestamp=utc()))
            # Model validates before accepting. Execution here is the logic/setpoint transaction, not physical arrival.
            result=model.command(command)
            if result['status']=='executed': publish('results',result | {'status':'accepted','reason':'Validiert und angenommen'})
            publish('results',result)
            publish('telemetry',model.snapshot())
            publish('alarms',model.alarm)
    except (ValueError,KeyError,TypeError): pass
    except Exception as e: print('Invalid MQTT message:',type(e).__name__,flush=True)
client.on_connect=connect; client.on_message=receive
client.reconnect_delay_set(1,15)
client.connect_async(os.getenv('MQTT_HOST','mqtt'),int(os.getenv('MQTT_PORT','1883')),30); client.loop_start()
last=time.monotonic()
while True:
    time.sleep(1)
    now=time.monotonic()
    with lock:
        snapshot=model.step(now-last)
        publish('telemetry',snapshot); publish('alarms',model.alarm)
        publish('status',{'schema_version':VERSION,'online':True,'timestamp':utc()},True)
        Path(os.getenv('SIM_HEARTBEAT','/data/heartbeat')).write_text(utc())
    last=now
