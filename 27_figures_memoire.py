"""27_figures_memoire.py : figures du memoire, au format de la page (largeur 6,3 pouces, polices 9 a 10 points).
fig01 schema du contrat ; fig02 journee type et declencheur ; fig03 dix soirees stylisees ; fig04 chaine de tresorerie ;
fig05 borne du logiciel optimal ; fig06 230 Fifth deux saisons (chemins_saison.csv) ; fig07 contrat reel contre parfait (chemins_parfait.csv) ;
fig08 calibration de la cote (tables h2). Sorties PDF et PNG dans memoire/figures/.
Palette : bleu #2a78d6 (sans couverture), orange #eb6834 (avec), rouge #e34948 (soiree perdue), gris #898781."""
import os, glob, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch
from matplotlib.ticker import FuncFormatter
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=f"{HERE}/figures"; os.makedirs(OUT,exist_ok=True)
BLEU="#2a78d6"; ORANGE="#eb6834"; ROUGE="#e34948"; GRIS="#898781"; NOIR="#2c2c2a"; CLAIR="#f1efe8"; W=6.3
plt.rcParams.update({"font.family":"serif","font.size":9,"axes.spines.top":False,"axes.spines.right":False,"axes.edgecolor":"#9a9a96","axes.labelcolor":"#52514e","xtick.color":"#52514e","ytick.color":"#52514e","figure.facecolor":"white","legend.frameon":False})
def save(name): plt.savefig(f"{OUT}/{name}.pdf",bbox_inches="tight"); plt.savefig(f"{OUT}/{name}.png",dpi=200,bbox_inches="tight"); plt.close(); print(name)
def box(ax,x,y,w,h,txt,fc=CLAIR,ec=GRIS,fs=8.5):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02,rounding_size=0.12",fc=fc,ec=ec,lw=1))
    ax.text(x+w/2,y+h/2,txt,ha="center",va="center",fontsize=fs,color=NOIR,linespacing=1.35)
def arrow(ax,x0,y0,x1,y1,color=GRIS): ax.add_patch(FancyArrowPatch((x0,y0),(x1,y1),arrowstyle="-|>",mutation_scale=11,color=color,lw=1.1))
kfmt=FuncFormatter(lambda x,_: f"{x/1e6:.1f} M" if abs(x)>=1e6 else f"{x/1e3:.0f} k")

# ---------- fig01 : le contrat et ses deux issues ----------
fig,ax=plt.subplots(figsize=(W,3.9)); ax.set_xlim(0,10); ax.set_ylim(0,5.3); ax.axis("off")
box(ax,0.1,3.3,3.0,1.9,"La veille, à midi\n\nle gérant achète\nN contrats « Oui, il pleut\ndemain » au prix p",fc="#e6f1fb",ec=BLEU,fs=7.0)
box(ax,3.5,3.3,3.0,1.9,"Le jour\n\nla station de\nCentral Park mesure\nla pluie de minuit à minuit",fc=CLAIR,fs=7.0)
box(ax,6.9,4.3,3.0,0.9,"Pluie : contrat à 1 $\ngain net N × (1 − p)",fc="#faece7",ec=ORANGE,fs=7.0)
box(ax,6.9,3.3,3.0,0.9,"Pas de pluie : contrat à 0\nperte N × p",fc=CLAIR,fs=7.0)
arrow(ax,3.1,4.25,3.5,4.25); arrow(ax,6.5,4.45,6.9,4.75); arrow(ax,6.5,4.05,6.9,3.75)
box(ax,0.1,0.3,4.8,2.4,"Soirée de pluie\n\nla terrasse se vide,\nla recette est perdue,\nmais le contrat paie N × (1 − p)",fc="#fcebeb",ec=ROUGE,fs=7.4)
box(ax,5.1,0.3,4.8,2.4,"Soirée sèche\n\nla terrasse est pleine,\nla recette est encaissée,\nmais la prime N × p est perdue",fc="#eaf3de",ec="#639922",fs=7.4)
ax.text(5,2.95,"Ce qu'on attend d'une couverture : le contrat perd quand la soirée gagne, et gagne quand la soirée perd.",ha="center",va="center",fontsize=7.2,color=NOIR,style="italic")
save("fig01_contrat")

# ---------- fig02 : journee type ----------
fig,axes=plt.subplots(2,1,figsize=(W,3.4),sharex=True)
cases=[("Journée A : averse à 8 h, soirée pleine. Le contrat paie, le rooftop n'a rien perdu.",[(7,9,1.2)]),("Journée B : orage à 21 h, terrasse vidée. Le contrat paie, le rooftop a perdu sa soirée.",[(20.5,23,2.5)])]
for ax,(t,rains) in zip(axes,cases):
    ax.axvspan(18,25,color="#faece7",alpha=0.9,lw=0); ax.text(21.5,3.1,"heures d'ouverture\n18 h à 1 h",ha="center",va="center",fontsize=8,color="#993c1d")
    ax.axvspan(0,24,color="#e6f1fb",alpha=0.5,lw=0,ymin=0,ymax=0.12); ax.text(14,0.25,"fenêtre du contrat : minuit à minuit",ha="center",fontsize=8,color="#185fa5")
    for a,b,h in rains: ax.bar((a+b)/2,h,width=b-a,color=BLEU if a<18 else ROUGE)
    ax.set_ylim(0,3.8); ax.set_xlim(0,25); ax.set_yticks([]); ax.set_title(t,loc="left",fontsize=8.5); ax.spines["left"].set_visible(False)
axes[1].set_xticks(range(0,26,3)); axes[1].set_xticklabels([f"{h%24} h" for h in range(0,26,3)]); axes[1].set_xlabel("Heure locale")
save("fig02_declencheur")

# ---------- fig03 : dix soirees ----------
outs={"Sans couverture":[15,15,15,15,25,25,25,25,25,25],"Contrat réel, 5 000 $ à 0,80":[16,16,16,16,26,26,26,26,21,21],
      "Contrat réel, 25 000 $ à 0,80":[20,20,20,20,30,30,30,30,5,5],"Contrat parfait, 10 000 $ à 0,40":[21]*10}
cols=[ROUGE]*4+[BLEU]*4+[GRIS]*2
fig,axes=plt.subplots(2,2,figsize=(W,5.2),sharey=True)
for ax,(t,v) in zip(axes.ravel(),outs.items()):
    ax.bar(range(1,11),v,color=cols,width=0.65); ax.set_title(f"{t}\nécart {min(v)} à {max(v)} k, total {sum(v)} k",fontsize=8.5,loc="left")
    ax.set_ylim(0,32); ax.set_xticks([1,5,10]); ax.grid(axis="y",color="#eeeeee"); ax.set_axisbelow(True)
for ax in axes[:,0]: ax.set_ylabel("Résultat de la soirée (k$)")
for ax in axes[1,:]: ax.set_xlabel("Soirée")
fig.legend(handles=[Patch(color=ROUGE,label="4 soirées perdues (pluie le soir)"),Patch(color=BLEU,label="4 soirées pleines, pluie le matin"),Patch(color=GRIS,label="2 soirées pleines, journée sèche")],loc="lower center",ncol=3,fontsize=8,bbox_to_anchor=(0.5,-0.02))
plt.tight_layout(rect=(0,0.04,1,1)); save("fig03_dix_soirees")

# ---------- fig04 : chaine ----------
fig,ax=plt.subplots(figsize=(W,2.0)); ax.set_xlim(0,10); ax.set_ylim(0,2.6); ax.axis("off")
steps=[("Soirée de pluie\ncoûts engagés,\nrecette absente","#faece7",ORANGE),("Week-ends perdus\n40 % de la\nsemaine en 2 soirs",CLAIR,GRIS),("Charges fixes\nloyer 12 mois,\npaie hebdomadaire",CLAIR,GRIS),("Trou de\ntrésorerie\n16 jours de réserve","#fcebeb",ROUGE),("Crédit d'urgence\n20 à 200 %\npar an","#fcebeb",ROUGE)]
for k,(t,fc,ec) in enumerate(steps):
    box(ax,0.1+k*2.0,0.5,1.8,1.9,t,fc=fc,ec=ec,fs=6.5)
    if k<4: arrow(ax,1.9+k*2.0,1.45,2.1+k*2.0,1.45)
save("fig04_chaine")

# ---------- fig05 : borne ----------
A=pd.read_csv(f"{HERE}/tables/logiciel_borne.csv")
lab={"aucune":"Aucune","cote seule":"Cote","prevision soir seule":"Prévision\ndu soir","cote + prevision soir (veille 12 h)":"Cote et\nprévision soir","cote + prevision soir + prevision jour (veille 12 h)":"Cote et prév.\nsoir et jour","cote + prevision soir (jour 9 h)":"Cote et prév.,\nle jour à 9 h"}
fig,ax=plt.subplots(figsize=(W,3.3)); keys=list(lab); x=np.arange(len(keys)); w=0.36
for j,(regle,c,t) in enumerate((("actuelle, trace = oui",BLEU,"Règle jusqu'en juillet 2026 (trace comptée oui)"),("TWC, trace = non",ORANGE,"Règle actuelle (trace comptée zéro)"))):
    s=A[A.regle==regle].set_index("information").loc[keys]; v=s[["e_max_oos_2025","e_max_oos_2026"]].mean(axis=1).values; lo=s[["e_max_oos_2025","e_max_oos_2026"]].min(axis=1).values; hi=s[["e_max_oos_2025","e_max_oos_2026"]].max(axis=1).values
    ax.bar(x+(j-0.5)*w,v,w,color=c,label=t); ax.errorbar(x+(j-0.5)*w,v,yerr=[v-lo,hi-v],fmt="none",ecolor=NOIR,capsize=2.5,lw=0.9)
ax.axhline(1,color=ROUGE,ls="--",lw=1.1); ax.text(len(keys)-0.5,0.97,"contrat parfait : 1",ha="right",va="top",fontsize=8.5,color=ROUGE)
ax.set_xticks(x); ax.set_xticklabels([lab[k] for k in keys],fontsize=7.5); ax.set_ylim(0,1.05); ax.set_ylabel("Réduction de variance maximale"); ax.set_xlabel("Information dont dispose l'acheteur la veille")
ax.legend(fontsize=8,loc="upper left",bbox_to_anchor=(0,0.92)); ax.grid(axis="y",color="#eeeeee"); ax.set_axisbelow(True)
save("fig05_borne")

# ---------- fig06 / fig07 : chiffre d'affaires cumule des grosses soirees, 230 Fifth 2026, perte 50 %, h = 0,6 de la perte ----------
cp=pd.read_csv(f"{HERE}/data/chemins_parfait.csv",parse_dates=["date"]); cal=pd.read_csv(f"{HERE}/data/calendrier.csv",parse_dates=["date"])
gro=cal[(cal.nom=="230 Fifth")&(cal.saison==2026)][["date","grosse","K","R"]]
def nuits(contrat):
    g=cp[(cp.nom=="230 Fifth")&(cp.contrat==contrat)].sort_values("date").copy()
    g["sans"]=g.cum_sans.diff().fillna(g.cum_sans); g["avec"]=g.cum_avec.diff().fillna(g.cum_avec)
    g=g.merge(gro,on="date"); return g[g.grosse==1].reset_index(drop=True)
nr=nuits("reel"); npf=nuits("parfait"); K=nr.K.values
# charges par grosse soiree : cout engage K plus la part de charges fixes (75 % de la marge attendue des grosses soirees, repartie egalement)
pD=nr.D.mean(); marge_att=(nr.R*(1-0.5*pD)-nr.K).sum(); fixe=0.75*marge_att/len(nr); charges=K+fixe
def deux_panneaux(v0,v1,D,titre,lab1,name):
    x=np.arange(1,len(v0)+1); c0=np.cumsum(v0-charges)/1e3; c1=np.cumsum(v1-charges)/1e3; h=np.cumsum(v1-v0)/1e3
    fig,axes=plt.subplots(2,1,figsize=(W,6.0),sharex=True,gridspec_kw={"height_ratios":[1.35,1]})
    ax=axes[0]; ax.plot(x,c0,color=BLEU,lw=1.7,marker="o",ms=2.8,label="Sans couverture"); ax.plot(x,c1,color=ORANGE,lw=1.7,ls="--",marker="o",ms=2.8,label=lab1)
    ax.scatter(x[D==1],c0[D==1],s=40,color=ROUGE,zorder=4,label="Soirée perdue (moitié de la recette)"); ax.axhline(0,color=GRIS,lw=0.8)
    sd0=(v0/1e3).std(ddof=0); sd1=(v1/1e3).std(ddof=0)
    ax.set_title(f"{titre}\ntrésorerie cumulée : fin de saison {c0[-1]:.0f} k sans, {c1[-1]:.0f} k avec ; écart-type des soirées {sd0:.1f} k sans, {sd1:.1f} k avec".replace(".",","),loc="left",fontsize=8.5)
    ax.set_ylabel("Trésorerie cumulée (k$)"); ax.grid(color="#eeeeee"); ax.set_axisbelow(True); ax.legend(fontsize=8,loc="upper left"); ax.set_ylim(-150,1150)
    ax=axes[1]; ax.plot(x,h,color=ORANGE,lw=1.7,marker="o",ms=2.8); ax.axhline(0,color=GRIS,lw=0.8); ax.fill_between(x,h,0,where=h<0,color=ROUGE,alpha=0.18,lw=0); ax.fill_between(x,h,0,where=h>=0,color="#639922",alpha=0.15,lw=0)
    for xi in x[D==1]: ax.axvline(xi,color=ROUGE,lw=0.7,alpha=0.45)
    ax.set_title(f"Apport cumulé du contrat (avec moins sans) ; traits rouges : soirées perdues",loc="left",fontsize=8.5); ax.set_ylabel("Apport du contrat (k$)"); ax.grid(color="#eeeeee"); ax.set_axisbelow(True); ax.set_ylim(-160,120)
    ax.set_xlabel(f"Grosses soirées de la saison 2026 (n = {len(v0)}), 230 Fifth")
    plt.tight_layout(); save(name)
    print(name,"fin sans",round(c0[-1]),"fin avec",round(c1[-1]),"min sans",round(c0.min()),"min avec",round(c1.min()),"sd",round(sd0,1),round(sd1,1),"apport min",round(h.min()),"apport fin",round(h[-1]),"apport aux soirs perdus",np.round(np.diff(np.r_[0,h])[D==1]).tolist())
deux_panneaux(nr["sans"].values,nr["avec"].values,nr.D.values,"Contrat Kalshi réel, grosses soirées à cote ≥ 0,4, couverture de 60 % de la perte","Avec le contrat Kalshi","fig06_cumul_reel")
deux_panneaux(npf["sans"].values,npf["avec"].values,npf.D.values,"Contrat parfait, grosses soirées à prix ≥ 0,2, couverture de 60 % de la perte","Avec le contrat parfait","fig07_cumul_parfait")
print("charges par grosse soiree (k) :",round(charges.mean()/1e3,1),"; couvertes reel",int(nr.couverte.sum()),"parfait",int(npf.couverte.sum()))
# fig09 stylisee : perte de moitie pour coller a l'hypothese centrale
s2=None
# ---------- fig09 : ce qu'est une couverture (saison stylisee) ----------
rng_=np.random.default_rng(7); n=20; lost=np.zeros(n,bool); lost[[2,6,7,12,17]]=True
sans=np.where(lost,12.5,25.0); charges=np.full(n,21.5)   # 20 grosses soirees, 25 k pleine, 15 k perdue, 22 k de charges par soiree (loyer, personnel, artiste)
pfair=lost.mean(); avec=sans-12.5*pfair+np.where(lost,12.5,0.0)   # couverture parfaite : 12,5 k de contrats au prix actuariel
fig,axes=plt.subplots(2,2,figsize=(W,5.4),gridspec_kw={"width_ratios":[1.15,1]})
for row,(v,t) in enumerate(((sans,"Sans couverture"),(avec,"Avec une couverture parfaite"))):
    ax=axes[row,0]; ax.bar(np.arange(1,n+1),v,color=[ROUGE if l else BLEU for l in lost],width=0.7); ax.axhline(v.mean(),color=NOIR,lw=0.9,ls=":")
    ax.set_title(f"{t} : résultat par soirée\nécart-type {v.std():.1f} k, moyenne {v.mean():.1f} k".replace(".",","),loc="left",fontsize=8.5); ax.set_ylim(0,30); ax.set_ylabel("k$"); ax.grid(axis="y",color="#eeeeee"); ax.set_axisbelow(True)
    ax=axes[row,1]; tres=np.cumsum(v-charges); ax.plot(np.arange(1,n+1),tres,color=ORANGE if row else BLEU,lw=1.8,marker="o",ms=3); ax.axhline(0,color=GRIS,lw=0.8)
    ax.fill_between(np.arange(1,n+1),tres,0,where=tres<0,color=ROUGE,alpha=0.25,lw=0)
    ax.set_title(f"{t} : trésorerie cumulée\npoint le plus bas {tres.min():.0f} k".replace(".",","),loc="left",fontsize=8.5); ax.set_ylim(-20,20); ax.set_ylabel("k$"); ax.grid(color="#eeeeee"); ax.set_axisbelow(True)
for ax in axes[1,:]: ax.set_xlabel("Grosse soirée de la saison (1 à 20)")
fig.legend(handles=[Patch(color=BLEU,label="soirée pleine (25 k)"),Patch(color=ROUGE,label="soirée perdue (12,5 k)")],loc="lower center",ncol=2,fontsize=8,bbox_to_anchor=(0.5,-0.01))
plt.tight_layout(rect=(0,0.04,1,1)); save("fig09_couverture")

# ---------- fig08 : calibration ----------
fs=[f for f in glob.glob(f"{HERE}/tables/h2_*.csv") if "fiab" in f]
if fs:
    t=pd.read_csv(fs[0]); t=t[t.ville=="NYC"] if "ville" in t else t
    fig,ax=plt.subplots(figsize=(W,4.4)); ax.plot([0,1],[0,1],ls="--",color=GRIS,lw=1,label="Calibration parfaite")
    for src,mk,c,lab_ in (("kalshi_veille_12h","o",BLEU,"Cote Kalshi, veille à midi"),("mos_nbs","s",ORANGE,"Prévision du National Weather Service, veille à midi")):
        s=t[t.source==src]
        if len(s)==0: continue
        ax.errorbar(s.prix_moyen,s.frequence,yerr=[s.frequence-s.freq_ic_bas,s.freq_ic_haut-s.frequence],fmt=mk,color=c,mfc="white" if mk=="s" else c,capsize=2.5,lw=1,label=f"{lab_} (n = {int(s.n.sum())})")
    ax.set_xlim(0,1); ax.set_ylim(0,1); ax.set_xlabel("Probabilité annoncée, par décile"); ax.set_ylabel("Fréquence observée de règlement Oui"); ax.legend(fontsize=8,loc="upper left"); ax.grid(color="#eeeeee"); ax.set_axisbelow(True)
    save("fig08_calibration")
else: print("pas de table de fiabilite h2")
