-- Reconstruit une base ngram filtrée À PARTIR d'une base existante, sans la modifier.
-- L'ancienne base est attachée comme 'old' au lancement :
--   sqlite3 lemonde_ngram_filtre.db -cmd "ATTACH 'lemonde_ngram.db' AS old" < scripts/filtre_ngram.sql
--
-- - Garde les ngrams vus > 10 fois sur tout le corpus (filtre agressif, base légère).
-- - Conserve les totaux journaliers AVANT filtrage (total_*) = dénominateur N_t des
--   fréquences relatives (occurrences du mot / total du jour).
-- - Colonnes typées INTEGER -> la jointure token.id=w1 utilise la clé (rapide).
-- - Base neuve = compacte d'emblée : pas de VACUUM, et l'original n'est jamais touché
--   (filet naturel en cas d'interruption ; relançable tel quel).

PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;

DROP TABLE IF EXISTS total_unigram;
DROP TABLE IF EXISTS total_bigram;
DROP TABLE IF EXISTS total_trigram;
DROP TABLE IF EXISTS unigram;
DROP TABLE IF EXISTS bigram;
DROP TABLE IF EXISTS trigram;
DROP TABLE IF EXISTS token;

-- Totaux journaliers (sur l'ancienne base, complète)
CREATE TABLE total_unigram (annee INTEGER, mois INTEGER, jour INTEGER, total INTEGER,
    PRIMARY KEY (annee, mois, jour)) WITHOUT ROWID;
INSERT INTO total_unigram SELECT annee, mois, jour, SUM(n) FROM old.unigram GROUP BY annee, mois, jour;

CREATE TABLE total_bigram (annee INTEGER, mois INTEGER, jour INTEGER, total INTEGER,
    PRIMARY KEY (annee, mois, jour)) WITHOUT ROWID;
INSERT INTO total_bigram SELECT annee, mois, jour, SUM(n) FROM old.bigram GROUP BY annee, mois, jour;

CREATE TABLE total_trigram (annee INTEGER, mois INTEGER, jour INTEGER, total INTEGER,
    PRIMARY KEY (annee, mois, jour)) WITHOUT ROWID;
INSERT INTO total_trigram SELECT annee, mois, jour, SUM(n) FROM old.trigram GROUP BY annee, mois, jour;

-- Tables filtrées (total global > 10), typées INTEGER
CREATE TABLE unigram (w1 INTEGER, annee INTEGER, mois INTEGER, jour INTEGER, n INTEGER,
    PRIMARY KEY (w1, annee, mois, jour)) WITHOUT ROWID;
INSERT INTO unigram
SELECT w1, annee, mois, jour, n FROM (
    SELECT *, SUM(n) OVER (PARTITION BY w1) AS tot FROM old.unigram
) WHERE tot > 10;

CREATE TABLE bigram (w1 INTEGER, w2 INTEGER, annee INTEGER, mois INTEGER, jour INTEGER, n INTEGER,
    PRIMARY KEY (w1, w2, annee, mois, jour)) WITHOUT ROWID;
INSERT INTO bigram
SELECT w1, w2, annee, mois, jour, n FROM (
    SELECT *, SUM(n) OVER (PARTITION BY w1, w2) AS tot FROM old.bigram
) WHERE tot > 10;

CREATE TABLE trigram (w1 INTEGER, w2 INTEGER, w3 INTEGER, annee INTEGER, mois INTEGER, jour INTEGER, n INTEGER,
    PRIMARY KEY (w1, w2, w3, annee, mois, jour)) WITHOUT ROWID;
INSERT INTO trigram
SELECT w1, w2, w3, annee, mois, jour, n FROM (
    SELECT *, SUM(n) OVER (PARTITION BY w1, w2, w3) AS tot FROM old.trigram
) WHERE tot > 10;

-- token : seulement les mots encore référencés dans les tables filtrées
CREATE TABLE token (id INTEGER PRIMARY KEY, word TEXT UNIQUE);
INSERT INTO token
SELECT id, word FROM old.token WHERE id IN (
    SELECT w1 FROM unigram
    UNION SELECT w1 FROM bigram  UNION SELECT w2 FROM bigram
    UNION SELECT w1 FROM trigram UNION SELECT w2 FROM trigram UNION SELECT w3 FROM trigram
);
