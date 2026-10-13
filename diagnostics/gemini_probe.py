"""Compare plain text, tiny JSON, and the real draft contract on one model."""
import argparse
from dataclasses import asdict, dataclass, replace
import json
from typing import Literal
from google.genai import types
from pydantic import BaseModel, ValidationError
from core.models import Campaign
from services.gemini_service import (
    ErrorDiagnosis, GenerationError, _failure, _generate_response, generate_drafts,
)
from services.settings import Settings, load_settings


class ProbeStatus(BaseModel):
    status: Literal['ok']


@dataclass(frozen=True)
class ProbeResult:
    probe: str
    success: bool
    provider_status_code: int | None
    category: str
    reference: str | None = None


def synthetic_campaign() -> Campaign:
    return Campaign(
        sender_name='Alex', sender_company='Example Studio',
        product='Reusable project planning templates', usp='Editable templates with clear sections',
        audience='Small project teams', pain_point='Planning tasks may feel disorganized',
        objective='Ask permission to share a sample template',
    )


def _text_probe(settings: Settings, *, structured: bool):
    config = types.GenerateContentConfig(temperature=0, max_output_tokens=1024)
    prompt = 'Reply with exactly PITCHCRAFT_OK.'
    if structured:
        prompt = 'Return an object with status equal to ok.'
        config.response_mime_type = 'application/json'
        config.response_json_schema = ProbeStatus.model_json_schema()
    response = _generate_response(settings, prompt, config, retry=False)
    text = response.text
    if not text or not text.strip():
        raise _failure(ErrorDiagnosis('empty_response', 'The synthetic probe returned no text.'))
    if structured:
        try:
            ProbeStatus.model_validate_json(text)
        except ValidationError as exc:
            raise _failure(ErrorDiagnosis('invalid_response', 'The synthetic JSON probe returned invalid output.'), exc) from None
    # Do not return or log generated text, even in this synthetic diagnostic.


def run_diagnostics(settings: Settings) -> list[ProbeResult]:
    """Three single-attempt requests on the explicitly selected model; no failover."""
    probes = [
        ('minimal_text', lambda: _text_probe(settings, structured=False)),
        ('minimal_json', lambda: _text_probe(settings, structured=True)),
        ('three_draft_schema', lambda: generate_drafts(settings, synthetic_campaign(), retry=False)),
    ]
    results = []
    for name, operation in probes:
        try:
            operation()
        except GenerationError as exc:
            results.append(ProbeResult(name, False, exc.status_code, exc.category, exc.reference_id))
        except Exception as exc:
            failure = _failure(ErrorDiagnosis('diagnostic_error', 'The synthetic diagnostic could not complete.'), exc)
            results.append(ProbeResult(name, False, None, failure.category, failure.reference_id))
        else:
            results.append(ProbeResult(name, True, 200, 'success'))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description='Run three synthetic Gemini probes without printing credentials or responses.')
    parser.add_argument('--model-role', choices=['primary', 'alternate'], default='primary')
    args = parser.parse_args()
    try:
        import streamlit as st
        settings = load_settings(st.secrets)
        if not settings.api_key:
            print(json.dumps({'error': 'missing_api_key'}))
            return 2
        if args.model_role == 'alternate':
            if not settings.fallback_model:
                print(json.dumps({'error': 'alternate_model_not_configured'}))
                return 2
            settings = replace(settings, model=settings.fallback_model)
        results = run_diagnostics(settings)
        print(json.dumps([asdict(result) for result in results], indent=2))
        return 0 if all(result.success for result in results) else 1
    except Exception:
        print(json.dumps({'error': 'diagnostic_setup_failed'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
