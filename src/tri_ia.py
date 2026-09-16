"""AGENT IA de RECLASSEMENT de la pertinence.

Pourquoi ce module ?
--------------------
Le moteur de scoring (`scoring.py`) est mecanique : il additionne des bonus par
mots-cles / CPV. C'est rapide et gratuit, mais imprecis :
  - un marche PARFAIT peut plafonner a ~75 (bornes du bareme) ;
  - "ratisser large" fait remonter du bruit (une collectivite qui contient juste
    "accessibilite" ou "PMR" mais qui n'est PAS une salle de bain de logement).

Cet agent RELIT chaque marche (objet + acheteur + type + CPV + description) et,
comme le ferait un humain, juge sa pertinence par rapport a la cible ADOMSENIOR,
puis attribue :
  - une NOTE 0-100 (pertinence reelle) ;
  - une CATEGORIE (prioritaire / a_regarder / hors_cible) ;
  - une RAISON en une phrase.

Il APPELLE le modele Claude (via le SDK `anthropic`). Il est donc OPTIONNEL :
  - si aucune cle API n'est configuree, ou si on est hors-ligne, ou en cas
    d'erreur -> on GARDE le score par mots-cles (rien ne casse).

Cout maitrise :
  - on classe par LOTS (plusieurs marches par appel) ;
  - on met en CACHE le verdict de chaque marche (data/ia-cache.json) : un marche
    deja juge n'est jamais renote -> les relances quotidiennes ne coutent presque
    rien.

Configuration : section `ia:` de config.yaml. Cle API : variable d'environnement
`VEILLE_IA_KEY` (ou `ANTHROPIC_API_KEY`), sinon fichier local `cle-ia.txt`
(ignore par git, comme le mot de passe mail).
"""

from __future__ import annotations

import json
import os
import re

from .models import Tender

# --- Reglages par defaut (surchargeables dans config.yaml -> ia:) ---
DEFAULT_MODELE = "claude-haiku-4-5"   # rapide + tres economique pour de la classification
DEFAULT_LOT = 12                       # nombre de marches envoyes par appel
DEFAULT_CACHE = os.path.join("data", "ia-cache.json")
DEFAULT_FICHIER_CLE = "cle-ia.txt"
CATEGORIES = ("prioritaire", "a_regarder", "hors_cible")

# Definition de la CIBLE (le "cerveau metier" de l'agent). C'est ce texte qui
# permet a l'IA de distinguer un vrai marche salle de bain / adaptation d'un
# marche de collectivite hors sujet. Modifiable via ia.definition_cible dans
# config.yaml si besoin d'affiner.
DEFINITION_CIBLE = """\
Tu es l'assistant de veille d'ADOMSENIOR (entite LYES SANITAIRE / ETS OUHADDAD),
une entreprise qui realise EXCLUSIVEMENT :
  - le remplacement de BAIGNOIRE par une DOUCHE (douche a l'italienne, receveur
    extra-plat, bac a douche) ;
  - l'ADAPTATION de la SALLE DE BAIN / salle d'eau pour l'ACCESSIBILITE PMR et le
    MAINTIEN A DOMICILE (barres de maintien, sol antiderapant, siege de douche) ;
  - la pose de PANNEAUX MURAUX (habillage sans carrelage) ;
  principalement pour des BAILLEURS SOCIAUX, mais aussi CCAS, foyers, collectivites
  ou departements DES LORS QUE le marche porte sur l'adaptation de salle de bain /
  le maintien a domicile.

Marche CIBLE (note haute) :
  - remplacement baignoire/douche, amenagement ou adaptation de salle de bain /
    salle d'eau, mise en accessibilite PMR du LOGEMENT, maintien a domicile,
    plomberie sanitaire liee a l'adaptation, accord-cadre "adaptation des logements"
    ou "travaux d'accessibilite" incluant un lot salle de bain.

Marche HORS CIBLE (note basse) :
  - construction neuve, gros oeuvre, rehabilitation lourde tous corps d'etat non
    centree sur la salle de bain ;
  - chauffage, chaudiere, eau chaude sanitaire collective, CVC, climatisation,
    genie climatique, plomberie de reseau ;
  - maintenance/entretien courant multiservices, multitechnique, depannage ;
  - voirie, espaces verts, toiture, couverture, etancheite, ravalement ;
  - accessibilite de BATIMENTS PUBLICS / ERP / voirie / etablissements (ce n'est
    PAS du logement adapte : une rampe de mairie ou un ascenseur d'ecole = hors cible) ;
  - fourniture seule sans pose, carrelage/faience seul sans adaptation.

Regle d'or : ce qui compte, c'est l'OBJET du marche (adapter une salle de bain de
logement pour une personne agee/handicapee), PAS uniquement le type d'acheteur.
Un bailleur social qui fait de la maintenance de chaufferie = hors cible ; une
mairie qui adapte les salles de bain de logements communaux = cible.
"""

BAREME = """\
Bareme de NOTE (0-100) et CATEGORIE :
  - 80-100 -> "prioritaire" : marche clairement d'adaptation / remplacement de
    salle de bain (baignoire->douche, accessibilite PMR du logement, maintien a
    domicile). A traiter en priorite.
  - 45-79  -> "a_regarder" : lien plausible (plomberie sanitaire de logement, lot
    salle de bain possible dans un accord-cadre, objet un peu ambigu) mais a
    verifier.
  - 0-44   -> "hors_cible" : hors de notre metier (voir la liste HORS CIBLE).
"""


# ----------------------------------------------------------------------------
#  Configuration / activation
# ----------------------------------------------------------------------------
def _cfg(config) -> dict:
    try:
        return config.data.get("ia", {}) or {}
    except Exception:  # noqa: BLE001
        return {}


def is_enabled(config) -> bool:
    return bool(_cfg(config).get("actif", False))


def _resolve_key(config) -> str:
    """Cle API Claude : env VEILLE_IA_KEY -> env ANTHROPIC_API_KEY -> fichier local.
    On ne stocke JAMAIS la cle dans config.yaml (versionne)."""
    ia = _cfg(config)
    env_name = ia.get("cle_env", "VEILLE_IA_KEY")
    for name in (env_name, "ANTHROPIC_API_KEY"):
        val = os.environ.get(name, "").strip()
        if val:
            return val
    fichier = ia.get("cle_fichier", DEFAULT_FICHIER_CLE)
    try:
        if fichier and os.path.exists(fichier):
            with open(fichier, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:  # noqa: BLE001
        pass
    return ""


# ----------------------------------------------------------------------------
#  Cache (data/ia-cache.json) : {tender_id: {"note", "categorie", "raison", "modele"}}
# ----------------------------------------------------------------------------
def _cache_path(config) -> str:
    return _cfg(config).get("cache_fichier", DEFAULT_CACHE)


def _load_cache(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:  # noqa: BLE001
        return {}


def _save_cache(path: str, cache: dict):
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        pass


# ----------------------------------------------------------------------------
#  Construction de la requete
# ----------------------------------------------------------------------------
def _abrege(txt: str, n: int = 600) -> str:
    txt = (txt or "").strip().replace("\n", " ")
    return txt[:n]


def _marche_pour_ia(t: Tender) -> dict:
    return {
        "id": t.id,
        "objet": _abrege(t.title, 300),
        "acheteur": _abrege(t.buyer, 150),
        "type": _abrege(t.market_type, 80),
        "cpv": [str(c) for c in (t.cpv or [])][:6],
        "description": _abrege(t.description, 500),
    }


def _prompt_lot(marches: list[dict]) -> str:
    exemple = ('[{"id":"...","note":92,"categorie":"prioritaire",'
               '"raison":"Accord-cadre d\'adaptation de salles de bain PMR pour un bailleur"}]')
    return (
        "Voici une liste de marches publics a evaluer. Pour CHACUN, donne :\n"
        "  - \"id\" : recopie l'identifiant exact ;\n"
        "  - \"note\" : entier 0-100 (pertinence pour ADOMSENIOR) ;\n"
        "  - \"categorie\" : \"prioritaire\", \"a_regarder\" ou \"hors_cible\" ;\n"
        "  - \"raison\" : UNE phrase courte en francais expliquant la note.\n\n"
        "Reponds UNIQUEMENT par un tableau JSON, sans texte avant ni apres, "
        "un objet par marche, meme ordre. Exemple de format :\n"
        f"{exemple}\n\n"
        "MARCHES A EVALUER (JSON) :\n"
        + json.dumps(marches, ensure_ascii=False)
    )


def _extraire_json(texte: str) -> list:
    """Recupere le tableau JSON meme si le modele a ajoute du texte autour."""
    if not texte:
        return []
    try:
        return json.loads(texte)
    except Exception:  # noqa: BLE001
        pass
    i, j = texte.find("["), texte.rfind("]")
    if i != -1 and j != -1 and j > i:
        try:
            return json.loads(texte[i:j + 1])
        except Exception:  # noqa: BLE001
            return []
    return []


# ----------------------------------------------------------------------------
#  Appel au modele
# ----------------------------------------------------------------------------
def _classer_lot(client, modele: str, systeme: str, marches: list[dict]) -> dict:
    """Retourne {id: {"note","categorie","raison"}} pour un lot de marches."""
    reponse = client.messages.create(
        model=modele,
        max_tokens=2000,
        system=systeme,
        messages=[{"role": "user", "content": _prompt_lot(marches)}],
    )
    texte = "".join(b.text for b in reponse.content if getattr(b, "type", "") == "text")
    verdicts = {}
    for item in _extraire_json(texte):
        if not isinstance(item, dict):
            continue
        tid = str(item.get("id", "")).strip()
        if not tid:
            continue
        verdicts[tid] = {
            "note": _borne_note(item.get("note")),
            "categorie": _valide_cat(item.get("categorie"), item.get("note")),
            "raison": _abrege(str(item.get("raison", "")), 240),
        }
    return verdicts


def _borne_note(v) -> int:
    try:
        return max(0, min(100, int(round(float(v)))))
    except Exception:  # noqa: BLE001
        return 0


def _valide_cat(cat, note) -> str:
    c = str(cat or "").strip().lower().replace(" ", "_").replace("-", "_")
    if c in CATEGORIES:
        return c
    # Repli : deduire la categorie de la note
    n = _borne_note(note)
    if n >= 80:
        return "prioritaire"
    if n >= 45:
        return "a_regarder"
    return "hors_cible"


# ----------------------------------------------------------------------------
#  Point d'entree : reclasse une liste de marches
# ----------------------------------------------------------------------------
def reclasser(tenders: list[Tender], config) -> list[Tender]:
    """Reclasse les marches via l'agent IA. Sans effet (retourne tel quel) si l'IA
    est desactivee, sans cle, ou en cas d'erreur."""
    if not tenders or not is_enabled(config):
        return tenders

    key = _resolve_key(config)
    if not key:
        print("   (i) Agent IA active mais AUCUNE cle API trouvee "
              f"(env VEILLE_IA_KEY / ANTHROPIC_API_KEY, ou fichier {DEFAULT_FICHIER_CLE}).")
        print("       -> on garde le score par mots-cles.")
        return tenders

    try:
        import anthropic
    except ImportError:
        print("   (i) Module 'anthropic' non installe (pip install anthropic).")
        print("       -> on garde le score par mots-cles.")
        return tenders

    ia = _cfg(config)
    modele = ia.get("modele", DEFAULT_MODELE)
    taille_lot = int(ia.get("taille_lot", DEFAULT_LOT) or DEFAULT_LOT)
    definition = ia.get("definition_cible") or DEFINITION_CIBLE
    systeme = definition + "\n\n" + BAREME
    cache_path = _cache_path(config)
    cache = _load_cache(cache_path)

    # 1) Ne (re)classer que les marches absents du cache pour ce modele.
    a_classer = [t for t in tenders
                 if cache.get(t.id, {}).get("modele") != modele]
    print(f">> Agent IA ({modele}) : {len(a_classer)} marche(s) a analyser "
          f"({len(tenders) - len(a_classer)} depuis le cache).")

    if a_classer:
        try:
            client = anthropic.Anthropic(api_key=key)
        except Exception as e:  # noqa: BLE001
            print(f"   /!\\ Client IA indisponible : {e} -> score par mots-cles conserve.")
            return tenders

        for debut in range(0, len(a_classer), taille_lot):
            lot = a_classer[debut:debut + taille_lot]
            marches = [_marche_pour_ia(t) for t in lot]
            try:
                verdicts = _classer_lot(client, modele, systeme, marches)
            except Exception as e:  # noqa: BLE001
                print(f"   /!\\ Lot IA {debut}-{debut + len(lot)} : {e} (marches laisses au score mots-cles)")
                continue
            for t in lot:
                v = verdicts.get(t.id)
                if v:
                    cache[t.id] = {**v, "modele": modele}
        _save_cache(cache_path, cache)

    # 2) Appliquer les verdicts (cache) sur les marches.
    applique = 0
    for t in tenders:
        v = cache.get(t.id)
        if not v or v.get("modele") != modele:
            continue
        if t.score_mots_cles is None:
            t.score_mots_cles = t.score
        t.ia_note = _borne_note(v.get("note"))
        t.ia_categorie = _valide_cat(v.get("categorie"), v.get("note"))
        t.ia_raison = v.get("raison", "")
        # L'IA fait AUTORITE : elle remplace score + categorie.
        t.score = t.ia_note
        t.category = t.ia_categorie
        if "IA" not in t.flags:
            t.flags.append("IA")
        applique += 1

    print(f"   {applique} marche(s) reclasse(s) par l'agent IA.")
    return tenders
