# -*- coding: utf-8 -*-
"""Figure : le repli de tresorerie en cours de saison, avec et sans couverture.
Ce qui gene un exploitant n'est pas le resultat final, c'est le trou au milieu."""
import pandas as pd, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter

FIXE   = 10000.
MB, MP = 15000.-FIXE, -5000.-FIXE     # +5 000 si belle soiree, -15 000 si gachee
ECART  = MB - MP
H      = 0.70      # taille qui minimise le trou de tresorerie
SEUIL  = 0.30      # on ne couvre pas les soirees ou la pluie est tres improbable
N, NSIM = 20, 40000

SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e5e4e0'
S1, S2 = '#2a78d6', '#eb6834'

rng = np.random.default_rng(12)
d = pd.read_csv('data/days_prices_NYC.csv', parse_dates=['date']); d['mois']=d.date.dt.month
s = d[(d.mois>=5)&(d.mois<=9)&d.pi.notna()&d.Y.notna()&d.D.notna()].copy(); s['fee']=s.fee.fillna(0)
pi,Y,D,fee = s.pi.values,s.Y.values,s.D.values,s.fee.values
idx = rng.integers(0,len(s),size=(NSIM,N))
PI,YY,DD,FE = pi[idx],Y[idx],D[idx],fee[idx]
nuit_sans = MB*(1-DD) + MP*DD
nuit_avec = nuit_sans + H*ECART*(YY - PI - FE)*(PI >= SEUIL)
cum_sans, cum_avec = np.cumsum(nuit_sans,axis=1), np.cumsum(nuit_avec,axis=1)

def repli(cum):
    """distance sous le plus haut niveau de tresorerie deja atteint"""
    pic = np.maximum.accumulate(np.concatenate([np.zeros((len(cum),1)), cum],axis=1),axis=1)[:,1:]
    return pic - cum

dd_sans, dd_avec = repli(cum_sans), repli(cum_avec)
mx_sans, mx_avec = dd_sans.max(axis=1), dd_avec.max(axis=1)
x = np.arange(1,N+1)

fig,(ax1,ax2) = plt.subplots(1,2, figsize=(11.5,4.6), facecolor=SURFACE)
k = FuncFormatter(lambda v,_: f"{v/1000:,.0f} k")

# ---- Panneau 1 : le repli au fil de la saison, cas defavorable ----
ax1.set_facecolor(SURFACE)
for dd,col,lab in ((dd_sans,S1,"sans\ncouverture"),(dd_avec,S2,"avec\ncouverture")):
    q90 = np.percentile(dd,90,axis=0)
    ax1.plot(x, q90, color=col, lw=2.6, zorder=3, solid_capstyle='round')
    ax1.scatter([N],[q90[-1]], s=34, color=col, zorder=4, edgecolor=SURFACE, linewidth=2)
    ax1.annotate(lab,(N,q90[-1]),textcoords="offset points",xytext=(11,0),
                 ha='left',va='center',fontsize=9.5,color=col,weight='bold')
ax1.set_title("Le trou de tresorerie, dans une saison sur dix", fontsize=11.5, color=INK,
              loc='left', weight='bold', pad=10)
ax1.set_xlabel("soiree de la saison", fontsize=9, color=INK2)
ax1.set_ylabel("repli sous le plus haut atteint (dollars)", fontsize=9, color=INK2)
ax1.yaxis.set_major_formatter(k); ax1.set_xlim(1,N+3.4); ax1.set_xticks([1,5,10,15,20])
ax1.invert_yaxis()

# ---- Panneau 2 : le pire repli de la saison ----
ax2.set_facecolor(SURFACE)
g = np.linspace(0, 70000, 400)
ax2.plot(g, [(mx_sans<=v).mean() for v in g], color=S1, lw=2.4, label="sans couverture", zorder=3)
ax2.plot(g, [(mx_avec<=v).mean() for v in g], color=S2, lw=2.4, label="avec couverture", zorder=3)
for v in (30000,):
    a,b = (mx_sans>v).mean(), (mx_avec>v).mean()
    ax2.axvline(v, color=GRID, lw=1, zorder=1)
    ax2.annotate(f"{a:.0%} des saisons\ndepassent 30 k", (v,1-a), textcoords="offset points",
                 xytext=(-12,-6), ha='right', va='top', fontsize=8.5, color=S1, weight='bold')
    ax2.annotate(f"{b:.0%}\navec couverture", (v,1-b), textcoords="offset points", xytext=(16,-30),
                 ha='left', va='top', fontsize=8.5, color=S2, weight='bold')
ax2.set_title("Le pire trou de la saison", fontsize=11.5, color=INK, loc='left',
              weight='bold', pad=10)
ax2.set_xlabel("repli maximal atteint dans la saison (dollars)", fontsize=9, color=INK2)
ax2.set_ylabel("part des saisons en dessous", fontsize=9, color=INK2)
ax2.xaxis.set_major_formatter(k); ax2.yaxis.set_major_formatter(PercentFormatter(1))
ax2.set_ylim(0,1.02); ax2.set_xlim(0,70000)
leg = ax2.legend(frameon=False, fontsize=9, loc='lower right')
for t in leg.get_texts(): t.set_color(INK2)

for ax in (ax1,ax2):
    ax.grid(axis='y', color=GRID, lw=.8, zorder=0); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    for sp in ('left','bottom'): ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8.5, length=0)

fig.tight_layout()
fig.savefig('figures/fig_drawdown_saison.png', dpi=200, facecolor=SURFACE)

print(f"Couverture a {H:.0%} de l'exposition, uniquement si la cote depasse {SEUIL:.0%}. {N} grosses soirees.\n")
print(f"{'repli maximal de la saison':<34}{'sans':>12}{'avec':>12}")
for lab,q in [("saison mediane",50),("1 saison sur 4",75),("1 saison sur 10",90),("1 saison sur 20",95)]:
    print(f"{lab:<34}{np.percentile(mx_sans,q):>12,.0f}{np.percentile(mx_avec,q):>12,.0f}")
print()
for v in (20000,30000,40000):
    print(f"part des saisons avec un trou > {v/1000:.0f} k$ : "
          f"{(mx_sans>v).mean():>6.1%} sans, {(mx_avec>v).mean():>6.1%} avec")
