-- Filtre les bases ngram : supprime les uni/bi/trigrammes vus une seule fois
-- dans tout le corpus (total global n = 1), garde ceux avec total >= 2.
-- Recrée chaque table filtrée puis remplace l'originale (pas de DELETE en place).
-- Réutilisable sur les 3 bases :  sqlite3 lemonde_ngram.db < scripts/filtre_ngram.sql

PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;

-- unigram
CREATE TABLE unigram_new (w1, annee, mois, jour, n,
    PRIMARY KEY (w1, annee, mois, jour)) WITHOUT ROWID;
INSERT INTO unigram_new
SELECT w1, annee, mois, jour, n FROM (
    SELECT *, SUM(n) OVER (PARTITION BY w1) AS tot FROM unigram
) WHERE tot >= 2;
DROP TABLE unigram;
ALTER TABLE unigram_new RENAME TO unigram;

-- bigram
CREATE TABLE bigram_new (w1, w2, annee, mois, jour, n,
    PRIMARY KEY (w1, w2, annee, mois, jour)) WITHOUT ROWID;
INSERT INTO bigram_new
SELECT w1, w2, annee, mois, jour, n FROM (
    SELECT *, SUM(n) OVER (PARTITION BY w1, w2) AS tot FROM bigram
) WHERE tot >= 2;
DROP TABLE bigram;
ALTER TABLE bigram_new RENAME TO bigram;

-- trigram
CREATE TABLE trigram_new (w1, w2, w3, annee, mois, jour, n,
    PRIMARY KEY (w1, w2, w3, annee, mois, jour)) WITHOUT ROWID;
INSERT INTO trigram_new
SELECT w1, w2, w3, annee, mois, jour, n FROM (
    SELECT *, SUM(n) OVER (PARTITION BY w1, w2, w3) AS tot FROM trigram
) WHERE tot >= 2;
DROP TABLE trigram;
ALTER TABLE trigram_new RENAME TO trigram;

-- token : retire les mots devenus orphelins (plus référencés nulle part)
DELETE FROM token WHERE id NOT IN (
    SELECT w1 FROM unigram
    UNION SELECT w1 FROM bigram  UNION SELECT w2 FROM bigram
    UNION SELECT w1 FROM trigram UNION SELECT w2 FROM trigram UNION SELECT w3 FROM trigram
);

PRAGMA journal_mode = WAL;
VACUUM;
