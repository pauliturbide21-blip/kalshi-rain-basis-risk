"""23_figures.py : figure centrale par rooftop (deux saisons) et figure de synthese.
Chiffre d'affaires cumule au fil de tous les jours de saison, sans couverture (bleu, trait plein) et avec couverture (orange, tirets),
soirees effectivement couvertes marquees. Reglage : celui retenu sur l'autre saison pour l'objectif trou de tresorerie (grosses soirees).
Palette dataviz : bleu #2a78d6, orange #eb6834 ; lisible en noir et blanc par le style de trait ; axes nommes avec unites ; effectifs indiques.
Sorties : figures/fig_rooftop_<i>.png et .pdf, figures/fig_synthese.png et .pdf
"""
import os, re, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
HERE=os.path.dirname(os.path.abspath(__file__)); FIG=f"{HERE}/figures"; os.makedirs(FIG,exist_ok=True)
BLEU="#2a78d6"; ORANGE="#eb6834"
plt.rcParams.update({"font.size":9,"axes.spines.top":False,"axes.spines.right":False,"axes.edgecolor":"#9a9a96","axes.labelcolor":"#52514e","xtick.color":"#52514e","ytick.color":"#52514e","figure.facecolor":"white","axes.facecolor":"white"})
ch=pd.read_csv(f"{HERE}/data/chemins_saison.csv",parse_dates=["date"])
kfmt=FuncFormatter(lambda x,_: f"{x/1e6:.1f} M" if abs(x)>=1e6 else f"{x/1e3:.0f} k")
HYP="Hypotheses : liquidite illimitee, execution au prix milieu, achat la veille a midi. Borne haute."
def panel_plot(ax,g,titre):
    g=g.sort_values("date"); x=g.date
    ax.plot(x,g.cum_recette_sans,color=BLEU,lw=1.8,ls="-",label="Sans couverture")
    ax.plot(x,g.cum_recette_avec,color=ORANGE,lw=1.8,ls="--",label="Avec couverture")
    cov=g[g.couverte==1]
    ax.scatter(cov.date,cov.cum_recette_avec,s=14,color=ORANGE,edgecolor="black",linewidth=0.4,zorder=3,label=f"Soiree couverte (n = {len(cov)})")
    lost=g[g.D==1]
    ax.scatter(lost.date,lost.cum_recette_sans,s=18,marker="v",color="black",zorder=4,label=f"Soiree gachee (n = {len(lost)})")
    ax.yaxis.set_major_formatter(kfmt); ax.grid(color="#eeeeee",lw=0.6); ax.set_axisbelow(True)
    fin0=g.cum_recette_sans.iloc[-1]; finh=g.cum_recette_avec.iloc[-1]
    ax.set_title(f"{titre}\n{len(g)} soirees ; fin de saison : {fin0/1e6:.2f} millions de dollars sans couverture, {finh/1e6:.2f} avec (ecart {100*(finh/fin0-1):+.1f} %)",loc="left",fontsize=8.5)
noms=list(ch.nom.unique())
for i,nom in enumerate(noms,1):
    fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=False)
    for ax,s in zip(axes,(2025,2026)):
        g=ch[(ch.nom==nom)&(ch.saison==s)]
        if len(g)==0: ax.set_visible(False); continue
        reg=f"reglage choisi sur {2026 if s==2025 else 2025} : {g.critere.iloc[0]}, cote >= {g.seuil.iloc[0]:.1f}, h = {g.h.iloc[0]:.1f}"
        panel_plot(ax,g,f"Saison {s}, {reg}")
        ax.set_ylabel("Chiffre d'affaires cumule (millions ou milliers de dollars)")
    axes[-1].set_xlabel("Jour de saison (1er mai au 30 septembre 2025 ; 1er mai au 15 septembre 2026)")
    axes[0].legend(frameon=False,fontsize=8,loc="upper left")
    fig.suptitle(f"{nom} : chiffre d'affaires cumule, avec et sans couverture par contrats de pluie Kalshi.\n{HYP}",fontsize=9,x=0.01,ha="left")
    plt.tight_layout(rect=(0,0,1,0.94)); safe=re.sub(r"[^a-z0-9]+","_",nom.lower()).strip("_")
    plt.savefig(f"{FIG}/fig_rooftop_{i:02d}_{safe}.png",dpi=160); plt.savefig(f"{FIG}/fig_rooftop_{i:02d}_{safe}.pdf"); plt.close()
# synthese : indice 100 = cumul sans couverture en fin de saison, moyenne des dix lieux, deux saisons
fig,axes=plt.subplots(1,2,figsize=(12,4.8))
for ax,s in zip(axes,(2025,2026)):
    curves0=[];curvesh=[];n=0
    for nom in noms:
        g=ch[(ch.nom==nom)&(ch.saison==s)].sort_values("date")
        if len(g)==0: continue
        base=g.cum_recette_sans.iloc[-1]; t=np.linspace(0,1,len(g))
        curves0.append(np.interp(np.linspace(0,1,100),t,g.cum_recette_sans/base*100)); curvesh.append(np.interp(np.linspace(0,1,100),t,g.cum_recette_avec/base*100)); n+=1
    m0=np.mean(curves0,axis=0); mh=np.mean(curvesh,axis=0); lo=np.min(curvesh,axis=0); hi=np.max(curvesh,axis=0)
    xx=np.linspace(0,100,100)
    ax.fill_between(xx,lo,hi,color=ORANGE,alpha=0.15,lw=0,label="Etendue des dix lieux, avec couverture")
    ax.plot(xx,m0,color=BLEU,lw=2,ls="-",label="Sans couverture, moyenne des dix lieux"); ax.plot(xx,mh,color=ORANGE,lw=2,ls="--",label="Avec couverture, moyenne des dix lieux")
    ax.set_title(f"Saison {s} : n = {n} rooftops, fin de saison avec couverture = {mh[-1]:.1f} (sans = 100)",loc="left",fontsize=9)
    ax.set_xlabel("Avancement de la saison (pour cent des soirees)"); ax.set_ylabel("Chiffre d'affaires cumule, indice 100 = fin de saison sans couverture"); ax.grid(color="#eeeeee",lw=0.6); ax.set_axisbelow(True)
axes[0].legend(frameon=False,fontsize=8,loc="upper left")
fig.suptitle(f"Synthese des dix rooftops : lissage et niveau final du chiffre d'affaires cumule.\n{HYP}",fontsize=9,x=0.01,ha="left")
plt.tight_layout(rect=(0,0,1,0.92)); plt.savefig(f"{FIG}/fig_synthese.png",dpi=160); plt.savefig(f"{FIG}/fig_synthese.pdf"); plt.close()
print("figures :",len(noms),"lieux + synthese")
