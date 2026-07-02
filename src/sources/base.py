"""Utilitaires communs aux connecteurs de sources."""

from __future__ import annotations

import requests

# En-tete commun : certains serveurs publics refusent les requetes sans User-Agent.
HEADERS = {
    "User-Agent": "Veille-AO/1.0 (outil interne de veille appels d'offres)",
    "Accept": "application/json",
}

TIMEOUT = 30


def http_get(url: str, params: dict | None = None, headers: dict | None = None):
    """GET robuste : leve une exception en cas d'erreur, geree par l'appelant."""
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    resp = requests.get(url, params=params, headers=h, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def http_post_json(url: str, payload: dict, headers: dict | None = None):
    h = dict(HEADERS)
    h["Content-Type"] = "application/json"
    if headers:
        h.update(headers)
    resp = requests.post(url, json=payload, headers=h, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def http_post_form(url: str, data: dict, headers: dict | None = None):
    """POST d'un formulaire (application/x-www-form-urlencoded)."""
    h = dict(HEADERS)
    h["Accept"] = "text/html,application/xhtml+xml"
    h["Content-Type"] = "application/x-www-form-urlencoded"
    if headers:
        h.update(headers)
    resp = requests.post(url, data=data, headers=h, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp
