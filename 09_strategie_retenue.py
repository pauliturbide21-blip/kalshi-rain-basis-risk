"""Strategie retenue : rooftop all-in, couverture ciblee sur les grosses soirees
quand la pluie est deja probable. Sensibilite a l'execution."""
import pandas as pd, numpy as np
NSIM=40000; B=300000.0
rng=np.random.default_rng(11)
d=pd.read_csv('data/days_prices_NYC.csv',parse_dates=['date']); d['mois']=d.date.dt.month
s=d[(d.mois>=5)&(d.mois<=9)&d.pi.notna()&d.Y.notna()&d.D.notna()].copy()
s['fee']=s.fee.fillna(0); s['spread']=s.spread.fillna(s.spread.median())
pi,Y,D,fee,sp=s.pi.values,s.Y.values,s.D.values,s.fee.values,s.spread.values
L=np.full(20,0.3*B/17); L[:3]=0.7*B/3
idx=rng.integers(0,len(s),size=(NSIM,20))
PI,YY,DD,FE,SP=pi[idx],Y[idx],D[idx],fee[idx],sp[idx]
sans=-(L*DD).sum(axis=1); cv=np.zeros(20,bool); cv[:3]=True
rows=[dict(strategie='sans couverture',moyenne=sans.mean(),ecart_type=sans.std(),
           pire_5pct=np.percentile(sans,5),p_perte_120k=(sans<-120000).mean(),prime=0.0)]
for demi,ex in [(0.0,'mid'),(0.25,'quart de spread'),(0.5,'demi-spread')]:
    for h in [0.34,0.6]:
        m=cv[None,:]&(PI>=0.30); cout=PI+FE+demi*SP
        a=sans+h*(L*(YY-cout)*m).sum(axis=1)
        rows.append(dict(strategie=f'3 grosses, pi>30c, h={h}, {ex}',moyenne=a.mean(),
                         ecart_type=a.std(),pire_5pct=np.percentile(a,5),
                         p_perte_120k=(a<-120000).mean(),prime=float((h*L*cout*m).sum(axis=1).mean())))
pd.DataFrame(rows).to_csv('tables/strategie_retenue.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
