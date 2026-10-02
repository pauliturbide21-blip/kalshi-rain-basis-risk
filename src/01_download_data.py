"""Download the raw data: Kalshi daily rain markets (prices, settlements) and, from the Iowa Environmental Mesonet,
ASOS hourly rainfall at Central Park and NWS MOS forecasts. Files are cached in data/raw/.
Comments in the code are in French."""
import os, json, time, sys, requests
from datetime import datetime, timezone
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); RAW=f"{HERE}/data/raw"; os.makedirs(RAW,exist_ok=True)
K="https://api.elections.kalshi.com/trade-api/v2"
S=requests.Session(); S.headers["User-Agent"]="memoire-xhec-analyse/1.0"
LOG=open(f"{HERE}/data/collect.log","a")
def log(*a):
    m=" ".join(str(x) for x in a); print(m,flush=True); LOG.write(datetime.now(timezone.utc).isoformat()+" "+m+"\n"); LOG.flush()
def get(url,params=None,tries=5):
    for a in range(tries):
        try:
            r=S.get(url,params=params,timeout=60)
            if r.status_code==200: return r.json()
            if r.status_code==404: return None
            if r.status_code==429: time.sleep(3*(a+1)); continue
            log("http",r.status_code,url,str(params)[:120],r.text[:120])
        except Exception as e: log("exc",url,e)
        time.sleep(2*(a+1))
    return None
def cached(name,fn):
    p=f"{RAW}/{name}"
    if os.path.exists(p): return json.load(open(p))
    v=fn()
    if v is not None: json.dump(v,open(p,"w"))
    return v
def paged(url,params,key):
    out=[]; cur=None
    while True:
        p=dict(params);
        if cur: p["cursor"]=cur
        js=get(url,p)
        if not js: break
        out+=js.get(key,[]); cur=js.get("cursor")
        if not cur or not js.get(key): break
    return out

# ---------- 1. series
series=cached("series_climate.json",lambda: get(f"{K}/series",{"category":"Climate and Weather","include_volume":"true"}))
allser=series.get("series",[]) if series else []
rain=[s for s in allser if "rain" in (s.get("title","")+s.get("ticker","")).lower()]
log("series meteo",len(allser),"series rain",len(rain))
json.dump(rain,open(f"{RAW}/series_rain.json","w"),indent=1)
for s in rain: log("  ",s.get("ticker"),"|",s.get("title"),"|",s.get("frequency"))

# ---------- 2. marches : anciennes series par ville + serie multi-villes
TARGETS=["KXRAINNYC","KXRAINMIA","KXRAINCHI","KXRAIN"]
def markets_for(ser):
    hist=paged(f"{K}/historical/markets",{"series_ticker":ser,"limit":1000},"markets")
    live=paged(f"{K}/markets",{"series_ticker":ser,"limit":1000,"status":"settled"},"markets")
    seen={};
    for m in hist+live: seen[m["ticker"]]=m
    return list(seen.values())
markets={}
for ser in TARGETS:
    ms=cached(f"markets_{ser}.json",lambda ser=ser: markets_for(ser))
    markets[ser]=ms or []
    log("marches",ser,len(markets[ser]))
# evenements de la serie multi-villes (marches imbriques) pour completer
ev=cached("events_KXRAIN.json",lambda: paged(f"{K}/events",{"series_ticker":"KXRAIN","with_nested_markets":"true","limit":200},"events"))
log("events KXRAIN",len(ev or []))

# ---------- 3. chandeliers horaires
def iso_ts(s):
    try: return int(datetime.fromisoformat(s.replace("Z","+00:00")).timestamp())
    except Exception: return None
def candles(m,ser):
    t=m["ticker"]; o=iso_ts(m.get("open_time") or m.get("created_time") or ""); c=iso_ts(m.get("close_time") or m.get("expiration_time") or "")
    if not o or not c: return {"error":"no times"}
    p={"start_ts":o-86400,"end_ts":c+86400,"period_interval":60}
    js=get(f"{K}/historical/markets/{t}/candlesticks",p)
    if js is None or not js.get("candlesticks"):
        js2=get(f"{K}/series/{ser}/markets/{t}/candlesticks",p)
        if js2 and js2.get("candlesticks"): js=js2
    return js if js is not None else {"error":"none"}
os.makedirs(f"{RAW}/candles",exist_ok=True)
n=0
for ser in TARGETS:
    for m in markets[ser]:
        fn=f"{RAW}/candles/{m['ticker']}.json"
        if os.path.exists(fn): continue
        js=candles(m,ser); json.dump(js,open(fn,"w")); n+=1
        if n%100==0: log("chandeliers telecharges",n)
log("chandeliers termines, nouveaux :",n)

# ---------- 4. transactions (New York seulement, plafonne a 3 pages par marche)
os.makedirs(f"{RAW}/trades",exist_ok=True)
n=0
for ser in ["KXRAINNYC","KXRAIN"]:
    for m in markets[ser]:
        if ser=="KXRAIN" and not m["ticker"].endswith("-NYC"): continue
        fn=f"{RAW}/trades/{m['ticker']}.json"
        if os.path.exists(fn): continue
        out=[]; cur=None
        for page in range(3):
            p={"ticker":m["ticker"],"limit":1000}
            if cur: p["cursor"]=cur
            js=get(f"{K}/historical/trades",p) or get(f"{K}/markets/trades",p)
            if not js: break
            out+=js.get("trades",[]); cur=js.get("cursor")
            if not cur or not js.get("trades"): break
        json.dump(out,open(fn,"w")); n+=1
log("transactions termines, nouveaux :",n)

# ---------- 5. IEM ASOS p01i avec trace T
IEM="https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
STATIONS={"NYC":"America/New_York","MIA":"America/New_York","ORD":"America/Chicago"}
for st,tz in STATIONS.items():
    fn=f"{RAW}/asos_{st}.csv"
    if os.path.exists(fn): continue
    p={"station":st,"data":"p01i","year1":2021,"month1":1,"day1":1,"year2":2026,"month2":9,"day2":16,"tz":tz,"format":"onlycomma","trace":"T","report_type":3,"missing":"M"}
    for a in range(4):
        try:
            r=S.get(IEM,params=p,timeout=300)
            if r.status_code==200 and len(r.text)>1000: open(fn,"w").write(r.text); log("asos",st,len(r.text.splitlines()),"lignes"); break
            log("asos http",st,r.status_code,r.text[:100])
        except Exception as e: log("asos exc",st,e)
        time.sleep(5)

# ---------- 6. IEM MOS NBS (p12) par saison
MOS="https://mesonet.agron.iastate.edu/cgi-bin/request/mos.py"
for st in ["KNYC","KMIA","KORD"]:
    for y in [2021,2022,2025,2026]:
        fn=f"{RAW}/mos_{st}_{y}.csv"
        if os.path.exists(fn): continue
        p={"station":st,"model":"NBS","sts":f"{y}-04-29T00:00Z","ets":f"{y}-10-01T00:00Z","format":"csv"}
        for a in range(3):
            try:
                r=S.get(MOS,params=p,timeout=300)
                if r.status_code==200 and len(r.text)>200: open(fn,"w").write(r.text); log("mos",st,y,len(r.text.splitlines()),"lignes"); break
                log("mos http",st,y,r.status_code,r.text[:100])
            except Exception as e: log("mos exc",st,y,e)
            time.sleep(5)
log("COLLECTE TERMINEE")
