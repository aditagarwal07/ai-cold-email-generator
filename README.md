# PitchCraft AI — AI Cold Email & Pitch Generator

An IIT Patna Generative AI Capstone built with Python, Streamlit and the official
Groq and Google Gen AI SDKs. The Version 2 MVP helps you **generate → review/edit → copy/download**
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
- Safe error messages, bounded transient-error retries, request timeout and per-session cooldown
- Opt-in synthetic diagnostics and explicit alternate-model selection
- Explicit **AI Provider** selection: Groq by default, with Gemini retained
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
the Groq placeholder with your Groq key. Add a Gemini key only if you want to use
Gemini, and remove unused placeholder credentials. The real file is ignored by Git.
Alternatively, provide `GROQ_API_KEY` and optionally `GROQ_MODEL` through environment
variables; Gemini uses `GEMINI_API_KEY` and `GEMINI_MODEL`. A missing local secrets
file is handled safely. Do not paste
credentials into chat, commit them, or include them in screenshots.

```bash
python -m streamlit run app.py
```

The saved configuration disables file watching for deployed reliability. Buttons,
edits and normal Streamlit reruns still work. During local development, enable
automatic source reload explicitly:

```bash
python -m streamlit run app.py --server.fileWatcherType auto
```

No database, external server, Node.js, or separate build step is required. Pinned
direct dependencies are tested together; transitive dependency versions can still change.

### Provider and model choice

The sidebar **AI Provider** dropdown defaults to **Groq**, even if only a Gemini
key is present. Selecting a provider is explicit; errors never switch providers.
Each provider checks its own credential. Editing, downloads, follow-ups, word limits,
three strategy labels, stale-draft protection and factual safeguards work with both.
Changing the provider or model pauses exports/follow-ups until you regenerate or
restore the original selection. Drafts show which provider generated them.

Groq uses `GROQ_MODEL = "llama-3.3-70b-versatile"` by default. The ID is listed in
the [official Groq SDK request types](https://github.com/groq/groq-python/blob/main/src/groq/types/chat/completion_create_params.py).
We use `response_format={"type":"json_object"}`, supported by the SDK and shown
in Groq's JSON-mode cookbook. We do not assume this Llama model supports strict
`json_schema` mode: the schema is included in the system instructions, then output
is validated locally with the same Pydantic contracts as Gemini. JSON mode guarantees
JSON syntax, not the required shape or factual accuracy. Model availability for your
account must still be checked live; a documented ID is not proof of current access.

For an owner-run live access/compatibility check with secure local credentials:

```bash
python -m diagnostics.groq_probe
```

This retrieves the configured model's metadata, then runs one synthetic three-draft
JSON generation with validation. It prints only safe success flags or error category,
status and reference—never the key, raw response, model metadata or synthetic content.
SDK and generation retries are disabled for this diagnostic. It can consume quota.
Exit codes are 0 success, 1 provider/output failure, 2 missing configuration/setup error.
No live API success is claimed by the mocked automated tests.

Gemini's default remains `gemini-flash-latest`, the documented text-generation alias in the
[official Google Gen AI Python SDK](https://github.com/googleapis/python-genai#generate-content).
JSON generation follows its documented `response_json_schema` interface.
The alias can change its underlying model. For a repeatable capstone demonstration,
set `GEMINI_MODEL` to a supported explicit model ID available to your account after
checking [Google's model documentation](https://ai.google.dev/gemini-api/docs/models).
Model availability and free-tier quotas are account-dependent; the app does not silently
switch models or retry invalid responses. A present key is not a verified connection.

An optional `GEMINI_FALLBACK_MODEL` enables a sidebar **Model selection** control.
Google's [official Models cookbook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Models.ipynb)
lists `gemini-flash-lite-latest`, a lighter alternative to try after confirming access
and structured-output support for your account. Set that ID only if you choose to
evaluate it. The default alternate setting is blank: no model change occurs unless
you configure an alternate and explicitly select it. Failed requests never switch
models or providers. Both choices use the same three-draft schema and factual rules.
Changing selection marks existing drafts stale until you regenerate or restore it.

## Deploy on Streamlit Community Cloud

After reviewing the changes, run these commands from the repository. The first
command must print `capstone-v2`; stop if it prints another branch.

```bash
git branch --show-current
git add app.py README.md requirements.txt .gitignore .streamlit/config.toml .streamlit/secrets.toml.example core services tests docs diagnostics
git commit -m "Build PitchCraft AI Version 2 MVP"
git push origin capstone-v2
```

1. Review and commit the V2 files on **capstone-v2**, then push that branch to GitHub.
   Do not push `.streamlit/secrets.toml` or merge into main.
2. Sign into [Streamlit Community Cloud](https://share.streamlit.io/) and create a **new app**.
3. Select your repository, branch **capstone-v2**, and entry point **app.py**.
4. In advanced settings select Python **3.12** and add the required settings from
   `.streamlit/secrets.toml.example`, using your real API key only in the Secrets editor.
   For the default provider, set `GROQ_API_KEY` and `GROQ_MODEL = "llama-3.3-70b-versatile"`.
   Gemini settings are optional unless you select Gemini. Do not include unused placeholder keys.
5. Deploy. Community Cloud installs `requirements.txt` and uses `.streamlit/config.toml`.
6. Generate with an ordinary sample campaign. Confirm three distinct drafts, edits,
   downloads, stale-draft protection and a follow-up. Never use confidential test inputs.
7. If generation fails, check the sanitized message, model access and quota. Do not
   share logs that could contain secrets.

No Make.com secret is needed for this MVP. The initial public app has no email-delivery capability.

### Groq troubleshooting

Search Cloud logs for `pitchcraft_groq_failure`, `pitchcraft_groq_retry`, or
`pitchcraft_groq_recovered`. The safe reference, exception type, numeric status,
category, retry attempt and delay identify failures without keys, campaign content,
request URLs, raw provider bodies or tracebacks. Authentication (401), permissions
(403), unavailable models (404 or recognized decommissioning errors), quota/rate
limits (429), server failures and invalid outputs have distinct messages.

Groq shares the bounded retry policy below: at most three attempts, up to six seconds
of total backoff, provider `Retry-After` respected, a 60-second between-attempt budget
and at most 45-second per-attempt transport timeout. The Groq SDK's own retries are
disabled. Authentication, malformed JSON, invalid draft contracts and truncation
are not automatically retried. Both providers retain the same human factual review.

### Deployment runtime and import troubleshooting

Use Python **3.12** as the recommended deployment baseline. Select it in Community
Cloud's **Advanced settings** when creating/redeploying the app. `.devcontainer`
configures Codespaces/local containers only; it does not select Cloud's Python.
The container now uses 3.12 to match the recommended workflow. Do not assume that
a `.python-version` or `runtime.txt` file will change a deployed Cloud runtime.

Confirm the deployed branch is `capstone-v2`, entry point is `app.py`, the install
log matches `requirements.txt`, and startup logs show the intended Python version.
Both `core` and `services` are normal packages with tracked `__init__.py` files.
Do not work around import errors by deleting `sys.modules` entries or changing
package names without evidence. A `KeyError` involving a module name is different
from `ModuleNotFoundError`: it can indicate module-cache/reload interference.
The saved `server.fileWatcherType = "none"` disables Streamlit's source-file watcher
and avoids its file-triggered module eviction; normal UI reruns remain enabled.
Restart the deployed app after applying this config and verify the effective setting
is not overridden by `STREAMLIT_SERVER_FILE_WATCHER_TYPE` or a launch flag.

Python 3.14 is not proven incompatible by these errors alone. Capture the full
traceback, deployed Python/Streamlit versions, and whether errors coincide with
source updates or a reboot. Investigate Gemini failures independently using their
diagnostic reference; an import failure alone does not establish an API failure.

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

### Bounded retries

Generation and follow-ups retry HTTP **500, 502, 503 and 429** only, with a maximum
of **three attempts total** (two retries). SDK retries are disabled to avoid multiplying
attempts. Exponential backoff uses jitter (0.5–1 seconds, then 1–2 seconds normally),
with **at most six seconds of total sleep**. `Retry-After` seconds/HTTP dates and
Google `RetryInfo` are respected. If a requested wait exceeds the remaining sleep
or request budget, the app stops; it does not shorten the provider's wait.

A 60-second operation budget is checked between attempts, and each attempt's HTTP
timeout is capped at 45 seconds or the remaining budget. Transport timeouts apply
to network phases, so this is not a hard wall-clock cancellation guarantee. No
retries are made for authentication/model/configuration errors, network timeouts,
empty output or validation failures. Retries can consume additional API quota.

Logs distinguish `pitchcraft_gemini_retry`, `pitchcraft_gemini_recovered`, and final
`pitchcraft_gemini_failure`, sharing a reference for the request. Retry logs contain
only safe status/category/type, attempt number and numeric delay, never raw responses.

### Synthetic request comparison

From the repository with your ignored secrets file or environment key configured:

```bash
python -m diagnostics.gemini_probe
# Only if you configured an alternate and deliberately want to test it:
python -m diagnostics.gemini_probe --model-role alternate
```

This makes **three single-attempt requests on one chosen model**: minimal plain
text, a tiny JSON object, then the exact production three-draft contract with
synthetic campaign data. It validates outputs but prints only probe name, success,
status code, category and diagnostic reference. Responses, keys, model IDs and
campaign content are not printed. Exit codes: 0 all probes pass, 1 a probe fails,
2 missing configuration/setup error. Diagnostic requests do not use retries, so
you can observe the original status rather than a recovery masked by retries.

In a controlled/private Streamlit deployment, you can instead temporarily set
`ENABLE_GEMINI_DIAGNOSTICS = true` in app secrets and click **Run synthetic diagnostics**
in the sidebar. This setting only reveals a tool; it is not authentication. Leave
it false on the public app and disable it after investigation. The three requests
may consume quota. No user campaign is passed to the diagnostic.

- All probes return 503: investigate service/model capacity and account availability;
  this does not uniquely implicate structured output.
- Text passes but tiny JSON gets 400: investigate model/JSON-schema support.
- Text and tiny JSON pass but the draft request repeatedly gets 503: investigate
  workload-specific model capacity or a provider bug; simplify experimentally before
  blaming schema syntax. The current production schema is small, and a malformed
  request normally returns 400.
- API succeeds but output validation fails: investigate generation quality/contract,
  separately from service availability.

A sequential comparison is a diagnostic clue, not proof: server load changes over
time. Recheck deliberately under comparable conditions. Retry code cannot restore
Google's capacity or an exhausted daily quota. Recovery can require waiting for
Google, reducing request rate, checking quota, or explicitly selecting a verified
different model. The moving `latest` alias can change its underlying model.

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
- `services/ai_service.py`: explicit provider routing, without automatic failover
- `services/errors.py`: shared sanitized errors and support fields
- `services/gemini_service.py`: Gemini SDK calls, JSON validation, timeouts and safe errors
- `services/groq_service.py`: Groq SDK JSON mode, validation, timeouts and safe errors
- `services/retry.py`: bounded retry decisions and provider wait parsing
- `diagnostics/gemini_probe.py`: opt-in synthetic comparison (CLI and controlled UI)
- `diagnostics/groq_probe.py`: owner-run live model access and synthetic JSON check
- `docs/MAKE_INTEGRATION.md`: future secure delivery design (inactive)
- `tests/`: service, validation and UI regression tests

## Accuracy, privacy and public-use limits

The app does not browse websites or verify user-supplied facts. Pain points are framed
as possibilities. Prompts prohibit invented results, relationships, achievements,
statistics and fake personalization. Numeric-claim warnings and human review provide
additional safeguards, **not a guarantee** that every claim is true. Drafts that are
structurally invalid, too long or excessively similar are rejected.

Inputs and edited emails used for follow-ups are sent to the explicitly selected
provider: Groq or Google's Gemini service. Review that provider's data-use terms
for your account/tier. Do not enter sensitive personal,
client or confidential business information. This app has no application database,
analytics tracker or cross-user draft cache. Drafts live in session state; a new session
can lose them. Clearing the session does not erase data already sent to the provider.

The 20-second cooldown is per session, not a global abuse-control or spending limit.
A public URL can consume your quota through new sessions. Configure provider quotas,
monitor use, and use Community Cloud access controls for a controlled demonstration
if necessary. Free service allowances can change; no paid service is required by
this code, but free access is not guaranteed. This MVP has no campaign database,
bulk outreach, scheduling, automatic delivery, or external fact-checking.
