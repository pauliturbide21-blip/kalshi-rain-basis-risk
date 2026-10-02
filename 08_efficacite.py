"""Ou le dollar de prime est-il le mieux depense ?
Gain et reduction de risque rapportes a la prime engagee, par profil de saison,
par ciblage (toutes les soirees ou les plus grosses) et par bande de prix."""
import pandas as pd, numpy as np

NSIM = 20000; B_TOTAL = 300000.0
rng = np.random.default_rng(11)
d = pd.read_csv('data/days_prices_NYC.csv', parse_dates=['date']); d['mois']=d.date.dt.month
s = d[(d.mois>=5)&(d.mois<=9)&d.pi.notna()&d.Y.notna()&d.D.notna()].copy()
s['fee']=s.fee.fillna(0); s['spread']=s.spread.fillna(s.spread.median())
pi,Y,D,fee,sp = s.pi.values,s.Y.values,s.D.values,s.fee.values,s.spread.values

def budgets(n):
    if n=='plat':    return np.full(20, B_TOTAL/20)
    if n=='all-in':  b=np.full(20,0.3*B_TOTAL/17); b[:3]=0.7*B_TOTAL/3; return b

def run(prof,k,h,bande,demi=0.0):
    L=budgets(prof); N=len(L)
    idx=rng.integers(0,len(s),size=(NSIM,N))
    PI,YY,DD,FE,SP=pi[idx],Y[idx],D[idx],fee[idx],sp[idx]
    sans=-(L*DD).sum(axis=1)
    cv=np.zeros(N,bool); cv[np.argsort(-L)[:k]]=True
    m=cv[None,:]&(PI>=bande[0])&(PI<=bande[1])
    cout=PI+FE+demi*SP
    avec=sans+h*(L*(YY-cout)*m).sum(axis=1)
    prime=float((h*L*cout*m).sum(axis=1).mean())
    return sans,avec,prime

for prof in ['plat','all-in']:
    sans,_,_=run(prof,0,0,(0,1))
    q5_sans=np.percentile(sans,5)
    print(f"\n=== saison {prof} ===  sans couverture : moyenne {sans.mean():,.0f}, "
          f"ecart-type {sans.std():,.0f}, pire 1/20 {q5_sans:,.0f}")
    print(f"{'ciblage':<34}{'prime':>10}{'gain/prime':>12}{'baisse ec-type':>16}{'/1000$ prime':>14}{'pire 1/20':>12}")
    for lab,k,bande in [('toutes les soirees',20,(0.0,1.0)),
                        ('3 plus grosses soirees',3,(0.0,1.0)),
                        ('5 plus grosses soirees',5,(0.0,1.0)),
                        ('toutes, prix 20-60c',20,(0.20,0.60)),
                        ('toutes, prix > 40c',20,(0.40,1.00)),
                        ('toutes, prix < 30c',20,(0.00,0.30)),
                        ('3 plus grosses, prix > 30c',3,(0.30,1.00))]:
        _,avec,prime=run(prof,k,0.34,bande)
        if prime<1: continue
        dsd=sans.std()-avec.std()
        print(f"{lab:<34}{prime:>10,.0f}{(avec.mean()-sans.mean())/prime:>11.1%}"
              f"{dsd:>16,.0f}{1000*dsd/prime:>14,.0f}{np.percentile(avec,5):>12,.0f}")
