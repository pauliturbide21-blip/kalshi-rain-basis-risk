"""03_cost.py : H2, chargement. Prix de couverture depuis les chandeliers horaires, fiabilite, Brier, prevision MOS,
chargement brut et effectif, capacite, comparateur assurantiel.
Entrees : data/days_<ville>.csv, data/raw/candles/*.json, data/raw/mos_*.csv. Sorties : data/days_prices_<ville>.csv, tables/h2_*.csv, figures/fig2_calibration.png, data/resultats_h2.json
"""
import os, json, math
import numpy as np, pandas as pd
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
HERE=os.path.dirname(os.path.abspath(__file__)); RAW=f"{HERE}/data/raw"; TAB=f"{HERE}/tables"; FIG=f"{HERE}/figures"
TZ={"NYC":"America/New_York","MIA":"America/New_York","CHI":"America/Chicago"}; MOSST={"NYC":"KNYC","MIA":"KMIA","CHI":"KORD"}
PURCHASE={"veille_12h":(-1,12),"veille_18h":(-1,18),"jour_9h":(0,9)}; PREF="veille_12h"
FEE=lambda p:0.07*p*(1-p)
L_GRID=[2000,5000,10000,20000]; B=5000; BLOCK=7; rng=np.random.default_rng(20260916)
IN_PER_MM=1/25.4

def load_candles(ticker):
    fn=f"{RAW}/candles/{ticker}.json"
    if not os.path.exists(fn): return []
    js=json.load(open(fn)); cs=js.get("candlesticks",[]) if isinstance(js,dict) else []
    out=[]
    def g(d,k):   # deux formats : "close" (ancienne serie) ou "close_dollars" (serie multi-villes)
        v=d.get(k); v=d.get(k+"_dollars") if v in (None,"") else v
        return float(v) if v not in (None,"") else np.nan
    for c in cs:
        pr=c.get("price",{}) or {}; bid=c.get("yes_bid",{}) or {}; ask=c.get("yes_ask",{}) or {}
        out.append({"ts":int(c["end_period_ts"]),"close":g(pr,"close"),
                    "vol":float(c.get("volume") or c.get("volume_fp") or 0),"bid":g(bid,"close"),"ask":g(ask,"close"),
                    "oi":float(c.get("open_interest") or c.get("open_interest_fp") or 0)})
    return sorted(out,key=lambda x:x["ts"])
def spread_at(cs,t_local,tz):
    """ecart ask moins bid du dernier chandelier anterieur a t"""
    ts=int(t_local.replace(tzinfo=ZoneInfo(tz)).timestamp()); prev=[c for c in cs if c["ts"]<ts]
    for c in reversed(prev):
        if not np.isnan(c["bid"]) and not np.isnan(c["ask"]) and c["ask"]>0 and c["ask"]>=c["bid"]: return c["ask"]-c["bid"]
    return np.nan
def price_at(cs,t_local,tz):
    """dernier prix echange strictement avant t ; sinon mid bid ask du dernier chandelier anterieur (impute)"""
    ts=int(t_local.replace(tzinfo=ZoneInfo(tz)).timestamp())
    prev=[c for c in cs if c["ts"]<ts]
    if not prev: return np.nan,"absent"
    traded=[c for c in prev if c["vol"]>0 and not np.isnan(c["close"])]
    if traded: return traded[-1]["close"],"echange"
    for c in reversed(prev):
        if not np.isnan(c["bid"]) and not np.isnan(c["ask"]) and c["ask"]>0: return (c["bid"]+c["ask"])/2,"impute_mid"
    return np.nan,"absent"

# ---------- MOS
def load_mos(st):
    fns=sorted([f for f in os.listdir(RAW) if f.startswith(f"mos_{st}_")])
    if not fns: return None
    dfs=[]
    for f in fns:
        try: dfs.append(pd.read_csv(f"{RAW}/{f}"))
        except Exception: pass
    if not dfs: return None
    m=pd.concat(dfs); m.columns=[c.strip().lower() for c in m.columns]
    for c in ["runtime","ftime"]: m[c]=pd.to_datetime(m[c],utc=True,errors="coerce")
    for c in ["p12","p24","p06"]:
        if c in m.columns: m[c]=pd.to_numeric(m[c],errors="coerce")
    return m
def mos_pop(m,d,tz):
    """probabilite MOS NBS de pluie sur le jour civil local d, cycle 12Z de la veille ; repli cycle 00Z du jour (signale)"""
    if m is None: return np.nan,"absent"
    v=datetime(d.year,d.month,d.day,tzinfo=timezone.utc)-timedelta(days=1)
    # l'archive IEM horodate les cycles NBS a 13 Z (et 01, 07, 19 Z) avant 2026, a 12 Z ensuite : les deux sont acceptes pour le cycle de la veille
    cands=[(v+timedelta(hours=12),"12Z_veille"),(v+timedelta(hours=13),"12Z_veille"),(datetime(d.year,d.month,d.day,tzinfo=timezone.utc),"00Z_jour_repli"),(datetime(d.year,d.month,d.day,1,tzinfo=timezone.utc),"00Z_jour_repli")]
    for run,flag in cands:
        g=m[m.runtime==run]
        if len(g)==0: continue
        f1=datetime(d.year,d.month,d.day,0,tzinfo=timezone.utc)+timedelta(days=1); f2=f1+timedelta(hours=12)
        if "p24" in g.columns:
            r=g[g.ftime==f2]
            if len(r) and not np.isnan(r.p24.iloc[0]): return float(r.p24.iloc[0])/100,flag+"_p24"
        a=g[g.ftime==f1]; b=g[g.ftime==f2]
        if len(a) and len(b) and not np.isnan(a.p12.iloc[0]) and not np.isnan(b.p12.iloc[0]):
            return 1-(1-a.p12.iloc[0]/100)*(1-b.p12.iloc[0]/100),flag+"_p12x2"
    return np.nan,"absent"

# ---------- statistiques
def wilson(k,n,z=1.96):
    if n==0: return (np.nan,np.nan)
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return c-h,c+h
def brier_decomp(p,y,bins):
    p=np.asarray(p); y=np.asarray(y); n=len(p); bs=float(np.mean((p-y)**2)); ybar=y.mean()
    rel=0; res=0; rows=[]
    for lo,hi in zip(bins[:-1],bins[1:]):
        sel=(p>=lo)&(p<hi) if hi<1 else (p>=lo)&(p<=hi)
        if sel.sum()==0: continue
        pk=p[sel].mean(); ok=y[sel].mean(); nk=sel.sum()
        rel+=nk*(pk-ok)**2; res+=nk*(ok-ybar)**2; lo_,hi_=wilson(int(y[sel].sum()),int(nk))
        rows.append({"bin_bas":lo,"bin_haut":hi,"n":int(nk),"prix_moyen":pk,"frequence":ok,"freq_ic_bas":lo_,"freq_ic_haut":hi_})
    unc=ybar*(1-ybar); ece=sum(r["n"]*abs(r["prix_moyen"]-r["frequence"]) for r in rows)/n
    return {"brier":bs,"fiabilite":rel/n,"resolution":res/n,"incertitude":unc,"ece":ece},rows
def block_boot(df,fn,B=B,block=BLOCK):
    n=len(df); idx=np.arange(n); nb=int(math.ceil(n/block)); out=[]
    if n<block+1: return None
    for _ in range(B):
        starts=rng.integers(0,n-block+1,nb); sel=np.concatenate([idx[s:s+block] for s in starts])[:n]; out.append(fn(df.iloc[sel]))
    return pd.DataFrame(out)
def ci(boot,k): return (float(np.nanpercentile(boot[k],2.5)),float(np.nanpercentile(boot[k],97.5))) if boot is not None and k in boot else (np.nan,np.nan)

results={}; t_charge=[]; t_cap=[]; t_fiab=[]; t_ins=[]
for city in ["NYC","MIA","CHI"]:
    fn=f"{HERE}/data/days_{city}.csv"
    if not os.path.exists(fn): continue
    df=pd.read_csv(fn,parse_dates=["date"]); df["date"]=df.date.dt.date
    tz=TZ[city]; mos=load_mos(MOSST[city])
    for pk,(dd,hh) in PURCHASE.items():
        ps=[];fl=[];sp=[]
        for r in df.itertuples():
            cs=load_candles(r.ticker); t=datetime.combine(r.date+timedelta(days=dd),datetime.min.time()).replace(hour=hh)
            p,f=price_at(cs,t,tz); ps.append(p); fl.append(f); sp.append(spread_at(cs,t,tz))
        df[f"pi_{pk}"]=ps; df[f"pi_{pk}_source"]=fl; df[f"spread_{pk}"]=sp
    oimax=[];oiach=[];volc=[]
    for r in df.itertuples():
        cs=load_candles(r.ticker); oimax.append(max([c["oi"] for c in cs],default=np.nan)); volc.append(sum(c["vol"] for c in cs))
        t=datetime.combine(r.date-timedelta(days=1),datetime.min.time()).replace(hour=12); ts=int(t.replace(tzinfo=ZoneInfo(tz)).timestamp())
        prev=[c for c in cs if c["ts"]<ts]; oiach.append(prev[-1]["oi"] if prev else np.nan)
    df["oi_max"]=oimax; df["oi_achat"]=oiach; df["volume_chandeliers"]=volc
    df["pi"]=df[f"pi_{PREF}"]; df["pi_source"]=df[f"pi_{PREF}_source"]; df["fee"]=FEE(df.pi); df["spread"]=df[f"spread_{PREF}"]
    mp=[mos_pop(mos,d,tz) for d in df.date]; df["mos_pop"]=[x[0] for x in mp]; df["mos_source"]=[x[1] for x in mp]
    df.to_csv(f"{HERE}/data/days_prices_{city}.csv",index=False)
    d=df[df.ev_ok&df.day_ok].copy(); dp=d[d.pi.notna()].copy()
    print(city,"jours retenus",len(d),"avec prix",len(dp),"dont imputes",int((dp.pi_source=="impute_mid").sum()),"MOS disponibles",int(dp.mos_pop.notna().sum()),"dont repli",int(dp.mos_source.str.contains("repli").sum()))
    if len(dp)<20: continue
    # fiabilite et Brier, deciles de prix
    bins=list(np.quantile(dp.pi,np.linspace(0,1,11))); bins[0]=0; bins[-1]=1
    dec,rows=brier_decomp(dp.pi,dp.Y,bins)
    for r_ in rows: t_fiab.append(dict(r_,ville=city,source="kalshi_veille_12h"))
    dm=dp[dp.mos_pop.notna()]
    if len(dm)>=20:
        decm,rowsm=brier_decomp(dm.mos_pop,dm.Y,bins)
        for r_ in rowsm: t_fiab.append(dict(r_,ville=city,source="mos_nbs"))
        deck,_=brier_decomp(dm.pi,dm.Y,bins)
    else: decm=deck=None
    # chargements
    def charge(s):
        PY=s.Y.mean(); PYD=((s.Y==1)&(s.D==1)).mean()
        return {"pi_moyen":s.pi.mean(),"fee_moyen":s.fee.mean(),"P_Y":PY,"P_YD":PYD,"lambda":s.pi.mean()/PY-1 if PY else np.nan,
                "Lambda":(s.pi.mean()+s.fee.mean())/PYD if PYD else np.nan,"Lambda_sans_frais":s.pi.mean()/PYD if PYD else np.nan,
                "ecart_mos":(s.pi-s.mos_pop).mean() if s.mos_pop.notna().any() else np.nan,"spread_moyen":s.spread.mean() if "spread" in s else np.nan,"spread_median":s.spread.median() if "spread" in s else np.nan}
    pc=charge(dp); bc=block_boot(dp,charge)
    row={"ville":city,"n":len(dp),"achat":PREF}
    for k in pc: row[k]=pc[k]; row[f"{k}_ic_bas"],row[f"{k}_ic_haut"]=ci(bc,k)
    row.update({f"brier_{k}":v for k,v in dec.items()})
    if decm: row.update({f"brier_mos_{k}":v for k,v in decm.items()}); row.update({f"brier_kalshi_meme_jours_{k}":v for k,v in deck.items()}); row["n_mos"]=len(dm)
    t_charge.append(row)
    # heures d'achat alternatives
    for pk in PURCHASE:
        s=d[d[f"pi_{pk}"].notna()].copy(); s["pi"]=s[f"pi_{pk}"]; s["fee"]=FEE(s.pi)
        if len(s)<20: continue
        p_=charge(s); b_=block_boot(s,charge,B=1000); r_={"ville":city,"n":len(s),"achat":pk}
        for k in ["pi_moyen","lambda","Lambda"]: r_[k]=p_[k]; r_[f"{k}_ic_bas"],r_[f"{k}_ic_haut"]=ci(b_,k)
        t_charge.append(r_)
    # capacite
    for L in L_GRID:
        oim=float(d.oi_max.median()); oia=float(d.oi_achat.median())
        t_cap.append({"ville":city,"L":L,"volume_median":float(d.volume.median()),"oi_max_median":oim,"oi_achat_median":oia,"part_oi_max":L/oim if oim>0 else np.nan,"part_oi_achat":L/oia if oia>0 else np.nan,
                      "part_volume":L/float(d.volume.median()) if d.volume.median()>0 else np.nan,"jours_oi_max_sup_L":float((d.oi_max>=L).mean()),"jours_volume_sup_L":float((d.volume>=L).mean())})
    # comparateur assurantiel : probabilite de declenchement a la station, seuils et plages de l'assureur
    for th in [1.0,2.5,5.0]:
        for wn,col in [("18h-01h",f"D_18h-01h_{th}"),("12h-24h",f"D_12h-24h_{th}")]:
            Ptrig=float(d[col].mean())
            for prime in [0.018,0.05,0.10,0.18]:
                t_ins.append({"ville":city,"seuil_mm":th,"plage":wn,"P_declenchement":Ptrig,"prime_pct":prime,"Lambda_assurance":prime/Ptrig if Ptrig else np.nan})
    results[city]={"chargement":row}

pd.DataFrame(t_charge).to_csv(f"{TAB}/h2_chargement.csv",index=False); pd.DataFrame(t_cap).to_csv(f"{TAB}/h2_capacite.csv",index=False)
pd.DataFrame(t_fiab).to_csv(f"{TAB}/h2_fiabilite.csv",index=False); pd.DataFrame(t_ins).to_csv(f"{TAB}/h2_assurance.csv",index=False)
json.dump(results,open(f"{HERE}/data/resultats_h2.json","w"),indent=1,default=str)

# ---------- figure 2 : fiabilite, New York
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
tf=pd.DataFrame(t_fiab); tf=tf[tf.ville=="NYC"] if (tf.ville=="NYC").any() else tf
fig,ax=plt.subplots(figsize=(7,6.5))
ax.plot([0,1],[0,1],color="0.6",lw=1,ls="--",label="Calibration parfaite")
for src,mk,lab in [("kalshi_veille_12h","o","Cote Kalshi, veille 12 h"),("mos_nbs","s","Prevision MOS NBS, cycle 12 Z de la veille")]:
    s=tf[tf.source==src]
    if len(s)==0: continue
    ax.errorbar(s.prix_moyen,s.frequence,yerr=[s.frequence-s.freq_ic_bas,s.freq_ic_haut-s.frequence],fmt=mk,color="black" if src.startswith("kalshi") else "0.45",mfc="white" if src.startswith("mos") else "black",capsize=3,label=f"{lab} (n = {int(s.n.sum())})")
    for r in s.itertuples(): ax.annotate(str(int(r.n)),(r.prix_moyen,r.frequence),xytext=(5,-9 if src.startswith("kalshi") else 6),textcoords="offset points",fontsize=7,color="0.3")
ax.set_xlabel("Probabilite annoncee (cote du contrat Oui ou prevision), par decile de cote"); ax.set_ylabel("Frequence realisee de reglement Oui (fraction), IC 95 % de Wilson")
ax.set_xlim(0,1); ax.set_ylim(0,1); ax.legend(frameon=False,fontsize=8,loc="upper left"); ax.grid(color="0.9")
ax.set_title("Fiabilite de la cote de la veille, contrats de pluie New York, saisons mai a septembre",fontsize=9,loc="left")
plt.tight_layout(); plt.savefig(f"{FIG}/fig2_calibration.png",dpi=170); plt.close()
print(pd.DataFrame(t_charge)[[c for c in ["ville","n","achat","pi_moyen","P_Y","P_YD","lambda","lambda_ic_bas","lambda_ic_haut","Lambda","Lambda_ic_bas","Lambda_ic_haut","ecart_mos","brier_brier","brier_ece","brier_mos_brier","n_mos"] if c in pd.DataFrame(t_charge).columns]].round(3).to_string())
print(pd.DataFrame(t_cap).round(2).to_string())
