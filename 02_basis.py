"""02_basis.py : H1, risque de base. Construit la table des jours (marche + station), calcule la contingence Y x D,
FP, UC, phi, rho, les quatre etats, bootstrap par blocs de 7 jours, experience naturelle (declencheurs A et B), concordance, grilles.
Sorties : data/days_<ville>.csv, tables/h1_*.csv, figures/fig1_etats_du_monde.png, data/resultats_h1.json
"""
import os, json, glob, re, math
import numpy as np, pandas as pd
from datetime import datetime, date, timedelta
HERE=os.path.dirname(os.path.abspath(__file__)); RAW=f"{HERE}/data/raw"; TAB=f"{HERE}/tables"; FIG=f"{HERE}/figures"
os.makedirs(TAB,exist_ok=True); os.makedirs(FIG,exist_ok=True)
PRE=json.load(open(f"{HERE}/data/params.json")) if os.path.exists(f"{HERE}/data/params.json") else {}
IN_PER_MM=1/25.4
THETA_REF=1.0; THETAS=[0.25,1.0,2.5,5.0]
WINDOWS={"17h-23h":(17,23,0),"18h-01h":(18,23,1),"19h-02h":(19,23,2),"12h-24h":(12,23,0)}   # 12h-24h : plage de l'assureur (comparateur H2), pas une plage de soiree   # (h debut jour t, h fin jour t, h fin jour t+1 exclue = nombre d'heures de t+1)
WREF="18h-01h"
CITY_STATION={"NYC":"NYC","MIA":"MIA","CHI":"ORD"}
RULE_CHANGE=date(2026,7,15)
SEASON=lambda d: 5<=d.month<=9
B=5000; BLOCK=7; rng=np.random.default_rng(20260916)
MON={m:i+1 for i,m in enumerate(["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"])}

# ---------- marches
def parse_market(m):
    t=m["ticker"]; ev=m.get("event_ticker","")
    mm=re.match(r"^(KX)?RAIN(NYC|MIA|CHI)?-(\d\d)([A-Z]{3})(\d\d)(?:-(\w+))?$",t)
    if not mm: return None
    city=mm.group(2) or (mm.group(6) if mm.group(6) and mm.group(6)!="T0" else None)
    if city is None: return None
    d=date(2000+int(mm.group(3)),MON[mm.group(4)],int(mm.group(5)))
    return {"ticker":t,"city":city,"date":d,"status":m.get("status"),"result":m.get("result"),
            "volume":float(m.get("volume_fp") or 0),"open_interest":float(m.get("open_interest_fp") or 0),
            "expiration_value":m.get("expiration_value"),"open_time":m.get("open_time"),"close_time":m.get("close_time"),
            "serie":"multi" if t.startswith("KXRAIN-") else "ville","rules":m.get("rules_primary","")}
rows=[]
for fn in glob.glob(f"{RAW}/markets_*.json"):
    for m in json.load(open(fn)):
        p=parse_market(m)
        if p and p["city"] in CITY_STATION: rows.append(p)
mk=pd.DataFrame(rows).drop_duplicates("ticker")
mk=mk[mk.status=="finalized"].copy(); mk["Y"]=(mk.result=="yes").astype(int)
mk["season"]=mk.date.map(SEASON)
print("marches finalises par ville :",mk.groupby("city").size().to_dict()," en saison :",mk[mk.season].groupby("city").size().to_dict())

# ---------- station
def load_asos(st):
    fn=f"{RAW}/asos_{st}.csv"
    if not os.path.exists(fn): return None
    lines=[l for l in open(fn).read().splitlines() if l and not l.startswith("#")]
    df=pd.read_csv(pd.io.common.StringIO("\n".join(lines)))
    df["valid"]=pd.to_datetime(df["valid"]); df["p"]=df["p01i"].astype(str).str.strip()
    df["trace"]=df.p=="T"; df["missing"]=df.p.isin(["M",""," ","nan","None"])
    df["inch"]=pd.to_numeric(df.p.where(~df.trace & ~df.missing),errors="coerce")
    df.loc[df.trace,"inch"]=0.0
    df["day"]=df.valid.dt.date; df["hour"]=df.valid.dt.hour
    # observation horaire = derniere observation de chaque heure locale (routine a :51)
    df=df.sort_values("valid").groupby(["day","hour"]).tail(1)
    return df[["valid","day","hour","inch","trace","missing"]].reset_index(drop=True)
def day_table(city):
    st=CITY_STATION[city]; a=load_asos(st)
    if a is None: return None
    byday={d:g for d,g in a.groupby("day")}
    out=[]
    for r in mk[(mk.city==city)&mk.season].itertuples():
        d=r.date; g=byday.get(d); g1=byday.get(d+timedelta(days=1))
        if g is None: continue
        rec={"date":d,"ticker":r.ticker,"Y":r.Y,"volume":r.volume,"open_interest":r.open_interest,"serie":r.serie,"expiration_value":r.expiration_value}
        # journee civile locale 0h a 23h59 : observations d'heure 0 a 23 du jour t
        gd=g[(g.hour>=0)&(g.hour<=23)]
        rec["n_obs_day"]=len(gd); rec["missing_day"]=int(gd.missing.sum()); rec["day_in"]=float(gd.inch.sum()) if len(gd) else np.nan; rec["day_trace"]=bool(gd.trace.any())
        for wn,(h0,h1,nxt) in WINDOWS.items():
            gw=g[(g.hour>=h0)&(g.hour<=h1)]; parts=[gw]
            if nxt and g1 is not None: parts.append(g1[g1.hour<nxt])
            gw=pd.concat(parts) if len(parts)>1 else gw
            expected=(h1-h0+1)+nxt
            rec[f"ev_in_{wn}"]=float(gw.inch.sum()); rec[f"ev_missing_{wn}"]=int(gw.missing.sum())+(expected-len(gw)); rec[f"ev_trace_{wn}"]=bool(gw.trace.any())
        out.append(rec)
    df=pd.DataFrame(out).sort_values("date").reset_index(drop=True)
    df["day_ok"]=(df.missing_day==0)&(df.n_obs_day>=22)
    df["trigA"]=((df.day_in>0)|df.day_trace).astype(int); df["trigB"]=(df.day_in>0).astype(int)
    for wn in WINDOWS:
        for th in THETAS: df[f"D_{wn}_{th}"]=(df[f"ev_in_{wn}"]>=th*IN_PER_MM).astype(int)
        df[f"ev_ok_{wn}"]=df[f"ev_missing_{wn}"]==0
    df["D"]=df[f"D_{WREF}_{THETA_REF}"]; df["ev_ok"]=df[f"ev_ok_{WREF}"]
    df["periode_regle"]=np.where(df.date<RULE_CHANGE,"avant_15juil2026","apres_15juil2026")
    df["annee"]=[d.year for d in df.date]
    return df

# ---------- statistiques
def stats(Y,D):
    Y=np.asarray(Y); D=np.asarray(D); n=len(Y)
    a=int(((Y==1)&(D==1)).sum()); b=int(((Y==1)&(D==0)).sum()); c=int(((Y==0)&(D==1)).sum()); d=int(((Y==0)&(D==0)).sum())
    FP=b/(a+b) if a+b else np.nan; UC=c/(a+c) if a+c else np.nan
    den=math.sqrt((a+b)*(c+d)*(a+c)*(b+d)); phi=(a*d-b*c)/den if den else np.nan
    return {"n":n,"paye_perte":a/n,"paye_sans_perte":b/n,"perte_non_payee":c/n,"sec":d/n,"FP":FP,"UC":UC,"phi":phi,"rho":phi,"P_Y":(a+b)/n,"P_D":(a+c)/n,"P_YD":a/n}
def block_boot(df,fn,B=B,block=BLOCK):
    """bootstrap par blocs mobiles de `block` jours sur la serie ordonnee ; fn(sub) -> dict"""
    n=len(df); out=[]
    if n<block+1: return None
    idx=np.arange(n); nb=int(math.ceil(n/block))
    for _ in range(B):
        starts=rng.integers(0,n-block+1,nb); sel=np.concatenate([idx[s:s+block] for s in starts])[:n]
        out.append(fn(df.iloc[sel]))
    return pd.DataFrame(out)
def with_ci(point,boot,keys):
    res={}
    for k in keys:
        res[k]=point[k]
        if boot is not None and k in boot: res[f"{k}_ic_bas"]=float(np.nanpercentile(boot[k],2.5)); res[f"{k}_ic_haut"]=float(np.nanpercentile(boot[k],97.5))
    return res

results={"parametres":{"theta_ref_mm":THETA_REF,"fenetre_ref":WREF,"bootstrap":B,"bloc_jours":BLOCK}}
tables_cont=[]; tables_sens=[]; tables_nat=[]; tables_conc=[]; day_tables={}
for city in ["NYC","MIA","CHI"]:
    df=day_table(city)
    if df is None or len(df)==0: print(city,": pas de station ou pas de marche"); continue
    df.to_csv(f"{HERE}/data/days_{city}.csv",index=False); day_tables[city]=df
    excl=len(df)-int((df.ev_ok&df.day_ok).sum())
    d=df[df.ev_ok&df.day_ok].reset_index(drop=True)
    print(city,"jours de saison avec marche :",len(df),"exclus pour donnees station manquantes :",excl,"retenus :",len(d), "annees",sorted(d.annee.unique()))
    # concordance des declencheurs reconstruits avec le reglement officiel, par periode
    for per,g in d.groupby("periode_regle"):
        for trig in ["trigA","trigB"]:
            tables_conc.append({"ville":city,"periode":per,"declencheur":trig,"n":len(g),"concordance":float((g[trig]==g.Y).mean()),
                                "Y1_trig0":int(((g.Y==1)&(g[trig]==0)).sum()),"Y0_trig1":int(((g.Y==0)&(g[trig]==1)).sum())})
    # H1 contingence de reference
    pt=stats(d.Y,d.D); bt=block_boot(d,lambda s:stats(s.Y,s.D))
    keys=["paye_perte","paye_sans_perte","perte_non_payee","sec","FP","UC","phi","rho","P_Y","P_D","P_YD"]
    r=with_ci(pt,bt,keys); r.update({"ville":city,"n":pt["n"],"n_exclus_station":excl,"annees":",".join(map(str,sorted(d.annee.unique())))}); tables_cont.append(r)
    # par annee et par periode de regle (sans bootstrap si trop court)
    for grp,g in list(d.groupby("annee"))+list(d.groupby("periode_regle")):
        p=stats(g.Y,g.D); b=block_boot(g,lambda s:stats(s.Y,s.D),B=1000) if len(g)>=30 else None
        rr=with_ci(p,b,["FP","UC","rho"]); rr.update({"ville":city,"groupe":str(grp),"n":len(g)}); tables_sens.append(dict(rr,theta_mm=THETA_REF,fenetre=WREF,type="groupe"))
    # grilles theta x fenetre
    for wn in WINDOWS:
        dd=df[df[f"ev_ok_{wn}"]&df.day_ok]
        for th in THETAS:
            p=stats(dd.Y,dd[f"D_{wn}_{th}"]); b=block_boot(dd,lambda s,wn=wn,th=th:stats(s.Y,s[f"D_{wn}_{th}"]),B=1000)
            rr=with_ci(p,b,["FP","UC","rho","P_D"]); rr.update({"ville":city,"groupe":"tous","n":len(dd),"theta_mm":th,"fenetre":wn,"type":"grille"}); tables_sens.append(rr)
    # experience naturelle : declencheurs A et B sur les memes jours, contre D
    def nat(s):
        a=stats(s.trigA,s.D); b=stats(s.trigB,s.D)
        return {"FP_A":a["FP"],"UC_A":a["UC"],"rho_A":a["rho"],"FP_B":b["FP"],"UC_B":b["UC"],"rho_B":b["rho"],"P_A":a["P_Y"],"P_B":b["P_Y"],
                "dFP":b["FP"]-a["FP"],"dUC":b["UC"]-a["UC"],"drho":b["rho"]-a["rho"],"part_trace_seule":float(((s.trigA==1)&(s.trigB==0)).mean())}
    pn=nat(d); bn=block_boot(d,nat)
    rn=with_ci(pn,bn,list(pn.keys())); rn.update({"ville":city,"n":len(d)}); tables_nat.append(rn)
    results[city]={"contingence":r,"experience_naturelle":rn}

pd.DataFrame(tables_cont).to_csv(f"{TAB}/h1_contingence.csv",index=False)
pd.DataFrame(tables_sens).to_csv(f"{TAB}/h1_sensibilite.csv",index=False)
pd.DataFrame(tables_nat).to_csv(f"{TAB}/h1_experience_naturelle.csv",index=False)
pd.DataFrame(tables_conc).to_csv(f"{TAB}/h1_concordance.csv",index=False)
json.dump(results,open(f"{HERE}/data/resultats_h1.json","w"),indent=1,default=str)

# ---------- figure 1 : quatre etats du monde, en part des jours, par ville, avec IC
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
tc=pd.DataFrame(tables_cont)
states=[("paye_perte","Paye et perte reelle"),("paye_sans_perte","Paye sans perte (faux paiement)"),("perte_non_payee","Perte non payee"),("sec","Sec et non paye")]
hatches=["","//","xx","..."]; greys=["0.25","0.55","0.8","1.0"]
fig,ax=plt.subplots(figsize=(10,5.6))
xs=np.arange(len(tc)); width=0.6; bottom=np.zeros(len(tc))
for (k,lab),h,gcol in zip(states,hatches,greys):
    v=tc[k].values; err=np.vstack([v-tc[f"{k}_ic_bas"].values,tc[f"{k}_ic_haut"].values-v])
    ax.bar(xs,v,width,bottom=bottom,color=gcol,edgecolor="black",hatch=h,label=lab)
    for i in range(len(tc)):
        if v[i]<0.03: continue
        ax.text(xs[i],bottom[i]+v[i]/2,f"{100*v[i]:.0f} %\n[{100*tc[f'{k}_ic_bas'].values[i]:.0f} ; {100*tc[f'{k}_ic_haut'].values[i]:.0f}]",ha="center",va="center",fontsize=7.5,color="white" if gcol in ("0.25","0.55") else "black",bbox=dict(boxstyle="round,pad=0.15",fc="white" if gcol not in ("0.25","0.55") else "none",ec="none",alpha=0.7))
    bottom+=v
ax.set_xticks(xs); ax.set_xticklabels([f"{r.ville}\nn = {r.n} jours\n{r.annees.replace(',',', ')}" for r in tc.itertuples()],fontsize=8)
ax.set_ylabel("Part des jours de saison (fraction)"); ax.set_ylim(0,1.02)
ax.set_title(f"Reglement Kalshi contre soiree perdue (au moins {THETA_REF:g} mm entre 18 h et 1 h a la station), part des jours de saison.\nIntervalles a 95 % par bootstrap par blocs de 7 jours, {B} repetitions. Perte non payee : 0 % dans les trois villes.",fontsize=8.5,loc="left")
ax.legend(frameon=False,fontsize=8,loc="upper left",bbox_to_anchor=(1.0,1.0))
plt.tight_layout(); plt.savefig(f"{FIG}/fig1_etats_du_monde.png",dpi=170); plt.close()
print(tc[["ville","n","FP","FP_ic_bas","FP_ic_haut","UC","UC_ic_bas","UC_ic_haut","rho","rho_ic_bas","rho_ic_haut","P_Y","P_D"]].round(3).to_string())
print(pd.DataFrame(tables_conc).round(3).to_string())
print(pd.DataFrame(tables_nat)[["ville","n","FP_A","FP_B","dFP","dFP_ic_bas","dFP_ic_haut","UC_A","UC_B","rho_A","rho_B","drho","drho_ic_bas","drho_ic_haut","part_trace_seule"]].round(3).to_string())
