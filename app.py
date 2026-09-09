import os
import streamlit as st
from google import genai

st.set_page_config(page_title="AI Cold Email Generator", page_icon="✉️")

st.title("✉️ AI Cold Email & Pitch Generator")
st.write("Generate high-converting cold outreach emails using AI.")

# Retrieve key safely from Streamlit Secrets
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

st.sidebar.header("System Status")
if not api_key:
    st.sidebar.error("⚠️ API Key Missing! Please add GEMINI_API_KEY to Secrets.")
    st.stop()
else:
    st.sidebar.success("✅ Connected to Gemini API")

with st.form("email_form"):
    st.subheader("Campaign Details")
    user_offer = st.text_input("Your Product/Service", placeholder="e.g., Web Design for E-commerce")
    target_client = st.text_input("Target Client", placeholder="e.g., Marketing Manager")
    client_pain_point = st.text_area("Pain Point Solved", placeholder="e.g., Low conversion rates")
    email_tone = st.selectbox("Tone", ["Short & Punchy", "Problem-Solver", "Formal"])
    submit = st.form_submit_button("🚀 Generate 3 Email Drafts")

if submit:
    if not user_offer or not target_client:
        st.warning("Please fill in your offer and target client.")
    else:
        with st.spinner("Generating cold emails..."):
            try:
                client = genai.Client(api_key=api_key)
                prompt = f"""
                Act as a master copywriter. Write 3 distinct cold email options for:
                - Service: {user_offer}
                - Recipient: {target_client}
                - Pain Point: {client_pain_point}
                - Tone: {email_tone}
                
                Provide a Subject Line, Body, and Call to Action for Option 1, Option 2, and Option 3.
                """
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt
                )
                st.success("Your Emails are Ready!")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {str(e)}")
