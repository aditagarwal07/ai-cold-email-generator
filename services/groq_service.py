"""Official Groq SDK, JSON mode, shared draft contracts and safe failures."""
import json
import logging
import time
import uuid
import groq
from pydantic import ValidationError
from core.models import Campaign, DraftBatch, FollowUp, WORD_LIMITS, edited_email
from core.prompts import SYSTEM_INSTRUCTION, draft_prompt, follow_up_prompt
from services.errors import ErrorDiagnosis, GenerationError
from services.retry import MAX_ATTEMPTS, MAX_REQUEST_TIMEOUT_MS, REQUEST_BUDGET_SECONDS, retry_delay
from services.settings import Settings

logger = logging.getLogger(__name__)


def _diagnose_error(exc: Exception) -> ErrorDiagnosis:
    if isinstance(exc, (groq.APITimeoutError, TimeoutError)):
        return ErrorDiagnosis('timeout', 'Groq took too long to respond. Please try again later.')
    if isinstance(exc, groq.APIConnectionError):
        return ErrorDiagnosis('network', 'Could not reach Groq. Please check connectivity and try again.')
    if isinstance(exc, groq.APIStatusError):
        code = exc.status_code if type(exc.status_code) is int and 100 <= exc.status_code <= 599 else None
        body = exc.body if isinstance(exc.body, dict) else {}
        detail = body.get('error', body)
        reason = detail.get('code') if isinstance(detail, dict) else None
        def result(category, message):
            return ErrorDiagnosis(category, message, code)
        if code == 401:
            return result('authentication', 'Groq could not authenticate this app. The app owner should check GROQ_API_KEY in Streamlit Cloud Secrets.')
        if code == 403:
            return result('access_denied', 'Groq access is denied. The app owner should check account permissions and model access.')
        if code == 404 or (code == 400 and reason in ('model_not_found', 'model_decommissioned')):
            return result('model_unavailable', 'The configured Groq model is unavailable. The app owner should check GROQ_MODEL and model access.')
        if code == 429:
            return result('quota_or_rate_limit', 'A Groq quota or rate limit was reached. Please try later; the app owner should check usage and limits.')
        if code in (408, 504):
            return result('timeout', 'Groq took too long to respond. Please try again later.')
        if code is not None and code >= 500:
            return result('temporary_service', 'Groq reported a temporary service failure. Please try again later.')
        if code == 400 and reason == 'json_validate_failed':
            return result('invalid_response', 'Groq could not produce valid JSON. Please generate again or ask the app owner to check model compatibility.')
        if code == 400:
            return result('invalid_request', 'Groq rejected the request. The app owner should check GROQ_MODEL and JSON-mode support.')
        return result('provider_error', 'Groq could not complete the request. Ask the app owner to check the support reference in Cloud logs.')
    return ErrorDiagnosis('unexpected', 'Generation could not be completed. Please try again or contact the app owner.')


def _failure(diagnosis: ErrorDiagnosis, exc: Exception | None = None, *, reference: str | None = None):
    reference = reference or uuid.uuid4().hex[:12]
    logger.warning('pitchcraft_groq_failure reference=%s exception_type=%s provider_status_code=%s category=%s',
                   reference, type(exc).__name__ if exc is not None else 'None', diagnosis.status_code, diagnosis.category)
    return GenerationError(diagnosis.message, category=diagnosis.category, reference_id=reference,
                           status_code=diagnosis.status_code)


def _request(settings: Settings, prompt: str, schema, *, retry: bool = True):
    if not settings.groq_api_key:
        raise _failure(ErrorDiagnosis('configuration', 'Groq is not configured. The app owner must add GROQ_API_KEY in secrets.'))
    reference = uuid.uuid4().hex[:12]
    started = time.monotonic()
    waited = 0.0
    response = None
    # JSON mode guarantees JSON syntax, not schema conformance. Validate locally below.
    system = SYSTEM_INSTRUCTION + '\nReturn a JSON object matching this schema exactly:\n' + json.dumps(schema.model_json_schema())
    try:
        with groq.Groq(api_key=settings.groq_api_key, max_retries=0, timeout=MAX_REQUEST_TIMEOUT_MS / 1000) as client:
            for attempt in range(1, (MAX_ATTEMPTS if retry else 1) + 1):
                remaining = REQUEST_BUDGET_SECONDS - (time.monotonic() - started)
                if remaining <= 0:
                    raise _failure(ErrorDiagnosis('timeout', 'The Groq request time budget was reached. Please try again later.'), reference=reference)
                try:
                    response = client.chat.completions.create(
                        model=settings.groq_model,
                        messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}],
                        response_format={'type': 'json_object'}, max_completion_tokens=4096, temperature=0.7,
                        timeout=min(MAX_REQUEST_TIMEOUT_MS / 1000, remaining),
                    )
                except Exception as exc:
                    diagnosis = _diagnose_error(exc)
                    remaining = REQUEST_BUDGET_SECONDS - (time.monotonic() - started)
                    delay = retry_delay(exc, attempt, waited, remaining, status_code=diagnosis.status_code) if retry else None
                    if delay is None:
                        raise _failure(diagnosis, exc, reference=reference) from None
                    logger.warning('pitchcraft_groq_retry reference=%s exception_type=%s provider_status_code=%s category=%s attempt=%s delay_seconds=%.3f',
                                   reference, type(exc).__name__, diagnosis.status_code, diagnosis.category, attempt, delay)
                    time.sleep(delay)
                    waited += delay
                    continue
                if attempt > 1:
                    logger.warning('pitchcraft_groq_recovered reference=%s attempt=%s', reference, attempt)
                break
    except GenerationError:
        raise
    except Exception as exc:
        raise _failure(_diagnose_error(exc), exc, reference=reference) from None
    try:
        choice = response.choices[0] if response.choices else None
        if choice is not None and choice.finish_reason == 'length':
            raise _failure(ErrorDiagnosis('output_truncated', 'Groq reached the output limit before finishing. Please try a shorter email length.'), reference=reference)
        text = choice.message.content if choice is not None else None
        if not isinstance(text, str) or not text.strip():
            raise _failure(ErrorDiagnosis('empty_response', 'Groq returned no usable text. Please revise your inputs and try again.'), reference=reference)
        return schema.model_validate_json(text)
    except GenerationError:
        raise
    except (ValidationError, ValueError) as exc:
        raise _failure(ErrorDiagnosis('invalid_response', 'Groq returned incomplete, repetitive, or invalid drafts. Please generate again.'), exc, reference=reference) from None
    except Exception as exc:
        raise _failure(ErrorDiagnosis('invalid_response', 'Groq returned an unexpected response. Please generate again.'), exc, reference=reference) from None


def generate_drafts(settings: Settings, campaign: Campaign, *, retry: bool = True) -> DraftBatch:
    batch = _request(settings, draft_prompt(campaign), DraftBatch, retry=retry)
    for draft in batch.drafts:
        if len(draft.body.split()) > WORD_LIMITS[campaign.length]:
            raise _failure(ErrorDiagnosis('output_length', 'Groq exceeded the selected email length. Please generate again.'))
        if draft.call_to_action not in draft.body:
            raise _failure(ErrorDiagnosis('output_contract', 'Groq returned an inconsistent call to action. Please generate again.'))
    return batch


def generate_follow_up(settings: Settings, campaign: Campaign, subject: str, body: str) -> FollowUp:
    subject, body = edited_email(subject, body)
    return _request(settings, follow_up_prompt(campaign, subject, body), FollowUp)
