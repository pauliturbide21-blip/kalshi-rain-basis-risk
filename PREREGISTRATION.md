# Préenregistrement de l'analyse empirique

Horodatage : 2026-09-16 19:11 UTC. Écrit avant tout téléchargement de données. Aucune définition ci-dessous n'est modifiée ensuite ; tout écart est consigné dans la section « écarts au protocole » du rapport.

Question : les contrats journaliers de pluie de Kalshi constituent-ils une couverture efficace pour un rooftop bar dont le chiffre d'affaires dépend de ses soirées en extérieur ?

## 1. Données

Kalshi, API publique sans authentification, base `https://api.elections.kalshi.com/trade-api/v2`. Séries visées : contrats journaliers « Will it rain in [ville] on [date] ? ». New York en priorité (ancienne série par ville, puis série multi-villes à partir du 15 juillet 2026), Miami et Chicago ensuite. Pour chaque marché : ticker, ville, date cible, statut, résultat de règlement, volume, open interest, chandeliers horaires, transactions si accessibles. Sauvegarde brute en JSON dans `data/raw/` avant tout traitement ; aucun re-téléchargement de ce qui est sur disque.

Précipitations horaires : Iowa Environmental Mesonet, service ASOS, `p01i` en pouces, `tz` locale, trace codée `T` et conservée distincte du zéro. Stations : NYC (Central Park), MIA, ORD.

Prévision de la veille : archive MOS de l'IEM, même station, probabilité de précipitation à 12 heures. Référence de calibration seulement ; si l'accès échoue, limite déclarée.

## 2. Définitions figées

- Saison : du 1er mai au 30 septembre inclus, chaque année où des marchés existent.
- Jour d'analyse : un jour civil local t de saison pour lequel un marché de pluie existe et s'est réglé, et pour lequel les données horaires de station couvrent la plage horaire de soirée. Les jours sans marché sont exclus (aucune couverture n'était possible) ; les jours sans données de station sur la plage sont exclus et comptés dans le rapport.
- Soirée perdue : D_t = 1 si le cumul de précipitations entre 18 h 00 et 01 h 00 heure locale (nuit rattachée au jour t, donc de 18 h le jour t à 1 h le jour t + 1) est supérieur ou égal à θ, référence θ = 1 mm (0,0394 pouce). La trace compte pour 0 mm.
- Règlement : Y_t = 1 si le contrat du jour t s'est réglé Oui.
- Prix de couverture : π_t = dernier prix échangé (close du chandelier horaire) strictement avant 12 h 00 heure locale la veille du jour t. Si aucun échange, milieu bid ask du chandelier horaire le plus proche antérieur, observation marquée imputée. Si aucun chandelier antérieur, observation sans prix, exclue des calculs de H2 et H3 et comptée.
- Frais : f_t = 0,07 × π_t × (1 − π_t) par contrat.
- Perte : L dollars de marge perdue sur une soirée perdue. Paramètre balayé, jamais estimé.
- Concentration : c = part de la marge annuelle réalisée sur les soirées de saison. Paramètre balayé.

## 3. Clarifications de dimension, posées avant les données

- Nombre de contrats : N = r × L, avec r le ratio de couverture. Un contrat paie 1 dollar si Y_t = 1. Profit de saison sans couverture : Π_0 = A − L × Σ D_t. Avec couverture : Π_r = Π_0 + N × Σ (Y_t − π_t − f_t). Le ratio de variance minimale h* est exprimé en contrats, h* = Cov(L × D, Y) / Var(Y), et r* = h* / L.
- Marge annuelle : A = n_s × L / c, où n_s est le nombre de jours d'analyse de la saison. Hypothèse déclarée : la marge d'une soirée vaut L et elle est entièrement perdue quand la soirée est perdue. La marge hors saison, (1 − c) × A, est certaine.
- Charges fixes annuelles F = (F/A) × A. Déficit S = max(0, F − marge réalisée). Coût d'un dollar de déficit : κ. La couverture crée de la valeur si κ × [E(S_0) − E(S_r)] > E(Π_0) − E(Π_r).

## 4. Grilles de sensibilité, déclarées à l'avance

- θ dans {0,25 ; 1 ; 2,5 ; 5} mm.
- Plage horaire dans {17 h à 23 h ; 18 h à 1 h ; 19 h à 2 h}.
- Heure d'achat dans {veille 12 h ; veille 18 h ; jour même 9 h}, heure locale.
- Ratio de couverture r dans {0,25 ; 0,5 ; 0,75 ; 1 ; r*}.
- L dans {2 000 ; 5 000 ; 10 000 ; 20 000} dollars.
- c de 0,05 à 0,90 par pas de 0,05.
- κ dans {0,2 ; 0,5 ; 1,0}. F/A dans {0,6 ; 0,75 ; 0,9}.
- Ville, mois, station alternative quand elle existe.

## 5. Analyse

H1, risque de base. Table de contingence Y_t × D_t sur les jours d'analyse. FP = P(D = 0 | Y = 1). UC = P(Y = 0 | D = 1). Coefficient phi et corrélation ρ entre L × D_t et Y_t. Les quatre états du monde en part des jours. Intervalles de confiance à 95 pour cent par bootstrap par blocs mobiles de 7 jours, 5 000 répétitions.

Expérience naturelle. Deux déclencheurs reconstruits depuis la station sur tout l'échantillon : déclencheur A, pluie journalière strictement positive ou trace (règle Kalshi avant le 15 juillet 2026) ; déclencheur B, pluie journalière strictement positive, trace exclue (règle depuis le 15 juillet 2026). Journée civile locale de 0 h à 23 h 59. FP, UC et ρ comparés entre A et B sur les mêmes jours. Concordance de chaque déclencheur avec le règlement officiel observé sur sa période de validité ; en dessous de 95 pour cent, enquête et documentation.

H2, chargement. Diagramme de fiabilité de π_t contre la fréquence réalisée de Y_t par déciles de prix. Score de Brier et décomposition (fiabilité, résolution, incertitude), erreur de calibration moyenne. Écart signé entre π_t et la prévision officielle. Chargement brut λ = π̄ / P(Y = 1) − 1. Chargement effectif, métrique principale : Λ = (π̄ + f̄) / P(Y = 1 et D = 1). Capacité : volume et open interest médians par jour, part de l'open interest que représenterait N = L contrats pour chaque L. Comparateur assurantiel : prime en pourcentage de la somme garantie balayée de 1,8 à 18 pour cent, probabilité de déclenchement estimée sur l'historique de station au seuil et sur la plage horaire de l'assureur (balayés : seuil dans {1 ; 2,5 ; 5} mm, plage dans {18 h à 1 h ; 12 h à minuit}), Λ_assurance = prime / P(déclenchement), comparé à Λ, présenté en plage.

Prévision officielle : MOS NBS cycle 12 Z de la veille, station de référence. Probabilité de pluie du jour civil t obtenue en combinant les deux périodes de 12 heures couvrant le jour, p = 1 − (1 − p12a)(1 − p12b) ; si un champ p24 existe pour la période, il est utilisé à la place. Déclaré avant lecture des données.

H3, valeur. h*, efficacité d'Ederington e = 1 − Var(Π_r) / Var(Π_0) avec vérification numérique que le maximum vaut ρ², semi-variance sous la moyenne, coût espéré E(Π_0) − E(Π_r), coût par unité de variance réduite. Rejeu de saisons par bootstrap par blocs sur les saisons historiques (blocs de 7 jours tirés dans les saisons observées, saison synthétique de n_s jours), jamais par loi ajustée. Critère de valeur balayé sur c, κ, F/A ; c* présenté comme une surface. Validation hors échantillon : h* estimé sur la saison 2025, efficacité évaluée sur 2026.

## 6. Ordre de priorité

H1 New York avec l'expérience naturelle ; H2 New York ; H3 New York ; villes supplémentaires ; grilles complètes.

## 7. Interdits

Choisir un paramètre après avoir vu son effet. Retirer des jours sans règle déclarée. Point estimé sans intervalle. Pluie simulée par loi ajustée. Confondre calibration du contrat et qualité de couverture. Combler un trou par une valeur plausible.
