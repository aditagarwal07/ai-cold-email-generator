"""Read secrets safely without requiring a local secrets file."""
import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_MODEL = 'gemini-flash-latest'


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default='', repr=False)
    model: str = DEFAULT_MODEL


def load_settings(secrets: Mapping | None = None) -> Settings:
    def read(name: str, default: str = '') -> str:
        value = None
        if secrets is not None:
            try:
                value = secrets.get(name)
            except (FileNotFoundError, KeyError):
                pass
        value = value.strip() if isinstance(value, str) else ''
        if not value:
            value = os.environ.get(name, default)
        return value.strip() if isinstance(value, str) else default
    return Settings(api_key=read('GEMINI_API_KEY'), model=read('GEMINI_MODEL', DEFAULT_MODEL) or DEFAULT_MODEL)
