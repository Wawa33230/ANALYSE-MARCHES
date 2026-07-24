"""Envoi d'un recapitulatif par e-mail (SMTP) des consultations interessantes.

Concu pour l'execution HEBDOMADAIRE automatique : apres la collecte, l'outil
peut envoyer un e-mail HTML resumant les marches "prioritaires" et "a regarder",
en mettant en avant les NOUVEAUTES depuis la derniere execution.

Securite : AUCUN secret n'est stocke dans le depot. Le mot de passe d'application
SMTP est lu, dans cet ordre :
  1. la variable d'environnement nommee par email.mot_de_passe_env
     (par defaut VEILLE_SMTP_PASSWORD) ;
  2. le fichier local nomme par email.mot_de_passe_fichier
     (par defaut motdepasse-mail.txt, ignore par git) ;
  3. le champ email.mot_de_passe du config.yaml (deconseille : ne pas committer).
"""

from __future__ import annotations

import os
import smtplib
import ssl
from datetime import date, datetime
from email.message import EmailMessage

CATEGORY_LABEL = {
    "prioritaire": "Cible prioritaire",
    "a_regarder": "A regarder",
    "hors_cible": "Hors cible",
}


# --------------------------------------------------------------------------
#  Recuperation du mot de passe (jamais en clair dans le depot)
# --------------------------------------------------------------------------
def _resolve_password(config) -> str | None:
    env_name = config.get("email.mot_de_passe_env", "VEILLE_SMTP_PASSWORD")
    if env_name:
        val = os.environ.get(env_name)
        if val and val.strip():
            return val.strip()

    fichier = config.get("email.mot_de_passe_fichier", "motdepasse-mail.txt")
    if fichier and os.path.exists(fichier):
        try:
            with open(fichier, "r", encoding="utf-8") as f:
                val = f.read().strip()
            if val:
                return val
        except Exception:
            pass

    inline = config.get("email.mot_de_passe", "")
    if inline and str(inline).strip() and str(inline).strip().upper() != "COLLE_ICI":
        return str(inline).strip()

    return None


# --------------------------------------------------------------------------
#  Mise en forme
# --------------------------------------------------------------------------
def _days_text(t) -> str:
    d = getattr(t, "days_left", None)
    if d is None:
        return "a verifier"
    if d < 0:
        return "echu"
    if d == 0:
        return "aujourd'hui"
    return f"{d} j"


def _days_color(t) -> str:
    d = getattr(t, "days_left", None)
    if d is None:
        return "#d98300"
    if d <= 7:
        return "#c0392b"
    if d <= 14:
        return "#d98300"
    return "#1b9e4b"


def _esc(s) -> str:
    s = "" if s is None else str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _row_html(t, is_new: bool) -> str:
    cat = getattr(t, "category", "")
    badge_bg = {"prioritaire": "#e7f6ed", "a_regarder": "#fdf1e0"}.get(cat, "#eef1f4")
    badge_fg = {"prioritaire": "#1b9e4b", "a_regarder": "#d98300"}.get(cat, "#566")
    new_tag = (
        '<span style="background:#fff4d6;color:#9a6b00;border:1px solid #f0d488;'
        'border-radius:5px;padding:1px 6px;font-size:11px;font-weight:700;margin-left:6px;">NOUVEAU</span>'
        if is_new else ""
    )
    ref = _esc(getattr(t, "reference", "") or "")
    ref_html = (
        f'<div style="font-family:Consolas,monospace;font-size:11px;color:#1f4e79;">Ref : {ref}</div>'
        if ref else ""
    )
    buyer = _esc(getattr(t, "buyer", "") or "-")
    dept = _esc(getattr(t, "department", "") or "")
    dept_html = f" &middot; Dpt {dept}" if dept else ""
    source = _esc(getattr(t, "source", "") or "")
    url = getattr(t, "url", "") or ""
    lien = (
        f'<a href="{_esc(url)}" style="color:#1f4e79;font-weight:600;text-decoration:none;">Ouvrir l\'avis &#8599;</a>'
        if url else "-"
    )
    return f"""
    <tr>
      <td style="padding:12px 10px;border-bottom:1px solid #eef1f4;vertical-align:top;width:52px;">
        <span style="display:inline-block;min-width:34px;text-align:center;font-weight:700;
          border-radius:6px;padding:4px 8px;background:{badge_bg};color:{badge_fg};">{getattr(t, 'score', 0)}</span>
      </td>
      <td style="padding:12px 10px;border-bottom:1px solid #eef1f4;vertical-align:top;">
        <div style="font-weight:600;color:#13202e;font-size:14px;">{_esc(getattr(t, 'title', ''))}{new_tag}</div>
        <div style="color:#566;font-size:12px;margin-top:2px;">{buyer}{dept_html} &middot; {source}</div>
        {ref_html}
      </td>
      <td style="padding:12px 10px;border-bottom:1px solid #eef1f4;vertical-align:top;white-space:nowrap;text-align:right;">
        <div style="font-weight:700;color:{_days_color(t)};font-size:13px;">{_days_text(t)}</div>
        <div style="color:#889;font-size:11px;">{_esc(getattr(t, 'deadline', '') or '')}</div>
        <div style="margin-top:6px;font-size:12px;">{lien}</div>
      </td>
    </tr>"""


def _section(titre: str, tenders: list, new_ids: set, couleur: str) -> str:
    if not tenders:
        return ""
    rows = "".join(_row_html(t, getattr(t, "id", None) in new_ids) for t in tenders)
    return f"""
    <h2 style="font-size:15px;color:#13202e;margin:26px 0 8px;padding-left:10px;border-left:4px solid {couleur};">
      {titre} <span style="color:#889;font-weight:400;">({len(tenders)})</span>
    </h2>
    <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;">
      {rows}
    </table>"""


def build_html(tenders: list, new_ids: set, generated: str) -> str:
    interesting = [t for t in tenders if getattr(t, "category", "") in ("prioritaire", "a_regarder")]
    interesting.sort(key=lambda t: (-getattr(t, "score", 0),
                                    getattr(t, "days_left", None) if getattr(t, "days_left", None) is not None else 9999))
    nouveautes = [t for t in interesting if getattr(t, "id", None) in new_ids]
    prio = [t for t in interesting if getattr(t, "category", "") == "prioritaire"]
    regarder = [t for t in interesting if getattr(t, "category", "") == "a_regarder"]
    urgent = [t for t in interesting
              if getattr(t, "days_left", None) is not None and 0 <= t.days_left <= 7]

    intro = (
        f"{len(interesting)} consultation(s) ouverte(s) correspondant a ta cible "
        f"(<b>{len(nouveautes)} nouvelle(s)</b> cette semaine, "
        f"{len(prio)} prioritaire(s), {len(urgent)} a moins de 7 jours)."
    )
    if not interesting:
        intro = "Aucune consultation ne correspond a ta cible cette semaine. On reste en veille."

    corps = ""
    corps += _section("Nouveautes cette semaine", nouveautes, new_ids, "#9a6b00")
    corps += _section("Cibles prioritaires (toutes ouvertes)", prio, new_ids, "#1b9e4b")
    corps += _section("A regarder", regarder, new_ids, "#d98300")

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"></head>
<body style="margin:0;background:#f4f6f8;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1c2733;">
  <div style="max-width:720px;margin:0 auto;padding:20px;">
    <div style="background:#1f4e79;color:#fff;border-radius:10px;padding:18px 22px;">
      <div style="font-size:18px;font-weight:700;">Veille appels d'offres &mdash; Remplacement baignoire/douche &amp; PMR</div>
      <div style="opacity:.85;font-size:13px;margin-top:4px;">Recap automatique du {generated}</div>
    </div>
    <p style="font-size:14px;line-height:1.5;margin:18px 4px;">{intro}</p>
    {corps or '<p style="color:#566;padding:0 4px;">Rien a signaler cette semaine.</p>'}
    <p style="color:#889;font-size:12px;margin-top:26px;padding:0 4px;line-height:1.5;">
      Sources : BOAMP, TED (UE), marches-publics.info (AWS), flux plateformes (RSS).<br>
      Verifie toujours l'avis officiel via le lien avant de t'engager. Les scores sont indicatifs.<br>
      Le tableau de bord complet (recherche, tri, filtres) est en piece jointe.
    </p>
  </div>
</body></html>"""


# --------------------------------------------------------------------------
#  Envoi
# --------------------------------------------------------------------------
def send_recap(config, tenders: list, new_ids: set, dashboard_path: str | None = None) -> bool:
    """Envoie le recap. Retourne True si l'e-mail est parti, False sinon
    (configuration incomplete ou erreur SMTP). Ne leve jamais d'exception."""
    destinataire = config.get("email.destinataire", "")
    expediteur = config.get("email.expediteur", "")
    prefixe = config.get("email.objet_prefixe", "Veille AO")
    joindre = config.get("email.joindre_tableau", True)
    envoyer_si_vide = config.get("email.envoyer_si_vide", True)

    interesting = [t for t in tenders if getattr(t, "category", "") in ("prioritaire", "a_regarder")]
    nouveautes = [t for t in interesting if getattr(t, "id", None) in new_ids]

    if not interesting and not envoyer_si_vide:
        print("   (i) Aucune cible cette semaine et 'envoyer_si_vide' = false : e-mail non envoye.")
        return False

    if not destinataire or not expediteur:
        print("   /!\\ E-mail non envoye : renseigne email.destinataire et email.expediteur dans config.yaml.")
        return False

    password = _resolve_password(config)
    if not password:
        env_name = config.get("email.mot_de_passe_env", "VEILLE_SMTP_PASSWORD")
        fichier = config.get("email.mot_de_passe_fichier", "motdepasse-mail.txt")
        print("   /!\\ E-mail non envoye : mot de passe d'application SMTP introuvable.")
        print(f"       -> definis la variable {env_name}, ou cree le fichier '{fichier}'")
        print("          contenant le mot de passe d'application (voir VEILLE-AUTOMATIQUE-HEBDO.md).")
        return False

    generated = datetime.now().strftime("%d/%m/%Y a %H:%M")
    html = build_html(tenders, new_ids, generated)

    sujet = f"{prefixe} — {len(interesting)} consultation(s), {len(nouveautes)} nouvelle(s) — {date.today().strftime('%d/%m/%Y')}"

    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = expediteur
    msg["To"] = destinataire
    msg.set_content(
        f"Veille appels d'offres du {generated}.\n"
        f"{len(interesting)} consultation(s) ciblees, {len(nouveautes)} nouvelle(s) cette semaine.\n"
        "Ouvre cet e-mail dans un client HTML pour le detail, ou consulte le tableau joint."
    )
    msg.add_alternative(html, subtype="html")

    if joindre and dashboard_path and os.path.exists(dashboard_path):
        try:
            with open(dashboard_path, "rb") as f:
                data = f.read()
            msg.add_attachment(data, maintype="text", subtype="html",
                               filename="tableau-de-bord-veille.html")
        except Exception:
            pass  # l'e-mail part quand meme sans la piece jointe

    if _smtp_send(config, msg, password):
        print(f"   E-mail envoye a {destinataire} ({len(interesting)} cible(s), {len(nouveautes)} nouvelle(s)).")
        return True
    return False


def _smtp_send(config, msg: EmailMessage, password: str) -> bool:
    """Ouvre la connexion SMTP (STARTTLS ou SSL) et envoie le message.
    Ne leve jamais d'exception ; retourne True si l'envoi a reussi."""
    hote = config.get("email.smtp_hote", "smtp.gmail.com")
    port = int(config.get("email.smtp_port", 587) or 587)
    securite = str(config.get("email.securite", "starttls")).lower()
    expediteur = msg["From"]
    try:
        if securite == "ssl":
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(hote, port, context=ctx, timeout=30) as s:
                s.login(expediteur, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(hote, port, timeout=30) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                s.login(expediteur, password)
                s.send_message(msg)
        return True
    except smtplib.SMTPAuthenticationError:
        print("   /!\\ Echec d'authentification SMTP : verifie l'adresse expediteur et le")
        print("       MOT DE PASSE D'APPLICATION (pas le mot de passe habituel du compte).")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"   /!\\ Envoi e-mail impossible : {e}")
        return False


def _action_row(a: dict) -> str:
    dl = a.get("action_deadline") or ""
    dl_html = (
        f'<div style="font-weight:700;color:#c0392b;font-size:13px;">A faire avant le {_esc(dl)}</div>'
        if dl else '<div style="color:#889;font-size:12px;">Echeance a verifier sur la plateforme</div>'
    )
    ref = _esc(a.get("reference", "") or "")
    ref_html = f' &middot; <span style="font-family:Consolas,monospace;font-size:11px;color:#1f4e79;">Ref {ref}</span>' if ref else ""
    url = a.get("url", "") or ""
    lien = (f'<a href="{_esc(url)}" style="color:#1f4e79;font-weight:600;text-decoration:none;">Ouvrir la consultation &#8599;</a>'
            if url else "")
    return f"""
    <tr>
      <td style="padding:12px 10px;border-bottom:1px solid #eef1f4;vertical-align:top;">
        <div style="font-weight:700;color:#8a1c0a;font-size:13px;text-transform:uppercase;letter-spacing:.3px;">{_esc(a.get('nature','Action'))}</div>
        <div style="font-weight:600;color:#13202e;font-size:14px;margin-top:3px;">{_esc(a.get('title',''))}</div>
        <div style="color:#566;font-size:12px;margin-top:2px;">{_esc(a.get('buyer','') or '-')}{ref_html} &middot; {_esc(a.get('platform',''))}</div>
        <div style="margin-top:6px;">{lien}</div>
      </td>
      <td style="padding:12px 10px;border-bottom:1px solid #eef1f4;vertical-align:top;white-space:nowrap;text-align:right;">{dl_html}</td>
    </tr>"""


def _build_actions_html(actions: list) -> str:
    actions = sorted(actions, key=lambda a: a.get("action_deadline") or "9999")
    rows = "".join(_action_row(a) for a in actions)
    generated = datetime.now().strftime("%d/%m/%Y a %H:%M")
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"></head>
<body style="margin:0;background:#f4f6f8;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1c2733;">
  <div style="max-width:720px;margin:0 auto;padding:20px;">
    <div style="background:#8a1c0a;color:#fff;border-radius:10px;padding:18px 22px;">
      <div style="font-size:18px;font-weight:700;">Actions a realiser &mdash; consultations en cours</div>
      <div style="opacity:.9;font-size:13px;margin-top:4px;">Detecte le {generated} dans tes notifications de plateformes</div>
    </div>
    <p style="font-size:14px;line-height:1.5;margin:18px 4px;">
      Tu as <b>{len(actions)} action(s)</b> a traiter sur des consultations ou tu es <b>deja engage</b>
      (demande de complement, question/reponse, changement de date, document a retirer...).
      Ces consultations ne sont volontairement <b>pas</b> remontees comme nouveaux marches.
    </p>
    <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;">{rows}</table>
    <p style="color:#889;font-size:12px;margin-top:22px;padding:0 4px;line-height:1.5;">
      Verifie toujours le detail et l'echeance exacte directement sur la plateforme via le lien.
    </p>
  </div>
</body></html>"""


def send_actions(config, actions: list) -> bool:
    """Envoie l'e-mail 'actions a realiser' (notifications sur consultations en
    cours). Retourne True si parti. Ne leve jamais d'exception."""
    if not actions:
        return False
    expediteur = config.get("email.expediteur", "")
    destinataire = config.get("mail_alertes.actions_destinataire", "") or config.get("email.destinataire", "")
    if not expediteur or not destinataire:
        print("   /!\\ E-mail 'actions' non envoye : expediteur/destinataire manquant.")
        return False
    password = _resolve_password(config)
    if not password:
        print("   /!\\ E-mail 'actions' non envoye : mot de passe d'application introuvable.")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"[ACTION] {len(actions)} action(s) a realiser sur tes consultations en cours"
    msg["From"] = expediteur
    msg["To"] = destinataire
    msg.set_content(
        f"Tu as {len(actions)} action(s) a realiser sur des consultations en cours "
        "(demande de complement, question/reponse, changement de date...). "
        "Ouvre cet e-mail en HTML pour le detail."
    )
    msg.add_alternative(_build_actions_html(actions), subtype="html")
    if _smtp_send(config, msg, password):
        print(f"   E-mail 'actions' envoye a {destinataire} ({len(actions)} action(s)).")
        return True
    return False
