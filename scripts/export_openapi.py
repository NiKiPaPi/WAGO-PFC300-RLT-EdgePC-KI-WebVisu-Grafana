import json
import os
from pathlib import Path
os.environ.setdefault('DB_PATH','data/openapi.sqlite')
from backend.app import app
Path('docs/openapi.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2),encoding='utf-8')
