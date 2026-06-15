"""Registre des médias et de leur méthode de scraping. Dès qu'on ajoute un média, il faut lui créé une entrée ici."""

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
    "le_journal_du_dimanche": {"moteur": "firefox", "meta": {"strategie": "balises", "corps": "section.content-rte div.rte p, article.live-element-content div.rte p", "titre": "h1.main-title", "auteur": "a.author", "date": "time"}},
}
