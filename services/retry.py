"""Small retry limits and safe parsing of provider-requested wait times."""
import math
import random
import time
from email.utils import parsedate_to_datetime
from google.genai import errors

MAX_ATTEMPTS = 3
MAX_TOTAL_WAIT_SECONDS = 6.0
REQUEST_BUDGET_SECONDS = 60.0
MAX_REQUEST_TIMEOUT_MS = 45000
RETRYABLE_CODES = {500, 502, 503, 429}


def retry_after_seconds(exc: Exception) -> float | None:
    """Read Retry-After and Google RetryInfo without emitting their raw contents."""
    waits = []
    response = getattr(exc, 'response', None)
    if response is not None:
        raw = response.headers.get('Retry-After')
        if isinstance(raw, str):
            try:
                value = float(raw)
            except ValueError:
                try:
                    date = parsedate_to_datetime(raw)
                    value = date.timestamp() - time.time() if date.tzinfo is not None else math.nan
                except (ValueError, TypeError, OverflowError):
                    value = math.nan
            if math.isfinite(value) and value >= 0:
                waits.append(value)
    payload = getattr(exc, 'details', None)
    if isinstance(payload, dict):
        error = payload.get('error', payload)
        details = error.get('details', []) if isinstance(error, dict) else []
        if isinstance(details, list):
            for item in details:
                if not isinstance(item, dict) or item.get('@type') != 'type.googleapis.com/google.rpc.RetryInfo':
                    continue
                raw = item.get('retryDelay')
                if isinstance(raw, str) and raw.endswith('s'):
                    try:
                        value = float(raw[:-1])
                    except ValueError:
                        continue
                    if math.isfinite(value) and value >= 0:
                        waits.append(value)
    return max(waits) if waits else None


def retry_delay(exc: Exception, attempt: int, waited: float, remaining: float, *, status_code: int | None = None) -> float | None:
    """Return an allowed delay, or None to stop. Never shorten a provider wait."""
    code = exc.code if isinstance(exc, errors.APIError) else status_code
    if code not in RETRYABLE_CODES or attempt >= MAX_ATTEMPTS:
        return None
    ceiling = min(4.0, 2.0 ** (attempt - 1))
    delay = random.uniform(ceiling / 2, ceiling)  # bounded exponential backoff with equal jitter
    provider_wait = retry_after_seconds(exc)
    if provider_wait is not None:
        delay = max(delay, provider_wait)
    if delay > MAX_TOTAL_WAIT_SECONDS - waited or delay >= remaining:
        return None
    return delay
