"""Registre des médias et de leur méthode de scraping. Dès qu'on ajoute un média, il faut lui créé une entrée ici.

Champs par média :
- moteur  : "firefox" (Selenium + bypass paywall), "log" (Firefox connecté à un
            compte abonné, cf connexion.py) ou "basic" (simple requête HTTP,
            sans navigateur, cf basic.py).
- attente : secondes laissées à la page pour charger (moteurs Firefox
            uniquement). ATTENTE_DEFAUT si absent.
- meta    : stratégie d'extraction des métadonnées et du corps (cf extraction.py).
"""

ATTENTE_DEFAUT = 6

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
    "le_journal_du_dimanche": {"moteur": "basic", "meta": {"strategie": "balises", "corps": "section.content-rte div.rte p, article.live-element-content div.rte p", "titre": "h1.main-title", "auteur": "a.author", "date": "time"}},
}
