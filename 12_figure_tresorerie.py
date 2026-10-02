# -*- coding: utf-8 -*-
"""Figure : ce que la couverture change au risque de tresorerie d'une saison.
Panneau 1 : la mauvaise saison, au fil des soirees. Panneau 2 : risque de finir bas.
Donnees reelles New York."""
import pandas as pd, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter

FIXE   = 10000.                      # charges fixes allouees a chaque grosse soiree
MB, MP = 15000.-FIXE, -5000.-FIXE    # tresorerie nette : +5 000 si beau, -15 000 si gachee
ECART  = MB - MP
H      = 0.34
N, NSIM = 20, 40000

SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e5e4e0'
S1, S2 = '#2a78d6', '#eb6834'        # bleu = sans couverture, orange = avec

rng = np.random.default_rng(12)
d = pd.read_csv('data/days_prices_NYC.csv', parse_dates=['date']); d['mois']=d.date.dt.month
s = d[(d.mois>=5)&(d.mois<=9)&d.pi.notna()&d.Y.notna()&d.D.notna()].copy()
s['fee']=s.fee.fillna(0)
pi,Y,D,fee = s.pi.values,s.Y.values,s.D.values,s.fee.values

idx = rng.integers(0,len(s),size=(NSIM,N))
PI,YY,DD,FE = pi[idx],Y[idx],D[idx],fee[idx]
nuit_sans = MB*(1-DD) + MP*DD
nuit_avec = nuit_sans + H*ECART*(YY - PI - FE)
cum_sans, cum_avec = np.cumsum(nuit_sans,axis=1), np.cumsum(nuit_avec,axis=1)
fin_sans, fin_avec = cum_sans[:,-1], cum_avec[:,-1]

x = np.arange(1,N+1)
# une mauvaise saison reelle : on prend une trajectoire dont la fin est proche du 5e centile,
# et on lui applique les deux decisions. Meme meteo, meme prix, deux comportements.
cible = np.percentile(fin_sans,5)
j = int(np.argmin(np.abs(fin_sans-cible) + 0.001*np.abs(cum_sans[:,:].min(axis=1)-np.percentile(cum_sans.min(axis=1),5))))

fig,(ax1,ax2) = plt.subplots(1,2, figsize=(11.5,4.6), facecolor=SURFACE)
k = FuncFormatter(lambda v,_: f"{v/1000:,.0f} k")

# ---- Panneau 1 : une mauvaise saison reelle, soiree par soiree ----
ax1.set_facecolor(SURFACE)
ax1.axhline(0, color=INK2, lw=1, ls=(0,(4,3)), zorder=1, xmax=0.86)
ax1.text(1.15, 1200, "equilibre", fontsize=8, color=INK2)
ax1.plot(x, cum_sans[j], color=S1, lw=2.4, zorder=3, solid_capstyle='round')
ax1.plot(x, cum_avec[j], color=S2, lw=2.4, zorder=4, solid_capstyle='round')
for cum,col in ((cum_sans[j],S1),(cum_avec[j],S2)):
    ax1.scatter([N],[cum[-1]], s=34, color=col, zorder=5, edgecolor=SURFACE, linewidth=2)
ax1.annotate("sans\ncouverture", (N, cum_sans[j,-1]), textcoords="offset points",
             xytext=(10,0), ha='left', va='center', fontsize=9.5, color=S1, weight='bold')
ax1.annotate("avec\ncouverture", (N, cum_avec[j,-1]), textcoords="offset points",
             xytext=(10,0), ha='left', va='center', fontsize=9.5, color=S2, weight='bold')
ax1.set_title("Une mauvaise saison, soiree par soiree", fontsize=11.5, color=INK,
              loc='left', weight='bold', pad=10)
ax1.set_xlabel("soiree de la saison", fontsize=9, color=INK2)
ax1.set_ylabel("tresorerie cumulee (dollars)", fontsize=9, color=INK2)
ax1.yaxis.set_major_formatter(k); ax1.set_xlim(1,N+3.2); ax1.set_xticks([1,5,10,15,20])

# ---- Panneau 2 : risque de finir bas ----
ax2.set_facecolor(SURFACE)
grille = np.linspace(-60000, 120000, 400)
cdf_sans = [(fin_sans<=v).mean() for v in grille]
cdf_avec = [(fin_avec<=v).mean() for v in grille]
ax2.axvline(0, color=INK2, lw=1, ls=(0,(4,3)), zorder=1)
ax2.plot(grille, cdf_sans, color=S1, lw=2.4, zorder=3, label="sans couverture")
ax2.plot(grille, cdf_avec, color=S2, lw=2.4, zorder=3, label="avec couverture")
for v in (-20000, 0):
    a,b = (fin_sans<=v).mean(), (fin_avec<=v).mean()
    ax2.annotate(f"{a:.0%}", (v,a), textcoords="offset points", xytext=(-8,6),
                 ha='right', fontsize=8.5, color=S1, weight='bold')
    ax2.annotate(f"{b:.0%}", (v,b), textcoords="offset points", xytext=(8,-10),
                 ha='left', fontsize=8.5, color=S2, weight='bold')
ax2.set_title("Risque de finir la saison sous un niveau donne", fontsize=11.5,
              color=INK, loc='left', weight='bold', pad=10)
ax2.set_xlabel("tresorerie en fin de saison (dollars)", fontsize=9, color=INK2)
ax2.set_ylabel("part des saisons en dessous", fontsize=9, color=INK2)
ax2.xaxis.set_major_formatter(k); ax2.yaxis.set_major_formatter(PercentFormatter(1))
ax2.set_ylim(0,1); ax2.set_xlim(-60000,120000)
leg = ax2.legend(frameon=False, fontsize=9, loc='lower right')
for t in leg.get_texts(): t.set_color(INK2)

for ax in (ax1,ax2):
    ax.grid(axis='y', color=GRID, lw=.8, zorder=0); ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    for sp in ('left','bottom'): ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8.5, length=0)

fig.tight_layout()
fig.savefig('figures/fig_tresorerie_saison.png', dpi=200, facecolor=SURFACE)

print(f"Couverture a {H:.0%} de l'exposition, {N} grosses soirees, charges fixes {FIXE:,.0f} $ par soiree.\n")
print(f"{'':<30}{'sans couverture':>17}{'avec couverture':>17}")
for lab,a,b in [("fin de saison, moyenne", fin_sans.mean(), fin_avec.mean()),
                ("fin de saison, ecart-type", fin_sans.std(), fin_avec.std()),
                ("mauvaise saison (1 sur 20)", np.percentile(fin_sans,5), np.percentile(fin_avec,5)),
                ("tres mauvaise (1 sur 100)", np.percentile(fin_sans,1), np.percentile(fin_avec,1)),
                ("point bas, mauvaise saison", cum_sans[j].min(), cum_avec[j].min())]:
    print(f"{lab:<30}{a:>17,.0f}{b:>17,.0f}")
for v in (-20000,0):
    print(f"part des saisons sous {v/1000:>4.0f} k$ {(fin_sans<=v).mean():>16.1%}{(fin_avec<=v).mean():>17.1%}")
