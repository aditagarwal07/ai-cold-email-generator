# Tool-category evidence and optional Make.com plan

## Eligibility cannot yet be certified

The provided summary requires meaningful use of tools from two eligible categories,
but it does not define the categories. No official guideline document was found.
Do not substitute assumptions for the institutional list.

| Tool | Actual present role | Can it count now? |
|---|---|---|
| Groq | AI generation code; local mocked tests | Generative role is clear; eligibility and real execution pending |
| Streamlit | Application/UI framework and intended Cloud hosting | Development role is clear; official category eligibility pending |
| GitHub | Repository/history | Do not assume source control is an eligible category |
| Notion | Prepared documentation | No page published; do not assume documentation is an eligible category |
| Make.com | Old delivery integration disabled | No functional or category credit claimed |

If the rubric accepts application development and generative AI as separate categories,
Streamlit plus a live-tested Groq integration may satisfy it. If automation is required,
use the following owner-approved plan only after real core generation is reliable.

## Why sending is disabled

The original source/history exposed a Make webhook. The scenario's trigger, email
provider, authentication, recipient mapping and current behavior are outside this
repository. An HTTP 200 response is not proof that a message reached an inbox. No old
webhook was called during this task, and no delivery claim is made.

## Smallest meaningful automation demonstration, if required

1. In Make.com disable/revoke the old webhook and inspect unexpected execution history.
2. Create a separate **development** scenario with a new authenticated custom webhook.
3. Use a verified owner-controlled test inbox and an existing permitted email connector.
   Check current free-tier limits; a connector/account may be needed.
4. Define a payload with `request_id`, `recipient_email`, `email_subject`, `email_body`.
   Map the subject/body exactly; do not send all draft options as one message by mistake.
5. Have Make reject invalid authentication and unexpected recipient destinations.
   Deduplicate `request_id` **before** sending to avoid duplicate messages.
6. In a separately approved code change, load `MAKE_WEBHOOK_URL` and authentication
   securely from Secrets, never source. Restrict HTTPS destinations; set a finite timeout.
7. Add a preview of the exact edited recipient/subject/body and a separate confirmation.
   Changes invalidate confirmation. Public users must not send to arbitrary addresses.
8. Test once with explicit owner approval and a synthetic message to the test inbox.
   Confirm Make execution and inbox receipt, then document both. No auto retry on an
   ambiguous timeout: the email may already have been sent.
9. Demonstrate the actual automation step in the video and capture scenario evidence
   without showing webhook URLs, credentials or private inbox content.

This is a configuration/testing plan, **not an implemented or verified current integration**.
Do not add `MAKE_WEBHOOK_URL` to the current app expecting sending to become enabled.
If the official tool categories do not require automation, keep sending disabled and
avoid delaying a reliable core submission with an unnecessary integration.
