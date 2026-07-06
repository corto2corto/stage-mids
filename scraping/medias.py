"""Registre des médias et de leur méthode de scraping. Dès qu'on ajoute un média, il faut lui créé une entrée ici.

Champs par média :
- moteur  : "firefox" (Selenium + bypass paywall), "log" (Firefox connecté à un
            compte abonné, cf connexion.py) ou "basic" (simple requête HTTP,
            sans navigateur, cf basic.py).
- attente : secondes de pause après chaque URL. Pour firefox/log c'est le temps
            laissé à la page pour charger (ATTENTE_DEFAUT si absent) ; pour basic
            c'est un simple délai de politesse envers le site (ATTENTE_BASIC).
- timeout : secondes max de chargement d'une page (moteur firefox). À poser sur
            les médias dont certaines pages ne répondent jamais (anti-bot) :
            au-delà, on abandonne l'URL (etat=1) et on passe à la suivante.
- meta    : stratégie d'extraction des métadonnées et du corps (cf extraction.py).
"""

ATTENTE_DEFAUT = 4   # firefox/log : rendu JS après DOM (A/B 4s vs 6s : 0 bloqué BPC à 4s)
ATTENTE_BASIC = 1    # basic : la requête est instantanée, on temporise par politesse

MEDIAS = {
    # Sonde anciens médias 06/07/2026 (sonde_anciens.log) : le_capital, challenges,
    # l_opinion et la_depeche sortent complets en basic -> plus besoin de Firefox.
    "le_capital":            {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
    "le_figaro":             {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.fig-content-body"}},
    # le_monde : bypass en échec permanent -> compte abonné (moteur log, connexion.py).
    "le_monde":              {"moteur": "log", "attente": 3, "meta": {"strategie": "json_ld", "corps": ".article__content"}},
    "telerama":              {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "article.article__page-content"}},
    "valeurs_actuelles":     {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.post__content"}},
    "les_echos":             {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.post-paywall"}},
    "paris_match":           {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "section.content-rte"}},
    "le_nouvel_observateur": {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "p.node__paragraphe"}},
    "nice_matin":            {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "article"}},
    "atlantico":             {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.rich-content__text"}},
    "la_depeche":            {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.article-full__body-content"}},
    "l_opinion":             {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.RichTextArticleBody"}},
    "sud_ouest":             {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.full-content"}},
    "challenges":            {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
    # valeurs_actuelles et le_telegramme : candidats basic, corps json-ld à confirmer sur du payant.
    "le_telegramme":         {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
    "le_journal_du_dimanche": {"moteur": "basic", "meta": {"strategie": "balises", "corps": "section.content-rte div.rte p, article.live-element-content div.rte p", "titre": "h1.main-title", "auteur": "a.author", "date": "time"}},
    # mediapart : compte abonné (moteur log). Corps validé sur article connecté (06/07).
    "mediapart":             {"moteur": "log", "attente": 3, "meta": {"strategie": "json_ld", "corps": "div.news__body__center__article"}},

    # Nouveaux médias (sonde + analyse HTML du 06/07/2026) — moteur basic confirmé.
    "gala":         {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.fig-content-body"}},
    "voici":        {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
    "bfmtv":        {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.content_body_wrapper"}},
    "ouest_france": {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.su-article"}},
    "leparisien":   {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "section.content"}},
    "la_croix":     {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.article-content"}},
    "laprovence":   {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
    "francesoir":   {"moteur": "basic", "meta": {"strategie": "balises", "corps": "div.field--name-body", "titre": "h1", "auteur": "a[rel=author]", "date": "div.field--name-field-date.me-3"}},

    # Batch du 06/07/2026, 2e partie (corps validés sur les html_v2 du test bypass).
    # Paywalls non contournables : seuls les articles gratuits sortent complets,
    # les payants sont tronqués ou vides -> à filtrer via la colonne free.
    "marianne":        {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
    "midilibre":       {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.article-full__body-content"}},
    "paris_normandie": {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
    "latribune":       {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
    "liberation":      {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div[class*=TextElement__Container]"}},
    # Écartés : lexpress (9/10 payant, aucun corps json-ld, pas de sélecteur validable),
    # lepoint (URLs Wayback mortes en masse, corps rendu en JS invisible en basic).
}
