import os
import sys
import subprocess
import webbrowser
import datetime
from typing import Tuple, Optional

import speech_recognition as sr
import pyttsx3
from gtts import gTTS
from langdetect import detect

from nlp_model import MultilingualNLP


SUPPORTED_LANGS = {"en": "english", "hi": "hindi", "mr": "marathi"}


class TTSManager:
    def __init__(self) -> None:
        self.offline_engine = None
        try:
            self.offline_engine = pyttsx3.init()
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
        # Map language code for gTTS
        gtts_lang = "en"
        if lang in ("hi", "mr"):
            # gTTS supports 'hi' for Hindi, Marathi ideally 'mr' is supported, fallback to 'hi' if not available
            gtts_lang = "hi" if lang == "hi" else "mr"
        try:
            tts = gTTS(text=text, lang=gtts_lang)
            temp_file = "tts_output.mp3"
            tts.save(temp_file)
            # Use a simple cross-platform way to play audio
            if sys.platform.startswith("win"):
                os.startfile(temp_file)  # type: ignore
            else:
                # Try to use 'xdg-open' or 'mpg123' if available
                try:
                    subprocess.run(["xdg-open", temp_file], check=False)
                except Exception:
                    subprocess.run(["mpg123", temp_file], check=False)
            return True
        except Exception:
            return False


class VoiceAssistant:
    def __init__(self) -> None:
        self.recognizer = sr.Recognizer()
        self.tts = TTSManager()
        self.nlp = MultilingualNLP()

    def listen_once(self, timeout: int = 5, phrase_time_limit: int = 10) -> Tuple[str, Optional[str]]:
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
            audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        try:
            # Use Google's free recognizer as a convenient default; offline alternatives are limited
            text = self.recognizer.recognize_google(audio, language="hi-IN")
            # Heuristic: Google Hindi often recognizes Devanagari languages; also try English fallback
            if not text or all(ord(ch) < 128 for ch in text):
                try:
                    text = self.recognizer.recognize_google(audio, language="en-US")
                except Exception:
                    pass
            lang = self.nlp.detect_language(text)
            return text, lang
        except Exception:
            return "", None

    def speak(self, text: str, lang: str = "en") -> None:
        if not self.tts.speak_offline(text):
            self.tts.speak_online(text, lang=lang)

    def _open_whatsapp(self) -> str:
        try:
            # WhatsApp Web
            webbrowser.open("https://web.whatsapp.com")
            return "Opening WhatsApp"
        except Exception:
            return "I couldn't open WhatsApp."

    def _open_youtube(self) -> str:
        try:
            webbrowser.open("https://www.youtube.com")
            return "Opening YouTube"
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

    def _tell_time(self) -> str:
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {now}."

    def _play_music(self) -> str:
        # Try to open default music directory or a music URL
        try:
            music_dir = os.path.expanduser("~/Music")
            if os.path.isdir(music_dir):
                if sys.platform.startswith("win"):
                    os.startfile(music_dir)  # type: ignore
                elif sys.platform == "darwin":
                    subprocess.run(["open", music_dir], check=False)
                else:
                    subprocess.run(["xdg-open", music_dir], check=False)
                return "Opening your Music folder"
            else:
                webbrowser.open("https://music.youtube.com")
                return "Opening YouTube Music"
        except Exception:
            return "I couldn't play music right now."

    def handle_command(self, text: str, lang: Optional[str]) -> Optional[str]:
        query_lower = text.lower()

        # Basic commands across languages (simple keyword heuristics)
        if any(kw in query_lower for kw in ["open whatsapp", "whatsapp", "व्हाट्सअॅप", "व्हाट्सएप", "व्हाट्सॅप", "व्हाट्सअप"]):
            return self._open_whatsapp()
        if any(kw in query_lower for kw in ["open youtube", "youtube", "यूट्यूब", "यू ट्यूब"]):
            return self._open_youtube()
        if any(kw in query_lower for kw in ["what's the time", "time", "समय", "वेल", "वेळ", "कितना बजे", "कितने बजे"]):
            return self._tell_time()
        if any(kw in query_lower for kw in ["play music", "music", "गाना", "संगीत", "म्यूजिक", "गाणी"]):
            return self._play_music()
        if any(kw in query_lower for kw in ["open", "खोल", "खोलना", "खोलून"]):
            # naive URL extraction
            tokens = query_lower.split()
            for tok in tokens:
                if "." in tok and len(tok) > 3:
                    return self._open_website(tok)
        return None

    def answer(self, text: str) -> Tuple[str, str]:
        # Prefer command execution first
        detected_lang = self.nlp.detect_language(text)
        cmd = self.handle_command(text, detected_lang)
        if cmd:
            # Reply in detected language
            reply = self.nlp.translate_from_en(cmd, detected_lang)
            return reply, detected_lang
        # Otherwise use general QA / generation
        reply, lang = self.nlp.answer_in_user_language(text)
        return reply, lang
