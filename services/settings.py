"""Read secrets safely without requiring a local secrets file."""
import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_MODEL = 'gemini-flash-latest'
DEFAULT_GROQ_MODEL = 'llama-3.3-70b-versatile'


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default='', repr=False)
    model: str = DEFAULT_MODEL
    fallback_model: str = ''
    diagnostics_enabled: bool = False
    groq_api_key: str = field(default='', repr=False)
    groq_model: str = DEFAULT_GROQ_MODEL


def load_settings(secrets: Mapping | None = None) -> Settings:
    def read(name: str, default: str = '', *, boolean: bool = False) -> str:
        value = None
        if secrets is not None:
            try:
                value = secrets.get(name)
            except (FileNotFoundError, KeyError):
                pass
        if boolean and isinstance(value, bool):
            return 'true' if value else 'false'
        value = value.strip() if isinstance(value, str) else ''
        if not value:
            value = os.environ.get(name, default)
        return value.strip() if isinstance(value, str) else default
    return Settings(api_key=read('GEMINI_API_KEY'), model=read('GEMINI_MODEL', DEFAULT_MODEL) or DEFAULT_MODEL,
                    fallback_model=read('GEMINI_FALLBACK_MODEL'),
                    diagnostics_enabled=read('ENABLE_GEMINI_DIAGNOSTICS', boolean=True).casefold() == 'true',
                    groq_api_key=read('GROQ_API_KEY'),
                    groq_model=read('GROQ_MODEL', DEFAULT_GROQ_MODEL) or DEFAULT_GROQ_MODEL)
