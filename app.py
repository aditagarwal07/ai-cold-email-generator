"""PitchCraft AI: the original single-form workflow, finalized on main."""
import uuid
import streamlit as st
from pitchcraft import (LENGTHS, TONES, PitchCraftError, configuration,
                        export_text, generate, validate_campaign)

st.set_page_config(page_title='PitchCraft AI', page_icon='✉️', layout='centered')
st.title('✉️ PitchCraft AI')
st.write('AI-powered cold email & sales pitch generator')
st.caption('IIT Patna Generative AI Capstone · Provide your offer, review three approaches, and export your chosen draft.')
config = configuration(st.secrets)
with st.sidebar:
    st.subheader('Workspace status')
    if config.key:
        st.success('AI key configured')
    else:
        st.info('The app owner must add GROQ_API_KEY in secure app settings.')
    st.caption('Key presence does not confirm API access. This app uses Groq; sending is disabled.')
    if st.button('Start over'):
        st.session_state.clear()
        st.rerun()

st.info('Use only facts you can support. Inputs are sent to Groq when you generate; avoid confidential or sensitive information.')
with st.form('email_form'):
    st.subheader('Campaign details')
    st.caption('Required fields are marked *. Drafts use your last submitted campaign; changing fields alone does not regenerate them.')
    values = {}
    left, right = st.columns(2)
    with left:
        values['sender'] = st.text_input('Sender name *', placeholder='Your name', max_chars=100, key='sender')
    with right:
        values['company'] = st.text_input('Sender company *', placeholder='Your company or independent practice', max_chars=150, key='company')
    values['offer'] = st.text_area('Product or service *', placeholder='What do you offer, and how does it help?', max_chars=500, key='offer')
    values['difference'] = st.text_area('Unique selling proposition *', placeholder='A specific differentiator you can honestly support', max_chars=500, key='difference')
    values['audience'] = st.text_input('Target audience *', placeholder='For example: owners of small online retail businesses', max_chars=300, key='audience')
    left, right = st.columns(2)
    with left:
        values['recipient'] = st.text_input('Recipient name (optional)', placeholder='Leave blank if unknown', max_chars=100, key='recipient')
    with right:
        values['recipient_company'] = st.text_input('Recipient company (optional)', placeholder='Only add a known company', max_chars=150, key='recipient_company')
    values['pain'] = st.text_area('Recipient pain point *', placeholder='A challenge your audience may face; assumptions are phrased conditionally', max_chars=600, key='pain')
    values['objective'] = st.text_input('Campaign objective *', placeholder='Ask permission to share a relevant sample', max_chars=300, key='objective')
    values['facts'] = st.text_area('Supported recipient facts (optional)', placeholder='Facts you can support, with source/context if available. Leave blank if you have none.', max_chars=2000, key='facts')
    left, right = st.columns(2)
    with left:
        values['tone'] = st.selectbox('Preferred tone', TONES, key='tone')
    with right:
        values['length'] = st.selectbox('Preferred email length', list(LENGTHS), key='length', help='Short: 90 words. Medium: 140. Detailed: 200. Limits include greeting and signature.')
    submitted = st.form_submit_button('Generate 3 drafts', type='primary', disabled=not config.key)

if submitted:
    # A failed or invalid replacement request must never make old drafts look current.
    st.session_state['outdated'] = True
    try:
        campaign = validate_campaign(values)
        with st.spinner('Writing three distinct approaches…'):
            drafts = generate(config, campaign)
        st.session_state.update(drafts=drafts, revision=uuid.uuid4().hex, campaign=campaign, outdated=False)
        st.success('Your drafts are ready. Review and edit before use.')
    except PitchCraftError as exc:
        st.error(str(exc))
        if exc.reference:
            st.caption(f'Support reference: {exc.reference}')

if st.session_state.get('drafts'):
    st.divider()
    st.subheader('Review your drafts')
    st.warning('Verify recipient details and every factual claim. AI instructions and numeric checks are safeguards, not independent fact-checking.')
    outdated = st.session_state.get('outdated', False)
    if outdated:
        st.error('These are older drafts. The replacement request failed or was invalid. Generate successfully before exporting.')
    campaign = st.session_state['campaign']
    st.caption(f'Last successful campaign: {campaign["offer"]} · Audience: {campaign["audience"]}')
    edited = []
    revision = st.session_state['revision']
    current_drafts = st.session_state['drafts']
    draft_labels = tuple(d.strategy for d in current_drafts)
    for i, (tab, draft) in enumerate(zip(st.tabs(draft_labels), current_drafts)):
        with tab:
            subject = st.text_input('Subject line', value=draft.subject, max_chars=140, key=f'subject_{revision}_{i}')
            body = st.text_area('Email body', value=draft.body, height=260, max_chars=5000, key=f'body_{revision}_{i}')
            st.caption(f'{len(body.split())} words · Suggested next step is included in the body.')
            edited.append((subject, body))
    chosen = st.selectbox('Draft to copy or download', range(3), format_func=lambda i, labels=draft_labels: labels[i], key=f'choice_{revision}')
    try:
        content = export_text(*edited[chosen])
    except PitchCraftError as exc:
        st.error(str(exc))
    else:
        if not outdated:
            st.code(content, language=None, wrap_lines=True)
            st.caption('Use the copy icon at the top-right of the text box. Download uses your edited version.')
            st.download_button('Download selected draft', content, 'pitchcraft-email.txt', mime='text/plain', type='primary')

st.divider()
st.caption('Email sending is disabled while the exposed Make.com integration is reviewed. Download drafts for manual use. Nothing is emailed automatically.')
