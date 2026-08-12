# Briques communes des figures de la campagne PCA : style, chaine de calcul et
# vues partagees par plusieurs planches. Les points d'entree sont dans
# figures.py ; ici rien ne s'execute a l'import hors le style matplotlib.
#
# La chaine (pics -> NMS -> fenetres -> z-score -> PCA) etait recopiee dans les
# huit anciens scripts figures_*.py ; elle vit maintenant dans charger().
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")               # scripts en ligne de commande : pas de fenetre
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

from rupture.nms import nms
from rupture.pca import nettoyer, normaliser, pca

from campagne_pca.scripts.configs import parametres

# rupture.pca et rupture.graphes imposent Agg a l'import. Sous Jupyter — donc
# dans les blocs {python} des .qmd — cela empeche la capture des figures : on
# rend la main au backend inline, qui les serialise pour le document.
if "ipykernel" in sys.modules:
    matplotlib.use("module://matplotlib_inline.backend_inline")

# palette de la campagne (valeurs reprises telles quelles des anciens scripts)
BLEU, ROUGE = "#2a78d6", "#e34948"
GRILLE, ENCRE, ENCRE2, GRIS, AXE = "#e1e0d9", "#1a1a1a", "#52514e", "#c9ced6", "#c3c2b7"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9,
    "axes.edgecolor": AXE, "axes.linewidth": 0.8, "axes.labelcolor": ENCRE2,
    "xtick.color": ENCRE2, "ytick.color": ENCRE2,
    "axes.spines.top": False, "axes.spines.right": False,
})

# campagne_pca/ est le parent de scripts/ ; data/ et figures/ y sont freres.
SCRIPTS = Path(__file__).resolve().parent
ICI = SCRIPTS.parent
DATA = ICI / "data"
DONNEES = Path(os.environ.get("VOCAB_DIR", DATA / "data_local"))
SPECTRES = DATA / "kernel_spectres"
CACHE = DATA / "cache_pca"
FIGURES = ICI / "rapport_qmd" / "figures"

# mots-evenements cherches dans le plan PC1-PC2 (absents d'une config : ignores)
CANDIDATS = [("francisco", "conf. de San Francisco (ONU), 1945"),
             ("algérie", "accords d'Évian, 1962"),
             ("mitterrand", "réélection, 1988"),
             ("chirac", "élection, 1995"),
             ("attentats", "13-Novembre, 2015"),
             ("jaunes", "gilets jaunes, 2018"),
             ("covid", "Covid, 2020"),
             ("syrienne", "guerre civile syrienne")]


def sortie(nom):
    """Chemin d'un png de figures/ (cree le dossier au besoin)."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    return FIGURES / nom


def rendre(fig, chemin, dpi=200):
    """Ecrit la figure si un chemin est donne, sinon l'affiche (blocs {python}).

    chemin=None sert aux .qmd : plt.show() remet la figure a Quarto, qui
    l'insere dans le document. Rien n'est renvoye — la valeur d'une cellule
    serait affichee une seconde fois, en doublon de la figure.
    """
    if chemin is None:
        plt.show()
        return None
    fig.savefig(chemin, bbox_inches="tight", dpi=dpi)
    plt.close(fig)
    return chemin


def depuis_cache(prefixe):
    """Le resultat deja calcule d'une configuration, ou None s'il n'est pas la.

    Le cache est construit sur le serveur (scripts/construire_cache.py) : c'est
    ce qui permet de tracer en local sans les vocab_series_*.npz.
    """
    fichier = CACHE / f"{prefixe}.npz"
    if not fichier.exists():
        return None
    g = np.load(fichier, allow_pickle=False)
    Z, variance = g["Z"], g["variance"]
    demi = (Z.shape[1] - 1) // 2
    cum = np.cumsum(variance)
    return SimpleNamespace(
        Z=Z, composantes=g["composantes"], variance=variance, proj=g["proj"], cum=cum,
        mots=g["mots"], dates=g["dates"], surprise=g["surprise"], volume=g["volume"],
        demi=demi, js=np.arange(-demi, demi + 1), D=Z.shape[1], rang=Z.shape[1] - 1,
        K50=int(np.searchsorted(cum, 0.5) + 1))


def charger(media, demi, seuil, pics="", nettoie=0):
    """Chaine commune : pics filtres -> NMS (portee 2d+1) -> fenetres -> z-score -> PCA.

    Renvoie les fenetres z-scorees, la PCA, et — alignes ligne a ligne sur elles —
    le mot, la date, la surprise et le volume (pic en occurrences brutes) de
    chaque fenetre. nettoie > 0 interpole les jours dont N_t passe sous ce seuil.
    """
    g = np.load(DONNEES / f"vocab_series_{media}.npz")
    X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
    position = {int(dt): i for i, dt in enumerate(grille_dates)}
    colonne = {m: j for j, m in enumerate(g["mots"])}

    p = pd.read_csv(DONNEES / f"pics_{media}{pics}.csv")
    p = p[p["surprise"] >= seuil].assign(pos=lambda x: x["date"].map(position))
    gardes = [gr.index.to_numpy()[nms(gr["pos"].to_numpy(), gr["surprise"].to_numpy(),
                                     2 * demi + 1)[0]]
              for _, gr in p.groupby("mot", sort=False)]
    p = p.loc[np.concatenate(gardes)]
    pos, col = p["pos"].to_numpy(), p["mot"].map(colonne).to_numpy(int)
    complet = (pos - demi >= 0) & (pos + demi < len(grille_dates))
    p, pos, col = p[complet], pos[complet], col[complet]
    lignes = pos[:, None] + np.arange(-demi, demi + 1)
    brut = X[lignes, col[:, None]]          # occurrences brutes, avant tout rapport a N_t
    F = (1e5 * brut / grille_N[lignes]).astype(np.float64)

    if nettoie:
        F, garde_n, _, _ = nettoyer(F, grille_N[lignes], nettoie, demi)
        p, brut = p.iloc[garde_n], brut[garde_n]
    Z, garde_z = normaliser(F, "z")
    p, brut = p.iloc[garde_z], brut[garde_z]
    composantes, variance, proj = pca(Z)
    cum = np.cumsum(variance)
    return SimpleNamespace(
        Z=Z, composantes=composantes, variance=variance, proj=proj, cum=cum,
        mots=p["mot"].to_numpy(), dates=p["date"].to_numpy(),
        surprise=p["surprise"].to_numpy(),
        volume=brut.max(axis=1),            # volume d'une fenetre = son pic en occurrences
        demi=demi, js=np.arange(-demi, demi + 1), D=2 * demi + 1, rang=2 * demi,
        K50=int(np.searchsorted(cum, 0.5) + 1))


def presentation(media_nom, demi, seuil, pas_jours, couleur, accent, libelles=None,
                  decalages=None):
    """Habillage d'une planche : titre, unite de l'axe, couleurs, noms des composantes."""
    if pas_jours == 1:
        grille_libelle, unite_axe = (f"journalier, fenêtres ±{demi} jours",
                                     "jours autour du pic")
    else:
        grille_libelle = (f"blocs de {pas_jours} jours, fenêtres ±{demi} blocs "
                          f"(±{demi * pas_jours} jours de parution)")
        unite_axe = f"blocs de {pas_jours} jours autour du pic"
    return SimpleNamespace(
        titre=f"{media_nom}, {grille_libelle}, seuil de surprise {seuil:g}",
        unite_axe=unite_axe, couleur=couleur, accent=accent, decalages=decalages,
        libelles=libelles or [f"composante {k + 1}" for k in range(6)])


def cmap_media(couleur):
    """Degrade blanc -> couleur de charte, pour les hexbin."""
    return mcolors.LinearSegmentedColormap.from_list("media", ["#ffffff", couleur])


def cadre(ax):
    """Grille horizontale discrete, sous les traces."""
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)


def reperes(ax):
    """Les deux axes zero d'un profil de fenetre."""
    ax.axhline(0, lw=.6, color=GRILLE)
    ax.axvline(0, lw=.6, color=GRILLE)


def formes(d):
    """Indicateurs de forme des 6 premieres composantes, pour les nommer."""
    for k in range(6):
        v = d.composantes[k]
        centre = (v[np.abs(d.js) <= d.demi // 4] ** 2).sum() / (v ** 2).sum()
        print(f"  comp {k + 1} : {int((np.diff(np.sign(v)) != 0).sum())} croisements, "
              f"{centre * 100:3.0f} % d'energie au centre, "
              f"signe(avant)={np.sign(v[:d.demi].mean()):+.0f} "
              f"signe(apres)={np.sign(v[d.demi + 1:].mean()):+.0f}")


def filtre_volume(volume, vol_q, vol_min, mini):
    """Fenetres eligibles au titre d'archetype, et le seuil retenu.

    Le z-score efface l'echelle : sans ce filtre, un mot a 30 occurrences peut
    s'aligner parfaitement sur une composante et s'afficher comme archetype alors
    qu'il ne pese rien. La PCA, elle, reste calculee sur toutes les fenetres.
    """
    seuil_vol = max(np.percentile(volume, vol_q) if vol_q > 0 else 0, vol_min)
    eligibles = np.where(volume >= seuil_vol)[0]
    if len(eligibles) < mini:               # corpus trop maigre : on renonce au filtre
        print(f"  (archetypes) filtre de volume ignore : seuil {seuil_vol:.0f} ne laisse "
              f"que {len(eligibles)} fenetres")
        return 0, np.arange(len(volume))
    if seuil_vol > 0:
        print(f"  (archetypes) filtre de volume : >= {seuil_vol:.0f} occurrences au pic "
              f"(q{vol_q:g} = {np.percentile(volume, vol_q):.0f}, plancher {vol_min}) : "
              f"{len(eligibles)} fenetres eligibles sur {len(volume)}")
    return seuil_vol, eligibles


def config(prefixe, mini=3):
    """Une configuration chargee depuis le cache et prete a tracer.

    Factorise les quatre lignes (parametres -> cache -> presentation -> filtre
    de volume) repetees a l'identique dans les .qmd de la campagne.
    """
    p = parametres(prefixe)
    d = depuis_cache(prefixe)
    pres = presentation(p["media_nom"], p["demi"], p["seuil"], p["pas_jours"],
                         p["couleur"], p["accent"], p["libelles"], p["decalages"])
    seuil_vol, eligibles = filtre_volume(d.volume, p["vol_q"], p["vol_min"], mini)
    return d, pres, seuil_vol, eligibles


def ticks_log(ax, v):
    """Graduations en chiffres simples sur un axe log : matplotlib ecrirait
    « 2 x 10^1 » sous la decade."""
    bas, haut = v.min() * 0.9, v.max() * 1.15
    echelle = [c * 10 ** p for p in range(-2, 3) for c in (1, 1.5, 2, 3, 5, 7)]
    ticks = [t for t in echelle if bas <= t <= haut]
    ax.set_yticks(ticks)
    ax.set_yticks([], minor=True)
    ax.set_yticklabels([f"{t:g}".replace(".", ",") for t in ticks])
    ax.set_ylim(bas, haut)


# --- synthese : effets des hyperparametres, carte des medias -----------------

NOMS_MEDIAS = {"lemonde": "Le Monde", "lefigaro": "Le Figaro",
               "lesechos": "Les Échos", "mediapart": "Mediapart"}

AXES_SYNTHESE = [("base", "média", [NOMS_MEDIAS[b] for b in
                                    ["mediapart", "lesechos", "lemonde", "lefigaro"]],
                  ["mediapart", "lesechos", "lemonde", "lefigaro"]),
                 ("grille", "grille de temps", ["journalier", "3 jours", "7 jours"],
                  ["1j", "3j", "7j"]),
                 ("demi", "demi-fenêtre (± pas)", ["10", "15", "25", "50"],
                  [10, 15, 25, 50]),
                 ("seuil", "seuil de surprise", ["4", "6"], [4.0, 6.0])]


def donnees_synthese():
    """resultats_rotation.csv filtre : n apparie 5000, brut (sans log), grille equilibree.

    Cellule = (grille, demi, seuil, filtre) ; equilibree = presente pour les 4 medias.
    """
    r = pd.read_csv(DATA / "resultats_rotation.csv")
    r = r[(r["n_fenetres"] == 5000) & ~r["tag"].str.contains("_log")].copy()
    r["base"] = r["media"].str.replace(r"(3j|7j)$", "", regex=True)
    r["grille"] = r["media"].str.extract(r"(3j|7j)$")[0].fillna("1j")
    r["cellule"] = r["grille"] + "|" + r["demi"].astype(str) + "|" + \
        r["seuil"].astype(str) + "|" + r["filtre"]
    r = r.groupby(["base", "cellule", "grille", "demi", "seuil", "filtre"],
                  as_index=False)[["exces6", "alignement6"]].mean()   # graines
    completes = r.groupby("cellule")["base"].nunique()
    return r[r["cellule"].map(completes) == 4]                        # equilibre


def vue_synthese_axes(r, chemin):
    """Effets des 4 axes (media, grille, demi-fenetre, seuil) sur exces6/alignement6."""
    from rupture.graphes import BLEU, ORANGE
    fig, axs = plt.subplots(1, 4, figsize=(10.4, 3.2), sharey=True)
    for ax, (col, titre, etiquettes, ordre) in zip(axs, AXES_SYNTHESE):
        m = r.groupby(col)[["exces6", "alignement6"]].mean().loc[ordre]
        x = np.arange(len(ordre))
        ax.axhline(1, lw=.8, color=GRILLE)
        ax.plot(x, m["alignement6"], "-", lw=2, color=ORANGE, marker="o", ms=6,
                label="alignement6 (part ancrée sur le pic)")
        ax.plot(x, m["exces6"], "-", lw=2, color=BLEU, marker="o", ms=6,
                label="exces6 (structure au-delà des marges)")
        ax.set_xticks(x, etiquettes, fontsize=8)
        ax.set_title(titre, fontsize=9.5, color=ENCRE2)
        cadre(ax)
    axs[0].set_ylabel("concentration relative au nul", fontsize=9)
    poignees, textes = axs[0].get_legend_handles_labels()
    fig.legend(poignees, textes, frameon=False, fontsize=8.5, ncol=2,
               loc="upper center", bbox_to_anchor=(0.5, 0.93))
    fig.suptitle("Effets des hyperparamètres sur les deux métriques — brut, "
                 "n apparié à 5 000 fenêtres, grille équilibrée",
                 fontsize=10.5, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    return rendre(fig, chemin)


def vue_synthese_carte(r, chemin):
    """Carte (exces6, alignement6) des media x grilles a la config de reference."""
    from rupture.graphes import BLEU
    ref = r[(r["demi"] == 15) & (r["seuil"] == 4.0) & (r["filtre"] == "tous")]
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.axhline(1, lw=.8, color=GRILLE)
    ax.axvline(1, lw=.8, color=GRILLE)
    decalages = {("mediapart", "3j"): (-8, -14), ("mediapart", "7j"): (7, 6),
                 ("lemonde", "7j"): (-30, -16), ("lefigaro", "3j"): (7, 8)}
    for _, ligne in ref.iterrows():
        ax.scatter(ligne["exces6"], ligne["alignement6"], s=46, color=BLEU, zorder=3)
        dx, dy = decalages.get((ligne["base"], ligne["grille"]), (7, 3))
        ax.annotate(f"{NOMS_MEDIAS[ligne['base']]} {ligne['grille']}",
                    (ligne["exces6"], ligne["alignement6"]),
                    xytext=(dx, dy), textcoords="offset points",
                    fontsize=8, color=ENCRE2)
    ax.set_xlabel("exces6 — structure totale (texture comprise)", fontsize=9)
    ax.set_ylabel("alignement6 — part ancrée sur l'événement", fontsize=9)
    ax.set_title("Carte des médias × grilles (référence ±15, s4, tous, brut, "
                 "n = 5 000)", fontsize=10, color=ENCRE2)
    ax.grid(True, lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return rendre(fig, chemin)


# --- les cinq vues d'une configuration --------------------------------------

def vue_spectre(d, pres, chemin):
    """Variance expliquee par composante (z-score seul), echelle log."""
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    rangs = np.arange(1, d.D)
    v = d.variance[:d.rang] * 100
    isotrope = 100 / d.rang
    ax.plot(rangs, v, lw=1.8, color=pres.couleur, label="z-score par fenêtre")
    ax.scatter(rangs[:1], v[:1], s=18, color=pres.couleur)
    ax.annotate(f"{v[0]:.1f} %".replace(".", ","), (1, v[0]), xytext=(7, 2),
                textcoords="offset points", fontsize=8.5, color=ENCRE2)
    ax.axhline(isotrope, lw=1.0, ls="--", color=pres.accent,
               label=f"nuage sans structure ({isotrope:.1f} %)".replace(".", ","))
    ax.set_yscale("log")
    ticks_log(ax, v)
    ax.set_xlabel("rang de la composante")
    ax.set_ylabel("variance expliquée (%)")
    ax.set_xlim(0.5, d.D - 0.5)
    ax.set_xticks([1] + list(range(5, d.D, 5)))
    ax.legend(frameon=False, fontsize=8.5)
    cadre(ax)
    ax.set_title(f"Variance expliquée par composante — {d.K50} composantes pour 50 % "
                 f"(K50/rang={d.K50 / d.rang:.2f})\n{pres.titre}",
                 fontsize=9.5, color=ENCRE2)
    fig.tight_layout()
    return rendre(fig, chemin)


def vue_composantes(d, pres, chemin):
    """Les six premieres composantes comme profils temporels."""
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.2), sharex=True)
    for k, ax in enumerate(axes.flat):
        reperes(ax)
        ax.plot(d.js, d.composantes[k], lw=1.7, color=pres.couleur)
        ax.set_title(f"composante {k + 1} — {d.variance[k] * 100:.1f} %\n{pres.libelles[k]}",
                     fontsize=8.5, color=ENCRE2)
        ax.set_xticks([-d.demi, 0, d.demi])
        cadre(ax)
    for ax in axes[1]:
        ax.set_xlabel(pres.unite_axe)
    fig.suptitle(f"Les six premières composantes comme profils temporels\n{pres.titre}",
                 fontsize=10, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return rendre(fig, chemin)


def vue_plan12(d, pres, chemin, decalages=None):
    """Densite du nuage dans le plan PC1-PC2, evenements connus situes."""
    decalages = decalages or {}
    fig, ax = plt.subplots(figsize=(7.6, 5.6))
    hb = ax.hexbin(d.proj[:, 0], d.proj[:, 1], gridsize=60, bins="log",
                   cmap=cmap_media(pres.couleur), linewidths=0.2)
    fig.colorbar(hb, ax=ax, label="fenêtres par case (échelle log)", shrink=0.85)
    places = []
    for mot, libelle in CANDIDATS:
        sel = d.mots == mot
        if not sel.any():
            print(f"  (plan) « {mot} » absent de cette configuration")
            continue
        i = np.where(sel)[0][np.argmax(d.surprise[sel])]
        quand = pd.to_datetime(str(d.dates[i])).strftime("%m/%Y")
        ax.scatter(d.proj[i, 0], d.proj[i, 1], s=26, color=pres.accent, zorder=3)
        places.append((d.proj[i, 0], d.proj[i, 1], f"{mot} — {libelle}", mot))
        print(f"  (plan) {mot} {quand} : PC1={d.proj[i, 0]:+.1f} PC2={d.proj[i, 1]:+.1f}")
    for x, y, texte, mot in places:
        dx, dy, ha = decalages.get(mot, (9, 4, "left"))
        ax.annotate(texte, (x, y), xytext=(dx, dy), ha=ha,
                    textcoords="offset points", fontsize=8, color=ENCRE2,
                    arrowprops={"arrowstyle": "-", "color": AXE, "lw": 0.6})
    ax.set_xlabel(f"composante 1 ({d.variance[0] * 100:.1f} % — {pres.libelles[0]})")
    ax.set_ylabel(f"composante 2 ({d.variance[1] * 100:.1f} % — {pres.libelles[1]})")
    effectif = f"{len(d.Z):,}".replace(",", " ")
    ax.set_title(f"Les {effectif} fenêtres dans le plan des deux premières composantes\n"
                 f"{pres.titre}", fontsize=9.5, color=ENCRE2)
    fig.tight_layout()
    return rendre(fig, chemin)


def vue_archetypes(d, pres, chemin, seuil_vol, eligibles):
    """Les 3 fenetres reelles les plus alignees sur chacune des 4 premieres composantes."""
    fig, axes = plt.subplots(4, 3, figsize=(9.2, 9.6), sharex=True)
    for k in range(4):
        meilleurs = eligibles[np.argsort(d.proj[eligibles, k])[-3:][::-1]]
        for c, i in enumerate(meilleurs):
            ax = axes[k, c]
            reperes(ax)
            ax.plot(d.js, d.Z[i], lw=1.4, color=pres.couleur)
            ax.scatter([0], [d.Z[i, d.demi]], s=16, color=pres.accent, zorder=3)
            quand = pd.to_datetime(str(d.dates[i])).strftime("%d/%m/%Y")
            ax.set_title(f"{d.mots[i]} — {quand}\n{int(d.volume[i])} occ. au pic",
                         fontsize=8.5, color=ENCRE2)
            cadre(ax)
            if c == 0:
                ax.set_ylabel(f"comp. {k + 1}\n({pres.libelles[k]})", fontsize=8.5)
        print(f"  (archetypes) comp {k + 1} : "
              + ", ".join(f"{d.mots[i]} {int(d.dates[i])} ({int(d.volume[i])} occ.)"
                          for i in meilleurs))
    for ax in axes[-1]:
        ax.set_xticks([-d.demi, 0, d.demi])
        ax.set_xlabel(pres.unite_axe)
    filtre_libelle = (f",\nparmi les fenêtres d'au moins {seuil_vol:.0f} occurrences au pic"
                      if seuil_vol > 0 else "")
    fig.suptitle("Fenêtres archétypes : les 3 sauts réels les plus alignés sur chaque "
                 f"composante (z-score){filtre_libelle}\n{pres.titre}",
                 fontsize=10, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.95 if seuil_vol > 0 else 0.96))
    return rendre(fig, chemin)


def vue_reconstruction(d, pres, chemin):
    """Reconstruction progressive d'une fenetre celebre (repli : la plus surprenante)."""
    sel = np.zeros(len(d.mots), dtype=bool)
    for mot_cible in ("jaunes", "attentats", "covid", "chirac"):
        sel = d.mots == mot_cible
        if sel.any():
            break
    if not sel.any():
        sel = np.ones(len(d.mots), dtype=bool)
    i = np.where(sel)[0][np.argmax(d.surprise[sel])]
    w, Zmoy = d.Z[i], d.Z.mean(axis=0)
    paliers = sorted({1, 3, d.K50, 6})           # K50 inclus, en ordre croissant
    fig, axes = plt.subplots(1, len(paliers), figsize=(11.2, 3.0), sharey=True)
    for ax, K in zip(axes, paliers):
        recon = Zmoy + d.proj[i, :K] @ d.composantes[:K]
        restitue = 1 - ((w - recon) ** 2).sum() / ((w - w.mean()) ** 2).sum()
        reperes(ax)
        ax.plot(d.js, w, lw=2.0, color=GRIS)
        ax.plot(d.js, recon, lw=1.5, color=pres.couleur)
        ax.set_title(f"{K} composante{'s' if K > 1 else ''} — "
                     f"{restitue * 100:.0f} % restitués", fontsize=9, color=ENCRE2)
        ax.set_xticks([-d.demi, 0, d.demi])
        ax.set_xlabel(pres.unite_axe)
        cadre(ax)
    quand = pd.to_datetime(str(d.dates[i])).strftime("%d/%m/%Y")
    fig.suptitle(f"Reconstruction de la fenêtre « {d.mots[i]} » du {quand} (en gris) par "
                 f"les premières composantes (bleu)\n{pres.titre}",
                 fontsize=9.5, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    return rendre(fig, chemin)


def vue_comparaison(lignes, titre, rect, chemin):
    """Profils compares de plusieurs configurations : 3 premieres composantes en grille.

    lignes : (prefixe, media, demi, seuil, pics, nettoie, nom, sous_titre, couleur,
    unite). Lit le cache PCA de prefixe (data/cache_pca/), retombe sur la chaine
    complete si absent.
    """
    fig, axes = plt.subplots(len(lignes), 3, figsize=(9.6, 10.4))
    for row, (prefixe, media, demi, seuil, pics, nettoie, nom, sous_titre, couleur, unite) \
            in enumerate(lignes):
        d = depuis_cache(prefixe) or charger(media, demi, seuil, pics, nettoie)
        for k in range(3):
            ax = axes[row, k]
            reperes(ax)
            ax.plot(d.js, d.composantes[k], lw=1.7, color=couleur)
            ax.set_title(f"composante {k + 1} — {d.variance[k] * 100:.1f} %",
                         fontsize=8.5, color=ENCRE2)
            ax.set_xticks([-demi, 0, demi])
            cadre(ax)
            if row == len(lignes) - 1:
                ax.set_xlabel(f"{unite} autour du pic", fontsize=8)
            if k == 0:
                ax.set_ylabel(f"{nom}\n{sous_titre}", fontsize=8.5)
        print(f"{nom} ({sous_titre}) : {len(d.Z)} fenêtres, variance 1-3 = "
              f"{np.round(d.variance[:3] * 100, 1)}")
    fig.suptitle(titre, fontsize=11, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, rect))
    return rendre(fig, chemin)


def vue_comp_archetypes(d, pres, chemin, comp, seuil_vol, eligibles):
    """Planche d'une seule composante : son profil, puis ses 12 sauts les plus alignes."""
    K = comp - 1
    fig = plt.figure(figsize=(9.2, 11.4))
    gs = fig.add_gridspec(5, 3, height_ratios=[1.15, 1, 1, 1, 1], hspace=0.55, wspace=0.22)

    axp = fig.add_subplot(gs[0, 1])
    reperes(axp)
    axp.plot(d.js, d.composantes[K], lw=1.9, color=pres.couleur)
    axp.set_title(f"profil de la composante {comp} — {d.variance[K] * 100:.1f} %",
                  fontsize=9, color=ENCRE2)
    axp.set_xticks([-d.demi, 0, d.demi])
    axp.set_xlabel(pres.unite_axe, fontsize=8)
    cadre(axp)

    meilleurs = eligibles[np.argsort(d.proj[eligibles, K])[-12:][::-1]]
    for c, i in enumerate(meilleurs):
        ax = fig.add_subplot(gs[1 + c // 3, c % 3])
        reperes(ax)
        ax.plot(d.js, d.Z[i], lw=1.4, color=pres.couleur)
        ax.scatter([0], [d.Z[i, d.demi]], s=16, color=pres.accent, zorder=3)
        quand = pd.to_datetime(str(d.dates[i])).strftime("%d/%m/%Y")
        ax.set_title(f"{c + 1}. {d.mots[i]} — {quand}\n{int(d.volume[i])} occ. au pic",
                     fontsize=8.5, color=ENCRE2)
        ax.set_xticks([-d.demi, 0, d.demi])
        cadre(ax)
        if c % 3 == 0:
            ax.set_ylabel("écart-types", fontsize=8.5)
        if c >= 9:
            ax.set_xlabel(pres.unite_axe, fontsize=8)
    print(f"  (archetypes) comp {comp} : "
          + ", ".join(f"{d.mots[i]} {int(d.dates[i])} ({d.proj[i, K]:+.1f}, "
                      f"{int(d.volume[i])} occ.)" for i in meilleurs))

    filtre_libelle = (f", parmi les fenêtres d'au moins {seuil_vol:.0f} occurrences au pic"
                      if seuil_vol > 0 else "")
    fig.suptitle(f"Composante {comp} : les 12 sauts réels les plus alignés (z-score)"
                 f"{filtre_libelle}\n{pres.titre}", fontsize=10.5, color=ENCRE2, y=0.965)
    return rendre(fig, chemin)


# --- diagnostics de qualite (pas specifiques a une configuration) -----------

def vue_qualite_corpus(taux, effectifs, noms_tranches, comp, pres, chemin):
    """Part de projections extremes sur une composante, par tranche d'une variable
    de qualite (ex. N_min, le plus petit volume de corpus dans la fenetre)."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    x = np.arange(len(taux))
    ax.bar(x, taux, width=0.62, color=pres.couleur)
    for xi, (t, n) in enumerate(zip(taux, effectifs)):
        ax.annotate(f"{t:.2f} %".replace(".", ","), (xi, t), xytext=(0, 4),
                    textcoords="offset points", ha="center", fontsize=8.5, color=ENCRE2)
        ax.annotate(f"{n:,} fen.".replace(",", " "), (xi, 0), xytext=(0, -30),
                    textcoords="offset points", ha="center", fontsize=7.5, color=ENCRE2)
    ax.set_xticks(x, noms_tranches, fontsize=8)
    ax.set_ylabel(f"part de projections extrêmes\n(|proj. comp. {comp}| > 2,5, en %)")
    ax.set_title(f"Projections extrêmes de la composante {comp} par tranche\n{pres.titre}",
                 fontsize=9.5, color=ENCRE2)
    cadre(ax)
    fig.tight_layout()
    return rendre(fig, chemin)


def vue_nms_evenement(dates, serie, avant, apres, mot, pres, chemin):
    """Serie quotidienne d'un mot, pics detectes avant/apres dedoublonnage NMS."""
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    ax.plot(dates, serie, lw=.5, color=GRIS)
    ax.scatter(avant["date"], avant["f_t"], s=9, color=pres.couleur, zorder=3,
               label=f"{len(avant)} pics détectés")
    ax.scatter(apres["date"], apres["f_t"], s=42, color=pres.accent, zorder=4,
               marker="o", facecolors="none", linewidths=1.6,
               label=f"{len(apres)} représentants gardés par le NMS")
    ax.set_ylabel("$f_t$ (pour 100 000 mots)")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    cadre(ax)
    ax.margins(x=0)
    ax.set_title(f"« {mot} » : effet du NMS (dédoublonnage des pics voisins)",
                 fontsize=9.5, color=ENCRE2)
    fig.tight_layout()
    return rendre(fig, chemin)
