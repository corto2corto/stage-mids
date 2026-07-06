"""Tests des moteurs de scraping v2 : dispatch, basic, log, pipeline, extraction.

Sans réseau ni Firefox : les moteurs sont remplacés par des doublures (mock).
Lancer :  python -m unittest tests.test_scraping_v2 -v
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from scraping import basic, connexion, extraction, moteurs, pipeline
from scraping.medias import ATTENTE_DEFAUT, MEDIAS
from scraping.paywall import est_bloque

FAUX_MEDIAS = {
    "m_firefox": {"moteur": "firefox", "meta": {}},
    "m_log":     {"moteur": "log", "meta": {}},
    "m_basic":   {"moteur": "basic", "meta": {}},
    "m_lent":    {"moteur": "firefox", "attente": 12, "meta": {}},
}


class TestRegistreMedias(unittest.TestCase):
    def test_chaque_media_a_un_moteur_connu(self):
        for media, regles in MEDIAS.items():
            self.assertIn(regles["moteur"], ("firefox", "log", "basic"), media)

    def test_chaque_media_a_une_strategie_extraction(self):
        for media, regles in MEDIAS.items():
            self.assertIn(regles["meta"]["strategie"], ("json_ld", "balises"), media)
            self.assertTrue(regles["meta"]["corps"], media)
            if regles["meta"]["strategie"] == "balises":
                for champ in ("titre", "auteur", "date"):
                    self.assertIn(champ, regles["meta"], media)

    def test_moteur_log_exige_une_procedure_de_connexion(self):
        for media, regles in MEDIAS.items():
            if regles["moteur"] == "log":
                self.assertIn(media, connexion.CONNEXIONS, media)


class TestDispatchMoteurs(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(MEDIAS, FAUX_MEDIAS)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_ouvrir_firefox(self):
        with patch("scraping.navigateur.ouvrir_firefox", return_value="DRIVER") as m:
            self.assertEqual(moteurs.ouvrir_session("m_firefox"), "DRIVER")
            m.assert_called_once()

    def test_ouvrir_basic(self):
        with patch("scraping.basic.ouvrir_session", return_value="SESSION") as m:
            self.assertEqual(moteurs.ouvrir_session("m_basic"), "SESSION")
            m.assert_called_once()

    def test_ouvrir_log(self):
        with patch("scraping.moteurs.ouvrir_firefox_connecte", return_value="CONNECTE") as m:
            self.assertEqual(moteurs.ouvrir_session("m_log"), "CONNECTE")
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
            self.assertEqual(moteurs.scraper("m_basic", "session", "http://u"), "<html>")
            m.assert_called_once_with("session", "http://u")
            sleep.assert_called_once()   # délai de politesse appliqué

    def test_fermer_basic_close_et_firefox_quit(self):
        session, driver = MagicMock(), MagicMock()
        moteurs.fermer_session("m_basic", session)
        session.close.assert_called_once()
        session.quit.assert_not_called()
        moteurs.fermer_session("m_firefox", driver)
        driver.quit.assert_called_once()
        driver.close.assert_not_called()


class TestMoteurBasic(unittest.TestCase):
    def test_scraper_renvoie_le_html(self):
        session = MagicMock()
        session.get.return_value = MagicMock(text="<html>ok</html>")
        self.assertEqual(basic.scraper(session, "http://u"), "<html>ok</html>")
        session.get.return_value.raise_for_status.assert_called_once()

    def test_scraper_propage_les_erreurs_http(self):
        session = MagicMock()
        session.get.return_value.raise_for_status.side_effect = Exception("403")
        with self.assertRaises(Exception):
            basic.scraper(session, "http://u")


class TestMoteurLog(unittest.TestCase):
    """ouvrir_firefox_connecte : les identifiants sont lus AVANT d'ouvrir Firefox
    (pas de navigateur orphelin si la config manque)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fichier = Path(self.tmp.name) / "identifiants.json"
        patcher = patch("scraping.connexion.IDENTIFIANTS", self.fichier)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_fichier_identifiants_absent(self):
        with patch("scraping.connexion.ouvrir_firefox") as firefox:
            with self.assertRaises(FileNotFoundError):
                connexion.ouvrir_firefox_connecte("le_monde")
            firefox.assert_not_called()

    def test_media_absent_du_fichier(self):
        self.fichier.write_text(json.dumps({"autre": {"email": "a", "mot_de_passe": "b"}}))
        with patch("scraping.connexion.ouvrir_firefox") as firefox:
            with self.assertRaises(KeyError):
                connexion.ouvrir_firefox_connecte("le_monde")
            firefox.assert_not_called()

    def test_media_sans_procedure_de_connexion(self):
        self.fichier.write_text(json.dumps({"inconnu": {"email": "a", "mot_de_passe": "b"}}))
        with patch("scraping.connexion.ouvrir_firefox") as firefox:
            with self.assertRaises(KeyError):
                connexion.ouvrir_firefox_connecte("inconnu")
            firefox.assert_not_called()

    def test_connexion_nominale(self):
        self.fichier.write_text(json.dumps({"le_monde": {"email": "e@x.fr", "mot_de_passe": "mdp"}}))
        driver = MagicMock()
        with patch("scraping.connexion.ouvrir_firefox", return_value=driver), \
             patch("scraping.connexion.time.sleep"):
            self.assertIs(connexion.ouvrir_firefox_connecte("le_monde"), driver)
        driver.get.assert_called_once_with(connexion.CONNEXIONS["le_monde"]["url"])
        saisies = [appel.args for appel in driver.find_element.return_value.send_keys.call_args_list]
        self.assertEqual(saisies, [("e@x.fr",), ("mdp",)])
        # Validation par clic JS (traverse un bandeau cookies) sur le champ trouvé.
        driver.execute_script.assert_called_once_with("arguments[0].click();", driver.find_element.return_value)
        driver.quit.assert_not_called()

    def test_echec_de_saisie_ferme_le_firefox(self):
        self.fichier.write_text(json.dumps({"le_monde": {"email": "e@x.fr", "mot_de_passe": "mdp"}}))
        driver = MagicMock()
        driver.find_element.side_effect = Exception("champ introuvable")
        with patch("scraping.connexion.ouvrir_firefox", return_value=driver), \
             patch("scraping.connexion.time.sleep"):
            with self.assertRaises(Exception):
                connexion.ouvrir_firefox_connecte("le_monde")
        driver.quit.assert_called_once()


class TestPipeline(unittest.TestCase):
    def test_session_en_echec_ignoree(self):
        batch = {"a": (1, "http://a"), "b": (2, "http://b")}
        def ouvrir(media):
            if media == "b":
                raise RuntimeError("boum")
            return f"session_{media}"
        with patch("scraping.pipeline.ouvrir_session", side_effect=ouvrir):
            self.assertEqual(pipeline.ouvrir_sessions(batch), {"a": "session_a"})

    def test_aucune_session_ne_demarre(self):
        batch = {"a": (1, "http://a")}
        with patch("scraping.pipeline.ouvrir_session", side_effect=RuntimeError):
            self.assertEqual(pipeline.ouvrir_sessions(batch), {})

    def test_scraper_batch_echec_isole(self):
        batch = {"a": (1, "http://a"), "b": (2, "http://b")}
        sessions = {"a": "s_a", "b": "s_b"}
        def scraper(media, session, url):
            if media == "b":
                raise RuntimeError("timeout")
            return "<html>"
        with patch("scraping.pipeline.scraper", side_effect=scraper):
            resultats = pipeline.scraper_batch(batch, sessions)
        self.assertEqual(resultats["a"], (1, "http://a", "<html>"))
        self.assertEqual(resultats["b"], (2, "http://b", None))


class TestExtraction(unittest.TestCase):
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
        self.assertEqual(article.get("headline"), "Titre")

    def test_extraire_nominal(self):
        infos = extraction.extraire("le_capital", self.HTML)
        self.assertEqual(infos["titre"], "Titre")
        self.assertEqual(infos["auteur"], "Alice")
        self.assertEqual(infos["free"], "non")
        self.assertEqual(infos["contenu"], "Le corps complet.")

    def test_page_sans_json_ld(self):
        infos = extraction.extraire("le_capital", "<html><body><p>rien</p></body></html>")
        self.assertEqual(infos["titre"], "")
        self.assertEqual(infos["contenu"], "")

    def test_date_balises_texte_sans_datetime(self):
        # francesoir : la date est un div texte, sans attribut datetime
        html = "<h1>T</h1><div class='field--name-field-date me-3'>Publié le 14 mars 2017</div>"
        meta = {"titre": "h1", "auteur": "a[rel=author]", "date": "div.field--name-field-date.me-3"}
        infos = extraction.meta_balises(BeautifulSoup(html, "html.parser"), meta)
        self.assertEqual(infos["date"], "Publié le 14 mars 2017")

    def test_date_balises_datetime_prioritaire(self):
        html = "<time datetime='2026-07-06'>6 juillet</time>"
        meta = {"titre": "h1", "auteur": "a", "date": "time"}
        infos = extraction.meta_balises(BeautifulSoup(html, "html.parser"), meta)
        self.assertEqual(infos["date"], "2026-07-06")


class TestPaywall(unittest.TestCase):
    def test_contenu_vide_est_bloque(self):
        self.assertTrue(est_bloque(""))
        self.assertTrue(est_bloque("   "))

    def test_signal_en_fin_est_bloque(self):
        self.assertTrue(est_bloque("Début. " * 100 + "La suite est réservée aux abonnés."))

    def test_signal_au_debut_seulement_ne_bloque_pas(self):
        self.assertFalse(est_bloque("réservée aux abonnés. " + "La suite du texte normal. " * 50))

    def test_texte_normal_pas_bloque(self):
        self.assertFalse(est_bloque("Un article tout à fait normal. " * 30))


if __name__ == "__main__":
    unittest.main()
