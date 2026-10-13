"""PitchCraft AI: campaign → review → export. No email delivery actions."""
import time
import uuid
import streamlit as st
from pydantic import ValidationError
from core.models import (
    Campaign, Length, Tone, claim_warnings, edited_email, email_fingerprint,
)
from services.gemini_service import GenerationError, generate_drafts, generate_follow_up
from services.settings import load_settings

st.set_page_config(page_title='PitchCraft AI · Cold Email & Pitch Generator', page_icon='✦', layout='wide')
st.markdown('''<style>
.block-container {max-width: 1180px; padding-top: 5rem;}
h1, h2, h3 {letter-spacing: -0.025em;}
.hero {border-left: 5px solid #4F46E5; padding: .4rem 1.2rem; margin-bottom: 1.5rem;}
.hero .eyebrow {color: #4F46E5; font-weight: 700; letter-spacing: .08em; font-size: .78rem;}
.hero h1 {margin: .15rem 0; font-size: clamp(2rem, 5vw, 3rem);}
.hero p {color: #475569; margin: .2rem 0;}
</style>
<div class="hero"><div class="eyebrow">IIT PATNA · GENERATIVE AI CAPSTONE</div>
<h1>PitchCraft AI</h1><p>Thoughtful outreach. Clear value. Your final say.</p></div>''', unsafe_allow_html=True)

settings = load_settings(st.secrets)
COOLDOWN_SECONDS = 20


def begin_request() -> bool:
    now = time.monotonic()
    remaining = COOLDOWN_SECONDS - (now - st.session_state.get('last_request', -COOLDOWN_SECONDS))
    if remaining > 0:
        st.warning(f'Please wait {int(remaining) + 1} seconds before another AI request.')
        return False
    st.session_state['last_request'] = now
    return True


def show_generation_error(exc: GenerationError) -> None:
    st.error(str(exc))
    if exc.reference_id:
        st.caption(f'Support reference: {exc.reference_id}. The app owner can look up this reference in Streamlit Cloud logs.')


with st.sidebar:
    st.subheader('Your writing workspace')
    st.write('**1. Campaign** — provide the offer and facts.\n\n**2. Review** — compare and refine.\n\n**3. Export** — copy or download.')
    st.divider()
    if settings.api_key:
        st.success('Gemini key configured')
    else:
        st.info('Add GEMINI_API_KEY to app secrets to generate drafts.')
    st.caption('Key presence does not confirm API access. Model availability and quota depend on the app owner’s account.')
    st.caption('Email delivery is disabled. This app never sends email.')
    if st.button('Clear this session', use_container_width=True):
        for key in list(st.session_state):
            if key != 'last_request':
                del st.session_state[key]
        st.rerun()

st.caption('AI Cold Email & Pitch Generator · Create three strategies, edit your favorite, and export it.')
campaign_tab, review_tab, export_tab = st.tabs(['1 · Campaign', '2 · Review & edit', '3 · Copy & download'])

with campaign_tab:
    st.subheader('Build your campaign')
    st.caption('Required fields are marked *. Inputs are sent to Google Gemini when you generate. Avoid sensitive personal or confidential information.')
    with st.container(border=True):
        st.markdown('#### Your offer')
        left, right = st.columns(2)
        with left:
            sender_name = st.text_input('Sender name *', max_chars=100, placeholder='Aditi Agarwal', key='input_sender_name')
            product = st.text_area('Product or service *', max_chars=500, placeholder='Landing page design for independent online retailers', key='input_product')
        with right:
            sender_company = st.text_input('Sender company *', max_chars=150, placeholder='Your company or independent practice', key='input_sender_company')
            usp = st.text_area('Unique selling proposition *', max_chars=500, placeholder='What makes your offer useful and different? Include only claims you can support.', key='input_usp')
    with st.container(border=True):
        st.markdown('#### Your audience')
        audience = st.text_input('Target audience *', max_chars=300, placeholder='Marketing managers at small online retail businesses', key='input_audience')
        left, right = st.columns(2)
        with left:
            recipient_name = st.text_input('Recipient name (optional)', max_chars=100, placeholder='Leave blank for a general draft', key='input_recipient_name')
        with right:
            recipient_company = st.text_input('Recipient company (optional)', max_chars=150, placeholder='Only add a company you actually know', key='input_recipient_company')
        pain = st.text_area('Recipient pain point *', max_chars=600, placeholder='A challenge your audience may face. An assumption will be phrased conditionally.', key='input_pain_point')
        facts = st.text_area('Verified or user-supported recipient facts (optional)', max_chars=2000, placeholder='One fact per line, with a source or context when available. Leave blank if you have no supported facts.', key='input_facts', help='The app does not browse or independently verify facts. Do not enter guesses as facts.')
    with st.container(border=True):
        st.markdown('#### Writing direction')
        objective = st.text_input('Campaign objective *', max_chars=300, placeholder='Ask whether a short introduction would be useful', key='input_objective')
        left, right = st.columns(2)
        with left:
            tone = st.selectbox('Tone', [item.value for item in Tone], key='input_tone')
        with right:
            length = st.selectbox('Email length', [item.value for item in Length], key='input_length', help='Short: up to 100 words. Medium: 160. Detailed: 240, including greeting and signature.')

    values = dict(sender_name=sender_name, sender_company=sender_company, product=product, usp=usp,
                  audience=audience, recipient_name=recipient_name, recipient_company=recipient_company,
                  pain_point=pain, objective=objective, facts=facts, tone=tone, length=length)
    campaign = None
    validation_errors = []
    try:
        campaign = Campaign(**values)
    except ValidationError as exc:
        labels = {'sender_name': 'Sender name', 'sender_company': 'Sender company', 'product': 'Product or service',
                  'usp': 'Unique selling proposition', 'audience': 'Target audience', 'pain_point': 'Recipient pain point',
                  'objective': 'Campaign objective'}
        for error in exc.errors():
            label = labels.get(error['loc'][0], str(error['loc'][0]).replace('_', ' ').capitalize())
            validation_errors.append(f'{label}: {error["msg"]}.')

    if st.button('Generate 3 email drafts', type='primary', disabled=not settings.api_key, key='generate'):
        if validation_errors:
            st.error('Please complete the campaign:\n\n' + '\n\n'.join(validation_errors))
        elif begin_request():
            st.session_state['generation_failed'] = False
            with st.spinner('Writing three distinct strategies…'):
                try:
                    batch = generate_drafts(settings, campaign)
                    st.session_state.update(batch=batch, campaign_fingerprint=campaign.fingerprint(),
                                            revision=uuid.uuid4().hex, followups={})
                    st.success('Three drafts are ready. Open “2 · Review & edit”.')
                except GenerationError as exc:
                    st.session_state['generation_failed'] = True
                    show_generation_error(exc)

batch = st.session_state.get('batch')
stale = batch is not None and (campaign is None or campaign.fingerprint() != st.session_state.get('campaign_fingerprint'))
selected_subject = selected_body = ''
selected_index = 0
edit_valid = False
revision = st.session_state.get('revision', '')

with review_tab:
    st.subheader('Compare and refine')
    if batch is None:
        st.info('Complete your campaign and generate drafts to start reviewing.')
    else:
        if stale:
            st.warning('Campaign inputs have changed. These are older drafts. Regenerate, or restore the original inputs, before follow-up or export.')
        if st.session_state.get('generation_failed'):
            st.warning('The latest generation failed. The drafts below are from the previous successful request.')
        st.info('Review every claim before use. Recipient facts are user-supplied; AI output is not independently verified.')
        draft_tabs = st.tabs([draft.strategy.value for draft in batch.drafts])
        edited = []
        for i, (draft, tab) in enumerate(zip(batch.drafts, draft_tabs)):
            with tab:
                st.caption(f'{draft.strategy.value} · The suggested next step is already included in the body.')
                subject = st.text_input('Subject line', value=draft.subject, max_chars=140, key=f'edit_subject_{revision}_{i}')
                body = st.text_area('Email body', value=draft.body, height=300, max_chars=5000, key=f'edit_body_{revision}_{i}')
                edited.append((subject, body))
                st.caption(f'{len(body.split())} words · Suggested CTA: {draft.call_to_action}')
                if campaign and not stale:
                    for warning in claim_warnings(campaign, subject + '\n' + body):
                        st.warning(warning)
        selected_index = st.selectbox('Draft to export or follow up', range(3), format_func=lambda i: batch.drafts[i].strategy.value, key=f'select_{revision}')
        selected_subject, selected_body = edited[selected_index]
        try:
            selected_subject, selected_body = edited_email(selected_subject, selected_body)
            edit_valid = True
        except ValueError as exc:
            st.warning(str(exc))

        st.divider()
        st.markdown('#### A gentle follow-up')
        st.caption('Uses the selected, edited email. No assumption that the recipient opened, read, or replied. Generating a follow-up does not send it.')
        source_id = email_fingerprint(selected_subject, selected_body)
        if st.button('Generate a short follow-up', disabled=stale or not edit_valid or not settings.api_key, key='generate_followup'):
            if begin_request():
                with st.spinner('Writing a short follow-up…'):
                    try:
                        followup = generate_follow_up(settings, campaign, selected_subject, selected_body)
                        st.session_state['followups'][selected_index] = (source_id, followup)
                    except GenerationError as exc:
                        show_generation_error(exc)
                    except ValueError as exc:
                        st.error(str(exc))
        saved = st.session_state.get('followups', {}).get(selected_index)
        if saved:
            if saved[0] != source_id or stale:
                st.warning('The source email or campaign changed. Generate a new follow-up to match it.')
            else:
                followup = saved[1]
                st.markdown('**Follow-up draft**')
                st.code(f'Subject: {followup.subject}\n\n{followup.body}', language=None, wrap_lines=True)
                st.caption(f'{len(followup.body.split())} words · Use the copy icon in the text box. Verify claims before use.')
                st.download_button('Download follow-up', data=f'Subject: {followup.subject}\n\n{followup.body}', file_name='pitchcraft-follow-up.txt', mime='text/plain', key=f'followup_download_{selected_index}')

with export_tab:
    st.subheader('Your final say')
    if batch is None:
        st.info('Your selected draft will appear here after generation.')
    elif stale:
        st.warning('Export is paused because your campaign changed. Generate new drafts or restore the original campaign inputs.')
    elif not edit_valid:
        st.warning('Complete the selected subject and body in the review stage before exporting.')
    else:
        st.caption(f'Selected strategy: {batch.drafts[selected_index].strategy.value} · {len(selected_body.split())} words')
        text = f'Subject: {selected_subject}\n\n{selected_body}'
        st.code(text, language=None, wrap_lines=True)
        st.caption('To copy, use the copy icon at the top-right of the text box.')
        reviewed = st.checkbox('I have reviewed the recipient details and factual claims.', key=f'reviewed_{revision}_{email_fingerprint(selected_subject, selected_body)}')
        st.download_button('Download selected email', data=text, file_name='pitchcraft-email.txt', mime='text/plain', disabled=not reviewed, type='primary')
        st.caption('Text exports only. Make.com delivery is intentionally disabled in this MVP.')

st.divider()
st.caption('PitchCraft AI · IIT Patna Generative AI Capstone · AI assists your writing; you remain responsible for accuracy and final use.')
