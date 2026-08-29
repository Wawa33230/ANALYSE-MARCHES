"""Diagnostic complet de la veille : verifie en 30 secondes que TOUT fonctionne.

Usage :
    python -m src.diagnostic               # verifications seules
    python -m src.diagnostic --envoi-test  # + envoi d'un e-mail de test

Verifie, dans l'ordre :
  1. le chargement de config.yaml (adresses e-mail renseignees) ;
  2. la presence du mot de passe d'application (fichier ou variable d'env) ;
  3. la connexion IMAP (lecture des alertes) + l'acces au libelle Gmail
     "Notifications AO" + le nombre d'e-mails recents dedans ;
  4. la connexion SMTP (envoi des recaps) ;
  5. (option) l'envoi reel d'un e-mail de test au destinataire configure.

Chaque etape affiche [OK] ou [ERREUR] avec l'explication et le remede.
"""

from __future__ import annotations

import argparse
import imaplib
import smtplib
import ssl
import sys
from datetime import date, datetime, timedelta

from .config import Config
from .notify import _resolve_password, _smtp_send, _log_send
from email.message import EmailMessage

OK = "[OK]    "
KO = "[ERREUR]"
INFO = "[i]     "


def _check_config(config) -> bool:
    dest = config.get("email.destinataire", "")
    exp = config.get("email.expediteur", "")
    if not dest or not exp:
        print(f"{KO} config.yaml : renseigne email.destinataire et email.expediteur.")
        return False
    print(f"{OK} config.yaml charge : recap envoye de '{exp}' vers '{dest}'.")
    return True


def _check_password(config) -> str | None:
    pwd = _resolve_password(config)
    if not pwd:
        env_name = config.get("email.mot_de_passe_env", "VEILLE_SMTP_PASSWORD")
        fichier = config.get("email.mot_de_passe_fichier", "motdepasse-mail.txt")
        print(f"{KO} Mot de passe d'application INTROUVABLE.")
        print(f"        -> cree le fichier '{fichier}' (contenant le mot de passe")
        print(f"           d'application Google) ou la variable d'environnement {env_name}.")
        print("           Procedure : VEILLE-AUTOMATIQUE-HEBDO.md, etape 1.")
        return None
    print(f"{OK} Mot de passe d'application trouve ({len(pwd)} caracteres).")
    if len(pwd) != 16:
        print(f"{INFO} Un mot de passe d'application Google fait normalement 16 caracteres :")
        print("        verifie qu'il n'y a pas de texte en trop dans le fichier.")
    return pwd


def _check_imap(config, pwd: str) -> bool:
    hote = config.get("mail_alertes.imap_hote", "imap.gmail.com")
    port = int(config.get("mail_alertes.imap_port", 993) or 993)
    compte = config.get("mail_alertes.compte", "") or config.get("email.expediteur", "")
    dossier = config.get("mail_alertes.dossier", "INBOX")
    jours = int(config.get("mail_alertes.jours_recents", 14) or 14)
    try:
        M = imaplib.IMAP4_SSL(hote, port)
    except Exception as e:  # noqa: BLE001
        print(f"{KO} Connexion IMAP a {hote}:{port} impossible : {e}")
        print("        -> verifie la connexion internet / le pare-feu.")
        return False
    try:
        M.login(compte, pwd)
    except Exception as e:  # noqa: BLE001
        print(f"{KO} Identification IMAP refusee pour {compte} : {e}")
        print("        -> mot de passe d'application invalide ou IMAP desactive dans Gmail")
        print("           (parametres Gmail -> 'Transfert et POP/IMAP' -> activer IMAP).")
        return False
    print(f"{OK} Connexion IMAP reussie ({compte} sur {hote}).")
    ok = True
    try:
        name = dossier if dossier == "INBOX" else '"%s"' % dossier
        typ, _ = M.select(name, readonly=True)
        if typ != "OK":
            raise RuntimeError("dossier introuvable")
        since = (date.today() - timedelta(days=jours)).strftime("%d-%b-%Y")
        typ, data = M.search(None, "SINCE", since)
        nb = len(data[0].split()) if data and data[0] else 0
        print(f"{OK} Libelle '{dossier}' accessible : {nb} e-mail(s) sur les {jours} derniers jours.")
        if nb == 0:
            print(f"{INFO} Aucun e-mail recent dans '{dossier}' : normal si les plateformes")
            print("        n'ont rien envoye, sinon verifie le filtre Gmail (voir doc).")
    except Exception:  # noqa: BLE001
        print(f"{KO} Le libelle Gmail '{dossier}' est introuvable.")
        print("        -> cree-le dans Gmail (ou corrige mail_alertes.dossier dans config.yaml).")
        ok = False
    try:
        M.logout()
    except Exception:
        pass
    return ok


def _check_smtp(config, pwd: str) -> bool:
    hote = config.get("email.smtp_hote", "smtp.gmail.com")
    port = int(config.get("email.smtp_port", 587) or 587)
    securite = str(config.get("email.securite", "starttls")).lower()
    exp = config.get("email.expediteur", "")
    try:
        if securite == "ssl":
            with smtplib.SMTP_SSL(hote, port, context=ssl.create_default_context(), timeout=30) as s:
                s.login(exp, pwd)
        else:
            with smtplib.SMTP(hote, port, timeout=30) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                s.login(exp, pwd)
        print(f"{OK} Connexion SMTP reussie ({exp} sur {hote}:{port}) : l'envoi de mail fonctionne.")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"{KO} Identification SMTP refusee pour {exp}.")
        print("        -> c'est le MOT DE PASSE D'APPLICATION qu'il faut (pas celui du compte),")
        print("           et l'expediteur doit etre le compte qui a cree ce mot de passe.")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"{KO} Connexion SMTP impossible : {e}")
        return False


def _send_test(config, pwd: str) -> bool:
    dest = config.get("email.destinataire", "")
    exp = config.get("email.expediteur", "")
    sujet = f"[TEST] Veille AO - envoi de test du {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = exp
    msg["To"] = dest
    msg.set_content(
        "Ceci est un e-mail de TEST de l'outil de veille appels d'offres.\n"
        "Si tu le recois, l'envoi automatique fonctionne.\n"
        "(Pense a verifier le dossier SPAM si tu ne le vois pas en boite de reception.)"
    )
    ok, err = _smtp_send(config, msg, pwd)
    _log_send(sujet, dest, ok, err)
    if ok:
        print(f"{OK} E-mail de TEST envoye a {dest} : verifie ta boite (et le dossier spam).")
    else:
        print(f"{KO} E-mail de test NON parti : {err}")
    return ok


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Diagnostic de la veille (config, IMAP, SMTP)")
    parser.add_argument("--envoi-test", action="store_true", help="Envoyer aussi un e-mail de test")
    parser.add_argument("--config", default=None)
    args = parser.parse_args(argv)

    print("=" * 64)
    print(" DIAGNOSTIC - Veille appels d'offres")
    print("=" * 64)
    try:
        config = Config.load(args.config)
    except Exception as e:  # noqa: BLE001
        print(f"{KO} Impossible de lire config.yaml : {e}")
        return 1

    ok = _check_config(config)
    pwd = _check_password(config) if ok else None
    if not pwd:
        print("=" * 64)
        return 1
    imap_ok = _check_imap(config, pwd)
    smtp_ok = _check_smtp(config, pwd)
    test_ok = True
    if args.envoi_test and smtp_ok:
        test_ok = _send_test(config, pwd)

    print("-" * 64)
    if imap_ok and smtp_ok and test_ok:
        print(f"{OK} TOUT FONCTIONNE. La veille automatique peut tourner.")
        print("=" * 64)
        return 0
    print(f"{KO} Au moins un point est a corriger (voir messages ci-dessus).")
    print("=" * 64)
    return 1


if __name__ == "__main__":
    sys.exit(main())
