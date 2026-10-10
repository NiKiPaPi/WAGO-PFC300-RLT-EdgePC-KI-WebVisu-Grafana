"""Generate local secrets once. Never print their values."""
import secrets
from pathlib import Path
p=Path('.env')
if p.exists(): raise SystemExit('.env existiert; keine Überschreibung')
template=Path('.env.example').read_text()
keys=['INITIAL_VIEWER_PASSWORD','INITIAL_OPERATOR_PASSWORD','INITIAL_ADMINISTRATOR_PASSWORD','MQTT_API_PASSWORD','MQTT_SIM_PASSWORD','INFLUX_PASSWORD','INFLUX_TOKEN','GRAFANA_PASSWORD']
for key in keys: template=template.replace(key+'=',key+'='+secrets.token_urlsafe(24),1)
p.write_text(template,encoding='utf-8')
print('.env erstellt. Zugangsdaten lokal in .env lesen; nicht weitergeben oder committen.')
