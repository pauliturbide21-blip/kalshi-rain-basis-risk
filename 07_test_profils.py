"""Ou le gerant est-il vraiment gagnant ?
On fait varier la structure de la saison (nombre de soirees, concentration du budget),
la regle de couverture (quelles soirees, quelle taille) et l'execution (mid ou spread).
Donnees reelles : 239 jours de saison a New York."""

import pandas as pd, numpy as np, json, itertools

NSIM = 20000
B_TOTAL = 300000.0        # marge totale a risque sur la saison, identique partout
SEUIL_MAUVAISE = 120000.0 # une saison est "mauvaise" au dela de cette perte

rng = np.random.default_rng(11)
d = pd.read_csv('data/days_prices_NYC.csv', parse_dates=['date'])
d['mois'] = d.date.dt.month
s = d[(d.mois>=5)&(d.mois<=9)&d.pi.notna()&d.Y.notna()&d.D.notna()].copy()
s['fee'] = s.fee.fillna(0); s['spread'] = s.spread.fillna(s.spread.median())
pi, Y, D, fee, sp = s.pi.values, s.Y.values, s.D.values, s.fee.values, s.spread.values

# --- profils de saison : meme budget total, concentration differente ---
def budgets(nom):
    if nom == 'plat 20 soirees':        return np.full(20, B_TOTAL/20)
    if nom == 'concentre 20 soirees':   # 5 grosses soirees portent 60 %
        b = np.full(20, 0.4*B_TOTAL/15); b[:5] = 0.6*B_TOTAL/5; return b
    if nom == 'all-in 20 soirees':      # 3 soirees portent 70 %
        b = np.full(20, 0.3*B_TOTAL/17); b[:3] = 0.7*B_TOTAL/3; return b
    if nom == 'all-in 8 soirees':       # saison courte, 3 soirees portent 70 %
        b = np.full(8, 0.3*B_TOTAL/5);  b[:3] = 0.7*B_TOTAL/3; return b
    if nom == 'plat 40 soirees':        return np.full(40, B_TOTAL/40)

PROFILS = ['plat 40 soirees','plat 20 soirees','concentre 20 soirees',
           'all-in 20 soirees','all-in 8 soirees']

def simule(nom_profil, k, h, demi_spread, bande=(0.0,1.0)):
    """k = nombre de soirees couvertes, les plus grosses d'abord. h = ratio de couverture."""
    L = budgets(nom_profil); N = len(L)
    idx = rng.integers(0, len(s), size=(NSIM, N))
    PI, YY, DD, FE, SP = pi[idx], Y[idx], D[idx], fee[idx], sp[idx]
    sans = -(L*DD).sum(axis=1)
    ordre = np.argsort(-L)                       # les plus gros budgets d'abord
    couvre = np.zeros(N, bool); couvre[ordre[:k]] = True
    dans_bande = (PI >= bande[0]) & (PI <= bande[1])
    m = couvre[None,:] & dans_bande
    cout = PI + FE + demi_spread*SP
    avec = sans + h*(L*(YY - cout)*m).sum(axis=1)
    prime = float((h*L*cout*m).sum(axis=1).mean())
    return sans, avec, prime

def ligne(sans, avec, prime, lab):
    return dict(strategie=lab, moyenne=avec.mean(), ecart_type=avec.std(),
                pire_5pct=np.percentile(avec,5), gain=avec.mean()-sans.mean(),
                p_mauvaise=(avec < -SEUIL_MAUVAISE).mean(),
                p_mauvaise_sans=(sans < -SEUIL_MAUVAISE).mean(), prime=prime)

out = []
for prof in PROFILS:
    N = len(budgets(prof))
    sans, _, _ = simule(prof, 0, 0, 0)
    out.append({'profil':prof, **ligne(sans, sans, 0, 'sans couverture')})
    for k_lab, k in [('toutes', N), ('top 5', min(5,N)), ('top 3', min(3,N))]:
        for h in [0.34, 0.6, 1.0]:
            for demi, ex in [(0.0,'mid'), (0.5,'demi-spread')]:
                _, avec, prime = simule(prof, k, h, demi)
                out.append({'profil':prof,
                            **ligne(sans, avec, prime, f'{k_lab}, h={h}, {ex}')})

df = pd.DataFrame(out)
df.to_csv('tables/test_profils.csv', index=False)

pd.set_option('display.width', 200)
for prof in PROFILS:
    g = df[df.profil==prof]
    print(f"\n=== {prof} ===  (budget total a risque {B_TOTAL:,.0f} $)")
    print(f"{'strategie':<28}{'moyenne':>11}{'ec-type':>10}{'pire 1/20':>11}{'gain':>10}{'P(mauvaise)':>13}{'prime':>11}")
    for _, r in g.iterrows():
        print(f"{r.strategie:<28}{r.moyenne:>11,.0f}{r.ecart_type:>10,.0f}{r.pire_5pct:>11,.0f}"
              f"{r.gain:>10,.0f}{r.p_mauvaise:>12.0%}{r.prime:>11,.0f}")
