"""Explicit provider routing: no automatic model or provider failover."""
from services import gemini_service, groq_service
from services.settings import Settings
from core.models import Campaign


def _service(provider: str):
    if provider == 'Groq':
        return groq_service
    if provider == 'Gemini':
        return gemini_service
    raise ValueError('Choose a supported AI provider.')


def generate_drafts(settings: Settings, campaign: Campaign, *, provider: str):
    return _service(provider).generate_drafts(settings, campaign)


def generate_follow_up(settings: Settings, campaign: Campaign, subject: str, body: str, *, provider: str):
    return _service(provider).generate_follow_up(settings, campaign, subject, body)
