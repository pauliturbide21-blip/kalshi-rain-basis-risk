"""La table que le gerant veut lire : pour un nombre donne de soirees gachees
dans la saison, combien il gagne avec et sans couverture. Donnees reelles NYC."""
import pandas as pd, numpy as np

MARGE_BEAU, MARGE_PLUIE = 15000., -5000.   # marge d'une grosse soiree
ECART   = MARGE_BEAU - MARGE_PLUIE         # 20 000 $ en jeu par soiree
H       = 0.6                              # taille de couverture
SEUIL   = 0.40                             # il se couvre si la cote depasse 40 cents
N, NSIM = 20, 60000

rng = np.random.default_rng(5)
d = pd.read_csv('data/days_prices_NYC.csv', parse_dates=['date']); d['mois']=d.date.dt.month
s = d[(d.mois>=5)&(d.mois<=9)&d.pi.notna()&d.Y.notna()&d.D.notna()].copy()
s['fee']=s.fee.fillna(0); s['spread']=s.spread.fillna(s.spread.median())
pi,Y,D,fee,sp = s.pi.values,s.Y.values,s.D.values,s.fee.values,s.spread.values

idx = rng.integers(0,len(s),size=(NSIM,N))
PI,YY,DD,FE,SP = pi[idx],Y[idx],D[idx],fee[idx],sp[idx]
couv  = PI >= SEUIL
marge = MARGE_BEAU*(1-DD) + MARGE_PLUIE*DD
marge = marge.sum(axis=1)
n_gachees = DD.sum(axis=1).astype(int)

for prix_lab, prix in [('au mid', PI+FE), ("a l'ask", PI+FE+SP)]:
    cout = (H*ECART*prix*couv).sum(axis=1)
    gain = (H*ECART*YY*couv).sum(axis=1)
    tot  = marge - cout + gain
    print(f"\n=== Execution {prix_lab} === (couverture si la cote depasse {SEUIL:.0%}, "
          f"taille {H:.0%} de l'exposition)")
    print(f"{'soirees gachees':<18}{'% des saisons':>14}{'sans hedge':>14}{'cout hedge':>13}"
          f"{'hedge paie':>13}{'avec hedge':>13}{'ecart':>11}")
    for k in range(0,8):
        m = n_gachees==k
        if m.sum()<60: continue
        print(f"{k:<18}{m.mean():>13.0%}{marge[m].mean():>14,.0f}{-cout[m].mean():>13,.0f}"
              f"{gain[m].mean():>13,.0f}{tot[m].mean():>13,.0f}{(tot[m]-marge[m]).mean():>11,.0f}")
    m = n_gachees>=8
    if m.sum()>=60:
        print(f"{'8 et plus':<18}{m.mean():>13.0%}{marge[m].mean():>14,.0f}{-cout[m].mean():>13,.0f}"
              f"{gain[m].mean():>13,.0f}{tot[m].mean():>13,.0f}{(tot[m]-marge[m]).mean():>11,.0f}")
    print(f"{'ensemble':<18}{1.0:>13.0%}{marge.mean():>14,.0f}{-cout.mean():>13,.0f}"
          f"{gain.mean():>13,.0f}{tot.mean():>13,.0f}{(tot-marge).mean():>11,.0f}")
