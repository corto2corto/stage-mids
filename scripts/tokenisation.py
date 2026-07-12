# Découpage du texte en tokens — LA référence unique, importée par les builds
# (ngram_*.py), la MAJ quotidienne (maj_ngram.py), le précalcul des tops
# (top_ngram.py) et l'API (api/app.py).
# ATTENTION : toute modification ici change le découpage, donc invalide les bases
# construites avant — ne pas toucher sans reconstruire les bases.

import re

# Mots outils (+ nombres, testés à part) : drapeau stop=1 dans les bases top.
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

# La regex d'abréviations supprime les points précédés d'une majuscule (M., U.S.A.)
# pour ne pas y couper de phrase — choix acté, ne pas « améliorer » sans décision.
_ABREVIATIONS = re.compile(r"(?<=[A-Z])\.")
_PONCTUATION_FORTE = re.compile(r"""[!"#$%&\()*+,./:;<=>?@\[\\\]^_`{|}~\n]""")
_MOT = re.compile(r"[a-zà-ÿ0-9']+")


def tokeniser(texte):
    """Tokens d'une expression courte (recherche API) : pas de découpage en phrases."""
    texte = _ABREVIATIONS.sub("", texte).lower().replace("’", "'")
    return _MOT.findall(texte)


def phrases(texte):
    """Listes de tokens, une par phrase — les ngrammes ne franchissent pas les phrases."""
    texte = _ABREVIATIONS.sub("", texte).lower().replace("’", "'")
    return [_MOT.findall(p) for p in _PONCTUATION_FORTE.split(texte)]
