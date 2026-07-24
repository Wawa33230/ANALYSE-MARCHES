"""Source "alertes e-mail" : lit la boite Gmail (IMAP) et transforme les
e-mails d'alerte des plateformes (Ternum BFC, achatpublic, maximilien,
marches-securises, e-marchespublics, megalis, PLACE...) en consultations.

Pourquoi cette source ? La plupart des plateformes recentes n'offrent PLUS de
flux RSS : elles proposent uniquement des ALERTES E-MAIL sur recherche
sauvegardee. On cree donc une alerte sur chaque plateforme, et cet outil lit
automatiquement ces e-mails pour en extraire les avis (titre + lien, plus
acheteur / reference / date limite quand ils sont presents), puis les filtre et
les score comme les autres sources.

Connexion : IMAP Gmail (imap.gmail.com:993 SSL). Le mot de passe est le MEME
"mot de passe d'application" que pour l'envoi (voir section email du config.yaml
et VEILLE-AUTOMATIQUE-HEBDO.md) : il donne acces en lecture a la boite.

Robuste par conception : toute erreur (identifiants absents, boite injoignable,
e-mail illisible) est signalee sans bloquer le reste de l'outil.
"""

from __future__ import annotations

import email
import imaplib
import re
from datetime import date, timedelta
from email.header import decode_header, make_header
from urllib.parse import urlparse

from ..models import Tender
from ..notify import _resolve_password
from .plateformes import BUYER_RE, REF_RE, _strip_tags, _guess_date

# Lien "consultation" plausible dans un e-mail d'alerte.
A_RE = re.compile(r'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)

# Texte d'ancre qui est en fait une URL (achatpublic met l'URL comme libelle) :
# a ne PAS utiliser comme titre.
URLISH_RE = re.compile(r'^\s*(?:https?://|www\.)', re.I)

# Format tres courant (achatpublic, variantes Atexo) :
#   "consultation [intitulee] <TITRE> (reference <REF>) lancee/publiee par <ACHETEUR>"
CONSULT_RE = re.compile(
    r'consultation\s+(?:intitul[ée]e?\s+)?["“«\']?\s*(.+?)\s*["”»\']?\s*'
    r'\(\s*r[ée]f[ée]rence\s*[:°]?\s*([A-Za-z0-9][A-Za-z0-9\-_/.]+?)\s*\)',
    re.I | re.S)
# Acheteur dans la prose : "lancee par X", "publiee par X", "l'organisme X"
PAR_RE = re.compile(
    r'(?:lanc[ée]e?\s+par|publi[ée]e?\s+par|par\s+l[\'’]organisme|l[\'’]organisme)\s+'
    r'([A-ZÉÈÀ0-9][\wÀ-ÿ&\'’\-. ]{1,50})',
    re.I)
# Dates : ISO (2026-08-14) OU francais (14/08/2026), y compris "au 14/08/2026".
_DATE_ISO = re.compile(r'(\d{4})[-/](\d{2})[-/](\d{2})')
_DATE_FR = re.compile(r'\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b')
# Contexte d'une date limite (on privilegie la date qui suit ces mots).
_DEADLINE_CTX = re.compile(
    r'(?:date limite|remise des (?:offres|plis)|remise des offres|'
    r'limite de r[ée]ception|avant le|au plus tard le|cl[ôo]ture)\b(.{0,60})',
    re.I | re.S)


def _to_iso(text: str) -> str:
    m = _DATE_ISO.search(text or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _DATE_FR.search(text or "")
    if m:
        d, mo, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{y}-{mo}-{d}"
    return ""


def _guess_deadline(text: str) -> str:
    """Cherche d'abord une date proche d'un mot 'date limite / remise des plis',
    sinon n'importe quelle date du texte."""
    m = _DEADLINE_CTX.search(text or "")
    if m:
        d = _to_iso(m.group(1))
        if d:
            return d
    return _to_iso(text)


# --- Classification : nouvelle OPPORTUNITE vs NOTIFICATION d'action -----------
# Signaux d'une nouvelle consultation issue d'une recherche sauvegardee.
NEW_RE = re.compile(
    r"nouvelle[s]?\s+consultation|correspond[a-z]*\s+[àa]\s+votre\s+recherche|"
    r"recherche\s+sauvegard|nouvel(?:le)?\s+avis|nouveaux\s+avis|votre\s+alerte|"
    r"r[ée]sultats?\s+de\s+votre\s+recherche|nouvelle\s+annonce",
    re.I)
# Signaux d'une notification sur une consultation ou l'on est DEJA engage
# (elle demande souvent une action de ta part).
ACTION_RE = re.compile(
    r"demande\s+de\s+compl[ée]ment|r[ée]ponse\s+attendue|habilitation\s+[àa]\s+retirer|"
    r"questions?\s*/\s*r[ée]ponses?|question[-\s]r[ée]ponse|modification\s+de\s+la\s+date|"
    r"report\s+de\s+la\s+date|nouvelle\s+date\s+limite|message\s+de\s+l.?acheteur|"
    r"invitation\s+[àa]|n[ée]gociation|r[ée]gularisation|pi[èe]ce[s]?\s+manquante|"
    r"accus[ée]\s+de\s+r[ée]ception|avenant|rectificatif|notification\s+de\s+rejet|"
    r"attribution|infructueux|retir[ée]?\s+.{0,20}document|d[ée]p[ôo]t\s+de\s+(?:votre\s+)?r[ée]ponse",
    re.I)

# Sujet achatpublic : "[ACHETEUR] Consultation REF / <nature de l'action>"
SUBJ_AP = re.compile(r"\[([^\]]+)\]\s*Consultation\s+([^/]+?)\s*/\s*(.+)", re.I)
# Echeance d'une ACTION : "reponse attendue avant le 24/07/2026", "avant le ...".
ACTION_DEADLINE_RE = re.compile(
    r"(?:r[ée]ponse\s+attendue|avant\s+le|au\s+plus\s+tard\s+le|"
    r"date\s+limite[^0-9]{0,30})[^0-9]{0,15}"
    r"(\d{1,2}[/.]\d{1,2}[/.]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})",
    re.I)


def _classify(subject: str, body: str) -> str:
    """'opportunity' (nouveau marche a remonter) ou 'action' (notification sur une
    consultation en cours). Par defaut on remonte (opportunity), sauf signal d'action."""
    blob = f"{subject or ''} {body or ''}"
    if NEW_RE.search(blob):
        return "opportunity"
    if ACTION_RE.search(blob):
        return "action"
    return "opportunity"


def _extract_action(subject: str, html: str, text: str, sender: str) -> dict:
    body_text = _strip_tags(html or "") or (text or "")
    buyer = reference = nature = title = ""
    ms = SUBJ_AP.search(subject or "")
    if ms:
        buyer, reference, nature = ms.group(1).strip(), ms.group(2).strip(), ms.group(3).strip()
    else:
        nature = (subject or "").strip()
    mc = CONSULT_RE.search(body_text)
    if mc:
        title = re.sub(r"\s+", " ", mc.group(1)).strip(" \"'«»“”")
        reference = reference or mc.group(2).strip()
    if not buyer:
        mb = PAR_RE.search(body_text)
        if mb:
            buyer = mb.group(1).strip().rstrip(".,;:")
    md = ACTION_DEADLINE_RE.search(body_text)
    action_deadline = _to_iso(md.group(1)) if md else ""
    url = _pick_consultation_url(_all_links(html or ""))
    return {
        "platform": _label_for(sender, urlparse(url).netloc if url else ""),
        "buyer": buyer,
        "reference": reference,
        "title": title or nature,
        "nature": nature,
        "action_deadline": action_deadline,
        "url": url,
    }


def _handle_actions(config, actions: list) -> None:
    """Envoie un e-mail 'action a realiser' pour les NOUVELLES notifications
    (celles jamais signalees), avec memoire dans data/actions-notifiees.json."""
    if not actions or not config.get("mail_alertes.email_actions", True):
        return
    import json
    import os
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", "actions-notifiees.json")
    seen: set = set()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                seen = set(json.load(f))
        except Exception:
            seen = set()
    nouvelles = [a for a in actions if a.get("_key") not in seen]
    if not nouvelles:
        print(f"      actions : {len(actions)} notification(s), aucune nouvelle a signaler.")
        return
    from ..notify import send_actions
    if send_actions(config, nouvelles):
        seen |= {a.get("_key") for a in nouvelles if a.get("_key")}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(sorted(seen), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

# Indices qu'un lien pointe vers une consultation (et pas vers un pied de page).
LINK_HINTS = (
    "consultation", "annonce", "avis", "detail", "entreprise", "index.php",
    "refconsultation", "orgacronyme", "?id=", "idcons", "objet", "marche",
)
# Liens a IGNORER (desinscription, navigation, reseaux sociaux, etc.).
LINK_EXCLUDE = (
    "unsubscribe", "desinscri", "desabonn", "preferenc", "mentions", "cookie",
    "rgpd", "aide", "faq", "contact", "connexion", "login", "compte",
    "mot-de-passe", "facebook", "twitter", "linkedin", "instagram", "youtube",
    "mailto:", "tel:", "google.com", "apple.com", "play.google",
)
TEXT_EXCLUDE = (
    "se desinscrire", "se desabonner", "gerer mes alertes", "voir toutes",
    "modifier ma recherche", "mentions legales", "nous contacter",
    "cliquez ici", "en savoir plus", "acceder au site", "mon compte",
)

# Jolis libelles par domaine d'expediteur connu.
DOMAIN_LABEL = {
    "ternum-bfc.fr": "Ternum BFC",
    "achatpublic.com": "achatpublic",
    "maximilien.fr": "Maximilien (IDF)",
    "marches-securises.fr": "marches-securises",
    "e-marchespublics.com": "e-marchespublics",
    "megalis.bretagne.bzh": "Megalis Bretagne",
    "marches-publics.gouv.fr": "PLACE (Etat)",
    "atexo.com": "Atexo",
}


def _strip_accents(s: str) -> str:
    table = str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc")
    return (s or "").lower().translate(table)


def _decode_hdr(value: str) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""


def _part_text(part) -> str:
    try:
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    except Exception:
        return ""


def _get_bodies(msg) -> tuple[str, str]:
    """Retourne (html, texte). L'un des deux peut etre vide."""
    html, text = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            disp = str(part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            ctype = part.get_content_type()
            if ctype == "text/html" and not html:
                html = _part_text(part)
            elif ctype == "text/plain" and not text:
                text = _part_text(part)
    else:
        if msg.get_content_type() == "text/html":
            html = _part_text(msg)
        else:
            text = _part_text(msg)
    return html, text


def _label_for(sender: str, link_host: str) -> str:
    blob = (sender + " " + link_host).lower()
    for dom, label in DOMAIN_LABEL.items():
        if dom in blob:
            return label
    host = link_host or (sender.split("@")[-1] if "@" in sender else sender)
    return host or "plateforme"


def _looks_like_consultation(href: str, title: str) -> bool:
    h = href.lower()
    if not h.startswith("http"):
        return False
    if any(x in h for x in LINK_EXCLUDE):
        return False
    t = _strip_accents(title).strip()
    if any(x in t for x in TEXT_EXCLUDE):
        return False
    if any(x in h for x in LINK_HINTS):
        return len(t) >= 6
    # Sinon on accepte si l'intitule ressemble a un objet de marche (assez long).
    return 12 <= len(t) <= 300


def _all_links(html: str) -> list[tuple[str, str]]:
    """(href, texte_ancre) pour tous les liens http, sans doublon d'URL."""
    out, seen = [], set()
    for href, inner in A_RE.findall(html):
        href = href.strip()
        if not href.lower().startswith("http") or href in seen:
            continue
        seen.add(href)
        out.append((href, re.sub(r"\s+", " ", _strip_tags(inner)).strip()))
    return out


def _pick_consultation_url(links: list[tuple[str, str]]) -> str:
    """Choisit le lien vers la FICHE de consultation (et pas le lien 'telecharger
    le document' ni la desinscription)."""
    prefer = ("fichecsl", "consultation", "detailconsultation", "ficheconsultation",
              "annonce", "avis", "detail")
    for href, _ in links:
        h = href.lower()
        if any(x in h for x in LINK_EXCLUDE):
            continue
        if any(p in h for p in prefer):
            return href
    for href, _ in links:
        if not any(x in href.lower() for x in LINK_EXCLUDE):
            return href
    return ""


def _extract_from_html(html: str, sender: str) -> list[Tender]:
    body_text = _strip_tags(html)
    links = _all_links(html)
    tenders: list[Tender] = []
    seen_ids: set[str] = set()

    # --- Cas 1 : le titre est dans la PROSE (achatpublic, variantes Atexo) :
    #     "consultation <TITRE> (reference <REF>) lancee par <ACHETEUR>". ---
    for m in CONSULT_RE.finditer(body_text):
        title = re.sub(r"\s+", " ", m.group(1)).strip(" \"'«»“”")
        reference = m.group(2).strip().rstrip(".,;:")
        if not title or len(title) < 4:
            continue
        window = body_text[m.start(): m.start() + 500]
        mb = PAR_RE.search(window) or PAR_RE.search(body_text)
        buyer = mb.group(1).strip().rstrip(".,;:") if mb else ""
        url = _pick_consultation_url(links)
        tid = f"mail:{reference or title[:40]}"
        if tid in seen_ids:
            continue
        seen_ids.add(tid)
        tenders.append(
            Tender(
                id=tid,
                source=f"Alerte mail ({_label_for(sender, urlparse(url).netloc)})",
                title=title,
                reference=reference,
                buyer=buyer,
                market_type="Plateforme (alerte e-mail)",
                deadline=_guess_deadline(window) or _guess_deadline(body_text),
                url=url,
                description=f"Extrait d'une alerte e-mail ({sender}).",
            )
        )
    if tenders:
        return tenders

    # --- Cas 2 : le titre est porte par les LIENS (digests "nouveaux resultats"). ---
    items = [(h, t) for h, t in links
             if t and not URLISH_RE.match(t) and _looks_like_consultation(h, t)]
    positions, search_from = [], 0
    for _, title in items:
        key = title[:40] if title else ""
        idx = body_text.find(key, search_from) if key else -1
        positions.append(idx)
        if idx >= 0:
            search_from = idx + max(1, len(key))

    default_buyer = ""
    mbd = BUYER_RE.search(body_text)
    if mbd:
        default_buyer = mbd.group(1).strip().rstrip(".,;:")

    for n, (href, title) in enumerate(items):
        idx = positions[n]
        if idx >= 0:
            nxt = next((positions[k] for k in range(n + 1, len(items)) if positions[k] > idx), -1)
            window = body_text[idx: nxt if nxt > 0 else idx + 300]
        else:
            window = title
        mref = REF_RE.search(title) or REF_RE.search(window)
        reference = mref.group(1).rstrip(".,;:") if mref else ""
        mb2 = BUYER_RE.search(window)
        buyer = (mb2.group(1).strip().rstrip(".,;:") if mb2 else default_buyer)
        tenders.append(
            Tender(
                id=f"mail:{href}",
                source=f"Alerte mail ({_label_for(sender, urlparse(href).netloc)})",
                title=title,
                reference=reference,
                buyer=buyer,
                market_type="Plateforme (alerte e-mail)",
                deadline=_guess_deadline(window) or _guess_deadline(title),
                url=href,
                description=f"Extrait d'une alerte e-mail ({sender}).",
            )
        )
    return tenders


URL_RE = re.compile(r'https?://[^\s<>"\')]+', re.I)


def _extract_from_text(text: str, sender: str) -> list[Tender]:
    """Repli quand l'e-mail n'a pas de version HTML : on associe chaque URL a la
    ligne de texte non vide qui la precede (souvent l'intitule)."""
    tenders: list[Tender] = []
    seen: set[str] = set()
    lines = [ln.strip() for ln in (text or "").splitlines()]
    for i, ln in enumerate(lines):
        for href in URL_RE.findall(ln):
            title = ""
            for j in range(i, -1, -1):
                cand = lines[j]
                if cand and not URL_RE.search(cand) and len(cand) >= 12:
                    title = cand
                    break
            if not title or not _looks_like_consultation(href, title):
                continue
            if href in seen:
                continue
            seen.add(href)
            host = urlparse(href).netloc
            tenders.append(
                Tender(
                    id=f"mail:{href}",
                    source=f"Alerte mail ({_label_for(sender, host)})",
                    title=re.sub(r"\s+", " ", title).strip(),
                    market_type="Plateforme (alerte e-mail)",
                    deadline=_guess_deadline(title),
                    url=href,
                    description=f"Extrait d'une alerte e-mail ({sender}).",
                )
            )
    return tenders


def _select_folder(M: imaplib.IMAP4_SSL, dossier: str):
    name = dossier or "INBOX"
    if name != "INBOX" and (" " in name or "-" in name):
        name = '"%s"' % name
    M.select(name, readonly=True)


def fetch(config) -> list[Tender]:
    if not config.get("sources.mail_alertes", False):
        return []

    hote = config.get("mail_alertes.imap_hote", "imap.gmail.com")
    port = int(config.get("mail_alertes.imap_port", 993) or 993)
    compte = config.get("mail_alertes.compte", "") or config.get("email.expediteur", "")
    dossier = config.get("mail_alertes.dossier", "INBOX")
    jours = int(config.get("mail_alertes.jours_recents", 14) or 14)
    non_lus = bool(config.get("mail_alertes.seulement_non_lus", False))
    expediteurs = [str(e).lower() for e in (config.get("mail_alertes.expediteurs", []) or [])]

    if not compte:
        print("    /!\\ Alertes e-mail : renseigne mail_alertes.compte (ou email.expediteur).")
        return []
    password = _resolve_password(config)
    if not password:
        print("    /!\\ Alertes e-mail : mot de passe d'application introuvable "
              "(meme mecanisme que l'envoi, voir VEILLE-AUTOMATIQUE-HEBDO.md).")
        return []

    tenders: list[Tender] = []
    try:
        M = imaplib.IMAP4_SSL(hote, port)
        M.login(compte, password)
        _select_folder(M, dossier)

        since = (date.today() - timedelta(days=jours)).strftime("%d-%b-%Y")
        criteria = ["SINCE", since]
        if non_lus:
            criteria = ["UNSEEN"] + criteria
        typ, data = M.search(None, *criteria)
        ids = data[0].split() if data and data[0] else []

        lus = 0
        actions: list[dict] = []
        for num in ids:
            typ, msgdata = M.fetch(num, "(RFC822)")
            if typ != "OK" or not msgdata or not msgdata[0]:
                continue
            raw = msgdata[0][1]
            msg = email.message_from_bytes(raw)
            sender = _decode_hdr(msg.get("From", ""))
            sender_l = sender.lower()
            # Ne garder que les expediteurs d'alerte connus (si une liste est fournie).
            if expediteurs and not any(dom in sender_l for dom in expediteurs):
                continue
            lus += 1
            subject = _decode_hdr(msg.get("Subject", ""))
            html, text = _get_bodies(msg)

            # Notification sur une consultation en cours (deja engage) ?
            if _classify(subject, (text or "") + " " + _strip_tags(html or "")) == "action":
                act = _extract_action(subject, html, text, sender)
                act["_key"] = msg.get("Message-ID") or f"{sender}|{subject}"
                actions.append(act)
                continue  # -> ne PAS remonter comme nouveau marche

            found = _extract_from_html(html, sender) if html else []
            if not found and text:
                found = _extract_from_text(text, sender)
            tenders += found

        try:
            M.close()
        except Exception:
            pass
        M.logout()
        print(f"      alertes e-mail : {lus} e-mail(s) lus, {len(tenders)} consultation(s) extraite(s), "
              f"{len(actions)} notification(s) d'action.")
        _handle_actions(config, actions)
    except imaplib.IMAP4.error as e:
        print(f"    /!\\ Alertes e-mail : connexion/lecture IMAP impossible ({e}).")
        print("        Verifie le mot de passe d'application et que l'IMAP est active dans Gmail.")
        return []
    except Exception as e:  # noqa: BLE001
        print(f"    /!\\ Alertes e-mail ignorees : {e}")
        return []

    return tenders
