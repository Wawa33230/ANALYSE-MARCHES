"""Chargement et acces a la configuration (config.yaml)."""

from __future__ import annotations

import os
import yaml


DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")


class Config:
    """Petit wrapper autour du dictionnaire YAML, avec acces par chemin pointe."""

    def __init__(self, data: dict):
        self.data = data or {}

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        path = path or DEFAULT_PATH
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(data)

    def get(self, dotted: str, default=None):
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    # Raccourcis pratiques -----------------------------------------------
    @property
    def scoring(self) -> dict:
        return self.data.get("scoring", {})

    @property
    def sources(self) -> dict:
        return self.data.get("sources", {})
