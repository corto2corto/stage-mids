# Avancement — partie maths du mémoire

Carnet de bord du travail avec `/teacher`. Programme complet : `to_do.tex`.

## Séance en cours

- **Où on en est** : rien de commencé, on part du module 0.
- **Objectif du jour** : à définir au lancement de `/teacher`.

## Feuille de route

- [ ] 0. Fondations à rafraîchir — variable aléatoire, loi, moyenne/variance ; pourquoi normaliser par $N_t$ (garder $X_t$ entier plutôt que $f_t$).
- [ ] 1. Poisson scalé — ajuster $\mathrm{Poisson}(\lambda N_t)$ mot par mot ; notion de MLE.
- [ ] 2. Binomiale négative (NB2) — surdispersion, paramétrisation $m,r$, `exposure`, $\phi=1/r$ ; Poisson comme limite $r\to\infty$.
- [ ] 3. Diagnostics d'ajustement — moments observés vs loi (moyenne, écart-type, skewness, kurtosis), histogramme données vs densité, histogramme des $p$-valeurs.
- [ ] 4. Détection de pics — $p$-valeur $=1-F(X_t)$, surprise $=-\log_{10}(p_t)$, seuil, nettoyage en plusieurs tours.
- [ ] 5. Différentiels $X_t - X_{t-1}$ — sauts haut/bas (censure), effet rebond.
- [ ] 6. Seuil « principled » — déduire le seuil des données (où l'ajustement casse, Cook discret, test statistique).
- [ ] 7. Séries temporelles — autocorrélation de $f_t$, AR(1), $m_t=N_t e^{R_t}$, AR(2)/AR(3).
- [ ] 8. Difficile — loi commune multi-mots ; breakpoints (rachats) ; bruit en $\sqrt{n}$ / ESS / bootstrap.

**Fil rouge visé** : batterie d'indicateurs + graphes pour 5-6 mots (modules 1→4).

## Décisions actées

_(rien pour l'instant)_

## Notes / questions ouvertes

_(rien pour l'instant)_
