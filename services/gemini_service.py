"""Bounded Gemini requests with validated JSON and safe public errors."""
import httpx
from google import genai
from google.genai import errors, types
from pydantic import ValidationError
from core.models import Campaign, DraftBatch, FollowUp, WORD_LIMITS, edited_email
from core.prompts import SYSTEM_INSTRUCTION, draft_prompt, follow_up_prompt
from services.settings import Settings


class GenerationError(Exception):
    """Contains only a message safe to show to the user."""


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return 'Gemini took too long to respond. Please wait briefly and try again.'
    if isinstance(exc, errors.APIError):
        code = exc.code
        if code in (401, 403):
            return 'Gemini access was denied. The app owner should check the API key and permissions.'
        if code == 400:
            return 'Gemini rejected the request. The app owner should check the API key and model configuration.'
        if code == 404:
            return 'The configured Gemini model is unavailable. Ask the app owner to check GEMINI_MODEL.'
        if code == 429:
            return 'The Gemini usage limit has been reached. Please try later; the app owner may need to check quota.'
        if code in (408, 504):
            return 'Gemini took too long to respond. Please try again later.'
        if code and code >= 500:
            return 'Gemini is temporarily unavailable. Please try again later.'
    if isinstance(exc, httpx.TransportError):
        return 'Could not reach Gemini. Please check connectivity and try again.'
    return 'Generation could not be completed. Please try again or contact the app owner.'


def _request(settings: Settings, prompt: str, schema):
    if not settings.api_key:
        raise GenerationError('Gemini is not configured. The app owner must add GEMINI_API_KEY in secrets.')
    try:
        # SDK timeout is milliseconds. Avoid retries that silently multiply quota usage.
        with genai.Client(
            api_key=settings.api_key,
            vertexai=False,
            http_options=types.HttpOptions(
                timeout=45000, retry_options=types.HttpRetryOptions(attempts=1)
            ),
        ) as client:
            response = client.models.generate_content(
                model=settings.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type='application/json',
                    response_json_schema=schema.model_json_schema(),
                    max_output_tokens=4096,
                    temperature=0.7,
                ),
            )
            text = response.text
    except Exception as exc:
        raise GenerationError(_safe_error(exc)) from None
    if not text or not text.strip():
        raise GenerationError('Gemini returned no usable text. The response may have been blocked; try revising your inputs.')
    try:
        return schema.model_validate_json(text)
    except (ValidationError, ValueError):
        raise GenerationError('Gemini returned incomplete, repetitive, or invalid drafts. Please generate again.') from None


def generate_drafts(settings: Settings, campaign: Campaign) -> DraftBatch:
    batch = _request(settings, draft_prompt(campaign), DraftBatch)
    for draft in batch.drafts:
        if len(draft.body.split()) > WORD_LIMITS[campaign.length]:
            raise GenerationError('Gemini exceeded the selected email length. Please generate again.')
        if draft.call_to_action not in draft.body:
            raise GenerationError('Gemini returned an inconsistent call to action. Please generate again.')
    return batch


def generate_follow_up(settings: Settings, campaign: Campaign, subject: str, body: str) -> FollowUp:
    subject, body = edited_email(subject, body)
    return _request(settings, follow_up_prompt(campaign, subject, body), FollowUp)
