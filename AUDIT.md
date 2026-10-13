# Original main audit — 13 October 2026

Scope: original `main` commit `6458782a8b7735f13cb292841c001e96c27926ae`.
The audit inspected its three tracked files. No V2 source was merged or copied.
No institutional guideline files were found; only the supplied summary is available.

| Area | Original evidence | Targeted response |
|---|---|---|
| Features | One Streamlit form, Gemini generation of three options, session-state text, Make.com delivery button | Preserve the one-form workflow; add required campaign fields and editable exports |
| Configuration | Hardcoded `gemini-3.6-flash`; no live connection check | Use one configurable Groq model because of reported recurring Gemini failures and an existing Cloud Groq key; live verification remains pending |
| Model status | Model ID/account availability not verified live | Do not call it invalid without evidence; use documented Groq `llama-3.3-70b-versatile` with JSON mode, then validate output locally |
| Dependencies | Unpinned `streamlit`, `google-genai`; `requests` used without direct declaration | Two pinned direct dependencies: Streamlit and official Groq SDK; eliminate unused delivery client |
| Secrets | `st.secrets.get` can fail before environment fallback; key presence labeled connected | Safe missing-file handling; configuration presence is not an API health claim |
| Exposure | Active hardcoded Make webhook in source/history | Remove it from active code and disable sending; owner must replace/revoke old webhook |
| Validation | Required fields checked only for nonempty text; no length limits | Trim/validate essential fields and cap input/output sizes |
| AI quality | Free-form response; no distinct-strategy or factual grounding checks | JSON contract, exactly three named strategies, body/CTA/length checks, duplicate and unsupported-number rejection |
| UX | No sender identity, editing, copying or downloads | Brand as PitchCraft AI, keep the form, add three review tabs and edited text exports |
| Error handling | Raw provider exceptions displayed, no timeouts on webhook POST | Static sanitized messages, safe diagnostic references, bounded SDK retries and timeout |
| Draft state | Previous results can remain after failed replacements | Label prior drafts as older and block export after failed/invalid replacement |
| Make.com | Scenario/provider configuration not in repository; 200 treated as delivered | No delivery claim or webhook calls; future safe demonstration plan documented separately |
| Deployment | README only a title; no runtime/setup guidance | Explain main/app.py/Python 3.12, secrets, package installation and owner verification |
| Capstone evidence | No tests, idea document, Notion document, video, posts or official category definitions | Supply documents, script/post drafts, tests and a checklist that marks missing evidence honestly |

## Security action required outside code

The old webhook must be treated as potentially compromised. Disable the old scenario
or webhook, replace its URL in Make.com, and inspect execution history for unexpected
runs. Revocation/rotation has **not** been performed by this task. Removing the value
from today's files does not erase it from Git history. No API-key literal was found
in the original tracked files; inspect provider usage and rotate keys if other exposure
is known. Do not paste keys or replacement webhook URLs into chat or Git.

## Limits of this audit

The public URL could not be reached from this execution environment (URL access failed).
This is not evidence that the public app is down. No local Gemini or Groq credential
is present, and no real generation or Make.com delivery was attempted. The Cloud app's
currently saved secrets, runtime and live behavior are not independently verified.
Prior V2 error reports establish reported failures, not a live test of V1's model.
