"""Single authoritative tag catalog. All ranges below are simulation assumptions."""
import datetime as dt
import json
import math
import os
from pathlib import Path

VERSION = '1.0'
PREFIX = 'rlt/simulation/v1'
if os.getenv('RUN_MODE', 'simulation') != 'simulation':
    raise RuntimeError('Realbetrieb ist nicht implementiert und ausdrücklich gesperrt')

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def age(timestamp):
    value = dt.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('UTC timestamp required')
    return (dt.datetime.now(dt.timezone.utc) - value).total_seconds()

def tag(label, component, kind='number', unit='', minimum=None, maximum=None, write=False, choices=None):
    return dict(label=label, component=component, type=kind, unit=unit, minimum=minimum,
                maximum=maximum, writable=write, roles=['operator','administrator'] if write else [],
                choices=choices, direction='command' if write else 'feedback',
                quality='good/stale/bad', timestamp='UTC ISO 8601',
                mqtt=PREFIX + ('/commands' if write else '/telemetry'), history=not write,
                measurement='rlt' if kind=='number' else 'rlt_state', field='value',
                range_basis='Simulationsannahme; reale Werte TBD – technische Klärung erforderlich')

TAGS = {
 'temperature.requested': tag('Zulufttemperatur angefordert', 'Zuluft', unit='°C', minimum=16, maximum=30, write=True),
 'temperature.accepted': tag('Zulufttemperatur akzeptiert', 'Zuluft', unit='°C', minimum=16, maximum=30),
 'temperature.supply': tag('Zulufttemperatur Ist', 'Zuluft', unit='°C'),
 'temperature.outdoor': tag('Außentemperatur', 'Außenluft', unit='°C'),
 'temperature.extract': tag('Ablufttemperatur', 'Abluft', unit='°C'),
 'temperature.exhaust': tag('Fortlufttemperatur', 'Fortluft', unit='°C'),
 'mode.requested': tag('Betriebsart angefordert', 'Anlage', 'string', write=True, choices=['auto','manual','off']),
 'mode.accepted': tag('Betriebsart akzeptiert', 'Anlage', 'string'),
 'plant.state': tag('Anlagenzustand', 'Anlage', 'string'),
 'alarm.ack': tag('Alarm quittieren', 'Anlage', 'boolean', write=True),
 'fault.inject': tag('Simulierte Verriegelung', 'Anlage', 'boolean', write=True),
 'interlock.active': tag('Simulierte Verriegelung aktiv', 'Anlage', 'boolean'),
}
for side, label in [('supply','Zuluft'),('extract','Abluft')]:
    TAGS[f'fan.{side}.request'] = tag(f'{label}ventilator Drehzahl angefordert',label,unit='%',minimum=0,maximum=100,write=True)
    TAGS[f'fan.{side}.enable'] = tag(f'{label}ventilator Freigabe angefordert',label,'boolean',write=True)
    TAGS[f'fan.{side}.command'] = tag(f'{label}ventilator Stellbefehl',label,unit='%')
    TAGS[f'fan.{side}.feedback'] = tag(f'{label}ventilator Rückmeldung',label,unit='%')
    TAGS[f'pressure.{side}'] = tag(f'{label}druck',label,unit='Pa')
    TAGS[f'filter.{side}.dp'] = tag(f'{label}filter Differenzdruck',label,unit='Pa')
for device,label in [('outdoor','Außenluftklappe'),('exhaust','Fortluftklappe'),('heat','Heizventil'),('cool','Kühlventil'),('recovery','Wärmerückgewinnung')]:
    for suffix in ['request','command','feedback']:
        TAGS[f'actuator.{device}.{suffix}'] = tag(f'{label} {suffix}',label,unit='%',minimum=0,maximum=100,write=suffix=='request')

def validate(tag_id, value):
    t = TAGS.get(tag_id)
    if not t or not t['writable']:
        raise ValueError('Tag ist nicht schreibbar')
    if t['type'] == 'number':
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):
            raise ValueError('Endliche Zahl erforderlich')
        if not t['minimum'] <= value <= t['maximum']:
            raise ValueError(f"Wertebereich {t['minimum']} bis {t['maximum']}")
    elif t['type'] == 'boolean' and type(value) is not bool:
        raise ValueError('Boolescher Wert erforderlich')
    elif t['type'] == 'string' and value not in t['choices']:
        raise ValueError('Ungültige Betriebsart')
    return value

def schema_validate(kind, payload):
    import jsonschema
    schema = json.loads((Path(__file__).parent / f'{kind}.schema.json').read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)

if __name__ == '__main__':
    (Path(__file__).parent/'tags.json').write_text(json.dumps({'schema_version':VERSION,'tags':TAGS},ensure_ascii=False,indent=2),encoding='utf-8')
