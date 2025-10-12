import os
import io
import streamlit as st
from typing import Optional

from assistant import VoiceAssistant

st.set_page_config(page_title="BestBuddy", page_icon="🎧")

st.title("🎧 BestBuddy – Your Multilingual AI Assistant")

if "assistant" not in st.session_state:
    st.session_state.assistant = VoiceAssistant()

assistant = st.session_state.assistant

st.sidebar.header("Interaction Mode")
mode = st.sidebar.radio("Choose mode", ["Text", "Voice"], index=0)

st.info("Hello! I’m BestBuddy 👋. How can I help you today?")

response_text: Optional[str] = None
response_lang: Optional[str] = None

if mode == "Text":
    user_input = st.text_input("Type your message (English / Hindi / Marathi)")
    if st.button("Send") and user_input.strip():
        with st.spinner("Thinking..."):
            reply, lang = assistant.answer(user_input)
            response_text, response_lang = reply, lang
elif mode == "Voice":
    st.write("Click the button and speak.")
    if st.button("🎤 Start Listening"):
        with st.spinner("Listening..."):
            text, lang = assistant.listen_once()
        if not text:
            st.warning("Sorry, I didn't catch that. Please try again.")
        else:
            st.write(f"You said: {text}")
            with st.spinner("Thinking..."):
                reply, lang2 = assistant.answer(text)
                response_text, response_lang = reply, lang2 or lang or "en"
            with st.spinner("Speaking..."):
                assistant.speak(response_text, response_lang or "en")

if response_text:
    st.subheader("Assistant says:")
    st.write(response_text)
