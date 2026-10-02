"""Optimal program: variance-minimising quantity each day, theoretical bound and simulation.
Comments in the code are in French."""
import os, math, numpy as np, pandas as pd
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); TAB=f"{HERE}/results"; DATA=f"{HERE}/data"
B=2000; BLOCK=7; rng=np.random.default_rng(20260918); FEE=lambda p:0.07*p*(1-p); PERTE=0.5   # part de la recette perdue un soir de pluie
d=pd.read_csv(f"{DATA}/days_prevision_NYC.csv",parse_dates=["date"]); d["Y_twc"]=(d.day_in>0).astype(int); d["saison"]=d.date.dt.year
d["D_twc"]=d.D*d.Y_twc   # sous la regle TWC une soiree perdue est toujours une pluie mesuree (>= 1 mm)
INFO={"aucune":[],"cote seule":["pi_veille_12h"],"prevision soir seule":["p_strict_veille"],"cote + prevision soir (veille 12 h)":["pi_veille_12h","p_strict_veille"],
      "cote + prevision soir + prevision jour (veille 12 h)":["pi_veille_12h","p_strict_veille","p_soir_veille"],"cote + prevision soir (jour 9 h)":["pi_jour_9h","p_strict_jour"]}
def bins(x,k=4): return pd.qcut(x.rank(method="first"),k,labels=False) if x.notna().sum()>=k else pd.Series(0,index=x.index)
def cells(sub,cols):
    if not cols: return pd.Series(0,index=sub.index)
    key=pd.Series("",index=sub.index)
    for c in cols: key=key+"|"+bins(sub[c],3 if len(cols)>1 else 5).astype(str)
    return key
def e_max(train,test,cols,Ycol,Dcol):
    """estime P(Y|I), P(D|I) par cellule sur train, applique a test ; borne d'efficacite ponderee par Var(D|I)"""
    ok=train[cols].notna().all(1) if cols else pd.Series(True,index=train.index); tr=train[ok]; ct=cells(tr,cols)
    tab=tr.assign(c=ct).groupby("c").agg(pY=(Ycol,"mean"),pD=(Dcol,"mean"),n=(Ycol,"size"))
    okt=test[cols].notna().all(1) if cols else pd.Series(True,index=test.index); te=test[okt].copy()
    if len(te)==0: return np.nan,0
    # projection des cellules de test : memes seuils de quantiles que train
    if cols:
        key=pd.Series("",index=te.index)
        for c in cols:
            q=np.quantile(tr[c].dropna(),np.linspace(0,1,(3 if len(cols)>1 else 5)+1)[1:-1]); key=key+"|"+pd.Series(np.searchsorted(q,te[c].values,side="right"),index=te.index).astype(str)
        te["c"]=key
        # cellules train recodees de la meme facon
        keyt=pd.Series("",index=tr.index)
        for c in cols:
            q=np.quantile(tr[c].dropna(),np.linspace(0,1,(3 if len(cols)>1 else 5)+1)[1:-1]); keyt=keyt+"|"+pd.Series(np.searchsorted(q,tr[c].values,side="right"),index=tr.index).astype(str)
        tab=tr.assign(c=keyt).groupby("c").agg(pY=(Ycol,"mean"),pD=(Dcol,"mean"),n=(Ycol,"size"))
    else: te["c"]=0
    m=te.merge(tab,left_on="c",right_index=True,how="left"); m["pY"]=m.pY.fillna(train[Ycol].mean()); m["pD"]=m.pD.fillna(train[Dcol].mean())
    pY=m.pY.clip(1e-3,1-1e-3); pD=m.pD.clip(1e-3,1-1e-3); pD=np.minimum(pD,pY)
    e=pD*(1-pY)/(pY*(1-pD)); w=pD*(1-pD)
    return float((e*w).sum()/w.sum()) if w.sum()>0 else np.nan,len(te)
rowsA=[]
for regle,Ycol,Dcol in (("actuelle, trace = oui","Y","D"),("TWC, trace = non","Y_twc","D_twc")):
    for lab,cols in INFO.items():
        e_in,n=e_max(d,d,cols,Ycol,Dcol)
        oos=[]; 
        for s in (2025,2026):
            e_o,n_o=e_max(d[d.saison!=s],d[d.saison==s],cols,Ycol,Dcol); oos.append(e_o)
        rowsA.append({"regle":regle,"information":lab,"n":n,"e_max_in":e_in,"e_max_oos_2025":oos[0],"e_max_oos_2026":oos[1]})
A=pd.DataFrame(rowsA); A.to_csv(f"{TAB}/optimal_program_bound.csv",index=False); pd.set_option("display.width",250)
print("--- Partie A : borne d'efficacite de couverture (reduction de variance maximale), jour par jour"); print(A.round(3).to_string())
# --- Partie B : simulation dix lieux
cal=pd.read_csv(f"{DATA}/calendar.csv",parse_dates=["date"]); panel=pd.read_csv(f"{DATA}/venues.csv")
d2=d[d.saison.isin([2025,2026])].copy(); d2["sp_ref"]=d2.spread_veille_12h.fillna(d2.spread_veille_12h.median())
def pDY_hat(train,test,cols):
    """P(D | Y = 1, I) par cellule de prevision, estime sur train (jours de pluie), applique a test"""
    tr=train[(train.Y==1)&train[cols].notna().all(1)]
    qs={c:np.quantile(tr[c],[1/3,2/3]) for c in cols}
    def key(df):
        k=pd.Series("",index=df.index)
        for c in cols: k=k+"|"+pd.Series(np.searchsorted(qs[c],df[c].fillna(-1).values,side="right"),index=df.index).astype(str)
        return k
    tab=tr.assign(c=key(tr)).groupby("c").D.mean(); out=key(test).map(tab).fillna(tr.D.mean()); return out.values
def block_indices(n):
    nb=int(math.ceil(n/BLOCK)); starts=rng.integers(0,n-BLOCK+1,(B,nb)); return (starts[:,:,None]+np.arange(BLOCK)[None,None,:]).reshape(B,-1)[:,:n]
rowsB=[]
for v in panel.itertuples():
    for s in (2025,2026):
        ds=d2[d2.saison==s].copy(); train=d[d.saison!=s]
        ds["pdy_cote"]=pDY_hat(train,ds,["pi_veille_12h"]); ds["pdy_prev"]=pDY_hat(train,ds,["p_strict_veille"]); ds["pdy_both"]=pDY_hat(train,ds,["pi_veille_12h","p_strict_veille"])
        ds["pdy_in"]=pDY_hat(d,ds,["pi_veille_12h","p_strict_veille"])   # en echantillon, borne haute
        ds["pdy_const"]=float(train[train.Y==1].D.mean())
        c=cal[(cal.nom==v.nom)&(cal.saison==s)].merge(ds[["date","Y","D","pi_veille_12h","sp_ref","pdy_cote","pdy_prev","pdy_both","pdy_in","pdy_const"]],on="date",how="inner")
        c=c[c.ouvert==1].sort_values("date").reset_index(drop=True); n=len(c); bi=block_indices(n); R=c.R.values; K=c.K.values
        big=c[c.grosse==1].copy(); big["prio"]=np.where((big.date.dt.weekday==5)|(big.ferie_ou_veille==1),0,1); top=np.zeros(n,bool); top[list(big.sort_values(["prio","date"]).head(20).index)]=True
        Yb=c.Y.values[bi].astype(float); Db=c.D.values[bi].astype(float); pib=c.pi_veille_12h.values[bi]; spb=c.sp_ref.values[bi]; quot=~np.isnan(pib)
        cf0=R[None,:]*(1-PERTE*Db)-K[None,:]; r0=cf0.sum(1)
        for info,col in (("constante (FP moyen)","pdy_const"),("cote","pdy_cote"),("prevision soir","pdy_prev"),("cote + prevision soir","pdy_both"),("cote + prevision soir, en echantillon","pdy_in")):
            hb=c[col].values[bi]
            for perim,mask in (("toutes les soirees",np.ones(n,bool)),("20 grosses soirees",top)):
                for k in (0.6,1.0):
                    for frac,ex in ((0.0,"mid"),(0.25,"quart_spread")):
                        for contrat in ("reel","parfait"):
                            if contrat=="parfait" and (info!="constante (FP moyen)" or frac>0): continue
                            e=mask[None,:]&quot
                            if contrat=="reel":
                                hh=k*PERTE*hb; price=np.nan_to_num(pib)+frac*spb; fee=FEE(np.nan_to_num(pib)); pay=Yb
                            else:
                                hh=np.full_like(hb,k*PERTE); price=np.clip(np.nan_to_num(pib)*float(train[train.Y==1].D.mean()),0.01,0.99); fee=FEE(price); pay=Db
                            pnl=np.where(e,hh*R[None,:]*(pay-price-fee),0.0); r1=r0+pnl.sum(1); g=r1-r0
                            rowsB.append({"nom":v.nom,"saison":s,"contrat":contrat,"information":info,"perimetre":perim,"k":k,"execution":ex,"couvertes":float(e.sum(1).mean()),
                                          "engagement":float(np.where(e,hh*R[None,:]*(price+fee),0).sum(1).mean()),"gain_moyen":float(g.mean()),"ic_bas":float(np.percentile(g,2.5)),"ic_haut":float(np.percentile(g,97.5)),
                                          "pire5_sans":float(np.percentile(r0,5)),"pire5_avec":float(np.percentile(r1,5)),"ederington_e":float(1-r1.var()/r0.var()),"R_saison":float(R.sum())})
    print(v.nom,"ok")
bs=pd.DataFrame(rowsB); bs.to_csv(f"{TAB}/optimal_program_simulation.csv",index=False)
bs=bs.assign(gain_pct=100*bs.gain_moyen/bs.R_saison,eng_pct=100*bs.engagement/bs.R_saison,pire_pct=100*(bs.pire5_avec/bs.pire5_sans-1))
g=bs.groupby(["contrat","perimetre","k","execution","information","saison"]).agg(couvertes=("couvertes","median"),eng_pct=("eng_pct","median"),gain_pct=("gain_pct","median"),n_pos=("ic_bas",lambda x:int((x>0).sum())),n_neg=("ic_haut",lambda x:int((x<0).sum())),pire_pct=("pire_pct","median"),e=("ederington_e","median")).reset_index()
print("\n--- Partie B : logiciel optimal, h = k x P(D | Y, I), mediane des dix lieux, gain en % de la recette de saison"); print(g.round(2).to_string())
