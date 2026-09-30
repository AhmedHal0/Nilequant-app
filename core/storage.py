import json
from pathlib import Path
def load_json(path,default):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():return default
    try:return json.loads(p.read_text(encoding="utf8"))
    except:return default
def save_json(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf8")
