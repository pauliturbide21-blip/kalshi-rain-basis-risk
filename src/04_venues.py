"""The ten venues: capacity, revenue and committed cost per night (low, central, high), from public sources.
Comments in the code are in French."""
import os, csv, math
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.makedirs(f"{HERE}/build",exist_ok=True); os.makedirs(f"{HERE}/data",exist_ok=True); os.makedirs(f"{HERE}/results",exist_ok=True)

# Depense par tete (boissons, hors taxes et pourboires) : 2 a 3 consommations a p dollars, plus 15 % de nourriture quand la carte existe
def spend(p_low,p_high,food=0.15): return (2.0*p_low*(1+food), 2.5*(p_low+p_high)/2*(1+food), 3.0*p_high*(1+food))

# Parametres par lieu : (capacite basse, centrale, haute), prix d'un cocktail (bas, haut), occupation soir normal (bas, central, haut),
# occupation grosse soiree, rotation soir normal, rotation grosse soiree, palier de programmation (cachet bas, central, haut), jours d'ouverture, soirees a programmation, statut
VENUES=[
 dict(nom="230 Fifth",quartier="NoMad, Manhattan",cap=(900,1200,1200),prix=(14,18),occ_n=(0.25,0.35,0.5),occ_b=(0.6,0.8,1.0),rot_n=(1.5,2.0,2.5),rot_b=(2.0,2.5,3.0),
      dj=(500,1500,3000),jours="lun-dim",prog="ven,sam",statut="retenu",
      src="capacite : site officiel et Vendry (1 200 sur le rooftop garden) ; prix : happy-hour.nyc (cocktail ~14 $, tiers) ; 1,1 M clients et 20 M$ par an en 2012 (Crain's) ; DJ live et soirees a theme (site)"),
 dict(nom="Elsewhere Rooftop",quartier="Bushwick, Brooklyn",cap=(400,500,500),prix=(10,14),occ_n=(0.3,0.45,0.6),occ_b=(0.7,0.85,1.0),rot_n=(1.2,1.5,2.0),rot_b=(1.5,2.0,2.5),
      dj=(1000,2500,5000),jours="jeu-dim",prog="jeu,ven,sam,dim",statut="retenu",
      src="capacite : Vendry (500 debout, 150 assis, mai a octobre) ; prix : Discotech (well 8 $, biere 6 $, cover ~20 $, tiers) ; DJ sets jeudi a dimanche, series recurrentes (site) ; billets d'ouverture 15 $ (amNY)"),
 dict(nom="The Rooftop at Pier 17",quartier="Seaport, Manhattan",cap=(2266,3400,3500),prix=(14,18),occ_n=(0.4,0.6,0.8),occ_b=(0.8,0.95,1.0),rot_n=(1.0,1.0,1.2),rot_b=(1.0,1.0,1.2),
      dj=(15000,40000,100000),jours="jeu-dim",prog="jeu,ven,sam,dim",statut="retenu, modele billetterie distinct",
      src="capacite : Vendry (3 500 debout, 2 266 assis) et Billboard (~3 400) ; saison 2026 du 2 mai au 10 octobre, plus de 60 concerts Live Nation (TicketNews) ; cachets : ordre de grandeur des garanties d'artistes de salle de 3 000 places, non publie"),
 dict(nom="Berry Park",quartier="Williamsburg, Brooklyn",cap=(250,300,300),prix=(9,13),occ_n=(0.3,0.45,0.6),occ_b=(0.7,0.85,1.0),rot_n=(1.5,2.0,2.5),rot_b=(2.0,2.5,3.0),
      dj=(300,600,1500),jours="mar-dim",prog="ven,sam",statut="sous reserve : toit decrit comme couvert et chauffe par Vendry",
      src="capacite : Revelr (~300, estime) ; DJ chaque vendredi et samedi (rooftop guide) ; horaires : Yelp ; prix non trouves, fourchette biere allemande et belge"),
 dict(nom="Time Out Market rooftop",quartier="Dumbo, Brooklyn",cap=(250,350,350),prix=(15,19),occ_n=(0.3,0.45,0.6),occ_b=(0.7,0.85,1.0),rot_n=(1.5,2.0,2.5),rot_b=(2.0,2.5,3.0),
      dj=(500,1500,3000),jours="lun-dim",prog="mer,jeu,ven,sam,dim",statut="retenu",
      src="capacite : Resident 2025 (350 debout a l'etage) ; privatisation du rooftop 28 000 $ pour 150 a 400 (Eventective) ; jazz mardi, DJ mercredi a samedi, live dimanche (Resident) ; prix non trouves, marche premium"),
 dict(nom="Sultan Room Rooftop",quartier="Bushwick, Brooklyn",cap=(150,200,250),prix=(12,16),occ_n=(0.3,0.45,0.6),occ_b=(0.7,0.85,1.0),rot_n=(1.2,1.5,2.0),rot_b=(1.5,2.0,2.5),
      dj=(300,800,2000),jours="mar-dim",prog="jeu,ven,sam,dim",statut="retenu",
      src="capacite rooftop non trouvee, salle interieure 201 debout (site) ; residences DJ jeudi a dimanche, vinyl mardi (Brooklyn Paper) ; rooftop 17 h a 23 h (Brooklyn Paper) ; prix non trouves"),
 dict(nom="Eagle NYC",quartier="West Chelsea, Manhattan",cap=(200,300,400),prix=(10,14),occ_n=(0.3,0.45,0.6),occ_b=(0.7,0.85,1.0),rot_n=(1.5,2.0,2.5),rot_b=(2.0,2.5,3.0),
      dj=(300,600,1500),jours="lun-dim",prog="ven,sam,dim",statut="retenu, toit chauffe",
      src="capacite non trouvee, bar sur plusieurs niveaux avec roof deck (Wikipedia, Atly) ; DJ a chaque niveau, soirees quotidiennes (NYC Tourism) ; horaires 22 h a 4 h (Atly) ; prix non trouves"),
 dict(nom="City Vineyard (Pier 26)",quartier="Tribeca, Manhattan",cap=(150,200,250),prix=(14,18),occ_n=(0.3,0.5,0.7),occ_b=(0.7,0.85,1.0),rot_n=(1.5,2.0,2.5),rot_b=(1.5,2.0,2.5),
      dj=(500,1500,3000),jours="lun-dim",prog="ven,sam",statut="retenu, programmation concerts et non DJ",
      src="capacite : site officiel (South Rooftop 150 en reception, buyout 550) ; concerts Voices on the Hudson limites a 100 billets (site) ; horaires site ; rooftop saisonnier, dates non trouvees ; prix non trouves"),
 dict(nom="Bar 13",quartier="Union Square, Manhattan",cap=(100,150,200),prix=(8,12),occ_n=(0.3,0.45,0.6),occ_b=(0.7,0.85,1.0),rot_n=(1.5,2.0,2.5),rot_b=(2.0,2.5,3.0),
      dj=(300,600,1500),jours="lun-dim",prog="jeu,ven,sam",statut="sous reserve : site en travaux, sources contradictoires",
      src="capacite non trouvee, toit petit (Rooftop Drinker) ; cocktails 5 a 10 $, cover 10 a 20 $ (Discotech, ancien) ; Top 40, afrobeats, soiree RA fevrier 2026 (Resident Advisor)"),
 dict(nom="Watermark (Pier 15)",quartier="Seaport, Manhattan",cap=(600,900,1200),prix=(12,16),occ_n=(0.25,0.4,0.55),occ_b=(0.6,0.8,1.0),rot_n=(1.5,2.0,2.5),rot_b=(2.0,2.5,3.0),
      dj=(500,1500,3000),jours="lun-dim",prog="ven,sam",statut="sous reserve : terrasse de jetee, pas un toit d'immeuble",
      src="capacite : site officiel (200 a 1 200 invites, 10 000 sq ft) ; happy hour biere 8 $, cocktail canette 10 $ (menu) ; DJ reggaeton vendredi et samedi 21 h (site) ; Watermark Beach des le 1er mai 2026 (Time Out)"),
]
WAGE={"serveur":(14.15+3,14.15+6,17+8),"barman":(14.15+5,14.15+8,17+12),"securite":(18,21,26),"hote":(17,19,22),"sup":(25,30,35)}  # taux horaire charge de pourboire estime, bas/central/haut
HOURS=(6,7,8)
def staff_cost(cap,level):
    """personnel d'une soiree pour une capacite donnee, ratio Porcci pour 500 personnes, mis a l'echelle"""
    i={"low":0,"mid":1,"high":2}[level]; scale=cap/500
    n_serv=(12,12.5,13)[i]*scale; n_bar=(5,6,7)[i]*scale; n_hote=(2,2.5,3)[i]*scale; n_sec=max(2,cap/(50,37,25)[i]); n_sup=1
    h=HOURS[i]
    return h*(n_serv*WAGE["serveur"][i]+n_bar*WAGE["barman"][i]+n_hote*WAGE["hote"][i]+n_sec*WAGE["securite"][i]+n_sup*WAGE["sup"][i])
rows=[]; params=[]
for v in VENUES:
    s=spend(*v["prix"])
    R_n=[v["cap"][i]*v["occ_n"][i]*v["rot_n"][i]*s[i] for i in range(3)]
    R_b=[v["cap"][i]*v["occ_b"][i]*v["rot_b"][i]*s[i] for i in range(3)]
    # cout engage la veille : personnel (verrouille 14 jours avant, indemnite de presence), securite, programmation (acompte 50 % non remboursable au minimum, cachet du en cas d'annulation le jour meme : on retient 100 % pour la grosse soiree), promotion 5 % de la recette attendue
    K_n=[staff_cost(v["cap"][i]*0.6,l)+0.5*v["dj"][i]*0.3+0.03*R_n[i] for i,l in enumerate(["low","mid","high"])]   # soir normal : equipe reduite, programmation legere
    K_b=[staff_cost(v["cap"][i],l)+v["dj"][i]+0.05*R_b[i] for i,l in enumerate(["low","mid","high"])]
    if "Pier 17" in v["nom"]:
        # billetterie : recette de billets 45 a 75 $ prevendus a 70 % (peu sensible a la pluie), bar en sus ; cout = garantie d'artiste + production
        tick=[v["cap"][i]*v["occ_b"][i]*(45,60,75)[i] for i in range(3)]
        R_b=[tick[i]+v["cap"][i]*v["occ_b"][i]*s[i]*0.6 for i in range(3)]; R_n=R_b
        K_b=[v["dj"][i]+staff_cost(v["cap"][i],l)+0.15*tick[i] for i,l in enumerate(["low","mid","high"])]; K_n=K_b
    rows.append({"nom":v["nom"],"quartier":v["quartier"],"statut":v["statut"],"capacite_basse":v["cap"][0],"capacite":v["cap"][1],"capacite_haute":v["cap"][2],
                 "prix_cocktail_bas":v["prix"][0],"prix_cocktail_haut":v["prix"][1],"depense_tete_basse":round(s[0]),"depense_tete":round(s[1]),"depense_tete_haute":round(s[2]),
                 "jours_ouverture":v["jours"],"soirees_programmees":v["prog"],"cachet_bas":v["dj"][0],"cachet":v["dj"][1],"cachet_haut":v["dj"][2],
                 "R_normal_bas":round(R_n[0]),"R_normal":round(R_n[1]),"R_normal_haut":round(R_n[2]),"R_grosse_bas":round(R_b[0]),"R_grosse":round(R_b[1]),"R_grosse_haut":round(R_b[2]),
                 "K_normal_bas":round(K_n[0]),"K_normal":round(K_n[1]),"K_normal_haut":round(K_n[2]),"K_grosse_bas":round(K_b[0]),"K_grosse":round(K_b[1]),"K_grosse_haut":round(K_b[2]),
                 "methode":"R = capacite x occupation x rotation x depense par tete (2 a 3 consommations plus 15 % de nourriture) ; K = personnel au ratio Porcci pour 500 personnes mis a l'echelle x 6 a 8 h x taux NYSDOL charges, plus securite (1 agent pour 25 a 50), plus cachet (100 % pour une grosse soiree, 15 % pour un soir normal), plus promotion (3 a 5 % de R)",
                 "sources":v["src"]})
    params.append({"nom":v["nom"],"occ_normal":v["occ_n"],"occ_grosse":v["occ_b"],"rot_normal":v["rot_n"],"rot_grosse":v["rot_b"],"heures":HOURS,"spend":tuple(round(x) for x in s)})
with open(f"{HERE}/data/venues.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open(f"{HERE}/build/panel_parametres.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(params[0].keys())); w.writeheader(); w.writerows(params)
for r in rows: print(f"{r['nom']:26s} cap {r['capacite']:5d}  R normal {r['R_normal_bas']:7d} {r['R_normal']:7d} {r['R_normal_haut']:7d} | R grosse {r['R_grosse_bas']:7d} {r['R_grosse']:7d} {r['R_grosse_haut']:7d} | K grosse {r['K_grosse_bas']:6d} {r['K_grosse']:6d} {r['K_grosse_haut']:6d}")
