import json, re, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
for d in ["raw","metadata","processed","qa","splits"]: (DATA/d).mkdir(parents=True,exist_ok=True)
IGNORE={".git",".venv","venv","node_modules","vendor","dist","build","target","out","__pycache__"}
EXT={".py":"python",".java":"java"}
MAX_BYTES=1_000_000
SECRET=[re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*[^,\s]{8,}"),
re.compile(r"\\bgh[pousr]_[A-Za-z0-9]{20,}\\b"),re.compile(r"\\bAKIA[0-9A-Z]{16}\\b")]
def sid(*x): return hashlib.sha256("::".join(map(str,x)).encode()).hexdigest()[:20]
def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+"\n")
def read(path):
    if not path.exists():return []
    with path.open(encoding="utf-8") as f:return [json.loads(x) for x in f if x.strip()]
def secret(s):return any(p.search(s) for p in SECRET)
def skip(p):
    return any(x.lower() in IGNORE for x in p.parts) or p.suffix.lower() not in EXT or (p.stat().st_size>MAX_BYTES)
