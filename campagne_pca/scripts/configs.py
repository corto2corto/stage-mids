# Les configurations PCA retenues dans les rapports, sous forme exploitable.
#
# Ces parametres etaient jusqu'ici tapes a la main : rien dans le depot ne
# permettait de savoir ce que valaient « configA » ou « hebdoMonde ». Ils sont
# reconstitues depuis les tableaux et les titres des rapports (rapports/*.qmd),
# ou chaque configuration est decrite en toutes lettres.
#
# `fenetres` est le nombre de fenetres annonce par le rapport : il sert de
# controle. Une configuration rejouee qui ne le retrouve pas n'est pas la bonne
# (cf. verifier() plus bas).
#
# Couleurs : charte de chaque titre, reprises des anciens scripts de figures.
# Le Monde noir sobre, Le Figaro bleu marine, Les Échos rouge sombre, Mediapart
# rouge vif. ACCENT sert aux annotations, distinct de la couleur du media.

ACCENT = "#e34948"
BLEU_ETUDE = "#2a78d6"          # bleu neutre des planches « optimale »

COULEURS = {"lemonde": "#1A171B", "lefigaro": "#163860",
            "lesechos": "#b00005", "mediapart": "#fc392b"}
NOMS = {"lemonde": "Le Monde", "lefigaro": "Le Figaro",
        "lesechos": "Les Échos", "mediapart": "Mediapart"}


def _c(prefixe, base, grille, demi, seuil, fenetres, pics="", nettoie=0,
       couleur=None, accent=ACCENT, vol_q=50, vol_min=50, libelles=None,
       decalages=None):
    """Une configuration. `grille` est le pas en jours (1 = journalier)."""
    media = base if grille == 1 else f"{base}{grille}j"
    return (prefixe, dict(
        media=media, demi=demi, seuil=seuil, pas_jours=grille, pics=pics,
        nettoie=nettoie, prefixe=prefixe, media_nom=NOMS[base],
        couleur=couleur or COULEURS[base], accent=accent,
        vol_q=vol_q, vol_min=vol_min, fenetres=fenetres,
        libelles=libelles, decalages=decalages))


# Noms des composantes de la configuration optimale, retenus apres inspection.
LIBELLES_OPTIMALE = ["pic confiné au bloc du saut", "montée progressive, chute brutale",
                     "changement de niveau avant/après", "pic élargi, creux encadrants",
                     "oscillation lente", "oscillation rapide"]
# Placement manuel des etiquettes du plan PC1-PC2 (le placement auto se chevauche).
DECALAGES_OPTIMALE = {"francisco": (9, 4, "left"), "algérie": (-9, -14, "right"),
                      "mitterrand": (9, 6, "left"), "chirac": (11, -15, "left"),
                      "attentats": (9, 11, "left"), "jaunes": (2, -18, "left")}

CONFIGS = dict([
    # --- configurations_A_C.qmd + configurations_figaro.qmd (tableau l. 59-62)
    _c("configA", "lemonde", 3, 15, 6.0, 14_102),
    _c("configC", "lemonde", 3, 15, 5.0, 24_593),
    _c("configD", "lesechos", 1, 12, 5.0, 21_073, pics="_s3", nettoie=5000),
    _c("configF", "mediapart", 1, 5, 4.0, 20_237, pics="_s3", nettoie=5000),
    _c("configG", "lefigaro", 1, 15, 5.0, 17_939, pics="_s3", nettoie=5000),
    _c("configH", "lefigaro", 3, 15, 4.0, 18_375, pics="_s3"),

    # --- configurations_hebdo.qmd (tableau l. 53-58)
    _c("hebdoMonde", "lemonde", 7, 10, 4.0, 27_707),
    _c("hebdoFigaro", "lefigaro", 7, 10, 4.0, 11_311, pics="_s3"),
    _c("hebdoEchos", "lesechos", 7, 10, 4.0, 8_633, pics="_s3"),
    _c("hebdoMediapart", "mediapart", 7, 10, 4.0, 5_483, pics="_s3"),

    # --- configuration_optimale.qmd et rapport.qmd : bleu d'etude, pas de
    # filtre de volume (planches produites avant l'ajout du filtre)
    _c("optimale", "lemonde", 7, 10, 6.0, 8_764, couleur=BLEU_ETUDE,
       vol_q=0, vol_min=0, libelles=LIBELLES_OPTIMALE,
       decalages=DECALAGES_OPTIMALE),
])

# Planches d'une seule composante (composante3_lemonde.qmd) : configuration + rang.
COMPOSANTES = {"configA_comp3": ("configA", 3), "configC_comp3": ("configC", 3)}

# Jeux de comparaison multi-configurations (figures.py comparaison, *_A_C.qmd,
# *_hebdo.qmd) : (prefixe, media, demi, seuil, pics, nettoie, nom, sous-titre,
# couleur, unite). prefixe pointe vers un cache existant de CONFIGS.
JEUX = {
    "medias": dict(
        lignes=[
            ("configA", "lemonde3j", 15, 6.0, "", 0, "Le Monde",
             "blocs de 3 j, seuil 6 — 14 102 fenêtres", "#1A171B", "blocs de 3 j"),
            ("configC", "lemonde3j", 15, 5.0, "", 0, "Le Monde",
             "blocs de 3 j, seuil 5 — 24 593 fenêtres", "#1A171B", "blocs de 3 j"),
            ("configD", "lesechos", 12, 5.0, "_s3", 5000, "Les Échos",
             "journalier, seuil 5 — 21 073 fenêtres", "#b00005", "jours"),
            ("configF", "mediapart", 5, 4.0, "_s3", 5000, "Mediapart",
             "journalier, seuil 4 — 20 237 fenêtres", "#fc392b", "jours"),
        ],
        titre="La forme des sauts par configuration — trois premières composantes",
        rect=0.97, sortie="comparaison_medias.png"),
    "hebdo": dict(
        lignes=[
            ("hebdoMonde", "lemonde7j", 10, 4.0, "", 0, "Le Monde",
             "seuil 4 — 27 707 fenêtres", "#1A171B", "semaines"),
            ("hebdoFigaro", "lefigaro7j", 10, 4.0, "_s3", 0, "Le Figaro",
             "seuil 4 — 11 311 fenêtres", "#163860", "semaines"),
            ("hebdoEchos", "lesechos7j", 10, 4.0, "_s3", 0, "Les Échos",
             "seuil 4 — 8 633 fenêtres", "#b00005", "semaines"),
            ("hebdoMediapart", "mediapart7j", 10, 4.0, "_s3", 0, "Mediapart",
             "seuil 4 — 5 483 fenêtres", "#fc392b", "semaines"),
        ],
        titre="La forme des sauts par journal — trois premières composantes\n"
              "Grille hebdomadaire, fenêtres ±10 semaines, seuil 4",
        rect=0.95, sortie="comparaison_hebdo.png"),
}


def verifier(prefixe, n_fenetres):
    """Compare le nombre de fenetres obtenu a celui annonce par le rapport.

    Renvoie None si la configuration est inconnue ou sans effectif de reference.
    """
    attendu = CONFIGS.get(prefixe, {}).get("fenetres")
    if attendu is None:
        return None
    ecart = abs(n_fenetres - attendu)
    if ecart:
        print(f"  ATTENTION {prefixe} : {n_fenetres} fenetres obtenues, "
              f"{attendu} annoncees dans le rapport (ecart {ecart})")
    return ecart == 0


def parametres(prefixe):
    """Les arguments de figures.py pour une configuration, sans les metadonnees."""
    d = dict(CONFIGS[prefixe])
    d.pop("fenetres")
    return d
