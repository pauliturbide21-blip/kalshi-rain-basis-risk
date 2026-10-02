"""Season calendar per venue (2025, 2026): open nights, big nights, expected revenue and committed cost.
Comments in the code are in French."""
import os, csv
from datetime import date, timedelta
import pandas as pd
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURS={"lun":0,"mar":1,"mer":2,"jeu":3,"ven":4,"sam":5,"dim":6}
def jours_set(s):
    s=s.strip()
    if "-" in s:
        a,b=s.split("-"); a=JOURS[a]; b=JOURS[b]
        return set(range(a,b+1)) if a<=b else set(range(a,7))|set(range(0,b+1))
    return {JOURS[x] for x in s.split(",")}
SEASONS={2025:(date(2025,5,1),date(2025,9,30)),2026:(date(2026,5,1),date(2026,9,15))}
FERIES={2025:[date(2025,5,26),date(2025,7,4),date(2025,9,1)],2026:[date(2026,5,25),date(2026,7,4),date(2026,9,7)]}
panel=pd.read_csv(f"{HERE}/data/venues.csv")
rows=[]
for v in panel.itertuples():
    ouv=jours_set(v.jours_ouverture)
    for saison,(d0,d1) in SEASONS.items():
        feries=set(FERIES[saison]); veilles={f-timedelta(days=1) for f in feries}
        days=[d0+timedelta(days=i) for i in range((d1-d0).days+1)]
        opens=[d for d in days if d.weekday() in ouv]
        first,last=opens[0],opens[-1]
        for d in days:
            ouvert=d.weekday() in ouv
            grosse=ouvert and (d.weekday() in (4,5) or d in veilles or d in feries or d in (first,last))
            tier="grosse" if grosse else "normal"
            rows.append({"nom":v.nom,"saison":saison,"date":d.isoformat(),"jour_semaine":d.weekday(),"ouvert":int(ouvert),"grosse":int(grosse),
                         "ferie_ou_veille":int(d in feries or d in veilles),"ouverture_ou_cloture":int(d in (first,last)),
                         "R_bas":getattr(v,f"R_{tier}_bas") if ouvert else 0,"R":getattr(v,f"R_{tier}") if ouvert else 0,"R_haut":getattr(v,f"R_{tier}_haut") if ouvert else 0,
                         "K_bas":getattr(v,f"K_{tier}_bas") if ouvert else 0,"K":getattr(v,f"K_{tier}") if ouvert else 0,"K_haut":getattr(v,f"K_{tier}_haut") if ouvert else 0})
cal=pd.DataFrame(rows); cal.to_csv(f"{HERE}/data/calendar.csv",index=False)
g=cal[cal.ouvert==1].groupby(["nom","saison"]).agg(soirees=("ouvert","sum"),grosses=("grosse","sum"),R_saison=("R","sum"),K_saison=("K","sum"),R_grosses=("R",lambda x:0))
g["part_grosses_R"]=cal[(cal.ouvert==1)&(cal.grosse==1)].groupby(["nom","saison"]).R.sum()/cal[cal.ouvert==1].groupby(["nom","saison"]).R.sum()
print(g.drop(columns="R_grosses").round(2).to_string())
