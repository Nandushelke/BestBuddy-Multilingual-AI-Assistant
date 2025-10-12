import os
import sys
import webbrowser
import subprocess
from datetime import datetime
from typing import Optional

from nlp_model import MultilingualNLP

import speech_recognition as sr

try:
    import pyttsx3  # offline TTS
except Exception:
    pyttsx3 = None

try:
    from gtts import gTTS  # online TTS
except Exception:
    gTTS = None

import tempfile


class BestBuddyAssistant:
    def __init__(self) -> None:
        self.nlp = MultilingualNLP()
        self.recognizer = sr.Recognizer()
        self.microphone: Optional[sr.Microphone] = None
        try:
            self.microphone = sr.Microphone()
        except Exception:
            self.microphone = None

        # Initialize pyttsx3 if available
        self.tts_engine = None
        if pyttsx3 is not None:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 170)
            except Exception:
                self.tts_engine = None

    # ===== Speech APIs =====
    def listen_from_mic(self, timeout: int = 5, phrase_time_limit: int = 10) -> str:
        if self.microphone is None:
            raise RuntimeError("Microphone not available. Please check audio device and PyAudio.")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        try:
            # Use Google for STT (free) when online; fallback to Sphinx if installed
            try:
                text = self.recognizer.recognize_google(audio, language="hi-IN")
            except Exception:
                try:
                    text = self.recognizer.recognize_google(audio, language="mr-IN")
                except Exception:
                    text = self.recognizer.recognize_google(audio, language="en-US")
            return text
        except Exception:
            # Fallback to offline Sphinx if available
            try:
                text = self.recognizer.recognize_sphinx(audio)
                return text
            except Exception as e:
                raise RuntimeError(f"Speech recognition failed: {e}")

    def text_to_speech_bytes(self, text: str) -> Optional[bytes]:
        # Prefer pyttsx3 for offline synthesis to WAV, convert to bytes
        if self.tts_engine is not None:
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    temp_path = tf.name
                # pyttsx3 supports saving to file via driver property
                self.tts_engine.save_to_file(text, temp_path)
                self.tts_engine.runAndWait()
                with open(temp_path, "rb") as f:
                    data = f.read()
                os.remove(temp_path)
                return data
            except Exception:
                pass
        # Fallback to gTTS and encode as MP3
        if gTTS is not None:
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                    temp_path = tf.name
                tts = gTTS(text=text)
                tts.save(temp_path)
                with open(temp_path, "rb") as f:
                    data = f.read()
                os.remove(temp_path)
                return data
            except Exception:
                return None
        return None

    # ===== Command Handling =====
    def _open_whatsapp(self) -> str:
        # Open WhatsApp Web
        webbrowser.open("https://web.whatsapp.com/")
        return "Opening WhatsApp Web."

    def _open_youtube(self) -> str:
        webbrowser.open("https://www.youtube.com/")
        return "Opening YouTube."

    def _open_website(self, query: str) -> str:
        # Extract a domain if user mentioned one, basic heuristic
        tokens = query.split()
        for token in tokens:
            if "." in token:
                url = token if token.startswith("http") else f"https://{token}"
                webbrowser.open(url)
                return f"Opening {url}"
        webbrowser.open("https://www.google.com")
        return "Opening Google."

    def _tell_time(self) -> str:
        now = datetime.now().strftime("%I:%M %p")
        return f"The time is {now}."

    def _play_music(self) -> str:
        # Try platform default music folder
        music_dirs = [
            os.path.expanduser("~/Music"),
            os.path.expanduser("~/Downloads"),
        ]
        for folder in music_dirs:
            if os.path.isdir(folder):
                # Open folder to let user pick; or attempt to play first file via system
                try:
                    # Linux/Windows cross-platform open
                    if sys.platform.startswith("win"):
                        os.startfile(folder)  # type: ignore[attr-defined]
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", folder])
                    else:
                        subprocess.Popen(["xdg-open", folder])
                    return "Opening your music folder."
                except Exception:
                    continue
        return "I couldn't find a music folder."

    def execute_command_if_any(self, query: str) -> Optional[str]:
        q = query.lower()
        # Multilingual keyword triggers (English, Hindi, Marathi)
        if any(kw in q for kw in ["open whatsapp", "whatsapp", "व्हॉट्सअॅप", "व्हाट्सएप"]):
            return self._open_whatsapp()
        if any(kw in q for kw in ["open youtube", "youtube", "यूट्यूब"]):
            return self._open_youtube()
        if any(kw in q for kw in ["what time", "time", "समय", "वेल", "वेळ"]):
            return self._tell_time()
        if any(kw in q for kw in ["play music", "music", "गाना", "संगीत", "गाणी"]):
            return self._play_music()
        if any(kw in q for kw in ["open", "खोल", "खोलो", "ओपन"]):
            return self._open_website(query)
        return None

    # ===== Main handler =====
    def handle_query(self, user_text: str) -> str:
        # 1) Try command execution first
        cmd_reply = self.execute_command_if_any(user_text)
        if cmd_reply:
            # Answer in user's language if we can
            return self.nlp.respond_in_user_language(user_text, cmd_reply)

        # 2) Otherwise, delegate to NLP model for general Q&A
        model_reply = self.nlp.generate_answer(user_text)
        if model_reply:
            return model_reply
        return self.nlp.respond_in_user_language(
            user_text,
            "Sorry, I couldn't understand that. Please try again."
        )
