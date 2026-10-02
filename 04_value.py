"""04_value.py : H3, valeur de la couverture. h*, efficacite d'Ederington, semi-variance, cout, rejeu de saisons par bootstrap par blocs,
critere de valeur balaye sur c, kappa, F/A ; validation hors echantillon 2025 -> 2026.
Entrees : data/days_prices_<ville>.csv. Sorties : tables/h3_*.csv, figures/fig3_seuil.png, data/resultats_h3.json
"""
import os, json, math
import numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); TAB=f"{HERE}/tables"; FIG=f"{HERE}/figures"
L_GRID=[2000,5000,10000,20000]; R_GRID=[0.25,0.5,0.75,1.0]; C_GRID=[round(x,2) for x in np.arange(0.05,0.901,0.05)]
K_GRID=[0.2,0.5,1.0]; FA_GRID=[0.6,0.75,0.9]; B=5000; BLOCK=7; rng=np.random.default_rng(20260916)
FEE=lambda p:0.07*p*(1-p)

def season_days(df):
    d=df[df.ev_ok&df.day_ok&df.pi.notna()].copy().sort_values("date").reset_index(drop=True)
    d["fee"]=FEE(d.pi); d["pnl"]=d.Y-d.pi-d.fee   # P&L d'un contrat Oui achete la veille
    return d
def hstar(d,L):
    v=np.var(d.Y,ddof=1); return float(np.cov(L*d.D,d.Y,ddof=1)[0,1]/v) if v>0 else np.nan
def season_boot(d,n_s,B=B,block=BLOCK):
    """saisons synthetiques de n_s jours par blocs mobiles de `block` jours tires dans les jours observes (persistance conservee)"""
    n=len(d); nb=int(math.ceil(n_s/block)); D=d.D.values; P=d.pnl.values; Y=d.Y.values
    SD=np.empty(B); SP=np.empty(B)
    for b in range(B):
        starts=rng.integers(0,n-block+1,nb); sel=np.concatenate([np.arange(s,s+block) for s in starts])[:n_s]
        SD[b]=D[sel].sum(); SP[b]=P[sel].sum()
    return SD,SP
def metrics(SD,SP,L,N):
    P0=-L*SD; Pr=P0+N*SP
    v0=P0.var(); vr=Pr.var(); e=1-vr/v0 if v0>0 else np.nan
    sv0=np.mean(np.minimum(P0-P0.mean(),0)**2); svr=np.mean(np.minimum(Pr-Pr.mean(),0)**2)
    cost=P0.mean()-Pr.mean()
    return {"e":e,"semivar_reduction":1-svr/sv0 if sv0>0 else np.nan,"cout_espere":cost,"cout_par_variance_reduite":cost/(v0-vr) if v0>vr else np.nan,"var0":v0,"varr":vr,"E_pertes":L*SD.mean()}
def value(SD,SP,L,N,c,fa,kappa,n_s):
    A=n_s*L/c; F=fa*A
    m0=A-L*SD; mr=m0+N*SP
    S0=np.maximum(0,F-m0); Sr=np.maximum(0,F-mr)
    gain=kappa*(S0.mean()-Sr.mean()); cost=m0.mean()-mr.mean()
    return gain-cost,gain,cost,S0.mean(),Sr.mean()

results={}; t_eff=[]; t_val=[]; t_oos=[]
for city in ["NYC","MIA","CHI"]:
    fn=f"{HERE}/data/days_prices_{city}.csv"
    if not os.path.exists(fn): continue
    df=pd.read_csv(fn,parse_dates=["date"]); d=season_days(df)
    if len(d)<40: print(city,"trop peu de jours avec prix :",len(d)); continue
    N_S_SAISON=153   # jours civils du 1er mai au 30 septembre : le rooftop ouvre chaque soir (definition preenregistree de la saison)
    n_obs=int(round(d.groupby(d.date.dt.year).size().mean()))   # jours observes par an, indicateur de couverture des donnees seulement
    n_s=N_S_SAISON
    rho=float(np.corrcoef(d.D,d.Y)[0,1]); results[city]={"n_jours":len(d),"n_s":n_s,"n_obs_par_an":n_obs,"rho":rho,"rho2":rho**2,"P_D":float(d.D.mean()),"P_Y":float(d.Y.mean()),"pnl_moyen_contrat":float(d.pnl.mean())}
    # verification d'Ederington au niveau journalier : avec un contrat payant Y a prix constant, e(h*) = rho^2 exactement
    L0=10000; h0=hstar(d,L0); P0d=-L0*d.D.values; Phd=P0d+h0*d.Y.values
    results[city]["ederington_journalier"]={"e_h_star":float(1-Phd.var()/P0d.var()),"rho2":rho**2,"ecart":float(1-Phd.var()/P0d.var()-rho**2)}
    print(city,"jours",len(d),"n_s",n_s,"rho",round(rho,3),"rho2",round(rho**2,3),"P&L moyen par contrat",round(d.pnl.mean(),4))
    SD,SP=season_boot(d,n_s)
    # rejeu avec payoff Y seul pour isoler l'effet de la variabilite du prix
    d_y=d.copy(); d_y["pnl"]=d_y.Y; SDy,SPy=season_boot(d_y,n_s)
    results[city]["ederington_saisonnier"]={"e_payoff_Y_seul_h_star":metrics(SDy,SPy,10000,hstar(d,10000))["e"],"e_pnl_reel_h_star":metrics(SD,SP,10000,hstar(d,10000))["e"],"corr_sommes_saison_D_Y":float(np.corrcoef(SDy,SPy)[0,1])}
    for L in L_GRID:
        hs=hstar(d,L); rs=hs/L
        for r in R_GRID+["r*"]:
            N=hs if r=="r*" else r*L
            m=metrics(SD,SP,L,N); m.update({"ville":city,"L":L,"ratio":r,"ratio_val":rs if r=="r*" else r,"N_contrats":N,"h_star":hs}); t_eff.append(m)
    # verification numerique : e maximal = rho^2 (au ratio de variance minimale)
    L=10000; hs=hstar(d,L); emax=metrics(SD,SP,L,hs)["e"]; results[city]["e_max_numerique_L10000_rstar"]=emax; results[city]["ecart_e_max_rho2"]=emax-rho**2
    # critere de valeur : surface c x kappa x F/A, pour L = 10 000, r = r* et r = 1
    for L in [10000]:
        hs=hstar(d,L)
        for rlab,N in [("r*",hs),("1",L)]:
            for kappa in K_GRID:
                for fa in FA_GRID:
                    cstar=None
                    for c in C_GRID:
                        delta,gain,cost,s0,sr=value(SD,SP,L,N,c,fa,kappa,n_s)
                        t_val.append({"ville":city,"L":L,"ratio":rlab,"kappa":kappa,"F_A":fa,"c":c,"delta":delta,"gain_deficit":gain,"cout":cost,"E_S0":s0,"E_Sr":sr,"cree_valeur":delta>0})
                        if cstar is None and delta>0: cstar=c
                    results[city].setdefault("c_star",{})[f"r={rlab},kappa={kappa},F/A={fa}"]=cstar
    # validation hors echantillon : h* sur 2025, efficacite sur 2026 (si les deux existent)
    y=d.date.dt.year
    if (y==2025).any() and (y==2026).any():
        d25=d[y==2025]; d26=d[y==2026]
        for L in [10000]:
            h25=hstar(d25,L); h26=hstar(d26,L)
            SD26,SP26=season_boot(d26,len(d26),B=2000)
            e_in=metrics(*season_boot(d25,len(d25),B=2000),L,h25)["e"]; e_out=metrics(SD26,SP26,L,h25)["e"]; e_own=metrics(SD26,SP26,L,h26)["e"]
            t_oos.append({"ville":city,"L":L,"h_star_2025":h25,"h_star_2026":h26,"e_2025_avec_h2025":e_in,"e_2026_avec_h2025":e_out,"e_2026_avec_h2026":e_own,"n_2025":len(d25),"n_2026":len(d26),
                          "rho_2025":float(np.corrcoef(d25.D,d25.Y)[0,1]),"rho_2026":float(np.corrcoef(d26.D,d26.Y)[0,1])})
    # IC bootstrap sur e et le cout au ratio r*, L = 10 000 : reechantillonnage des jours (blocs) puis recalcul complet, 500 repetitions
    ee=[];cc=[]
    for _ in range(300):
        n=len(d); nb=int(math.ceil(n/BLOCK)); starts=rng.integers(0,n-BLOCK+1,nb); sel=np.concatenate([np.arange(s,s+BLOCK) for s in starts])[:n]
        db=d.iloc[sel].reset_index(drop=True); hs=hstar(db,10000)
        if np.isnan(hs): continue
        m=metrics(*season_boot(db,n_s,B=400),10000,hs); ee.append(m["e"]); cc.append(m["cout_espere"])
    results[city]["e_rstar_L10000"]={"point":emax,"ic_bas":float(np.nanpercentile(ee,2.5)),"ic_haut":float(np.nanpercentile(ee,97.5))}
    results[city]["cout_rstar_L10000"]={"point":metrics(SD,SP,10000,hstar(d,10000))["cout_espere"],"ic_bas":float(np.nanpercentile(cc,2.5)),"ic_haut":float(np.nanpercentile(cc,97.5))}
    # c* selon le scenario de cout espere : point, borne basse et borne haute de l'IC ; le gain de deficit vient du rejeu
    hs=hstar(d,10000); cpt=results[city]["cout_rstar_L10000"]
    for scen,cval in [("point",cpt["point"]),("ic_bas",cpt["ic_bas"]),("ic_haut",cpt["ic_haut"])]:
        for kappa in K_GRID:
            for fa in FA_GRID:
                cstar=None; gains=[]
                for c in C_GRID:
                    delta,gain,cost,s0,sr=value(SD,SP,10000,hs,c,fa,kappa,n_s); gains.append(gain)
                    if cstar is None and kappa*(s0-sr)-cval>0: cstar=c
                results[city].setdefault("c_star_scenarios",{})[f"cout={scen},kappa={kappa},F/A={fa}"]={"c_star":cstar,"gain_deficit_c0.9":gains[-1],"cout":cval}

pd.DataFrame(t_eff).to_csv(f"{TAB}/h3_efficacite.csv",index=False); pd.DataFrame(t_val).to_csv(f"{TAB}/h3_valeur.csv",index=False); pd.DataFrame(t_oos).to_csv(f"{TAB}/h3_hors_echantillon.csv",index=False)
json.dump(results,open(f"{HERE}/data/resultats_h3.json","w"),indent=1,default=str)

# ---------- figure 3 : valeur de la couverture en fonction de c, New York, L = 10 000, r = r*
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
tv=pd.DataFrame(t_val); city="NYC" if (tv.ville=="NYC").any() else tv.ville.iloc[0]
s=tv[(tv.ville==city)&(tv.L==10000)&(tv.ratio=="r*")]
fig,ax=plt.subplots(figsize=(9,5.5))
styles={0.2:":",0.5:"--",1.0:"-"}; widths={0.6:1.0,0.75:1.8,0.9:2.6}
for kappa in K_GRID:
    for fa in FA_GRID:
        g=s[(s.kappa==kappa)&(s.F_A==fa)].sort_values("c")
        ax.plot(g.c,g.delta/10000,ls=styles[kappa],lw=widths[fa],color="black",label=f"kappa = {kappa}, F/A = {fa}")
ax.axhline(0,color="0.5",lw=0.8); ax.axhspan(min(s.delta.min()/10000,-0.01),0,color="0.85",lw=0,zorder=0)
ax.text(0.06,min(s.delta.min()/10000,-0.01)*0.6,"zone de destruction de valeur (delta < 0)",fontsize=8,color="0.3")
ax.set_xlabel("Concentration c : part de la marge annuelle realisee sur les soirees de saison (fraction)")
ax.set_ylabel("Valeur nette par saison, en multiples de L\n(kappa x deficit evite, moins cout espere de la couverture)")
ax.set_title(f"Valeur de la couverture journaliere selon la concentration c, {city}, L = 10 000 $, ratio de variance minimale,\nsaisons de {results[city]['n_s']} soirees rejouees {B} fois par blocs de 7 jours tires dans {results[city]['n_jours']} jours observes",fontsize=8.5,loc="left")
ax.legend(frameon=False,fontsize=7,ncol=3,loc="upper left"); ax.grid(color="0.92")
plt.tight_layout(); plt.savefig(f"{FIG}/fig3_seuil.png",dpi=170); plt.close()
print(pd.DataFrame(t_eff)[(pd.DataFrame(t_eff).L==10000)].round(4).to_string())
print(json.dumps({k:v for k,v in results.items()},indent=1,default=str)[:3000])
