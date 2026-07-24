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


def _extract_from_html(html: str, sender: str) -> list[Tender]:
    body_text = _strip_tags(html)
    default_buyer = ""
    mb = BUYER_RE.search(body_text)
    if mb:
        default_buyer = mb.group(1).strip().rstrip(".,;:")

    # 1) Retenir les liens "consultation" (dans l'ordre du mail, sans doublon).
    items: list[tuple[str, str]] = []
    seen: set[str] = set()
    for href, inner in A_RE.findall(html):
        href = href.strip()
        title = re.sub(r"\s+", " ", _strip_tags(inner)).strip()
        if not _looks_like_consultation(href, title) or href in seen:
            continue
        seen.add(href)
        items.append((href, title))

    # 2) Localiser chaque intitule dans le texte, en avancant, pour BORNER la
    #    fenetre de contexte au debut de l'avis suivant (evite d'emprunter la
    #    reference / l'acheteur de la consultation d'apres).
    positions: list[int] = []
    search_from = 0
    for _, title in items:
        key = title[:40] if title else ""
        idx = body_text.find(key, search_from) if key else -1
        positions.append(idx)
        if idx >= 0:
            search_from = idx + max(1, len(key))

    tenders: list[Tender] = []
    for n, (href, title) in enumerate(items):
        idx = positions[n]
        if idx >= 0:
            nxt = next((positions[k] for k in range(n + 1, len(items)) if positions[k] > idx), -1)
            window = body_text[idx: nxt if nxt > 0 else idx + 300]
        else:
            window = title
        host = urlparse(href).netloc
        mref = REF_RE.search(title) or REF_RE.search(window)
        reference = mref.group(1).rstrip(".,;:") if mref else ""
        deadline = _guess_date(window) or _guess_date(title)
        mb2 = BUYER_RE.search(window)
        buyer = (mb2.group(1).strip().rstrip(".,;:") if mb2 else default_buyer)
        tenders.append(
            Tender(
                id=f"mail:{href}",
                source=f"Alerte mail ({_label_for(sender, host)})",
                title=title,
                reference=reference,
                buyer=buyer,
                market_type="Plateforme (alerte e-mail)",
                deadline=deadline,
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
                    deadline=_guess_date(title),
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
            html, text = _get_bodies(msg)
            found = _extract_from_html(html, sender) if html else []
            if not found and text:
                found = _extract_from_text(text, sender)
            tenders += found

        try:
            M.close()
        except Exception:
            pass
        M.logout()
        print(f"      alertes e-mail : {lus} e-mail(s) d'alerte lus, {len(tenders)} consultation(s) extraite(s).")
    except imaplib.IMAP4.error as e:
        print(f"    /!\\ Alertes e-mail : connexion/lecture IMAP impossible ({e}).")
        print("        Verifie le mot de passe d'application et que l'IMAP est active dans Gmail.")
        return []
    except Exception as e:  # noqa: BLE001
        print(f"    /!\\ Alertes e-mail ignorees : {e}")
        return []

    return tenders
