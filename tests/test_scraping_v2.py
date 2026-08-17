"""Tests des moteurs de scraping v2 : dispatch, basic, log, pipeline, extraction.

Sans réseau ni Firefox : les moteurs sont remplacés par des doublures (mock).
Lancer :  python -m pytest tests/ -v
"""
import json
import sqlite3
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from scraping import basic, connexion, extraction, moteurs, pipeline
from scraping.batch import prochaine_url
from scraping.medias import ATTENTE_DEFAUT, MEDIAS
from scraping.paywall import est_bloque

FAUX_MEDIAS = {
    "m_firefox": {"moteur": "firefox", "meta": {}},
    "m_log":     {"moteur": "log", "meta": {}},
    "m_basic":   {"moteur": "basic", "meta": {}},
    "m_lent":    {"moteur": "firefox", "attente": 12, "meta": {}},
    "m_hybride": {"moteur": "hybride", "meta": {}},
}


class TestRegistreMedias:
    def test_chaque_media_a_un_moteur_connu(self):
        for media, regles in MEDIAS.items():
            assert regles["moteur"] in ("firefox", "log", "basic", "hybride"), media

    def test_chaque_media_a_une_strategie_extraction(self):
        for media, regles in MEDIAS.items():
            assert regles["meta"]["strategie"] in ("json_ld", "balises"), media
            assert regles["meta"]["corps"], media
            if regles["meta"]["strategie"] == "balises":
                for champ in ("titre", "auteur", "date"):
                    assert champ in regles["meta"], media

    def test_moteur_log_exige_une_procedure_de_connexion(self):
        for media, regles in MEDIAS.items():
            if regles["moteur"] == "log":
                assert media in connexion.CONNEXIONS, media


class TestDispatchMoteurs:
    @pytest.fixture(autouse=True)
    def _faux_medias(self):
        with patch.dict(MEDIAS, FAUX_MEDIAS):
            yield

    def test_ouvrir_firefox(self):
        with patch("scraping.navigateur.ouvrir_firefox", return_value="DRIVER") as m:
            assert moteurs.ouvrir_session("m_firefox") == "DRIVER"
            m.assert_called_once()

    def test_ouvrir_basic(self):
        with patch("scraping.basic.ouvrir_session", return_value="SESSION") as m:
            assert moteurs.ouvrir_session("m_basic") == "SESSION"
            m.assert_called_once()

    def test_ouvrir_log(self):
        with patch("scraping.moteurs.ouvrir_firefox_connecte", return_value="CONNECTE") as m:
            assert moteurs.ouvrir_session("m_log") == "CONNECTE"
            m.assert_called_once_with("m_log")

    def test_scraper_firefox_efface_les_cookies_avec_attente_defaut(self):
        with patch("scraping.navigateur.scraper", return_value="<html>") as m:
            moteurs.scraper("m_firefox", "driver", "http://u")
            m.assert_called_once_with("driver", "http://u", ATTENTE_DEFAUT, garder_cookies=False)

    def test_scraper_log_garde_les_cookies(self):
        with patch("scraping.navigateur.scraper", return_value="<html>") as m:
            moteurs.scraper("m_log", "driver", "http://u")
            m.assert_called_once_with("driver", "http://u", ATTENTE_DEFAUT, garder_cookies=True)

    def test_scraper_respecte_attente_du_media(self):
        with patch("scraping.navigateur.scraper", return_value="<html>") as m:
            moteurs.scraper("m_lent", "driver", "http://u")
            m.assert_called_once_with("driver", "http://u", 12, garder_cookies=False)

    def test_scraper_basic(self):
        with patch("scraping.basic.scraper", return_value="<html>") as m, \
             patch("scraping.moteurs.time.sleep") as sleep:
            assert moteurs.scraper("m_basic", "session", "http://u") == "<html>"
            m.assert_called_once_with("session", "http://u")
            sleep.assert_called_once()   # délai de politesse appliqué

    def test_ouvrir_hybride_deux_sessions(self):
        with patch("scraping.basic.ouvrir_session", return_value="SESSION") as b, \
             patch("scraping.navigateur.ouvrir_firefox", return_value="DRIVER") as f:
            assert moteurs.ouvrir_session("m_hybride") == {"basic": "SESSION", "firefox": "DRIVER"}
            b.assert_called_once()
            f.assert_called_once()

    def test_scraper_hybride_gratuit_reste_en_basic(self):
        session = {"basic": "s_http", "firefox": "driver"}
        with patch("scraping.basic.scraper", return_value="<html>") as b, \
             patch("scraping.moteurs.extraction.extraire", return_value={"contenu": "texte complet"}), \
             patch("scraping.moteurs.est_bloque", return_value=False), \
             patch("scraping.navigateur.scraper") as f, \
             patch("scraping.moteurs.time.sleep"):
            assert moteurs.scraper("m_hybride", session, "http://u") == "<html>"
            b.assert_called_once_with("s_http", "http://u")
            f.assert_not_called()   # pas de Firefox pour un article gratuit

    def test_scraper_hybride_payant_bascule_sur_firefox(self):
        session = {"basic": "s_http", "firefox": "driver"}
        with patch("scraping.basic.scraper", return_value="<html tronqué>"), \
             patch("scraping.moteurs.extraction.extraire", return_value={"contenu": ""}), \
             patch("scraping.moteurs.est_bloque", return_value=True), \
             patch("scraping.navigateur.scraper", return_value="<html complet>") as f, \
             patch("scraping.moteurs.time.sleep") as sleep:
            assert moteurs.scraper("m_hybride", session, "http://u") == "<html complet>"
            f.assert_called_once_with("driver", "http://u", ATTENTE_DEFAUT)
            sleep.assert_called_once()   # espacement basic -> firefox

    def test_scraper_hybride_gratuit_applique_la_politesse(self):
        session = {"basic": "s_http", "firefox": "driver"}
        with patch("scraping.basic.scraper", return_value="<html>"), \
             patch("scraping.moteurs.extraction.extraire", return_value={"contenu": "texte"}), \
             patch("scraping.moteurs.est_bloque", return_value=False), \
             patch("scraping.moteurs.time.sleep") as sleep:
            moteurs.scraper("m_hybride", session, "http://u")
            sleep.assert_called_once_with(2)   # politesse par défaut du chemin rapide

    def test_fermer_hybride_ferme_les_deux(self):
        session = {"basic": MagicMock(), "firefox": MagicMock()}
        moteurs.fermer_session("m_hybride", session)
        session["basic"].close.assert_called_once()
        session["firefox"].quit.assert_called_once()

    def test_fermer_basic_close_et_firefox_quit(self):
        session, driver = MagicMock(), MagicMock()
        moteurs.fermer_session("m_basic", session)
        session.close.assert_called_once()
        session.quit.assert_not_called()
        moteurs.fermer_session("m_firefox", driver)
        driver.quit.assert_called_once()
        driver.close.assert_not_called()


class TestMoteurBasic:
    def test_scraper_renvoie_le_html(self):
        session = MagicMock()
        session.get.return_value = MagicMock(text="<html>ok</html>")
        assert basic.scraper(session, "http://u") == "<html>ok</html>"
        session.get.return_value.raise_for_status.assert_called_once()

    def test_scraper_propage_les_erreurs_http(self):
        session = MagicMock()
        session.get.return_value.raise_for_status.side_effect = Exception("403")
        with pytest.raises(Exception):
            basic.scraper(session, "http://u")


class TestMoteurLog:
    """ouvrir_firefox_connecte : les identifiants sont lus AVANT d'ouvrir Firefox
    (pas de navigateur orphelin si la config manque)."""

    @pytest.fixture(autouse=True)
    def _identifiants(self, tmp_path):
        self.fichier = tmp_path / "identifiants.json"
        with patch("scraping.connexion.IDENTIFIANTS", self.fichier):
            yield

    def test_fichier_identifiants_absent(self):
        with patch("scraping.connexion.ouvrir_firefox") as firefox:
            with pytest.raises(FileNotFoundError):
                connexion.ouvrir_firefox_connecte("le_monde")
            firefox.assert_not_called()

    def test_media_absent_du_fichier(self):
        self.fichier.write_text(json.dumps({"autre": {"email": "a", "mot_de_passe": "b"}}))
        with patch("scraping.connexion.ouvrir_firefox") as firefox:
            with pytest.raises(KeyError):
                connexion.ouvrir_firefox_connecte("le_monde")
            firefox.assert_not_called()

    def test_media_sans_procedure_de_connexion(self):
        self.fichier.write_text(json.dumps({"inconnu": {"email": "a", "mot_de_passe": "b"}}))
        with patch("scraping.connexion.ouvrir_firefox") as firefox:
            with pytest.raises(KeyError):
                connexion.ouvrir_firefox_connecte("inconnu")
            firefox.assert_not_called()

    def test_connexion_nominale(self):
        self.fichier.write_text(json.dumps({"le_monde": {"email": "e@x.fr", "mot_de_passe": "mdp"}}))
        driver = MagicMock()
        with patch("scraping.connexion.ouvrir_firefox", return_value=driver), \
             patch("scraping.connexion.time.sleep"):
            assert connexion.ouvrir_firefox_connecte("le_monde") is driver
        driver.get.assert_called_once_with(connexion.CONNEXIONS["le_monde"]["url"])
        saisies = [appel.args for appel in driver.find_element.return_value.send_keys.call_args_list]
        assert saisies == [("e@x.fr",), ("mdp",)]
        # Validation par clic JS (traverse un bandeau cookies) sur le champ trouvé.
        driver.execute_script.assert_called_once_with("arguments[0].click();", driver.find_element.return_value)
        driver.quit.assert_not_called()

    def test_echec_de_saisie_ferme_le_firefox(self):
        self.fichier.write_text(json.dumps({"le_monde": {"email": "e@x.fr", "mot_de_passe": "mdp"}}))
        driver = MagicMock()
        driver.find_element.side_effect = Exception("champ introuvable")
        with patch("scraping.connexion.ouvrir_firefox", return_value=driver), \
             patch("scraping.connexion.time.sleep"):
            with pytest.raises(Exception):
                connexion.ouvrir_firefox_connecte("le_monde")
        driver.quit.assert_called_once()


class TestPipeline:
    @pytest.fixture
    def conn(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE urls (id INTEGER PRIMARY KEY, media TEXT, "
                     "url TEXT, etat INTEGER DEFAULT 0)")
        conn.execute("INSERT INTO urls (id, media, url) VALUES (1, 'a', 'http://a')")
        return conn

    def test_session_en_echec_ignoree(self):
        batch = {"a": (1, "http://a"), "b": (2, "http://b")}
        def ouvrir(media):
            if media == "b":
                raise RuntimeError("boum")
            return f"session_{media}"
        with patch("scraping.pipeline.ouvrir_session", side_effect=ouvrir):
            assert pipeline.ouvrir_sessions(batch) == {"a": "session_a"}

    def test_aucune_session_ne_demarre(self):
        batch = {"a": (1, "http://a")}
        with patch("scraping.pipeline.ouvrir_session", side_effect=RuntimeError):
            assert pipeline.ouvrir_sessions(batch) == {}

    def test_traiter_url_echec_scrape(self, conn):
        with patch("scraping.pipeline.scraper", side_effect=RuntimeError("timeout")):
            etat = pipeline.traiter_url(conn, "a", "s_a", 1, "http://a")
        assert etat == 1
        assert conn.execute("SELECT etat FROM urls WHERE id=1").fetchone()[0] == 1

    def test_prochaine_url_nouvelles_puis_echecs(self, conn):
        conn.execute("INSERT INTO urls (id, media, url, etat) VALUES (2, 'a', 'http://echec', 1)")
        # tant qu'il reste du neuf (etat=0), il passe d'abord
        assert prochaine_url(conn, "a") == (1, "http://a", 0)
        conn.execute("UPDATE urls SET etat=2 WHERE id=1")
        # plus de neuf : les échecs ont une seconde chance
        assert prochaine_url(conn, "a") == (2, "http://echec", 1)
        conn.execute("UPDATE urls SET etat=4 WHERE id=2")
        # échec confirmé : plus jamais repris
        assert prochaine_url(conn, "a") is None

    def test_traiter_url_echec_confirme_apres_retentative(self, conn):
        with patch("scraping.pipeline.scraper", side_effect=RuntimeError("boum")):
            etat = pipeline.traiter_url(conn, "a", "s_a", 1, "http://a", etat_prec=1)
        assert etat == 4
        assert conn.execute("SELECT etat FROM urls WHERE id=1").fetchone()[0] == 4

    def test_traiter_url_succes(self, conn):
        with patch("scraping.pipeline.scraper", return_value="<html>"), \
             patch("scraping.pipeline.ecriture_csv", return_value=2):
            etat = pipeline.traiter_url(conn, "a", "s_a", 1, "http://a")
        assert etat == 2
        assert conn.execute("SELECT etat FROM urls WHERE id=1").fetchone()[0] == 2


class TestExtraction:
    HTML = """
    <html><head>
    <script type="application/ld+json">{invalide</script>
    <script type="application/ld+json">
    {"@type": "NewsArticle", "headline": "Titre", "datePublished": "2026-07-06",
     "author": {"name": "Alice"}, "isAccessibleForFree": "False",
     "articleBody": "Le corps complet."}
    </script>
    </head><body>
    <div class="articleBody"><p>Le corps</p><p>complet.</p></div>
    </body></html>"""

    def test_bloc_json_ld_invalide_ignore(self):
        article = extraction.noeud_json_ld(BeautifulSoup(self.HTML, "html.parser"))
        assert article.get("headline") == "Titre"

    def test_extraire_nominal(self):
        infos = extraction.extraire("le_capital", self.HTML)
        assert infos["titre"] == "Titre"
        assert infos["auteur"] == "Alice"
        assert infos["free"] == "non"
        assert infos["contenu"] == "Le corps complet."

    def test_page_sans_json_ld(self):
        infos = extraction.extraire("le_capital", "<html><body><p>rien</p></body></html>")
        assert infos["titre"] == ""
        assert infos["contenu"] == ""

    def test_date_balises_texte_sans_datetime(self):
        # francesoir : la date est un div texte, sans attribut datetime
        html = "<h1>T</h1><div class='field--name-field-date me-3'>Publié le 14 mars 2017</div>"
        meta = {"titre": "h1", "auteur": "a[rel=author]", "date": "div.field--name-field-date.me-3"}
        infos = extraction.meta_balises(BeautifulSoup(html, "html.parser"), meta)
        assert infos["date"] == "Publié le 14 mars 2017"

    def test_date_balises_datetime_prioritaire(self):
        html = "<time datetime='2026-07-06'>6 juillet</time>"
        meta = {"titre": "h1", "auteur": "a", "date": "time"}
        infos = extraction.meta_balises(BeautifulSoup(html, "html.parser"), meta)
        assert infos["date"] == "2026-07-06"


class TestPaywall:
    def test_contenu_vide_est_bloque(self):
        assert est_bloque("")
        assert est_bloque("   ")

    def test_signal_en_fin_est_bloque(self):
        assert est_bloque("Début. " * 100 + "La suite est réservée aux abonnés.")

    def test_signal_au_debut_seulement_ne_bloque_pas(self):
        assert not est_bloque("réservée aux abonnés. " + "La suite du texte normal. " * 50)

    def test_texte_normal_pas_bloque(self):
        assert not est_bloque("Un article tout à fait normal. " * 30)
