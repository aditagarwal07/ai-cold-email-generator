"""Provider-neutral diagnostics containing only safe public information."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorDiagnosis:
    category: str
    message: str
    status_code: int | None = None
    provider_status: str = 'UNKNOWN'


class GenerationError(Exception):
    """A sanitized message and safe support fields; never a raw provider error."""
    def __init__(self, message: str, *, category: str = 'unknown', reference_id: str | None = None,
                 status_code: int | None = None, provider_status: str = 'UNKNOWN'):
        super().__init__(message)
        self.category = category
        self.reference_id = reference_id
        self.status_code = status_code
        self.provider_status = provider_status
