# PitchCraft AI
## AI-Powered Cold Email & Sales Pitch Generator
**IIT Patna Generative AI Capstone · Project idea**

**Problem.** Freelancers, early-stage founders and small business teams often struggle
to explain their offer in concise, relevant outreach. Generic templates save time but
can sound impersonal; unconstrained AI can invent recipient facts or business results.

**Proposed solution.** PitchCraft AI is a Streamlit application that turns a structured
campaign brief into three distinct cold email or sales pitch drafts. Users describe
their offer, differentiator, audience, objective and supported recipient facts. They
choose tone and length, review the results, edit a selected draft, then copy or download
it. Human review stays central; the application does not send email.

**Target users.** Freelancers seeking relevant prospects, founders introducing a product,
small business owners explaining a service, and students practising professional outreach.

**Core features.** Sender and recipient details; optional supported facts; five tones;
three length limits; benefit-led, problem-aware and permission-first strategies; subject,
body and call to action; editable outputs; copy/text downloads; clear validation and
provider errors. Previous drafts are labeled and export-blocked after failed replacements.

**Technology and AI integration.** Python, Streamlit, the official Groq Python SDK and
GitHub. A configurable Groq chat model returns JSON. The application validates exactly
three drafts and checks fields, lengths, CTA consistency, similarity and unsupported
numbers. The prompt prohibits invented achievements, relationships, statistics and
misleading guarantees. No database or complex multi-provider system is required.

**Practical uses.** Draft a service introduction, request permission to share a sample,
or present a product's supplied benefits to an appropriate audience. Drafts can be used
as concise sales pitches but still require factual and recipient review.

**Expected benefits.** Reduce blank-page effort, make messages easier to compare and
encourage more careful personalization. These are intended benefits, not measured
conversion-rate or time-saving claims.

**Innovation and relevance.** The project combines three deliberate outreach strategies
with an accessible review workflow and conservative factual safeguards. It addresses a
practical communication problem while demonstrating AI request design, validation,
secure configuration and application deployment.

**Scope and evidence.** Sending and the exposed legacy Make.com webhook are disabled.
Live AI and public-deployment verification remain pending until secure credentials and
an approved deployment are available. The official two-category tool definitions have
not been supplied; category compliance is not yet certified.
