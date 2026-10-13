"""Owner-run Groq model access and JSON-mode check using synthetic data only."""
import json
import groq
from diagnostics.gemini_probe import synthetic_campaign
from services.errors import ErrorDiagnosis, GenerationError
from services.groq_service import _diagnose_error, _failure, generate_drafts
from services.settings import load_settings


def main() -> int:
    try:
        import streamlit as st
        settings = load_settings(st.secrets)
        if not settings.groq_api_key:
            print(json.dumps({'error': 'missing_groq_api_key'}))
            return 2
        try:
            with groq.Groq(api_key=settings.groq_api_key, max_retries=0, timeout=15) as client:
                model = client.models.retrieve(settings.groq_model)
            if model.id != settings.groq_model or getattr(model, 'active', True) is False:
                raise _failure(ErrorDiagnosis('model_unavailable', 'The configured Groq model is not available.'))
        except GenerationError:
            raise
        except Exception as exc:
            raise _failure(_diagnose_error(exc), exc) from None
        generate_drafts(settings, synthetic_campaign(), retry=False)
        print(json.dumps({'model_available': True, 'validated_three_draft_json': True}))
        return 0
    except GenerationError as exc:
        print(json.dumps({'category': exc.category, 'provider_status_code': exc.status_code, 'reference': exc.reference_id}))
        return 1
    except Exception:
        print(json.dumps({'error': 'diagnostic_setup_failed'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
