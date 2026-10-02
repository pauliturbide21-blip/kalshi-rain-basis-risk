"""22_strategie.py : recherche de la meilleure strategie de couverture, dix rooftops, deux saisons.
Hypotheses de travail (bornes hautes, rappelees dans chaque sortie) :
  H-A liquidite illimitee : le gerant achete la taille voulue (open interest median reel a l'heure d'achat : 2 contrats sur l'ancienne serie).
  H-B execution au prix milieu : ordre limite servi au mid ; l'ecart de carnet est rapporte en scenario degrade (quart et demi-ecart).
  H-C achat la veille a midi : aucune serie a plusieurs jours n'existe pour New York sur l'historique (serie week-end depuis le 17 aout 2026 seulement).
Regles declarees :
  - soiree gachee D_t : definition preenregistree (au moins 1 mm entre 18 h et 1 h a Central Park) ;
  - flux de la soiree sans couverture : R x (1 - D) - K (la recette est perdue, le cout engage est paye) ; sensibilite : perte partielle 50 % ;
  - couverture : N = h x R contrats Oui achetes la veille a midi au prix pi (dernier echange, sinon mid), frais 0,07 x pi x (1 - pi) ; payout N x Y ;
  - jours sans cotation a l'heure d'achat : soiree non couvrable, comptee ; sensibilite : achat le jour meme a 9 h ;
  - charges fixes : F = (F/A) x A avec A la marge de saison attendue, prelevees par douziemes le 1er de chaque mois de saison ; F/A de reference 0,75, grille 0,6 et 0,9 ;
  - trois objectifs : (1) trou de tresorerie maximal (minimum du cumul de tresorerie en saison), (2) resultat de la pire saison sur vingt (5e centile), (3) resultat moyen ;
  - reglage choisi sur une saison, evalue sur l'autre, dans les deux sens ; bootstrap par blocs de 7 jours, 2 000 saisons.
Sorties : tables/strategie_grille.csv, tables/strategie_optimale.csv, tables/conditions.csv, data/chemins_saison.csv, data/resultats_strategie.json
"""
import os, json, math, itertools
import numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); TAB=f"{HERE}/tables"; DATA=f"{HERE}/data"
B=2000; BLOCK=7; rng=np.random.default_rng(20260918)
H_GRID=[round(x,1) for x in np.arange(0,1.01,0.1)]
SEUILS=[0.0,0.2,0.3,0.4,0.5,0.6]
CRITERES=[(sel,s) for sel in ("grosses","toutes") for s in SEUILS]   # (soirees eligibles, seuil de cote)
FA_REF=0.75; FA_GRID=[0.6,0.75,0.9]; PERTE_REF=0.5; PERTE_GRID=[0.5,0.3,1.0]   # part de la recette perdue un soir de pluie : 0,5 central, 0,3 et 1,0 en sensibilite
EXEC={"mid":0.0,"quart_spread":0.25,"demi_spread":0.5}
ACHAT_REF="veille_12h"; ACHAT_ALT="jour_9h"
FEE=lambda p:0.07*p*(1-p)

days=pd.read_csv(f"{DATA}/days_prices_NYC.csv",parse_dates=["date"])
days=days[days.ev_ok&days.day_ok].copy(); days["saison"]=days.date.dt.year
days=days[(days.date.dt.month>=5)&(days.date.dt.month<=9)&days.saison.isin([2025,2026])].sort_values("date").reset_index(drop=True)
days["pi_ref"]=days[f"pi_{ACHAT_REF}"]; days["pi_alt"]=days[f"pi_{ACHAT_ALT}"]; days["sp_ref"]=days[f"spread_{ACHAT_REF}"].fillna(days[f"spread_{ACHAT_REF}"].median()); days["sp_alt"]=days[f"spread_{ACHAT_ALT}"].fillna(days[f"spread_{ACHAT_ALT}"].median())
cal=pd.read_csv(f"{DATA}/calendrier.csv",parse_dates=["date"])
panel=pd.read_csv(f"{DATA}/panel_rooftops.csv")
print("jours de saison observes :",days.groupby("saison").size().to_dict(),"| sans cotation la veille a midi :",days.groupby("saison").pi_ref.apply(lambda x:int(x.isna().sum())).to_dict(),"| sans cotation le jour a 9 h :",days.groupby("saison").pi_alt.apply(lambda x:int(x.isna().sum())).to_dict())

def season_arrays(nom,saison,achat="ref"):
    """aligne le calendrier du lieu sur les jours observes de la saison ; renvoie les tableaux sur les jours d'ouverture observes"""
    c=cal[(cal.nom==nom)&(cal.saison==saison)].merge(days[days.saison==saison][["date","Y","D",f"pi_{achat}",f"sp_{achat}"]],on="date",how="inner")
    c=c[c.ouvert==1].sort_values("date").reset_index(drop=True)
    return c
def block_indices(n,B_,block=BLOCK):
    nb=int(math.ceil(n/block)); starts=rng.integers(0,n-block+1,(B_,nb))
    idx=(starts[:,:,None]+np.arange(block)[None,None,:]).reshape(B_,-1)[:,:n]
    return idx
def evaluate(c,achat,fa,perte,exec_frac,boot_idx=None):
    """calcule pour chaque critere et chaque h : resultat de saison et trou de tresorerie, sur les jours observes (boot_idx=None) ou rejoues."""
    n=len(c); R=c.R.values.astype(float); K=c.K.values.astype(float); grosse=c.grosse.values.astype(bool)
    Y=c.Y.values.astype(float); D=c.D.values.astype(float); pi=c[f"pi_{achat}"].values.astype(float); sp=c[f"sp_{achat}"].values.astype(float)
    if boot_idx is None: boot_idx=np.arange(n)[None,:]
    Yb=Y[boot_idx]; Db=D[boot_idx]; pib=pi[boot_idx]; spb=sp[boot_idx]      # meteo et prix rejoues, calendrier fixe
    cf0=R[None,:]*(1-perte*Db)-K[None,:]                                  # flux sans couverture
    A=float(np.sum(R*(1-perte*Db.mean())-K))                                  # marge de saison attendue (sur la frequence rejouee)
    F_m=fa*A/12.0; first_of_month=(c.date.dt.day==1).values.astype(float)
    draw=F_m*first_of_month[None,:]
    quotable=~np.isnan(pib); price=np.where(quotable,pib+exec_frac*spb,np.nan); fee=np.where(quotable,FEE(np.nan_to_num(pib)),0.0)
    pnl=np.where(quotable,Yb-np.nan_to_num(price)-fee,0.0)               # P&L d'un contrat ; 0 si non couvrable
    out={}
    base_cum=np.cumsum(cf0-draw,axis=1); res0=cf0.sum(axis=1); trou0=np.minimum(base_cum.min(axis=1),0.0)
    out[("aucune",0.0,0.0)]=(res0,trou0)
    for sel,s in CRITERES:
        elig=(grosse if sel=="grosses" else np.ones(n,bool))[None,:]&quotable&(np.nan_to_num(pib)>=s)
        hedge_unit=np.where(elig,R[None,:]*pnl,0.0)                        # P&L de couverture pour h = 1
        cum_unit=np.cumsum(hedge_unit,axis=1)
        for h in H_GRID:
            if h==0: continue
            res=res0+h*hedge_unit.sum(axis=1); cum=base_cum+h*cum_unit; trou=np.minimum(cum.min(axis=1),0.0)
            out[(sel,s,h)]=(res,trou)
    return out,res0,trou0
def objectives(res,trou):
    return {"trou_max":float(np.mean(trou)),"pire_5pct":float(np.percentile(res,5)),"moyenne":float(np.mean(res))}
OBJ_SIGN={"trou_max":1,"pire_5pct":1,"moyenne":1}   # tous a maximiser (le trou est negatif, on le rapproche de zero)

grille=[]; optimal=[]; chemins=[]; conditions=[]; summary={"hypotheses":["H-A liquidite illimitee","H-B execution au prix milieu (spread en scenario degrade)","H-C achat la veille a midi, aucune serie a plusieurs jours pour New York"],"lieux":{}}
for v in panel.itertuples():
    nom=v.nom; summary["lieux"][nom]={}
    cs={s:season_arrays(nom,s,"ref") for s in (2025,2026)}
    if any(len(c)<30 for c in cs.values()): print(nom,"saison trop courte"); continue
    boots={s:block_indices(len(cs[s]),B) for s in (2025,2026)}
    evals={s:evaluate(cs[s],"ref",FA_REF,PERTE_REF,0.0,boots[s]) for s in (2025,2026)}
    # grille complete par saison (rejeu) : valeur de chaque objectif pour chaque reglage
    tab={}
    for s in (2025,2026):
        out,res0,trou0=evals[s]
        for key,(res,trou) in out.items():
            o=objectives(res,trou); tab[(s,key)]=o
            grille.append({"nom":nom,"saison":s,"critere":key[0],"seuil":key[1],"h":key[2],**o,"n_soirees":len(cs[s]),"n_couvrables":int((~np.isnan(cs[s].pi_ref.values)).sum())})
    # choix du reglage sur une saison, evaluation sur l'autre, avec IC bootstrap sur le gain hors echantillon
    for obj in ["trou_max","pire_5pct","moyenne"]:
        for s_in,s_out in [(2025,2026),(2026,2025)]:
            keys=[k for k in evals[s_in][0] if k[0]!="aucune"]
            best=max(keys,key=lambda k:tab[(s_in,k)][obj])
            base_in=tab[(s_in,("aucune",0.0,0.0))][obj]; base_out=tab[(s_out,("aucune",0.0,0.0))][obj]
            val_in=tab[(s_in,best)][obj]; val_out=tab[(s_out,best)][obj]
            # IC sur le gain hors echantillon : difference par replication
            res_o,trou_o=evals[s_out][0][best]; res_b,trou_b=evals[s_out][0][("aucune",0.0,0.0)]
            diff=(trou_o-trou_b) if obj=="trou_max" else (res_o-res_b)
            if obj=="pire_5pct":
                # IC du 5e centile par sous-bootstrap des replications
                sub=[np.percentile(res_o[rng.integers(0,B,B)],5)-np.percentile(res_b[rng.integers(0,B,B)],5) for _ in range(300)]
                lo,hi=float(np.percentile(sub,2.5)),float(np.percentile(sub,97.5)); gain_out=val_out-base_out
            else:
                lo,hi=float(np.percentile(diff,2.5)),float(np.percentile(diff,97.5)); gain_out=float(diff.mean())
            # cout moyen de la couverture hors echantillon (prime plus frais engages) et resultat moyen
            c=cs[s_out]; elig=((c.grosse.values.astype(bool) if best[0]=="grosses" else np.ones(len(c),bool))&(~np.isnan(c.pi_ref.values))&(np.nan_to_num(c.pi_ref.values)>=best[1]))
            prime=float(np.sum(best[2]*c.R.values[elig]*(np.nan_to_num(c.pi_ref.values[elig])+FEE(np.nan_to_num(c.pi_ref.values[elig])))))
            optimal.append({"nom":nom,"objectif":obj,"saison_choix":s_in,"saison_evaluation":s_out,"critere":best[0],"seuil":best[1],"h":best[2],
                            "valeur_sans_couverture_IS":base_in,"valeur_avec_IS":val_in,"gain_IS":val_in-base_in,
                            "valeur_sans_couverture_OOS":base_out,"valeur_avec_OOS":val_out,"gain_OOS":gain_out,"gain_OOS_ic_bas":lo,"gain_OOS_ic_haut":hi,
                            "moyenne_OOS_sans":tab[(s_out,("aucune",0.0,0.0))]["moyenne"],"moyenne_OOS_avec":tab[(s_out,best)]["moyenne"],
                            "prime_saison_OOS":prime,"n_soirees_couvertes_OOS":int(elig.sum())})
            summary["lieux"][nom][f"{obj}_{s_in}->{s_out}"]={"reglage":best,"gain_OOS":gain_out,"ic":[lo,hi]}
    # chemins realises (jours reellement observes) pour les figures : reglage choisi sur l'autre saison pour l'objectif trou de tresorerie
    for s_eval,s_choice in [(2026,2025),(2025,2026)]:
        row=[r for r in optimal if r["nom"]==nom and r["objectif"]=="trou_max" and r["saison_choix"]==s_choice][0]
        c=cs[s_eval]; out,_,_=evaluate(c,"ref",FA_REF,PERTE_REF,0.0,None)
        key=(row["critere"],row["seuil"],row["h"]); R=c.R.values; K=c.K.values; pi=c.pi_ref.values
        elig=((c.grosse.values.astype(bool) if key[0]=="grosses" else np.ones(len(c),bool))&(~np.isnan(pi))&(np.nan_to_num(pi)>=key[1]))
        cf0=R*(1-PERTE_REF*c.D.values)-K; pnl=np.where(~np.isnan(pi),c.Y.values-np.nan_to_num(pi)-FEE(np.nan_to_num(pi)),0.0); hed=np.where(elig,key[2]*R*pnl,0.0)
        rev0=R*(1-PERTE_REF*c.D.values); revh=rev0+hed
        for i,r in enumerate(c.itertuples()):
            chemins.append({"nom":nom,"saison":s_eval,"date":r.date.date().isoformat(),"grosse":int(r.grosse),"D":int(r.D),"Y":int(r.Y),"pi":pi[i],"couverte":int(elig[i]),"h":key[2],"critere":key[0],"seuil":key[1],
                            "recette_sans":rev0[i],"recette_avec":revh[i],"cf_sans":cf0[i],"cf_avec":cf0[i]+hed[i],"cum_recette_sans":rev0[:i+1].sum(),"cum_recette_avec":revh[:i+1].sum(),"cum_cf_sans":cf0[:i+1].sum(),"cum_cf_avec":(cf0+hed)[:i+1].sum()})
    # conditions cumulatives (3.6) : gain moyen et IC hors echantillon (2025 -> 2026) pour un ensemble de reglages et d'executions, objectif trou et moyenne
    c26=cs[2026]; bi=boots[2026]
    for ex,frac in EXEC.items():
        for achat in ("ref","alt"):
            c26a=season_arrays(nom,2026,achat)
            if len(c26a)!=len(c26): bi_a=block_indices(len(c26a),B)
            else: bi_a=bi
            out,res0,trou0=evaluate(c26a,achat,FA_REF,PERTE_REF,frac,bi_a)
            for sel in ("grosses","toutes"):
                for s in (0.0,0.4):
                    for h in (0.3,0.6,1.0):
                        res,trou=out[(sel,s,h)]
                        conditions.append({"nom":nom,"capacite":v.capacite,"achat":ACHAT_REF if achat=="ref" else ACHAT_ALT,"execution":ex,"critere":sel,"seuil":s,"h":h,
                                           "gain_trou_moyen":float((trou-trou0).mean()),"gain_trou_ic_bas":float(np.percentile(trou-trou0,2.5)),"gain_trou_ic_haut":float(np.percentile(trou-trou0,97.5)),
                                           "gain_resultat_moyen":float((res-res0).mean()),"gain_resultat_ic_bas":float(np.percentile(res-res0,2.5)),"gain_resultat_ic_haut":float(np.percentile(res-res0,97.5)),
                                           "pire_5pct_sans":float(np.percentile(res0,5)),"pire_5pct_avec":float(np.percentile(res,5)),"resultat_moyen_sans":float(res0.mean())})
    # sensibilites F/A et perte partielle, objectif trou, reglage grosses / 0,4 / 0,6
    for fa in FA_GRID:
        for perte in PERTE_GRID:
            out,res0,trou0=evaluate(c26,"ref",fa,perte,0.0,bi); res,trou=out[("grosses",0.4,0.6)]
            conditions.append({"nom":nom,"capacite":v.capacite,"achat":ACHAT_REF,"execution":"mid","critere":"grosses","seuil":0.4,"h":0.6,"F_A":fa,"perte":perte,
                               "gain_trou_moyen":float((trou-trou0).mean()),"gain_trou_ic_bas":float(np.percentile(trou-trou0,2.5)),"gain_trou_ic_haut":float(np.percentile(trou-trou0,97.5)),
                               "gain_resultat_moyen":float((res-res0).mean()),"gain_resultat_ic_bas":float(np.percentile(res-res0,2.5)),"gain_resultat_ic_haut":float(np.percentile(res-res0,97.5)),
                               "pire_5pct_sans":float(np.percentile(res0,5)),"pire_5pct_avec":float(np.percentile(res,5)),"resultat_moyen_sans":float(res0.mean())})
    print(nom,"ok")
pd.DataFrame(grille).to_csv(f"{TAB}/strategie_grille.csv",index=False)
opt=pd.DataFrame(optimal); opt.to_csv(f"{TAB}/strategie_optimale.csv",index=False)
pd.DataFrame(conditions).to_csv(f"{TAB}/conditions.csv",index=False)
pd.DataFrame(chemins).to_csv(f"{DATA}/chemins_saison.csv",index=False)
json.dump(summary,open(f"{DATA}/resultats_strategie.json","w"),indent=1,default=str)
pd.set_option("display.width",250)
print(opt[opt.saison_choix==2025][["nom","objectif","critere","seuil","h","gain_IS","gain_OOS","gain_OOS_ic_bas","gain_OOS_ic_haut","prime_saison_OOS","moyenne_OOS_sans","moyenne_OOS_avec"]].round(0).to_string())
