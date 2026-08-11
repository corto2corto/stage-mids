# Briques communes des figures de la campagne PCA : style, chaine de calcul et
# vues partagees par plusieurs planches. Les points d'entree sont dans
# figures.py ; ici rien ne s'execute a l'import hors le style matplotlib.
#
# La chaine (pics -> NMS -> fenetres -> z-score -> PCA) etait recopiee dans les
# huit anciens scripts figures_*.py ; elle vit maintenant dans charger().
import os
from types import SimpleNamespace

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

from rupture.nms import nms
from rupture.pca import nettoyer, normaliser, pca

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
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ICI = os.path.dirname(SCRIPTS)
DATA = os.path.join(ICI, "data")
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(DATA, "data_local"))
SPECTRES = os.path.join(DATA, "kernel_spectres")
CACHE = os.path.join(DATA, "cache_pca")
FIGURES = os.path.join(ICI, "rapport_qmd", "figures")

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
    os.makedirs(FIGURES, exist_ok=True)
    return os.path.join(FIGURES, nom)


def depuis_cache(prefixe):
    """Le resultat deja calcule d'une configuration, ou None s'il n'est pas la.

    Le cache est construit sur le serveur (scripts/construire_cache.py) : c'est
    ce qui permet de tracer en local sans les vocab_series_*.npz.
    """
    fichier = os.path.join(CACHE, f"{prefixe}.npz")
    if not os.path.exists(fichier):
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
    g = np.load(f"{DONNEES}/vocab_series_{media}.npz")
    X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
    position = {int(dt): i for i, dt in enumerate(grille_dates)}
    colonne = {m: j for j, m in enumerate(g["mots"])}

    p = pd.read_csv(f"{DONNEES}/pics_{media}{pics}.csv")
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


def presentation(media_nom, demi, seuil, pas_jours, couleur, accent, libelles=None):
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
        unite_axe=unite_axe, couleur=couleur, accent=accent,
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
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)


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
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)


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
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)


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
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)


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
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)


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
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)
