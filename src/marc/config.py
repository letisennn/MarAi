"""Runtime configuration and logging.

Settings come from environment (prefix ``MARC_``, optionally a ``.env`` file);
YAML config files under ``config/`` hold the universe and target definitions.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MARC_", env_file=".env", extra="ignore")

    db_path: Path = Path("data/marc.duckdb")
    data_dir: Path = Path("data")
    base_currency: str = "SEK"
    log_level: str = "INFO"

    def _abs(self, p: Path) -> Path:
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def abs_db_path(self) -> Path:
        return self._abs(self.db_path)

    @property
    def abs_data_dir(self) -> Path:
        return self._abs(self.data_dir)

    @property
    def raw_dir(self) -> Path:
        return self.abs_data_dir / "raw"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def load_yaml(rel: str) -> dict[str, Any]:
    path = project_path(rel)
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache
def universe_config() -> dict[str, Any]:
    return load_yaml("config/universe.yml")


@lru_cache
def targets_config() -> dict[str, Any]:
    return load_yaml("config/targets.yml")


@lru_cache
def score_config() -> dict[str, Any]:
    """Preliminary composite-score weights. Hand-set, unvalidated — see CLAUDE.md rule 1."""
    return load_yaml("config/score.yml")


_LOGGING_READY = False


def setup_logging(level: str | None = None) -> None:
    global _LOGGING_READY
    if _LOGGING_READY:
        return
    logging.basicConfig(
        level=(level or get_settings().log_level).upper(),
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    _LOGGING_READY = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
