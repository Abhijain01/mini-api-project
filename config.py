"""All settings live here. Nothing else in the project hard-codes a URL or a timeout."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Reads .env if it exists. Real environment variables (for example the ones
# Docker Compose sets) are never overridden.
load_dotenv()

VALID_LOG_LEVELS = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}


class ConfigError(RuntimeError):
    """A setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    countries_api_base: str
    frankfurter_api_base: str
    request_timeout: float
    database_url: str
    log_level: str


def _required(name: str, *, strip_slash: bool = False) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required setting: {name} (set it in .env)")
    return value.rstrip("/") if strip_slash else value


def _timeout(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ConfigError(f"Invalid setting {name}={raw!r}: must be a number") from None
    if value <= 0:
        raise ConfigError(f"Invalid setting {name}={raw!r}: must be greater than 0")
    return value


def _log_level(name: str, default: str) -> str:
    value = os.getenv(name, "").strip().upper() or default
    if value not in VALID_LOG_LEVELS:
        raise ConfigError(
            f"Invalid setting {name}={value!r}: must be one of {sorted(VALID_LOG_LEVELS)}"
        )
    return value


def load_settings() -> Settings:
    return Settings(
        countries_api_base=_required("COUNTRIES_API_BASE", strip_slash=True),
        frankfurter_api_base=_required("FRANKFURTER_API_BASE", strip_slash=True),
        request_timeout=_timeout("REQUEST_TIMEOUT_SECONDS", 5.0),
        database_url=_required("DATABASE_URL"),
        log_level=_log_level("LOG_LEVEL", "INFO"),
    )