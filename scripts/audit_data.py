import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from volforge.data import audit_dataset
print(json.dumps(audit_dataset(ROOT/'data'),indent=2))
