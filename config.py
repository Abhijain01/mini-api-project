"""All settings live here. Nothing else in the project hard-codes a URL or a timeout."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Reads .env if it exists. Real environment variables (for example from
# `docker run --env-file .env`) are never overridden.
load_dotenv()


class ConfigError(RuntimeError):
    """A setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    countries_api_base: str
    frankfurter_api_base: str
    request_timeout: float


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required setting: {name} (set it in .env)")
    return value.rstrip("/")


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


def load_settings() -> Settings:
    return Settings(
        countries_api_base=_required("COUNTRIES_API_BASE"),
        frankfurter_api_base=_required("FRANKFURTER_API_BASE"),
        request_timeout=_timeout("REQUEST_TIMEOUT_SECONDS", 5.0),
    )