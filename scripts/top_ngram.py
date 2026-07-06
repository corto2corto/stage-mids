# Top 500 des uni/bi/trigrammes par jour, mois et année, dans <corpus>_top.db.
# La base ngram source reste en lecture seule ; la base top est petite (~1 Go) et se
# reconstruit entièrement à chaque lancement. Le drapeau stop=1 marque les ngrams
# dont tous les mots sont des mots outils (ou des nombres), pour filtrage côté API.
# Usage : python -m scripts.top_ngram lesechos [dossier]

import os
import sqlite3
import sys
import time

# Les tris des window functions génèrent des dizaines de Go de temporaires : les
# forcer sur /data (5 To) et surtout PAS sur / (root, 20 Go, déborde -> "disk is full").
# On couvre les deux chemins que SQLite peut emprunter : SQLITE_TMPDIR et TMPDIR.
TMP = "/data/elias/stage-mids/data/sqlite_tmp"
if os.path.isdir("/data/elias/stage-mids/data"):
    os.makedirs(TMP, exist_ok=True)
    os.environ["SQLITE_TMPDIR"] = TMP
    os.environ["TMPDIR"] = TMP

corpus = sys.argv[1]
dossier = sys.argv[2] if len(sys.argv) > 2 else "/data/elias/stage-mids/data/corpus"

MOTS_OUTILS = """
le la les l' un une des du de d' au aux ce cet cette ces sa son ses ma mon mes ta ton
tes leur leurs notre nos votre vos quel quelle quels quelles quelque quelques chaque
tout toute tous toutes autre autres même mêmes tel telle tels telles
je tu il elle on nous vous ils elles me te se moi toi lui eux soi y en qui que quoi
dont où celui celle ceux celles cela ça ceci rien chacun chacune
à dans par pour sur avec sans sous entre vers chez depuis pendant avant après contre
selon malgré parmi dès jusque jusqu'à envers auprès autour afin lors hors sauf via
et ou mais donc or ni car si ne pas plus moins très trop aussi bien peu beaucoup
assez encore déjà toujours jamais souvent parfois ensuite puis alors ainsi comme
comment pourquoi quand lorsque tandis cependant pourtant néanmoins toutefois enfin
surtout notamment également puisque parce non oui voici voilà entre deux trois
est sont était étaient été être sera seront serait seraient suis es sommes êtes fut
furent soit soient étant a ont avait avaient avoir aura auront aurait auraient ai as
avons avez eu eut ayant fait faire faisait faisaient fera feront ferait font
peut peuvent pouvait pourrait pourraient pu doit doivent devait devraient devrait va
vont allait ira iront dit dire
c'est c'était d'un d'une d'autres l'on n'est n'a n'ont n'était n'y qu'il qu'ils
qu'elle qu'elles qu'on qu'un qu'une qu'à qu'en qu'au s'est s'il s'ils s'en j'ai d'en
l'a l'ont d'être d'avoir n'en
""".split()

# uri=True sur la connexion principale : nécessaire pour que l'ATTACH ?mode=ro fonctionne
conn = sqlite3.connect(f"file:{dossier}/{corpus}_top.db", uri=True)
conn.executescript(f"""
    PRAGMA journal_mode = OFF;
    PRAGMA synchronous = OFF;
    PRAGMA temp_store = 1;                       -- temp sur FICHIER (pas en RAM : trop gros)
    PRAGMA temp_store_directory = '{TMP}';       -- ces fichiers vont sur /data, pas sur /
    PRAGMA cache_size = -4000000;   -- ~4 Go de cache en RAM
    ATTACH DATABASE 'file:{dossier}/{corpus}_ngram.db?mode=ro' AS ng;
    DROP TABLE IF EXISTS top;
    CREATE TABLE top (ngram_n INTEGER, resolution TEXT, periode INTEGER, rang INTEGER,
        gram TEXT, n INTEGER, stop INTEGER,
        PRIMARY KEY (ngram_n, resolution, periode, rang)) WITHOUT ROWID;
    CREATE TEMP TABLE stopmot (word TEXT PRIMARY KEY);
""")
conn.executemany("INSERT OR IGNORE INTO stopmot VALUES (?)", [(m,) for m in MOTS_OUTILS])

for taille, table in [(1, "unigram"), (2, "bigram"), (3, "trigram")]:
    ws = ", ".join(f"w{i}" for i in range(1, taille + 1))
    gram = " || ' ' || ".join(f"t{i}.word" for i in range(1, taille + 1))
    jointures = " ".join(f"JOIN ng.token t{i} ON t{i}.id = s.w{i}" for i in range(1, taille + 1))
    est_outil = " AND ".join(f"(t{i}.word IN stopmot OR t{i}.word GLOB '[0-9]*')"
                             for i in range(1, taille + 1))
    for resolution, periode in [("jour", "date"), ("mois", "date/100"), ("annee", "date/10000")]:
        debut = time.time()
        conn.execute(f"""
            INSERT INTO top
            SELECT {taille}, '{resolution}', s.periode, s.rang, {gram}, s.n,
                   CASE WHEN {est_outil} THEN 1 ELSE 0 END
            FROM (
                SELECT {ws}, {periode} AS periode, SUM(n) AS n,
                       ROW_NUMBER() OVER (PARTITION BY {periode} ORDER BY SUM(n) DESC) AS rang
                FROM ng.{table} GROUP BY {ws}, {periode}
            ) s {jointures}
            WHERE s.rang <= 500
        """)
        conn.commit()
        print(f"{table} / {resolution} : {time.time() - debut:.0f} s", flush=True)

conn.execute("VACUUM")
conn.close()
