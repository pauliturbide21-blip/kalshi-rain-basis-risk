"""Test simple : un rooftop, 20 grosses soirees de mai a septembre, New York.
Question : le gerant finit-il la saison gagnant s'il se couvre sur Kalshi ?
Donnees reelles, 239 jours de saison avec prix et meteo observes."""

import pandas as pd, numpy as np, json

L, N, NSIM = 15000.0, 20, 20000       # perte par soiree gachee, soirees, saisons simulees
HSTAR = 0.34                          # ratio de variance minimale mesure sur ces donnees

rng = np.random.default_rng(3)
d = pd.read_csv('data/days_prices_NYC.csv', parse_dates=['date'])
d['mois'] = d.date.dt.month
s = d[(d.mois >= 5) & (d.mois <= 9) & d.pi.notna() & d.Y.notna() & d.D.notna()].copy()
s['fee'] = s.fee.fillna(0)
s['spread'] = s.spread.fillna(s.spread.median())

pi, Y, D, fee, sp = s.pi.values, s.Y.values, s.D.values, s.fee.values, s.spread.values
idx = rng.integers(0, len(s), size=(NSIM, N))
PI, YY, DD, FE, SP = pi[idx], Y[idx], D[idx], fee[idx], sp[idx]
sans = -L * DD.sum(axis=1)

def saison(h, demi_spread):
    cout = PI + FE + demi_spread * SP
    return sans + h * L * (YY - cout).sum(axis=1)

res = {'base': {'n_jours': int(len(s)), 'P_Y': float(Y.mean()), 'P_D': float(D.mean()),
                'pi_moyen': float(pi.mean()), 'spread_median': float(np.median(sp)),
                'spread_moyen': float(sp.mean()), 'L': L, 'N_soirees': N},
       'sans_couverture': {'moyenne': float(sans.mean()), 'ecart_type': float(sans.std()),
                           'pire_5pct': float(np.percentile(sans, 5))}}

for demi, lab in [(0.0, 'mid'), (0.5, 'demi_spread'), (1.0, 'ask')]:
    for h, nom in [(1.0, 'pleine'), (HSTAR, f'{HSTAR}')]:
        p = saison(h, demi)
        res[f'{lab}_taille_{nom}'] = {
            'moyenne': float(p.mean()), 'ecart_type': float(p.std()),
            'pire_5pct': float(np.percentile(p, 5)),
            'gain_vs_sans': float(p.mean() - sans.mean()),
            'part_saisons_ameliorees': float((p > sans).mean())}

json.dump(res, open('data/resultats_test_simple.json', 'w'), indent=2)
for k, v in res.items():
    print(k, json.dumps(v, indent=2) if isinstance(v, dict) else v)
