"""Liquidite supposee acquise, execution au prix milieu.
Quel seuil de declenchement et quelle taille de couverture pour un rooftop
de 20 grosses soirees ? Donnees reelles New York."""
import pandas as pd, numpy as np

MARGE_BEAU, MARGE_PLUIE = 15000., -5000.
ECART, N, NSIM = 20000., 20, 60000
rng = np.random.default_rng(5)
d = pd.read_csv('data/days_prices_NYC.csv', parse_dates=['date']); d['mois']=d.date.dt.month
s = d[(d.mois>=5)&(d.mois<=9)&d.pi.notna()&d.Y.notna()&d.D.notna()].copy()
s['fee']=s.fee.fillna(0)
pi,Y,D,fee = s.pi.values,s.Y.values,s.D.values,s.fee.values
idx = rng.integers(0,len(s),size=(NSIM,N))
PI,YY,DD,FE = pi[idx],Y[idx],D[idx],fee[idx]
marge = (MARGE_BEAU*(1-DD) + MARGE_PLUIE*DD).sum(axis=1)

print(f"Reference sans couverture : moyenne {marge.mean():,.0f} $, "
      f"ecart-type {marge.std():,.0f}, pire saison sur 20 {np.percentile(marge,5):,.0f}\n")
print(f"{'seuil':>7}{'taille':>8}{'n couv.':>9}{'moyenne':>11}{'ec-type':>10}"
      f"{'pire 1/20':>11}{'gain moyen':>12}{'gain pire':>11}")
best=None
for seuil in [0.0,0.20,0.30,0.40,0.50,0.60,0.70]:
    for h in [0.3,0.5,0.7,1.0]:
        m = PI>=seuil
        cout=(h*ECART*(PI+FE)*m).sum(axis=1); gain=(h*ECART*YY*m).sum(axis=1)
        t=marge-cout+gain
        g_pire=np.percentile(t,5)-np.percentile(marge,5)
        print(f"{seuil:>7.0%}{h:>8.0%}{m.sum(axis=1).mean():>9.1f}{t.mean():>11,.0f}{t.std():>10,.0f}"
              f"{np.percentile(t,5):>11,.0f}{t.mean()-marge.mean():>12,.0f}{g_pire:>11,.0f}")
        if best is None or g_pire>best[0]: best=(g_pire,seuil,h,t)
    print()
g,seuil,h,t = best
print(f"Meilleur reglage sur la pire saison : seuil {seuil:.0%}, taille {h:.0%}")
print(f"  pire saison : {np.percentile(marge,5):,.0f} -> {np.percentile(t,5):,.0f}  ({g:+,.0f})")
print(f"  moyenne     : {marge.mean():,.0f} -> {t.mean():,.0f}  ({t.mean()-marge.mean():+,.0f})")
print(f"  ecart-type  : {marge.std():,.0f} -> {t.std():,.0f}  ({100*(t.std()/marge.std()-1):+.0f} %)")
print(f"  saisons ou la couverture ameliore le resultat : {(t>marge).mean():.0%}")
