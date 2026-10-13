# Make.com delivery: future integration contract

Delivery is **disabled** in Version 2: there is no send button, webhook request,
or loaded webhook secret. Do not configure a webhook until these safeguards are implemented.

The legacy scenario is outside this repository and has not been audited. Its URL
appeared in Version 1. If it is active, replace it and review its authentication;
removing the URL from Version 2 does not remove it from Git history.

## Configuration for a future, separately authorized release

Store `MAKE_WEBHOOK_URL` and any scenario authentication credential in Streamlit
secrets, never source, examples, logs, or error messages. Use HTTPS and an approved
Make.com destination; do not accept a webhook destination from public form inputs.

Suggested payload (schema only, not an active integration):

- `request_id`: unique identifier for duplicate detection
- `recipient_email`: validated, permitted destination
- `email_subject`: reviewed subject of the selected draft
- `email_body`: reviewed body of the selected draft

## Required flow

1. Validate inputs and limit access. Start with a verified owner-controlled test inbox.
2. Show the exact recipient, subject, and body.
3. Require a separate explicit confirmation; editing anything clears confirmation.
4. Only then POST from the server with authentication and a finite timeout.
5. Do not automatically retry a delivery request: a timed-out request may have been processed.
6. Have Make.com deduplicate request IDs before dispatching, not just Streamlit.
7. Return an accepted/queued status and request ID. HTTP success is not proof of delivery.
8. Distinguish confirmed provider delivery, rejection, and unknown outcome.

Public visitors must not be able to send arbitrary emails. Add recipient restrictions,
access controls and enforceable service-level limits before enabling public delivery.
Test with a separate scenario and explicit owner authorization. Never test the old
production webhook merely to check connectivity.
