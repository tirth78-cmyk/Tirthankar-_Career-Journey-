"""Load and manage agent configuration from YAML."""

import os
from pathlib import Path

import yaml


DEFAULT_CONFIG = {
    "preferences": {
        "roles": ["Software Engineer"],
        "locations": ["Remote"],
        "experience_years": 3,
        "min_salary": 0,
        "job_type": "full-time",
    },
    "portals": {
        "linkedin": {"enabled": True, "email": "", "password": ""},
        "naukri": {"enabled": True, "email": "", "password": ""},
        "iimjobs": {"enabled": True, "email": "", "password": ""},
    },
    "matching": {
        "min_score": 0.45,
        "top_k": 20,
        "skill_weight": 0.4,
        "experience_weight": 0.3,
        "title_weight": 0.3,
    },
    "application": {
        "cover_letter_template": "templates/cover_letter.txt",
        "auto_apply": False,
        "daily_apply_limit": 25,
    },
    "storage": {
        "db_path": "data/jobs.json",
        "resumes_dir": "data/resumes/",
    },
}


class Settings:
    """Loads configuration from config.yaml with defaults fallback."""

    def __init__(self, config_path: str = "config.yaml"):
        self._config = dict(DEFAULT_CONFIG)
        self._config_path = Path(config_path)

        if self._config_path.exists():
            with open(self._config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
            self._deep_merge(self._config, user_config)

    def _deep_merge(self, base: dict, override: dict):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    @property
    def preferences(self) -> dict:
        return self._config["preferences"]

    @property
    def portals(self) -> dict:
        return self._config["portals"]

    @property
    def matching(self) -> dict:
        return self._config["matching"]

    @property
    def application(self) -> dict:
        return self._config["application"]

    @property
    def storage(self) -> dict:
        return self._config["storage"]

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
