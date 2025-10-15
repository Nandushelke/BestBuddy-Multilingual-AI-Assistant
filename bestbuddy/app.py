# app.py
import streamlit as st
from assistant import VoiceAssistant
import threading

# Create assistant instance (loads models lazily)
assistant = VoiceAssistant()

st.set_page_config(page_title="BestBuddy", page_icon="🎧", layout="centered")

st.title("🎧 BestBuddy — Multilingual AI Assistant")
st.markdown("Supports English, Hindi, and Marathi. Use Text or Voice mode. (Offline-first TTS)")

# Sidebar controls
mode = st.sidebar.selectbox("Interaction Mode", ["Text", "Voice"])
show_history = st.sidebar.checkbox("Show Memory / Conversation History", value=True)

if "responses" not in st.session_state:
    st.session_state.responses = []

if "busy" not in st.session_state:
    st.session_state.busy = False

def add_message(role: str, text: str):
    st.session_state.responses.append({"role": role, "text": text})

def process_user_input(user_text: str):
    st.session_state.busy = True
    try:
        reply, lang = assistant.answer(user_text)
        add_message("user", user_text)
        add_message("assistant", reply)
        # speak reply asynchronously (so Streamlit UI doesn't freeze too long)
        assistant.speak(reply, lang=lang)
    except Exception as e:
        add_message("assistant", f"Error: {str(e)}")
    finally:
        st.session_state.busy = False

# Text mode
if mode == "Text":
    with st.form("text_form", clear_on_submit=False):
        user_input = st.text_area("Type your message", key="text_input", height=120)
        submitted = st.form_submit_button("Send")
    if submitted and user_input.strip():
        process_user_input(user_input.strip())

# Voice mode
else:
    st.write("Click **Start Listening** and speak your message (short queries recommended).")
    col1, col2 = st.columns(2)
    with col1:
        start_listen = st.button("Start Listening")
    with col2:
        stop_listen = st.button("Stop (no-op)")

    if start_listen and not st.session_state.busy:
        # Run listening in a separate thread to keep UI responsive
        def listen_and_process():
            st.session_state.busy = True
            try:
                text, lang = assistant.listen_once()
                if text:
                    add_message("user", text)
                    reply, _lang = assistant.answer(text)
                    add_message("assistant", reply)
                    assistant.speak(reply, lang=_lang)
                else:
                    add_message("assistant", "Sorry, I didn't catch that. Please try again.")
            except Exception as e:
                add_message("assistant", "Error while listening: " + str(e))
            finally:
                st.session_state.busy = False

        t = threading.Thread(target=listen_and_process, daemon=True)
        t.start()

# Display conversation
st.subheader("Conversation")
for msg in st.session_state.responses:
    role = msg["role"]
    text = msg["text"]
    if role == "user":
        st.markdown(f"**You:** {text}")
    else:
        st.markdown(f"**BestBuddy:** {text}")

if show_history:
    st.subheader("Short Memory (persisted)")
    try:
        import json, os
        mem_path = os.path.join(".", "memory.json")
        if os.path.exists(mem_path):
            with open(mem_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            st.json(data.get("history", []))
        else:
            st.write("No memory yet.")
    except Exception as e:
        st.write("Could not load memory:", e)
