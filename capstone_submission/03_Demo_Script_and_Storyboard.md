# Narrated demonstration — target 4 minutes

**Status:** Complete recording script and storyboard; an actual narrated video has not
been recorded. Record only after an approved deployment and successful real AI request.
Do not present local mocked screenshots as live generation.

## Before recording

Open the public application in a signed-out/private browser. Check one real request
with nonconfidential data and ensure three drafts and downloads work. Keep credentials,
Cloud Secrets, provider dashboards and personal inboxes off screen. Use a synthetic
company/recipient and clearly identify them as sample inputs. Stop and resolve a live
API failure rather than editing a failed request into a false success claim.

Sample campaign: Alex, Example Studio, editable project planning templates, clear task
ownership, small project teams, possible planning disorganization, request permission
to share a sample, Professional tone, Short length. Recipient/facts may be left blank.

## 0:00–0:30 — Introduce the problem

**Screen:** Public URL and PitchCraft AI title; cursor briefly highlights the description.

**Narration:**
“Hello, this is PitchCraft AI, my Generative AI Capstone project
for IIT Patna. It helps users turn a clear description of their offer into cold email
and sales pitch drafts. The problem I am addressing is the blank page: how can a
freelancer or small business explain value clearly without using a generic template
or inventing facts about a prospect?”

## 0:30–1:20 — Explain the inputs

**Screen:** Fill/scroll the single campaign form with the sample above. Show optional facts.

**Narration:**
“The workflow begins with a campaign brief. I enter the sender identity, the product
or service, what makes it different, the audience, a possible pain point and the desired
next step. These are sample details, not a real recipient's information. Recipient
name and company are optional. There is also a field for facts the user can support.
If those facts are missing, the model should use neutral wording rather than pretend
it researched a company. Tone and length controls keep the output appropriate for the
campaign. Required fields and character limits are checked before an API request.”

## 1:20–2:05 — Generate and compare

**Screen:** Click Generate once. Keep a visible spinner segment; do not imply zero latency.
Then inspect all three tabs and subjects.

**Narration:**
“Now I request three drafts through the official Groq API. The application asks for
JSON and validates the result before displaying it. The approaches are benefit-led,
problem-aware and permission-first. They are intended to differ in their framing and
next step, rather than repeat the same email with a few synonyms changed. The prompt
prohibits invented statistics, achievements, relationships and misleading guarantees.
The application also checks output fields, lengths, call-to-action consistency,
similarity and newly introduced numbers. These checks improve reliability, but they
do not replace human judgment or independently verify facts.”

## 2:05–2:55 — Edit and export

**Screen:** Select one approach, edit the subject/body, show word count, copy and download.
Open the downloaded text file without exposing unrelated files.

**Narration:**
“I remain responsible for the final message. Each draft has editable subject and body
fields, and the word count updates as I refine the writing. I can compare the three
strategies, choose one, and use the copy control or download it as a plain text file.
The export includes my edits. Output is labeled with the last successful campaign;
a failed replacement request marks older drafts and blocks their export. The application
never sends email automatically. The old Make.com delivery feature is disabled because
its webhook was exposed and its current scenario has not been verified.”

## 2:55–3:35 — Explain architecture, safety and evidence

**Screen:** Briefly show the repository's two source files, tests and README; never Secrets.

**Narration:**
“I finalized the original V1 instead of merging the larger experimental V2 branch.
The main application has two Python source files: one for the Streamlit interface and
one for validation and AI generation. Credentials are read from secure settings, never
hardcoded. User-facing errors distinguish credentials, unavailable models, usage limits,
timeouts and outages. Automated tests use synthetic responses, including mocked HTTP
transport through the actual SDK. That is separate from the real API generation shown
in this recording. The documentation records these differences honestly.”

## 3:35–4:05 — Close with relevance and limits

**Screen:** Return to the reviewed draft; briefly show the project idea/documentation link.

**Narration:**
“PitchCraft AI is useful for freelancers, founders and small teams who need a clearer
starting point for outreach. Its intended benefit is less blank-page effort and better
review of alternative approaches, not a guaranteed conversion rate. Service availability,
quota and factual accuracy still matter. Future automation would require a new secure
webhook and explicit reviewed sending, but it is outside this reliable core. Thank you
for watching my project demonstration.”

## Recording and delivery

Use a free screen recorder with microphone narration. Aim for clear speech, readable
zoom and 3–5 minutes total. The timing is approximate; rehearse once before recording.
Export MP4, check audio and public/link access, and place the real video URL in
`05_Submission_Checklist.md`. Do not backdate or fabricate evidence. If the official
rubric requires showing another eligible tool, revise the storyboard only after that
integration is actually tested and its category is confirmed.
