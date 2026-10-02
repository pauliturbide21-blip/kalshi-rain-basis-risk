"""24_contrat_parfait.py : contrefactuel, un contrat Kalshi parfait.
Definition declaree : le contrat paie 1 dollar si et seulement si la soiree est perdue (D_t = 1, definition preenregistree : au moins 1 mm
entre 18 h et 1 h a Central Park). Risque de base nul par construction. Prix la veille a midi :
  regle A (conditionnelle) : pi*_t = pi_t x P(D = 1 | Y = 1), la cote reelle de pluie journaliere multipliee par la part des jours de pluie
                             qui gachent la soiree (1 moins FP, mesure sur l'autre saison pour rester hors echantillon) ;
  regle B (actuarielle inconditionnelle) : pi*_t = P(D = 1) de l'autre saison.
Chargement du teneur de marche lambda dans {0 ; 0,10 ; 0,25}, frais Kalshi 0,07 x pi (1 - pi), ecart de carnet reel en scenario degrade.
Memes hypotheses H-A (liquidite illimitee), H-B (mid), H-C (veille a midi), meme grille de strategies, memes objectifs, meme validation croisee.
Sorties : tables/parfait_optimale.csv, tables/parfait_scenario_bon_sens.csv, figures/fig_contrat_parfait.png/.pdf, data/chemins_parfait.csv
"""
import os, json, math
import numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); TAB=f"{HERE}/tables"; DATA=f"{HERE}/data"; FIG=f"{HERE}/figures"
B=2000; BLOCK=7; rng=np.random.default_rng(20260918)
H_GRID=[round(x,1) for x in np.arange(0,1.01,0.1)]; SEUILS=[0.0,0.1,0.2,0.3,0.4,0.5]
CRITERES=[(sel,s) for sel in ("grosses","toutes") for s in SEUILS]
FA_REF=0.75; FEE=lambda p:0.07*p*(1-p); PERTE=0.5   # part de la recette perdue un soir de pluie
days=pd.read_csv(f"{DATA}/days_prices_NYC.csv",parse_dates=["date"]); days=days[days.ev_ok&days.day_ok].copy(); days["saison"]=days.date.dt.year
days=days[(days.date.dt.month>=5)&(days.date.dt.month<=9)&days.saison.isin([2025,2026])].sort_values("date").reset_index(drop=True)
days["pi_ref"]=days.pi_veille_12h; days["sp_ref"]=days.spread_veille_12h.fillna(days.spread_veille_12h.median())
cal=pd.read_csv(f"{DATA}/calendrier.csv",parse_dates=["date"]); panel=pd.read_csv(f"{DATA}/panel_rooftops.csv")
# parametres de prix estimes sur l'autre saison
par={}
for s in (2025,2026):
    o=days[days.saison==(2026 if s==2025 else 2025)]
    par[s]={"pDY":float(o[o.Y==1].D.mean()),"pD":float(o.D.mean())}
print("parametres de prix (estimes sur l'autre saison) :",par)

def season(nom,s):
    c=cal[(cal.nom==nom)&(cal.saison==s)].merge(days[days.saison==s][["date","Y","D","pi_ref","sp_ref"]],on="date",how="inner")
    return c[c.ouvert==1].sort_values("date").reset_index(drop=True)
def block_indices(n,B_):
    nb=int(math.ceil(n/BLOCK)); starts=rng.integers(0,n-BLOCK+1,(B_,nb)); return (starts[:,:,None]+np.arange(BLOCK)[None,None,:]).reshape(B_,-1)[:,:n]
def evaluate(c,s,regle,lam,frac,boot_idx,contrat="parfait"):
    n=len(c); R=c.R.values; K=c.K.values; grosse=c.grosse.values.astype(bool); Y=c.Y.values.astype(float); D=c.D.values.astype(float); pi=c.pi_ref.values; sp=c.sp_ref.values
    Yb,Db,pib,spb=Y[boot_idx],D[boot_idx],pi[boot_idx],sp[boot_idx]
    cf0=R[None,:]*(1-PERTE*Db)-K[None,:]; A=float(np.sum(R*(1-PERTE*Db.mean())-K)); draw=(FA_REF*A/12)*(c.date.dt.day==1).values.astype(float)[None,:]
    if contrat=="parfait":
        payout=Db; quot=~np.isnan(pib)
        pstar=(np.nan_to_num(pib)*par[s]["pDY"] if regle=="A" else np.full_like(pib,par[s]["pD"]))*(1+lam)
        if regle=="B": quot=np.ones_like(quot)   # prix actuariel toujours disponible
        pstar=np.clip(pstar,0.01,0.99)
    else:
        payout=Yb; quot=~np.isnan(pib); pstar=np.nan_to_num(pib)
    price=pstar+frac*spb; fee=FEE(pstar); pnl=np.where(quot,payout-price-fee,0.0)
    base_cum=np.cumsum(cf0-draw,axis=1); res0=cf0.sum(1); trou0=np.minimum(base_cum.min(1),0.0); out={("aucune",0.0,0.0):(res0,trou0)}
    for sel,seuil in CRITERES:
        elig=(grosse if sel=="grosses" else np.ones(n,bool))[None,:]&quot&(pstar>=seuil)
        hu=np.where(elig,R[None,:]*pnl,0.0); cu=np.cumsum(hu,axis=1)
        for h in H_GRID:
            if h==0: continue
            out[(sel,seuil,h)]=(res0+h*hu.sum(1),np.minimum((base_cum+h*cu).min(1),0.0))
    return out,res0,trou0,pstar,quot
def obj(res,trou): return {"trou_max":float(trou.mean()),"pire_5pct":float(np.percentile(res,5)),"moyenne":float(res.mean())}
rows=[]; bons=[]; chem=[]
for v in panel.itertuples():
    nom=v.nom; cs={s:season(nom,s) for s in (2025,2026)}; bi={s:block_indices(len(cs[s]),B) for s in (2025,2026)}
    for regle in ("A","B"):
        for lam in (0.0,0.10,0.25):
            ev={s:evaluate(cs[s],s,regle,lam,0.0,bi[s]) for s in (2025,2026)}
            tab={(s,k):obj(*ev[s][0][k]) for s in (2025,2026) for k in ev[s][0]}
            for o in ("trou_max","pire_5pct","moyenne"):
                for s_in,s_out in ((2025,2026),(2026,2025)):
                    keys=[k for k in ev[s_in][0] if k[0]!="aucune"]; best=max(keys,key=lambda k:tab[(s_in,k)][o])
                    r_o,t_o=ev[s_out][0][best]; r_b,t_b=ev[s_out][0][("aucune",0.0,0.0)]
                    diff=(t_o-t_b) if o=="trou_max" else (r_o-r_b)
                    if o=="pire_5pct":
                        sub=[np.percentile(r_o[rng.integers(0,B,B)],5)-np.percentile(r_b[rng.integers(0,B,B)],5) for _ in range(300)]; lo,hi=np.percentile(sub,[2.5,97.5]); gain=tab[(s_out,best)][o]-tab[(s_out,("aucune",0.0,0.0))][o]
                    else: lo,hi=np.percentile(diff,[2.5,97.5]); gain=float(diff.mean())
                    Rs=float(cs[s_out].R.sum())
                    rows.append({"nom":nom,"regle_prix":regle,"chargement":lam,"objectif":o,"saison_choix":s_in,"saison_evaluation":s_out,"critere":best[0],"seuil":best[1],"h":best[2],
                                 "sans_OOS":tab[(s_out,("aucune",0.0,0.0))][o],"avec_OOS":tab[(s_out,best)][o],"gain_OOS":gain,"ic_bas":float(lo),"ic_haut":float(hi),"gain_pct_R":100*gain/Rs,
                                 "moyenne_sans":tab[(s_out,("aucune",0.0,0.0))]["moyenne"],"moyenne_avec":tab[(s_out,best)]["moyenne"]})
    # scenario de bon sens : 20 plus grosses soirees, achat si pi* >= seuil, h = 0,6, regle A, chargement 0 et 0,10, mid et quart de spread ; saison 2026
    c=cs[2026]; big=c[c.grosse==1].copy(); big["prio"]=np.where((big.date.dt.weekday==5)|(big.ferie_ou_veille==1),0,1); top=set(big.sort_values(["prio","date"]).head(20).index)
    for contrat in ("reel","parfait"):
        for lam in ((0.0,) if contrat=="reel" else (0.0,0.10)):
            for frac,ex in ((0.0,"mid"),(0.25,"quart_spread")):
                for seuil in ((0.4,0.5) if contrat=="reel" else (0.1,0.2,0.3)):
                    out,res0,trou0,pstar,quot=evaluate(c,2026,"A",lam,frac,bi[2026],contrat)
                    n=len(c); R=c.R.values; elig=np.zeros(n,bool); elig[list(top)]=True
                    e=elig[None,:]&quot&(pstar>=seuil); payout=(c.D.values if contrat=="parfait" else c.Y.values)[bi[2026]].astype(float)
                    price=pstar+frac*c.sp_ref.values[bi[2026]]; pnl=np.where(e,0.6*PERTE*R[None,:]*(payout-price-FEE(pstar)),0.0)
                    cf0=R[None,:]*(1-PERTE*c.D.values[bi[2026]])-c.K.values[None,:]; r0=cf0.sum(1); r1=r0+pnl.sum(1); g=r1-r0
                    bons.append({"nom":nom,"contrat":contrat,"chargement":lam,"execution":ex,"seuil":seuil,"couvertes":float(e.sum(1).mean()),"engagement":float(np.where(e,0.6*PERTE*R[None,:]*(price+FEE(pstar)),0).sum(1).mean()),
                                 "gain_moyen":float(g.mean()),"ic_bas":float(np.percentile(g,2.5)),"ic_haut":float(np.percentile(g,97.5)),"pire5_sans":float(np.percentile(r0,5)),"pire5_avec":float(np.percentile(r1,5)),
                                 "ederington_e":float(1-r1.var()/r0.var()),"R_saison":float(R.sum())})
    # chemin realise 2026, contrat parfait regle A, chargement 0, reglage grosses / seuil 0,2 / h = 0,6 (et contrat reel meme reglage pour comparaison)
    for contrat in ("reel","parfait"):
        out,res0,trou0,pstar,quot=evaluate(c,2026,"A",0.0,0.0,np.arange(len(c))[None,:],contrat)
        R=c.R.values; e=(c.grosse.values.astype(bool))&quot[0]&(pstar[0]>=(0.2 if contrat=="parfait" else 0.4)); payout=(c.D.values if contrat=="parfait" else c.Y.values).astype(float)
        hed=np.where(e,0.6*PERTE*R*(payout-pstar[0]-FEE(pstar[0])),0.0); rev0=R*(1-PERTE*c.D.values)
        for i,r in enumerate(c.itertuples()): chem.append({"nom":nom,"contrat":contrat,"date":r.date.date().isoformat(),"D":int(r.D),"couverte":int(e[i]),"cum_sans":rev0[:i+1].sum(),"cum_avec":(rev0+hed)[:i+1].sum()})
    print(nom,"ok")
opt=pd.DataFrame(rows); opt.to_csv(f"{TAB}/parfait_optimale.csv",index=False); bs=pd.DataFrame(bons); bs.to_csv(f"{TAB}/parfait_scenario_bon_sens.csv",index=False); ch=pd.DataFrame(chem); ch.to_csv(f"{DATA}/chemins_parfait.csv",index=False)
pd.set_option("display.width",250)
print("\n--- reglage optimal hors echantillon, mediane des dix lieux, gain en % de la recette de saison")
g=opt.groupby(["regle_prix","chargement","objectif","saison_choix"]).agg(gain_pct=("gain_pct_R","median"),n_pos=("ic_bas",lambda x:int((x>0).sum())),n_neg=("ic_haut",lambda x:int((x<0).sum())),h=("h","median"),crit=("critere",lambda x:x.mode()[0])).reset_index()
print(g.round(2).to_string())
print("\n--- scenario de bon sens, 20 grosses soirees, h = 0,6, saison 2026, mediane des dix lieux")
gb=bs.assign(gain_pct=100*bs.gain_moyen/bs.R_saison,eng_pct=100*bs.engagement/bs.R_saison,pire_pct=100*(bs.pire5_avec/bs.pire5_sans-1)).groupby(["contrat","chargement","execution","seuil"]).agg(couvertes=("couvertes","median"),eng_pct=("eng_pct","median"),gain_pct=("gain_pct","median"),n_pos=("ic_bas",lambda x:int((x>0).sum())),n_neg=("ic_haut",lambda x:int((x<0).sum())),pire_pct=("pire_pct","median"),e=("ederington_e","median")).reset_index()
print(gb.round(2).to_string())
# figure : 230 Fifth 2026, contrat reel contre contrat parfait
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.dates as mdates
plt.rcParams.update({"font.size":9,"axes.spines.top":False,"axes.spines.right":False}); BLEU="#2a78d6"; ORANGE="#eb6834"; GRIS="#6c6b66"
fig,axes=plt.subplots(1,2,figsize=(13,5),sharey=True)
for ax,contrat,lab in zip(axes,("reel","parfait"),("Contrat reel Kalshi (pluie journaliere, cote >= 0,4)","Contrat parfait (paie si soiree perdue, cote >= 0,2)")):
    g_=ch[(ch.nom=="230 Fifth")&(ch.contrat==contrat)].copy(); g_["date"]=pd.to_datetime(g_.date)
    ax.plot(g_.date,g_.cum_sans,color=BLEU,lw=1.8,label="Sans couverture"); ax.plot(g_.date,g_.cum_avec,color=ORANGE,lw=1.8,ls="--",label="Avec couverture, grosses soirees, h = 0,6")
    cov=g_[g_.couverte==1]; ax.scatter(cov.date,cov.cum_avec,s=14,color=ORANGE,edgecolor="black",linewidth=0.4,zorder=3,label=f"Soiree couverte (n = {len(cov)})")
    lost=g_[g_.D==1]; ax.scatter(lost.date,lost.cum_sans,s=18,marker="v",color="black",zorder=4,label=f"Soiree gachee (n = {len(lost)})")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:f"{x/1e6:.1f} M")); ax.grid(color="#eeeeee"); ax.set_axisbelow(True)
    f0=g_.cum_sans.iloc[-1]; f1=g_.cum_avec.iloc[-1]; ax.set_title(f"{lab}\nfin de saison {f0/1e6:.2f} M sans, {f1/1e6:.2f} M avec ({100*(f1/f0-1):+.1f} %)",loc="left",fontsize=9)
    ax.set_xlabel("Saison 2026, 1er mai au 15 septembre"); ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
axes[0].set_ylabel("Chiffre d'affaires cumule, 230 Fifth (millions de dollars)"); axes[0].legend(frameon=False,fontsize=8,loc="upper left")
fig.suptitle("230 Fifth, saison 2026 observee : contrat reel contre contrat parfait. Hypotheses : liquidite illimitee, execution au mid, achat la veille a midi, prix conditionnel sans chargement.",fontsize=9,x=0.01,ha="left")
plt.tight_layout(rect=(0,0,1,0.93)); plt.savefig(f"{FIG}/fig_contrat_parfait.png",dpi=160); plt.savefig(f"{FIG}/fig_contrat_parfait.pdf"); plt.close()
