"""Bounded Gemini requests with validated JSON and safe public errors."""
import logging
import time
import uuid
import httpx
from google import genai
from google.genai import errors, types
from pydantic import ValidationError
from core.models import Campaign, DraftBatch, FollowUp, WORD_LIMITS, edited_email
from core.prompts import SYSTEM_INSTRUCTION, draft_prompt, follow_up_prompt
from services.settings import Settings
from services.errors import ErrorDiagnosis, GenerationError
from services.retry import MAX_ATTEMPTS, MAX_REQUEST_TIMEOUT_MS, REQUEST_BUDGET_SECONDS, retry_delay

logger = logging.getLogger(__name__)


def _provider_reasons(exc: errors.APIError) -> set[str]:
    """Inspect structured reasons locally; never log provider details or messages."""
    payload = exc.details
    if not isinstance(payload, dict):
        return set()
    error = payload.get('error', payload)
    if not isinstance(error, dict):
        return set()
    details = error.get('details', [])
    if not isinstance(details, list):
        return set()
    return {item['reason'] for item in details
            if isinstance(item, dict) and isinstance(item.get('reason'), str)}


def _diagnose_error(exc: Exception) -> ErrorDiagnosis:
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return ErrorDiagnosis('timeout', 'Gemini took too long to respond. Please wait briefly and try again.')
    if isinstance(exc, errors.APIError):
        code = exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else None
        # Only allow known enum values into logs. Provider strings may contain sensitive data.
        known_statuses = {'INVALID_ARGUMENT', 'UNAUTHENTICATED', 'PERMISSION_DENIED', 'NOT_FOUND',
                          'RESOURCE_EXHAUSTED', 'INTERNAL', 'UNAVAILABLE', 'DEADLINE_EXCEEDED',
                          'FAILED_PRECONDITION', 'CANCELLED', 'UNKNOWN', 'UNIMPLEMENTED'}
        status = exc.status if isinstance(exc.status, str) and exc.status in known_statuses else 'UNKNOWN'
        reasons = _provider_reasons(exc)
        # Some responses omit ErrorInfo. These fixed phrases are inspected, never recorded.
        message = exc.message.casefold() if isinstance(exc.message, str) else ''

        def result(category, text):
            return ErrorDiagnosis(category, text, code, status)

        if code in (408, 504):
            return result('timeout', 'Gemini took too long to respond. Please try again later.')
        if code is not None and code >= 500:
            return result('temporary_service', 'Gemini reported a temporary service failure. Please try again later. If it persists, the app owner should check Google’s service status and Cloud logs.')
        if code in (400, 401, 403) and (
            reasons & {'API_KEY_INVALID', 'API_KEY_EXPIRED'}
            or 'api key not valid' in message or 'api key expired' in message
        ):
            return result('invalid_api_key', 'The Gemini API key is invalid or expired. The app owner should replace GEMINI_API_KEY in Streamlit Cloud Secrets.')
        if code == 401:
            return result('authentication', 'Gemini could not authenticate this app. The app owner should check GEMINI_API_KEY in Streamlit Cloud Secrets.')
        if code == 403:
            return result('access_denied', 'Gemini access is denied. The app owner should check API key restrictions, project permissions, and whether the Generative Language API is enabled.')
        if code == 404 or (code == 400 and (
            reasons & {'MODEL_NOT_FOUND', 'MODEL_NOT_SUPPORTED'}
            or 'not supported for generatecontent' in message
            or ('model' in message and 'not found for api version' in message)
        )):
            return result('model_unavailable', 'The configured Gemini model is unavailable or does not support this request. The app owner should check GEMINI_MODEL and model access in Google AI Studio.')
        if code == 429:
            if reasons & {'RATE_LIMIT_EXCEEDED'}:
                return result('rate_limit', 'Gemini’s request rate limit was reached. Please wait before trying again.')
            if reasons & {'QUOTA_EXCEEDED', 'RESOURCE_QUOTA_EXCEEDED'}:
                return result('quota', 'The Gemini quota has been exhausted. The app owner should check project usage and quota; waiting briefly may not resolve it.')
            return result('quota_or_rate_limit', 'A Gemini quota or rate limit was reached. Please try later; the app owner should check project usage and quota.')
        if code == 400:
            return result('invalid_request', 'Gemini rejected the request configuration. The app owner should check model capabilities, structured-output support, and account or regional eligibility in Cloud logs.')
        return result('provider_error', 'Gemini rejected the request. The app owner should check the diagnostic reference in Streamlit Cloud logs.')
    if isinstance(exc, httpx.TransportError):
        return ErrorDiagnosis('network', 'Could not reach Gemini. Please check connectivity and try again.')
    return ErrorDiagnosis('unexpected', 'Generation could not be completed. Please try again or contact the app owner.')


def _failure(diagnosis: ErrorDiagnosis, exc: Exception | None = None, *, reference_id: str | None = None) -> GenerationError:
    reference = reference_id or uuid.uuid4().hex[:12]
    # Do not use str(exc), repr(exc), exc_info, traceback, URLs, settings, or prompts here.
    logger.warning(
        'pitchcraft_gemini_failure reference=%s exception_type=%s provider_status_code=%s provider_status=%s category=%s',
        reference, type(exc).__name__ if exc is not None else 'None',
        diagnosis.status_code, diagnosis.provider_status, diagnosis.category,
    )
    return GenerationError(diagnosis.message, category=diagnosis.category, reference_id=reference,
                           status_code=diagnosis.status_code, provider_status=diagnosis.provider_status)


def _generate_response(settings: Settings, prompt: str, config: types.GenerateContentConfig, *, retry: bool = True):
    """One model only. SDK retries are off; application retries have explicit limits."""
    if not settings.api_key:
        raise _failure(ErrorDiagnosis('configuration', 'Gemini is not configured. The app owner must add GEMINI_API_KEY in secrets.'))
    reference = uuid.uuid4().hex[:12]
    started = time.monotonic()
    waited = 0.0
    try:
        with genai.Client(
            api_key=settings.api_key,
            vertexai=False,
            http_options=types.HttpOptions(
                timeout=MAX_REQUEST_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1)
            ),
        ) as client:
            for attempt in range(1, (MAX_ATTEMPTS if retry else 1) + 1):
                remaining = REQUEST_BUDGET_SECONDS - (time.monotonic() - started)
                if remaining <= 0:
                    raise _failure(ErrorDiagnosis('timeout', 'The Gemini request time budget was reached. Please try again later.'), reference_id=reference)
                attempt_config = config.model_copy(update={'http_options': types.HttpOptions(
                    timeout=min(MAX_REQUEST_TIMEOUT_MS, max(1, int(remaining * 1000))),
                    retry_options=types.HttpRetryOptions(attempts=1),
                )})
                try:
                    response = client.models.generate_content(model=settings.model, contents=prompt, config=attempt_config)
                except Exception as exc:
                    diagnosis = _diagnose_error(exc)
                    remaining = REQUEST_BUDGET_SECONDS - (time.monotonic() - started)
                    delay = retry_delay(exc, attempt, waited, remaining) if retry else None
                    if delay is None:
                        raise _failure(diagnosis, exc, reference_id=reference) from None
                    logger.warning(
                        'pitchcraft_gemini_retry reference=%s exception_type=%s provider_status_code=%s provider_status=%s category=%s attempt=%s delay_seconds=%.3f',
                        reference, type(exc).__name__, diagnosis.status_code, diagnosis.provider_status,
                        diagnosis.category, attempt, delay,
                    )
                    time.sleep(delay)
                    waited += delay
                    continue
                if attempt > 1:
                    logger.warning('pitchcraft_gemini_recovered reference=%s attempt=%s', reference, attempt)
                return response
    except GenerationError:
        raise
    except Exception as exc:
        raise _failure(_diagnose_error(exc), exc, reference_id=reference) from None


def _request(settings: Settings, prompt: str, schema, *, retry: bool = True):
    response = _generate_response(settings, prompt, types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type='application/json',
        response_json_schema=schema.model_json_schema(),
        max_output_tokens=4096,
        temperature=0.7,
    ), retry=retry)
    try:
        text = response.text
    except Exception as exc:
        raise _failure(_diagnose_error(exc), exc) from None
    if not text or not text.strip():
        raise _failure(ErrorDiagnosis('empty_response', 'Gemini returned no usable text. The response may have been blocked; try revising your inputs.'))
    try:
        return schema.model_validate_json(text)
    except (ValidationError, ValueError) as exc:
        raise _failure(ErrorDiagnosis('invalid_response', 'Gemini returned incomplete, repetitive, or invalid drafts. Please generate again.'), exc) from None


def generate_drafts(settings: Settings, campaign: Campaign, *, retry: bool = True) -> DraftBatch:
    batch = _request(settings, draft_prompt(campaign), DraftBatch, retry=retry)
    for draft in batch.drafts:
        if len(draft.body.split()) > WORD_LIMITS[campaign.length]:
            raise _failure(ErrorDiagnosis('output_length', 'Gemini exceeded the selected email length. Please generate again.'))
        if draft.call_to_action not in draft.body:
            raise _failure(ErrorDiagnosis('output_contract', 'Gemini returned an inconsistent call to action. Please generate again.'))
    return batch


def generate_follow_up(settings: Settings, campaign: Campaign, subject: str, body: str) -> FollowUp:
    subject, body = edited_email(subject, body)
    return _request(settings, follow_up_prompt(campaign, subject, body), FollowUp)
