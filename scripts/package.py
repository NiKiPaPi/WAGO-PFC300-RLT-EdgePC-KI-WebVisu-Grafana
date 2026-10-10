"""Create source delivery, excluding secrets, installed dependencies and runtime data."""
import hashlib
import argparse
import json
import zipfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--version',default='1.0.1');args=parser.parse_args()
if not all(c.isdigit() or c=='.' for c in args.version):raise SystemExit('Invalid release version')
dirs=['backend','contracts','docker','docs','frontend','grafana','influxdb','mqtt','plc','scripts','simulation','tests']
files=[]
for directory in dirs:
    for p in (root/directory).rglob('*'):
        if p.is_file() and not any(x in p.parts for x in ['node_modules','dist','__pycache__']):files.append(p)
for name in ['README.md','.env.example','.gitignore','.dockerignore','compose.yaml','requirements.in','requirements.lock','requirements-test.in','requirements-test.lock']:
    files.append(root/name)
files=sorted(set(files))
manifest=[{'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files if p.name!='delivery-manifest.json']
manifest_file=root/'docs'/'delivery-manifest.json';manifest_file.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
if manifest_file not in files:files.append(manifest_file)
target=root/'release'/f'rlt-simulation-{args.version}.zip';target.parent.mkdir(exist_ok=True)
if target.exists():raise SystemExit('Release already exists; choose a new version to preserve the previous delivery')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.relative_to(root))
print(f'Delivery: {target}; {len(files)} files; {target.stat().st_size} bytes; no .env or runtime data')
