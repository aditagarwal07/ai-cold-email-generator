# PitchCraft AI — AI Cold Email & Pitch Generator

An IIT Patna Generative AI Capstone built with Python, Streamlit and the official
Google Gen AI SDK. The Version 2 MVP helps you **generate → review/edit → copy/download**
three distinct outreach strategies. It can also draft a short follow-up. It never sends email.

## Version safety

Develop Version 2 only on `capstone-v2`. Version 1 is preserved on `main` and at commit
`6458782a8b7735f13cb292841c001e96c27926ae`. Do not merge or deploy automatically.
The historical Version 1 webhook is intentionally absent from Version 2. If active,
rotate it: its old URL still exists in Git history. A separate V2 Community Cloud
app lets you keep a V1 deployment available during evaluation.

## Features

- Sender/offer/audience details, objective, optional recipient details and supported facts
- Five tones and three length limits (100 / 160 / 240 words)
- Value-first, problem-solution and permission-based email strategies
- Validated JSON with strategy, subject, body and CTA
- Separate draft tabs, editable subjects/bodies, word counts, selected-draft text exports
- Campaign-change warnings and blocked exports/follow-ups for stale drafts
- Short follow-ups tied to the selected edited email; no assumptions about engagement
- Safe error messages, request timeout, bounded input/output and per-session cooldown
- Secrets kept outside Git; Make.com future contract documented but delivery disabled

## Local setup (Python 3.12)

From your existing repository checkout:

```bash
git switch capstone-v2
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on macOS/Linux, or
`.venv\Scripts\Activate.ps1` in Windows PowerShell. Then:

```bash
python -m pip install -r requirements.txt
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace only
the placeholder API key with your own Google AI Studio key. The real file is ignored
by Git. Alternatively, provide `GEMINI_API_KEY` and optionally `GEMINI_MODEL` through
environment variables. A missing local secrets file is handled safely. Do not paste
credentials into chat, commit them, or include them in screenshots.

```bash
python -m streamlit run app.py
```

No database, external server, Node.js, or separate build step is required. Pinned
direct dependencies are tested together; transitive dependency versions can still change.

### Model choice

The default is `gemini-flash-latest`, the documented text-generation alias in the
[official Google Gen AI Python SDK](https://github.com/googleapis/python-genai#generate-content).
JSON generation follows its documented `response_json_schema` interface.
The alias can change its underlying model. For a repeatable capstone demonstration,
set `GEMINI_MODEL` to a supported explicit model ID available to your account after
checking [Google's model documentation](https://ai.google.dev/gemini-api/docs/models).
Model availability and free-tier quotas are account-dependent; the app does not silently
switch models or retry invalid responses. A present key is not a verified connection.

## Deploy on Streamlit Community Cloud

After reviewing the changes, run these commands from the repository. The first
command must print `capstone-v2`; stop if it prints another branch.

```bash
git branch --show-current
git add app.py README.md requirements.txt .gitignore .streamlit/config.toml .streamlit/secrets.toml.example core services tests docs
git commit -m "Build PitchCraft AI Version 2 MVP"
git push origin capstone-v2
```

1. Review and commit the V2 files on **capstone-v2**, then push that branch to GitHub.
   Do not push `.streamlit/secrets.toml` or merge into main.
2. Sign into [Streamlit Community Cloud](https://share.streamlit.io/) and create a **new app**.
3. Select your repository, branch **capstone-v2**, and entry point **app.py**.
4. In advanced settings select Python **3.12** and add the two settings from
   `.streamlit/secrets.toml.example`, using your real API key only in the Secrets editor.
5. Deploy. Community Cloud installs `requirements.txt` and uses `.streamlit/config.toml`.
6. Generate with an ordinary sample campaign. Confirm three distinct drafts, edits,
   downloads, stale-draft protection and a follow-up. Never use confidential test inputs.
7. If generation fails, check the sanitized message, model access and quota. Do not
   share logs that could contain secrets.

No Make.com secret is needed for this MVP. The initial public app has no email-delivery capability.

### Troubleshooting Gemini failures

After running this version, open the app's management console in Streamlit Community
Cloud and inspect logs for `pitchcraft_gemini_failure`. Match the `reference` field
with the support reference displayed in the app. Each record contains only the
exception class, numeric provider status, an allowlisted provider status name and
an error category. Raw provider messages, tracebacks, keys, request URLs and campaign
content are not logged by this diagnostic handler.

`invalid_api_key` means a recognized invalid/expired-key error; `authentication` or
`access_denied` points to credentials/restrictions/permissions. `model_unavailable`
points to the model or method. `quota`, `rate_limit`, or `quota_or_rate_limit` points
to usage limits; HTTP 429 alone cannot distinguish daily quota from request rate.
`temporary_service` identifies HTTP 5xx other than the timeout code 504. `timeout`
and `network` distinguish slow responses and connectivity problems. `invalid_request`
is a remaining HTTP 400; inspect model capabilities and account eligibility.
For non-provider failures, `provider_status_code=None` is expected.

## Tests

Tests use Python's standard `unittest` runner; no testing package is needed:

```bash
python -m unittest discover -s tests -v
python -m pip check
```

They exercise input validation, draft contracts, prompts, sanitized service errors,
request configuration, follow-ups and Streamlit session behavior using mocked Gemini.
Mocks do **not** prove live model availability, factual accuracy or quality. With a
configured key, manually test a real generation and follow-up before presenting or publishing.

## Architecture

- `app.py`: three-stage Streamlit UI and user-session state
- `core/models.py`: validated campaign/draft contracts, fingerprints and numeric-claim warnings
- `core/prompts.py`: factual constraints and distinct strategy instructions
- `services/settings.py`: secrets/environment configuration, with safe missing-file handling
- `services/gemini_service.py`: SDK calls, JSON validation, timeouts and safe errors
- `docs/MAKE_INTEGRATION.md`: future secure delivery design (inactive)
- `tests/`: service, validation and UI regression tests

## Accuracy, privacy and public-use limits

The app does not browse websites or verify user-supplied facts. Pain points are framed
as possibilities. Prompts prohibit invented results, relationships, achievements,
statistics and fake personalization. Numeric-claim warnings and human review provide
additional safeguards, **not a guarantee** that every claim is true. Drafts that are
structurally invalid, too long or excessively similar are rejected.

Inputs and edited emails used for follow-ups are sent to Google's Gemini service.
Review Google's data-use terms for your account/tier. Do not enter sensitive personal,
client or confidential business information. This app has no application database,
analytics tracker or cross-user draft cache. Drafts live in session state; a new session
can lose them. Clearing the session does not erase data already sent to the provider.

The 20-second cooldown is per session, not a global abuse-control or spending limit.
A public URL can consume your quota through new sessions. Configure provider quotas,
monitor use, and use Community Cloud access controls for a controlled demonstration
if necessary. Free service allowances can change; no paid service is required by
this code, but free access is not guaranteed. This MVP has no campaign database,
bulk outreach, scheduling, automatic delivery, or external fact-checking.
