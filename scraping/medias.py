"""Registre des médias : source unique de vérité, une entrée par média.

Chaque étape du pipeline lit la clé qui la concerne :
- "moteur" : quel navigateur ouvrir (aujourd'hui "firefox") ;
- "meta"   : quoi extraire du HTML (métadonnées + corps) —
    - "strategie" : "json_ld" (schema.org) ou "balises" (lues dans le HTML, on
      fournit alors les sélecteurs titre/auteur/date) ;
    - "corps"     : sélecteur CSS du corps de l'article, ou "json_ld" si le
      corps n'est pas dans le HTML mais dans le champ articleBody du JSON-LD
      (challenges, le_telegramme).

Ajouter un média = déposer <media>_articles.csv (les URLs) + une entrée ici.
"""

MEDIAS = {
    "le_capital":            {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.articleBody"}},
    "le_figaro":             {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.fig-content-body"}},
    "le_monde":              {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": ".article__content"}},
    "telerama":              {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "article.article__page-content"}},
    "valeurs_actuelles":     {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.post__content"}},
    "les_echos":             {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.post-paywall"}},
    "paris_match":           {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "section.content-rte"}},
    "le_nouvel_observateur": {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "p.node__paragraphe"}},
    "nice_matin":            {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "article"}},
    "atlantico":             {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.rich-content__text"}},
    "la_depeche":            {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.article-full__body-content"}},
    "l_opinion":             {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.RichTextArticleBody"}},
    "sud_ouest":             {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.full-content"}},
    "challenges":            {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
    "le_telegramme":         {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
    "le_journal_du_dimanche": {
        "moteur": "firefox",
        "meta": {
            "strategie": "balises",
            "corps":  "section.content-rte div.rte p, article.live-element-content div.rte p",
            "titre":  "h1.main-title",
            "auteur": "a.author",
            "date":   "time",
        },
    },
}
