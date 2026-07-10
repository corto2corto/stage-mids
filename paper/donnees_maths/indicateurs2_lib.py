"""Bibliotheque de calcul pour indicateurs2.qmd (V2 - X_t et f_t).

Reprend la logique de indicateurs.py (V1) et l'etend au volet frequence f_t
(occurrences pour 100 000 mots). Purement descriptif : aucune loi ajustee.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from great_tables import GT, style, loc

# chemin absolu du dossier (independant du repertoire d'execution : Quarto
# lance les chunks depuis le dossier du .qmd, qui est ce meme dossier)
ICI = os.path.dirname(os.path.abspath(__file__))
BUILD = f"{ICI}/build_indic2"
os.makedirs(BUILD, exist_ok=True)

# nom de fichier -> libelle affiche (avec accents)
MOTS = {
    "president":    "président",
    "gouvernement": "gouvernement",
    "guerre":       "guerre",
    "climat":       "climat",
    "economie":     "économie",
    "inflation":    "inflation",
}

PERIODES = [("2020–2024", 20200101, 20241231)] + [
    (str(a), a * 10000 + 101, a * 10000 + 1231) for a in range(2020, 2025)
]

BLEU, GRIS = "#1f4e79", "#c9ced6"

METRIQUES = ["moy", "std", "disp", "skew", "kurt"]
LABELS_METRIQUES = {
    "moy": "Moyenne", "std": "Écart-type", "disp": "Var/Moy",
    "skew": "Skewness", "kurt": "Kurtosis",
}


def charger(nom):
    d = pd.read_csv(f"{ICI}/{nom}_lemonde.csv")
    d["dt"] = pd.to_datetime(d["date"], format="%Y%m%d")
    d["f_t"] = 1e5 * d["X_t"] / d["N_t"]        # occurrences pour 100 000 mots
    return d


def moments(x):
    """Moyenne, ecart-type, dispersion (Var/Moy), skewness, kurtosis (exces) d'une serie."""
    moy, var = x.mean(), x.var(ddof=1)
    return {
        "moy": moy,
        "std": x.std(ddof=1),
        "disp": var / moy if moy else np.nan,
        "skew": x.skew(),
        "kurt": x.kurt(),
    }


def ligne_periode(sub):
    """Une ligne de tableau : jours + moments de X_t (suffixe _x) et de f_t (suffixe _f)."""
    out = {"jours": len(sub)}
    out.update({f"{k}_x": v for k, v in moments(sub["X_t"]).items()})
    out.update({f"{k}_f": v for k, v in moments(sub["f_t"]).items()})
    return out


def table_periodes(d):
    """Une ligne par periode (globale 2020-2024 puis chaque annee)."""
    rows = []
    for lab, a, b in PERIODES:
        sub = d[(d["date"] >= a) & (d["date"] <= b)]
        rows.append({"periode": lab, **ligne_periode(sub)})
    return pd.DataFrame(rows)


def table_synthese(donnees, ordre):
    """Une ligne par mot, periode globale 2020-2024, triee par frequence f_t decroissante."""
    rows = []
    for nom in ordre:
        d = donnees[nom]
        rows.append({"mot": MOTS[nom], **ligne_periode(d)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# mise en forme great_tables
# ---------------------------------------------------------------------------

COLS_X = [f"{m}_x" for m in METRIQUES]
COLS_F = [f"{m}_f" for m in METRIQUES]
LABELS_COLS = {f"{m}_x": LABELS_METRIQUES[m] for m in METRIQUES}
LABELS_COLS.update({f"{m}_f": LABELS_METRIQUES[m] for m in METRIQUES})


def _base_gt(df, rowname_col, label_col_titre):
    gt = (
        GT(df, rowname_col=rowname_col)
        .tab_spanner(label="Occurrences Xₜ", columns=COLS_X)
        .tab_spanner(label="Fréquence fₜ (pour 100 000 mots)", columns=COLS_F)
        .cols_label(jours="Jours", **LABELS_COLS)
        .fmt_number(columns=["moy_x", "std_x", "skew_x", "kurt_x"], decimals=2, locale="fr")
        .fmt_number(columns=["moy_f", "std_f", "skew_f", "kurt_f"], decimals=2, locale="fr")
        .fmt_number(columns=["disp_x", "disp_f"], decimals=1, locale="fr")
        .fmt_integer(columns=["jours"], locale="fr")
        .cols_align(align="center", columns=["jours"])
        .cols_align(align="right", columns=COLS_X + COLS_F)
        .tab_stubhead(label=label_col_titre)
        .opt_table_font(font="Helvetica")
        .opt_horizontal_padding(scale=1.4)
        .tab_options(
            table_border_top_style="hidden",
            table_border_bottom_style="hidden",
            column_labels_border_top_color=BLEU,
            column_labels_border_top_width="2px",
            column_labels_border_bottom_color=BLEU,
            column_labels_border_bottom_width="1.5px",
            table_body_border_bottom_color=BLEU,
            table_body_border_bottom_width="1.5px",
            row_striping_include_table_body=True,
            row_striping_background_color="#f4f6f9",
            column_labels_background_color="white",
            table_font_size="15px",
            data_row_padding="7px",
            heading_background_color="white",
        )
        .opt_row_striping()
    )
    return gt


def gt_periodes(d, libelle):
    df = table_periodes(d)
    gt = _base_gt(df, "periode", "Période")
    gt = (
        gt.tab_style(style=style.text(weight="bold"), locations=loc.body(rows=[0]))
        .tab_style(style=style.text(weight="bold"), locations=loc.stub(rows=[0]))
        .tab_style(
            style=style.borders(sides="bottom", color=BLEU, weight="1.5px"),
            locations=loc.body(rows=[0]),
        )
    )
    return gt


def gt_synthese(donnees, ordre):
    df = table_synthese(donnees, ordre)
    return _base_gt(df, "mot", "Mot")


def figure_serie(d, chemin):
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.plot(d["dt"], d["f_t"], lw=.5, color=GRIS, label="quotidien")
    mm = d["f_t"].rolling(7, center=True, min_periods=1).mean()
    ax.plot(d["dt"], mm, lw=1.4, color=BLEU, label="moyenne mobile 7 jours")
    ax.set_ylabel("pour 100 000 mots", fontsize=11)
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(labelsize=10)
    ax.grid(True, axis="y", lw=.4, alpha=.4)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=10, frameon=False, loc="upper left", ncol=2)
    ax.margins(x=0)
    fig.tight_layout()
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
# sauvegarde -> chemins relatifs (utilises tels quels dans le .qmd)
# ---------------------------------------------------------------------------

def sauver_figure(nom, d):
    chemin = f"{BUILD}/fig_{nom}.png"
    figure_serie(d, chemin)
    return f"build_indic2/fig_{nom}.png"


def sauver_tableau(gt, nom):
    chemin = f"{BUILD}/tab_{nom}.png"
    gt.gtsave(chemin, zoom=3.0, vwidth=1700, vheight=500)
    return f"build_indic2/tab_{nom}.png"
