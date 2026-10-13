# Four build-in-public post drafts

**Status:** Prepared copy; nothing has been posted. Publish with real dates and actual
evidence links. Do not backdate posts or claim that drafts satisfy a publication requirement.
Check whether the official rubric requires posts during development rather than retrospectively.

## Post 1 — The problem and the idea

For my IIT Patna Generative AI Capstone, I am building **PitchCraft AI**: a small tool
that helps freelancers and founders explain an offer through cold email and sales
pitch drafts.

I wanted to address a practical problem: generic outreach saves effort but can feel
irrelevant. AI also needs constraints so it does not invent recipient achievements or
business results. My approach is a structured campaign brief, three writing strategies,
and a human review step before use.

I am focusing on a useful starting point, not guaranteed conversions or automatic emailing.

#BuildInPublic #GenerativeAI #IITPatna #Capstone #PitchCraftAI

**Evidence to attach:** One-page idea document and a clearly labeled form screenshot.

## Post 2 — Choosing a smaller, maintainable application

A lesson from PitchCraft AI: complexity is not the same as reliability.

After experimenting on a separate V2 branch and encountering AI service failures, I
returned to the original V1 workflow. I am finalizing one campaign form with two Python
source files and one AI provider. The form captures the offer, audience, sender identity,
objective, optional supported facts, tone and length.

I also removed an exposed delivery webhook from active code and disabled sending.
Removing a value from a current file does not erase Git history; the old webhook still
needs owner revocation or rotation.

#BuildInPublic #Python #Streamlit #ResponsibleAI #PitchCraftAI

**Evidence to attach:** Actual audit report and main-branch code screenshot after approval.

## Post 3 — Testing the parts that can break

For PitchCraft AI, I am treating response validation as part of the product.

The app checks required inputs, expects three different strategies, validates subject,
body and call-to-action fields, and rejects oversized, repeated or unsupported-number
outputs. Users can edit and download the selected draft. Failed replacements are labeled
so old drafts are not mistaken for new results.

My QA separates mocked unit/UI tests from real provider calls and deployment checks.
Passing mocked tests is useful engineering evidence, but it does not prove a live API
is available. The project documentation records that distinction.

#BuildInPublic #SoftwareTesting #AIEngineering #Streamlit #PitchCraftAI

**Evidence to attach:** Actual current test result and QA notes. If attaching mocked-output
screenshots, label them visibly. Do not imply a live API call until one is verified.

## Post 4 — Submission preparation and what remains

PitchCraft AI's capstone materials now include a one-page idea, Notion-ready documentation,
a demonstration storyboard, security notes and an evidence checklist.

My focus is a reliable generation-and-review experience. I am keeping the original
application recognizable and keeping human factual review central. Before claiming a
completed submission, I still need verified live generation, public deployment evidence,
the narrated video, published documentation/post links and confirmation of the official
tool-category rules.

Preparing an artifact is not the same as publishing or validating it. I am documenting
both the progress and the remaining checks honestly.

#BuildInPublic #CapstoneProject #GenerativeAI #Documentation #PitchCraftAI

**Evidence to attach:** Documentation package; add public app/video links only after
checking them. Update the outstanding checks truthfully when they are completed.
