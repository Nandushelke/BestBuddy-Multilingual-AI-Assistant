# nlp_model.py
import os
import json
import time
from typing import Tuple, Optional

import torch
from transformers import pipeline
from langdetect import detect, LangDetectException

# Models we attempt to use (downloaded via HF automatically)
GENERATION_MODEL = "google/flan-t5-base"      # primary (text2text)
FALLBACK_GENERATION = "distilgpt2"            # fallback small generator
EN_TO_INDIC = "ai4bharat/IndicTrans2-en-indic"
INDIC_TO_EN = "ai4bharat/IndicTrans2-indic-en"

MEMORY_PATH = os.path.join(os.path.dirname(__file__), "nlp_memory.json")
# Keep short conversation memory in this model too (in-memory) as well as persisted
SHORT_HISTORY_LIMIT = 6


class MultilingualNLP:
    """
    Lightweight wrapper around HF pipelines for:
    - text generation / Q&A
    - optional translation (EN <-> Indic)
    - language detection
    - short-term memory to provide context
    """

    def __init__(self):
        # device selection: -1 CPU, 0+ GPU
        self.device = 0 if torch.cuda.is_available() else -1
        self.generator = None
        self.generation_task = None
        self._load_generation_model()

        # translation pipelines lazy-loaded
        self.en_to_indic = None
        self.indic_to_en = None

        # short-term in-memory context
        self.history = []
        self._ensure_memory_file()

    def _ensure_memory_file(self):
        if not os.path.exists(MEMORY_PATH):
            with open(MEMORY_PATH, "w", encoding="utf-8") as f:
                json.dump({"history": []}, f)

    def _load_generation_model(self):
        # Try to load flan-t5 first (text2text). If fails, fallback to distilgpt2.
        try:
            self.generator = pipeline("text2text-generation", model=GENERATION_MODEL, device=self.device)
            self.generation_task = "text2text-generation"
        except Exception:
            try:
                # fallback
                self.generator = pipeline("text-generation", model=FALLBACK_GENERATION, device=self.device)
                self.generation_task = "text-generation"
            except Exception:
                self.generator = None
                self.generation_task = None

    def _ensure_en_to_indic(self):
        if self.en_to_indic is not None:
            return
        try:
            self.en_to_indic = pipeline("translation", model=EN_TO_INDIC, device=self.device)
        except Exception:
            self.en_to_indic = None

    def _ensure_indic_to_en(self):
        if self.indic_to_en is not None:
            return
        try:
            self.indic_to_en = pipeline("translation", model=INDIC_TO_EN, device=self.device)
        except Exception:
            self.indic_to_en = None

    def detect_language(self, text: str) -> str:
        """Return 'en', 'hi', or 'mr' (or 'en' fallback)"""
        if not text or not text.strip():
            return "en"
        try:
            code = detect(text)
            if code in ("en", "hi", "mr"):
                return code
            # If detection returned 'hi'/'mr' variants or others, fall back
            if code.startswith("hi"):
                return "hi"
            if code.startswith("mr"):
                return "mr"
            # Heuristic: Devanagari script implies hi or mr
            if any("\u0900" <= ch <= "\u097F" for ch in text):
                return "hi"
            return "en"
        except LangDetectException:
            # fallback heuristics
            if any("\u0900" <= ch <= "\u097F" for ch in text):
                return "hi"
            return "en"

    def translate_to_en(self, text: str, src_lang: str) -> str:
        if src_lang == "en":
            return text
        self._ensure_indic_to_en()
        if self.indic_to_en is None:
            # fallback: return text (no translation)
            return text
        try:
            out = self.indic_to_en(text)
            if isinstance(out, list) and out:
                return out[0].get("translation_text", text)
            if isinstance(out, dict):
                return out.get("translation_text", text)
        except Exception:
            return text
        return text

    def translate_from_en(self, text: str, tgt_lang: str) -> str:
        if tgt_lang == "en":
            return text
        self._ensure_en_to_indic()
        if self.en_to_indic is None:
            return text
        try:
            # The pipeline expects plain text and returns translation_text
            out = self.en_to_indic(text)
            if isinstance(out, list) and out:
                return out[0].get("translation_text", text)
            if isinstance(out, dict):
                return out.get("translation_text", text)
        except Exception:
            return text
        return text

    def generate_answer(self, prompt: str) -> str:
        """
        Use generator pipeline to produce an English answer (or same language depending on model).
        A simple context concatenation is used to give short memory.
        """
        if self.generator is None:
            return "I'm unable to load the language model right now. Please try again later."

        # Add short context
        contextual_prompt = prompt
        if self.history:
            # append last few turns to prompt to give context (keeps prompt small)
            recent = [h["text"] for h in self.history[-(SHORT_HISTORY_LIMIT // 2):]]
            contextual_prompt = " ".join(recent) + "\nUser: " + prompt

        try:
            if self.generation_task == "text2text-generation":
                outputs = self.generator(contextual_prompt, max_new_tokens=120)
                text = outputs[0].get("generated_text") or outputs[0].get("summary_text") or ""
            else:
                outputs = self.generator(contextual_prompt, max_length=120, num_return_sequences=1)
                text = outputs[0].get("generated_text", outputs[0].get("generated_text", ""))
            text = text.strip()
            # Save to history
            self._append_history("assistant", text)
            return text
        except Exception:
            return "I ran into a problem generating a response."

    def _append_history(self, role: str, text: str):
        entry = {"role": role, "text": text, "ts": int(time.time())}
        self.history.append(entry)
        self.history = self.history[-SHORT_HISTORY_LIMIT:]
        # persist minimal memory to disk too
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"history": []}
        hist = data.get("history", [])
        hist.append(entry)
        hist = hist[-SHORT_HISTORY_LIMIT:]
        data["history"] = hist
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def answer_in_user_language(self, user_text: str) -> Tuple[str, str]:
        """
        Detect language, translate to English if needed, generate an English answer,
        then translate back to user language. Returns (final_answer, detected_lang).
        """
        src_lang = self.detect_language(user_text)
        # Translate user text to English for robust generation if needed
        english_query = user_text
        if src_lang != "en":
            english_query = self.translate_to_en(user_text, src_lang)

        # Generate English (or model language) answer
        english_answer = self.generate_answer(english_query)

        # Translate back to user's language if needed
        final_answer = english_answer
        if src_lang != "en":
            final_answer = self.translate_from_en(english_answer, src_lang)
        return final_answer, src_lang

    # Optional small utility for intent detection (very basic)
    def detect_intent(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Return simple intent and optional entity.
        Example intents: open_app, open_website, get_time, play_music, question
        """
        q = text.lower()
        if any(k in q for k in ["whatsapp", "व्हाट्स", "व्हाट्सअॅप"]):
            return "open_app", "whatsapp"
        if "youtube" in q or "यूट्यूब" in q:
            return "open_app", "youtube"
        if "time" in q or "वेळ" in q or "समय" in q:
            return "get_time", None
        if "play" in q or "गाण" in q or "music" in q:
            return "play_music", None
        if "." in q:
            return "open_website", q
        return "question", None
