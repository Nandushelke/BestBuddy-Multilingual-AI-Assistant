# assistant.py
import os
import sys
import subprocess
import webbrowser
import datetime
import json
import tempfile
import time
from typing import Tuple, Optional

import speech_recognition as sr
import pyttsx3
from gtts import gTTS
from playsound import playsound
from langdetect import detect, LangDetectException

from nlp_model import MultilingualNLP

# Supported language mapping
SUPPORTED_LANGS = {"en": "english", "hi": "hindi", "mr": "marathi"}


class TTSManager:
    """
    Handles TTS: offline via pyttsx3 first, then fallback to gTTS (online).
    Saves temporary mp3 and plays it; removes the temp file after playing.
    """

    def __init__(self) -> None:
        self.offline_engine = None
        try:
            self.offline_engine = pyttsx3.init()
            # Optionally configure rate/voice
            self.offline_engine.setProperty("rate", 160)
        except Exception:
            self.offline_engine = None

    def speak_offline(self, text: str) -> bool:
        if not self.offline_engine:
            return False
        try:
            self.offline_engine.say(text)
            self.offline_engine.runAndWait()
            return True
        except Exception:
            return False

    def speak_online(self, text: str, lang: str = "en") -> bool:
        """
        Use gTTS to create an mp3 and play it using playsound or platform opener.
        Returns True if played, False otherwise.
        """
        try:
            # Map language codes for gTTS: 'hi' and 'mr' are supported
            gtts_lang = "en"
            if lang in ("hi", "mr"):
                gtts_lang = lang
            # Save to temp file
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(tmp_fd)
            tts = gTTS(text=text, lang=gtts_lang)
            tts.save(tmp_path)

            # Try playsound first (cross-platform)
            try:
                playsound(tmp_path)
            except Exception:
                # Platform-specific fallback
                if sys.platform.startswith("win"):
                    os.startfile(tmp_path)  # type: ignore
                elif sys.platform == "darwin":
                    subprocess.run(["open", tmp_path], check=False)
                else:
                    # linux: try xdg-open as fallback
                    subprocess.run(["xdg-open", tmp_path], check=False)
                # give some time for external player to start
                time.sleep(1.5)

            # Remove temp file
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            return True
        except Exception:
            return False


class VoiceAssistant:
    """
    Main assistant class: handles listening, speaking, command execution, and delegating to the NLP model.
    """

    def __init__(self) -> None:
        self.recognizer = sr.Recognizer()
        self.tts = TTSManager()
        self.nlp = MultilingualNLP()
        # A very small persistent memory file to store last N interactions
        self.memory_file = os.path.join(os.path.dirname(__file__), "memory.json")
        self.memory_limit = 6
        self._ensure_memory_file()

    def _ensure_memory_file(self):
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump({"history": []}, f)

    def _append_memory(self, role: str, text: str):
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"history": []}
        history = data.get("history", [])
        history.append({"role": role, "text": text, "ts": int(time.time())})
        # keep only the last memory_limit entries
        history = history[-self.memory_limit:]
        data["history"] = history
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def listen_once(self, timeout: int = 6, phrase_time_limit: int = 12) -> Tuple[str, Optional[str]]:
        """
        Listen via microphone once. Try Hindi, Marathi, then English recognition to improve capture.
        Returns (transcribed_text, detected_language_code) or ("", None) on failure.
        """
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except Exception:
                return "", None
        # Try recognition in three language fallbacks
        text = ""
        for lang in ("hi-IN", "mr-IN", "en-US"):
            try:
                text = self.recognizer.recognize_google(audio, language=lang)
                if text:
                    break
            except Exception:
                text = ""
        if not text:
            return "", None
        # detect language code using langdetect (may be 'hi', 'mr', 'en')
        try:
            lang_code = self.nlp.detect_language(text)
        except Exception:
            lang_code = "en"
        return text, lang_code

    def speak(self, text: str, lang: str = "en") -> None:
        """
        Speak text using offline engine first; if that fails, fallback to online gTTS.
        """
        spoken = False
        try:
            spoken = self.tts.speak_offline(text)
        except Exception:
            spoken = False
        if not spoken:
            try:
                self.tts.speak_online(text, lang=lang)
            except Exception:
                # If both fail, just print
                print("BestBuddy (TTS failed):", text)

    # ----- Task / Command Implementations -----
    def _open_whatsapp(self) -> str:
        try:
            webbrowser.open("https://web.whatsapp.com")
            return "Opening WhatsApp."
        except Exception:
            return "I couldn't open WhatsApp."

    def _open_youtube(self) -> str:
        try:
            webbrowser.open("https://www.youtube.com")
            return "Opening YouTube."
        except Exception:
            return "I couldn't open YouTube."

    def _open_website(self, url: str) -> str:
        try:
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url
            webbrowser.open(url)
            return f"Opening {url}"
        except Exception:
            return "I couldn't open that website."

    def _tell_time(self, lang: str = "en") -> str:
        now = datetime.datetime.now().strftime("%I:%M %p")
        if lang == "hi":
            return f"समय है {now}"
        if lang == "mr":
            return f"सध्याचा वेळ {now}"
        return f"The current time is {now}."

    def _play_music(self) -> str:
        # Attempt to open music folder, otherwise open YouTube Music
        try:
            music_dir = os.path.expanduser("~/Music")
            if os.path.isdir(music_dir):
                if sys.platform.startswith("win"):
                    os.startfile(music_dir)  # type: ignore
                elif sys.platform == "darwin":
                    subprocess.run(["open", music_dir], check=False)
                else:
                    subprocess.run(["xdg-open", music_dir], check=False)
                return "Opening your Music folder."
            else:
                webbrowser.open("https://music.youtube.com")
                return "Opening YouTube Music."
        except Exception:
            return "I couldn't play music right now."

    # ----- Command detection (basic intent rules) -----
    def handle_command(self, text: str, lang: Optional[str]) -> Optional[str]:
        """
        Try to detect and execute a command. If found, return a reply string (in user's language).
        Otherwise return None.
        """
        if not text:
            return None
        q = text.lower()

        # WhatsApp
        if any(kw in q for kw in ["open whatsapp", "whatsapp", "व्हाट्सअॅप", "व्हाट्सएप", "व्हाट्सॅप", "व्हाट्सअप"]):
            return self._open_whatsapp()

        # YouTube
        if any(kw in q for kw in ["open youtube", "youtube", "यूट्यूब"]):
            return self._open_youtube()

        # Time
        if any(kw in q for kw in ["what's the time", "time", "समय", "वेळ", "कितना बजे", "कितने बजे", "आत्ता वेळ"]):
            return self._tell_time(lang or "en")

        # Play music
        if any(kw in q for kw in ["play music", "play song", "music", "संगीत", "गाना", "गाणी"]):
            return self._play_music()

        # Open URL pattern (contains dot)
        tokens = q.split()
        for tok in tokens:
            if "." in tok and len(tok) > 3:
                return self._open_website(tok)

        # Could not find a command
        return None

    # ----- Main answer flow -----
    def answer(self, text: str) -> Tuple[str, str]:
        """
        Returns (reply_text, language_code)
        1. Try command execution first
        2. Otherwise use the NLP model to answer in user's language
        """
        if not text:
            return "माफ करा, मी समजत नाही. कृपया पुन्हा बोलावं.", "hi"

        # detect language
        user_lang = self.nlp.detect_language(text)

        # try commands first
        cmd_result = self.handle_command(text, user_lang)
        if cmd_result:
            # translate command response to user's language if needed using nlp
            reply = cmd_result
            # if reply is in English but user_lang not en, try translating
            if user_lang != "en":
                reply = self.nlp.translate_from_en(reply, user_lang)
            # store memory
            self._append_memory("assistant", reply)
            return reply, user_lang

        # fallback to general QA
        # Save user input to memory for context
        self._append_memory("user", text)
        reply, lang = self.nlp.answer_in_user_language(text)
        self._append_memory("assistant", reply)
        return reply, lang
