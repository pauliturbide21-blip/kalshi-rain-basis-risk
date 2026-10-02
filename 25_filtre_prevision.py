"""25_filtre_prevision.py : le gerant croise la cote Kalshi avec la prevision horaire avant d'acheter.
Question : acheter le contrat journalier reel seulement quand la prevision place la pluie pendant les heures d'ouverture
reduit-il les paiements inutiles et le cout de la couverture ? Le contrat reste le meme (il paie sur la pluie journaliere).
Prevision : MOS NBS (IEM), cycle 12 Z ou 13 Z de la veille (achat la veille a midi, hypothese H-C), probabilites p06 (pluie >= 0,01 pouce sur 6 h) :
  fenetre soir  = p06 valide 00 Z du lendemain (14 h a 20 h locales) et p06 valide 06 Z du lendemain (20 h a 2 h locales), combinees : 1 - (1-a)(1-b)
  fenetre stricte = p06 valide 06 Z du lendemain seulement (20 h a 2 h locales)
  fenetre hors soir = p06 valide 12 Z et 18 Z du jour (2 h a 14 h locales)
Sensibilite : cycle 07 Z du jour (achat le jour a 9 h, prix pi_jour_9h).
Sorties : tables/filtre_diag_jours.csv, tables/filtre_scenario_bon_sens.csv, data/days_prevision_NYC.csv
"""
import os, math, numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); TAB=f"{HERE}/tables"; DATA=f"{HERE}/data"; RAW=f"{DATA}/raw"
B=2000; BLOCK=7; rng=np.random.default_rng(20260918); FEE=lambda p:0.07*p*(1-p); PERTE=0.5   # part de la recette perdue un soir de pluie
mos=pd.concat([pd.read_csv(f"{RAW}/mos_KNYC_{y}.csv",parse_dates=["runtime","ftime"]) for y in (2021,2022,2025,2026)])
mos=mos[mos.station=="KNYC"]; p06={(r.runtime,r.ftime):r.p06/100 for r in mos[mos.p06.notna()].itertuples()}
runs=set(mos.runtime.unique())
def get(run,ft): return p06.get((run,ft),np.nan)
def prev(d):
    """previsions pour la date locale d, depuis le cycle de la veille (12/13 Z) et le cycle du jour (07 Z)"""
    out={}
    for lab,cands in (("veille",[pd.Timestamp(d-pd.Timedelta(days=1))+pd.Timedelta(hours=h) for h in (13,12)]),("jour",[pd.Timestamp(d)+pd.Timedelta(hours=7)])):
        run=next((r for r in cands if r in runs),None)
        if run is None: out.update({f"p_soir_{lab}":np.nan,f"p_strict_{lab}":np.nan,f"p_hors_{lab}":np.nan}); continue
        a=get(run,pd.Timestamp(d)+pd.Timedelta(hours=24)); b=get(run,pd.Timestamp(d)+pd.Timedelta(hours=30))
        c=get(run,pd.Timestamp(d)+pd.Timedelta(hours=12)); e=get(run,pd.Timestamp(d)+pd.Timedelta(hours=18))
        out[f"p_soir_{lab}"]=1-(1-a)*(1-b); out[f"p_strict_{lab}"]=b; out[f"p_hors_{lab}"]=1-(1-c)*(1-e)
    return out
days=pd.read_csv(f"{DATA}/days_prices_NYC.csv",parse_dates=["date"]); days=days[days.ev_ok&days.day_ok].copy()
days=days[(days.date.dt.month>=5)&(days.date.dt.month<=9)].sort_values("date").reset_index(drop=True); days["saison"]=days.date.dt.year
pv=pd.DataFrame([prev(d) for d in days.date]); days=pd.concat([days,pv],axis=1); days.to_csv(f"{DATA}/days_prevision_NYC.csv",index=False)
print("jours de saison :",len(days),"; avec prevision veille :",int(days.p_soir_veille.notna().sum()),"; avec cote veille 12 h :",int(days.pi_veille_12h.notna().sum()))
# --- 1. pouvoir predictif de la prevision sur la soiree perdue, compare a la cote
def auc(score,y):
    m=score.notna()&y.notna(); s=score[m].values; t=y[m].values.astype(bool)
    if t.sum()==0 or (~t).sum()==0: return np.nan
    r=pd.Series(s).rank().values; return (r[t].sum()-t.sum()*(t.sum()+1)/2)/(t.sum()*(~t).sum())
def boot_auc(score,y,n=500):
    m=(score.notna()&y.notna()).values; s=score[m].reset_index(drop=True); t=y[m].reset_index(drop=True); k=len(s)
    v=[auc(s.iloc[i],t.iloc[i]) for i in (rng.integers(0,k,k) for _ in range(n))]; return np.nanpercentile(v,[2.5,97.5])
diag=[]
for per,sub in (("2021-2026",days),("2025-2026",days[days.saison.isin([2025,2026])])):
    for nom,col in (("cote Kalshi veille 12 h","pi_veille_12h"),("prevision soir (14 h - 2 h)","p_soir_veille"),("prevision stricte (20 h - 2 h)","p_strict_veille"),("prevision hors soir (2 h - 14 h)","p_hors_veille"),("MOS pluie journaliere","mos_pop")):
        for cible in ("Y","D"):
            a=auc(sub[col],sub[cible]); lo,hi=boot_auc(sub[col],sub[cible])
            diag.append({"periode":per,"score":nom,"cible":cible,"n":int((sub[col].notna()).sum()),"auc":a,"ic_bas":lo,"ic_haut":hi})
diag=pd.DataFrame(diag); pd.set_option("display.width",250); print("\n--- AUC de chaque score pour predire la pluie journaliere (Y) et la soiree perdue (D)"); print(diag.round(3).to_string())
# --- 2. regles d'achat : cote >= s et prevision soir >= q ; qualite de la couverture sur les jours achetes
def qual(sub,mask,lab,per):
    b=sub[mask]; nb=sub[~mask & sub.pi_veille_12h.notna()]
    if len(b)<5: return None
    pi=b.pi_veille_12h; fee=FEE(pi); pYD=(b.Y*b.D).mean()
    return {"periode":per,"regle":lab,"n_achats":len(b),"P_Y_achat":b.Y.mean(),"P_D_achat":b.D.mean(),"P_D_sachant_Y":b[b.Y==1].D.mean() if (b.Y==1).any() else np.nan,
            "Lambda":(pi.mean()+fee.mean())/pYD if pYD>0 else np.inf,"corr_Y_D":np.corrcoef(b.Y,b.D)[0,1] if b.D.std()>0 and b.Y.std()>0 else np.nan,
            "part_D_couverts":b.D.sum()/sub[sub.pi_veille_12h.notna()].D.sum(),"P_D_non_achat":nb.D.mean(),"prime_moyenne":(pi+fee).mean()}
rows=[]
for per,sub in (("2021-2026",days),("2025-2026",days[days.saison.isin([2025,2026])])):
    for s in (0.3,0.4,0.5,0.6):
        base=sub.pi_veille_12h>=s
        r=qual(sub,base,f"cote >= {s}",per); rows.append(r) if r else None
        for q in (0.3,0.5,0.7):
            r=qual(sub,base&(sub.p_soir_veille>=q),f"cote >= {s} et prevision soir >= {q}",per); rows.append(r) if r else None
            r=qual(sub,base&(sub.p_strict_veille>=q),f"cote >= {s} et prevision stricte >= {q}",per); rows.append(r) if r else None
    for q in (0.3,0.5,0.7):
        r=qual(sub,sub.pi_veille_12h.notna()&(sub.p_soir_veille>=q),f"prevision soir >= {q} seule",per); rows.append(r) if r else None
dj=pd.DataFrame(rows); dj.to_csv(f"{TAB}/filtre_diag_jours.csv",index=False)
print("\n--- qualite de la couverture selon la regle d'achat (jours de saison avec cote veille 12 h)"); print(dj.round(3).to_string())
# --- 3. scenario de bon sens : 20 plus grosses soirees, h = 0,6, contrat reel, filtre prevision, dix lieux, saisons 2025 et 2026
cal=pd.read_csv(f"{DATA}/calendrier.csv",parse_dates=["date"]); panel=pd.read_csv(f"{DATA}/panel_rooftops.csv")
d2=days[days.saison.isin([2025,2026])].copy(); d2["sp_ref"]=d2.spread_veille_12h.fillna(d2.spread_veille_12h.median())
def season(nom,s):
    c=cal[(cal.nom==nom)&(cal.saison==s)].merge(d2[d2.saison==s][["date","Y","D","pi_veille_12h","sp_ref","p_soir_veille","p_strict_veille"]],on="date",how="inner")
    return c[c.ouvert==1].sort_values("date").reset_index(drop=True)
def block_indices(n,B_):
    nb=int(math.ceil(n/BLOCK)); starts=rng.integers(0,n-BLOCK+1,(B_,nb)); return (starts[:,:,None]+np.arange(BLOCK)[None,None,:]).reshape(B_,-1)[:,:n]
bons=[]
for v in panel.itertuples():
    for s in (2025,2026):
        c=season(v.nom,s); n=len(c); bi=block_indices(n,B); R=c.R.values; K=c.K.values
        big=c[c.grosse==1].copy(); big["prio"]=np.where((big.date.dt.weekday==5)|(big.ferie_ou_veille==1),0,1); top=np.zeros(n,bool); top[list(big.sort_values(["prio","date"]).head(20).index)]=True
        Yb=c.Y.values[bi].astype(float); Db=c.D.values[bi].astype(float); pib=c.pi_veille_12h.values[bi]; spb=c.sp_ref.values[bi]
        ps={"soir":c.p_soir_veille.values[bi],"stricte":c.p_strict_veille.values[bi]}
        quot=~np.isnan(pib); cf0=R[None,:]*(1-PERTE*Db)-K[None,:]; r0=cf0.sum(1)
        for fen,q in (("aucun",0.0),("soir",0.3),("soir",0.5),("soir",0.7),("stricte",0.3),("stricte",0.5)):
            for seuil in (0.4,0.5):
                for frac,ex in ((0.0,"mid"),(0.25,"quart_spread")):
                  for mode in ("h_0.6","net_0.6"):
                    filt=np.ones_like(quot) if fen=="aucun" else (np.nan_to_num(ps[fen],nan=-1)>=q)
                    e=top[None,:]&quot&(np.nan_to_num(pib)>=seuil)&filt; price=np.nan_to_num(pib)+frac*spb; fee=FEE(np.nan_to_num(pib))
                    # h_0.6 : 0,6 contrat par dollar de recette ; net_0.6 : assez de contrats pour que le paiement net couvre 60 % de la recette (h = 0,6 / (1 - prix - frais))
                    hh=np.full_like(price,0.6*PERTE) if mode=="h_0.6" else 0.6*PERTE/np.clip(1-price-fee,0.05,1)
                    pnl=np.where(e,hh*R[None,:]*(Yb-price-fee),0.0); r1=r0+pnl.sum(1); g=r1-r0
                    paid=(e&(Yb==1)); util=(e&(Yb==1)&(Db==1))
                    bons.append({"nom":v.nom,"saison":s,"filtre":fen,"q":q,"seuil":seuil,"execution":ex,"mode":mode,"couvertes":float(e.sum(1).mean()),"paiements":float(paid.sum(1).mean()),"paiements_utiles":float(util.sum(1).mean()),
                                 "engagement":float(np.where(e,hh*R[None,:]*(price+fee),0).sum(1).mean()),"gain_moyen":float(g.mean()),"ic_bas":float(np.percentile(g,2.5)),"ic_haut":float(np.percentile(g,97.5)),
                                 "pire5_sans":float(np.percentile(r0,5)),"pire5_avec":float(np.percentile(r1,5)),"ederington_e":float(1-r1.var()/r0.var()),"R_saison":float(R.sum())})
    print(v.nom,"ok")
bs=pd.DataFrame(bons); bs.to_csv(f"{TAB}/filtre_scenario_bon_sens.csv",index=False)
bs=bs.assign(gain_pct=100*bs.gain_moyen/bs.R_saison,eng_pct=100*bs.engagement/bs.R_saison,pire_pct=100*(bs.pire5_avec/bs.pire5_sans-1))
g=bs.groupby(["saison","mode","filtre","q","seuil","execution"]).agg(couvertes=("couvertes","median"),paiements=("paiements","median"),utiles=("paiements_utiles","median"),eng_pct=("eng_pct","median"),gain_pct=("gain_pct","median"),n_pos=("ic_bas",lambda x:int((x>0).sum())),n_neg=("ic_haut",lambda x:int((x<0).sum())),pire_pct=("pire_pct","median"),e=("ederington_e","median")).reset_index()
print("\n--- scenario de bon sens, 20 grosses soirees, h = 0,6, contrat reel, mediane des dix lieux"); print(g.round(2).to_string())
