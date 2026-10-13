# PitchCraft AI

**AI-Powered Cold Email & Sales Pitch Generator · IIT Patna Generative AI Capstone**

This finalization of the original V1 keeps one campaign form and a small application:
`app.py` for the Streamlit interface and `pitchcraft.py` for validation and generation.
It does not merge or copy `capstone-v2`. The original implementation is preserved in
Git at `6458782a8b7735f13cb292841c001e96c27926ae`; V2 remains on its own branch.

## What it does

Enter sender/offer/audience details, optional supported recipient facts, objective,
tone and length. Generate three strategies, edit subjects and bodies, copy a selected
draft, and download it as text. Campaign input remains in the original `email_form`.
A failed or invalid replacement labels previous drafts as older and blocks exports.
Changing fields without submitting does not regenerate: output is explicitly tied to
the last successful submitted campaign. Session state is temporary, not a database.

One provider keeps this submission small: the official Groq SDK, JSON mode, configurable
`GROQ_MODEL` (default `llama-3.3-70b-versatile`). The ID and JSON-mode interface are documented
in [Groq's official SDK](https://github.com/groq/groq-python/blob/main/src/groq/types/chat/completion_create_params.py).
Live access for this account is still pending. Groq was selected after investigating
V1's hardcoded Gemini call and considering the reported recurring Gemini outages and
existing Cloud Groq credential. No automatic provider switching, enrichment, scheduling,
follow-ups or bulk emailing is added to this V1 finalization.

## Local setup — Python 3.12

From this repository's **main** checkout:

```bash
python -m venv .venv
```

Activate with `source .venv/bin/activate` on macOS/Linux or
`.venv\Scripts\Activate.ps1` in Windows PowerShell, then:

```bash
python -m pip install -r requirements.txt
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, replacing the
placeholder only in the real ignored file. Alternatively set `GROQ_API_KEY` and
`GROQ_MODEL` as environment variables. Never commit the key or paste it into chat.

```bash
python -m streamlit run app.py
```

Missing credentials leave the interface available, with generation disabled. Source
file watching is disabled for deployment reliability. For local automatic reload:

```bash
python -m streamlit run app.py --server.fileWatcherType auto
```

## Deploy the existing Community Cloud app — only after approval

Do not delete the existing app. These instructions prepare an owner-approved update;
they are not a claim that an update has already been deployed.

1. Review the pending changes on **main**. Do not merge `capstone-v2`.
2. After approval, commit/push the reviewed main changes.
3. In Community Cloud, confirm repository `aditagarwal07/ai-cold-email-generator`,
   branch **main**, entry point **app.py**. Configure/redeploy with Python **3.12**.
   The runtime is selected in Cloud Advanced settings; a repository version file does
   not automatically change an existing Cloud runtime. If a new deployment is needed
   to change Python, preserve the existing app until the replacement is verified.
4. Confirm `GROQ_API_KEY` exists in **this app's** Secrets, not merely another app's.
   Keep an existing valid key. Optionally set `GROQ_MODEL = "llama-3.3-70b-versatile"`.
   The example's placeholder is not a working key. No Make.com secret is required.
5. Allow dependencies to install and restart/reboot if necessary. Confirm package/runtime
   versions in logs and make one real generation using nonconfidential sample input.
6. Verify three distinct drafts, edit/copy/download, and confirm no email is sent.

Existing app URL (current functionality not verified from this workspace):
https://ai-cold-email-generator-lya8dhtlbwjr9e96frxtgs.streamlit.app/

## Tests and evidence

```bash
python -m unittest discover -s tests -v
python -m pip check
```

Automated tests use synthetic inputs and mocked API responses, including an actual
SDK client with mocked HTTP transport. They do not prove live API availability or
public deployment. See `capstone_submission/06_QA_and_Evidence.md` for measured results,
remaining checks and screenshot provenance. Do not present mocked screenshots as live AI.

## Security, reliability and limitations

The system prompt prohibits fabricated facts, metrics, research, relationships and
recipient engagement. Recipient pain points are conditional; facts are user-supported,
not independently verified. JSON parsing validates exactly three strategies, subject/body/
CTA fields, length, similarity and newly introduced numbers. These are safeguards,
**not a guarantee of factual truth**: review each claim and any human edits before use.

Inputs are sent to Groq when generation is requested. Check its data-use terms and
avoid confidential/personal information. No application database, cross-user content
cache or analytics tracker is added. Downloads are local browser actions.

The SDK allows at most one retry for eligible transient failures and has a 20-second
transport timeout. Provider Retry-After can extend waiting; network phase timeouts
are not a hard wall-clock cancellation promise. Invalid content is not automatically
retried. Public users can consume quota; configure provider limits and consider a
controlled demonstration before unrestricted public use. Free allowances can change.

Error messages contain static guidance and a support reference. Logs use
`pitchcraft_failure reference=... error_type=... status_code=... category=...` without
raw exceptions, keys or campaign content. Categories distinguish credentials, models,
usage limits, outages, connectivity and bad responses. Keep provider debug logging off.

**Make.com sending is disabled.** The old webhook was exposed in Git history. Replace
or revoke it and review scenario execution history; deleting its current code value
does not erase history. No delivery success or tool-category credit is claimed.
See `capstone_submission/07_Make_and_Tool_Categories.md` for a safe, owner-tested future
plan if official category rules make it necessary.

## Submission package

`capstone_submission/` includes an idea document, Notion-ready documentation, a narrated
video script/storyboard, four post drafts, an evidence checklist and QA notes. They
are prepared materials, not already published artifacts. The actual narrated video,
Notion page, posts, live generation and official two-category eligibility still need
owner-supplied evidence. No official rubric/category definitions were found locally;
the supplied requirements summary is the baseline.
