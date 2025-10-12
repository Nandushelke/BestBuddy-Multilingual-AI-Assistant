import io
import os
import sys
import time
import base64
import tempfile
from typing import Optional

import streamlit as st

from assistant import BestBuddyAssistant

APP_TITLE = "🎧 BestBuddy – Your Multilingual AI Assistant"
GREETING = "Hello! I’m BestBuddy 👋. How can I help you today?"


def synth_to_audio_bytes(text: str, assistant: BestBuddyAssistant) -> Optional[bytes]:
    try:
        return assistant.text_to_speech_bytes(text)
    except Exception:
        return None


def main():
    st.set_page_config(page_title="BestBuddy", page_icon="🎧")
    st.title(APP_TITLE)

    # Sidebar: Mode selection
    st.sidebar.header("Interaction Mode")
    mode = st.sidebar.radio("Choose mode", options=["Text", "Voice"], index=0)

    if "assistant" not in st.session_state:
        st.session_state.assistant = BestBuddyAssistant()

    assistant: BestBuddyAssistant = st.session_state.assistant

    st.write(GREETING)

    # Conversation history
    if "history" not in st.session_state:
        st.session_state.history = []  # list of (user, assistant)

    # Display existing history
    for user_msg, bot_msg in st.session_state.history:
        with st.chat_message("user"):
            st.write(user_msg)
        with st.chat_message("assistant"):
            st.write(bot_msg)

    user_text: Optional[str] = None

    if mode == "Text":
        prompt = st.chat_input("Type your message…")
        if prompt:
            user_text = prompt
    else:
        st.info("Click the button to speak. We'll use your default microphone.")
        if st.button("🎙️ Speak now", use_container_width=True):
            with st.spinner("Listening…"):
                try:
                    user_text = assistant.listen_from_mic()
                except Exception as e:
                    st.error(f"Voice capture failed: {e}")

    if user_text:
        with st.chat_message("user"):
            st.write(user_text)
        with st.spinner("Thinking…"):
            response_text = assistant.handle_query(user_text)
        st.session_state.history.append((user_text, response_text))
        with st.chat_message("assistant"):
            st.write(response_text)
            # Optional audio playback of assistant response
            audio_bytes = synth_to_audio_bytes(response_text, assistant)
            if audio_bytes:
                # Try to detect if bytes are MP3 or WAV by magic header
                fmt = "audio/mp3"
                if audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb":
                    fmt = "audio/mp3"
                elif audio_bytes[:4] == b"RIFF":
                    fmt = "audio/wav"
                st.audio(audio_bytes, format=fmt)


if __name__ == "__main__":
    main()
