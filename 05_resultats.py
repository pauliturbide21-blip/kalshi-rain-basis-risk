"""05_resultats.py : consolide resultats_h1/h2/h3 et les tables en un seul resultats.json horodate."""
import os, json, glob
from datetime import datetime, timezone
import pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__))
out={"horodatage":datetime.now(timezone.utc).isoformat(),"preregistration":"00_PREREGISTRATION.md","hypotheses":{}}
for h in ["h1","h2","h3"]:
    fn=f"{HERE}/data/resultats_{h}.json"
    if os.path.exists(fn): out["hypotheses"][h]=json.load(open(fn))
out["tables"]={}
for fn in sorted(glob.glob(f"{HERE}/tables/*.csv")):
    out["tables"][os.path.basename(fn)]=pd.read_csv(fn).to_dict("records")
json.dump(out,open(f"{HERE}/resultats.json","w"),indent=1,default=str)
print("resultats.json :",len(out["tables"]),"tables,",list(out["hypotheses"].keys()))
