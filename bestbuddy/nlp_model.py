from typing import Optional
import os

from langdetect import detect
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM, AutoModel

# We will use:
# - ai4bharat/IndicBERT (for multilingual understanding/embedding if needed)
# - ai4bharat/IndicTrans2-en-indic for translation EN -> Indic; and indic-en for reverse
# - A light open-source QA/generation pipeline; we default to 'google/flan-t5-base' for general Q&A
#   (still open-source, college-friendly).

DEFAULT_QA_MODEL = "google/flan-t5-base"
INDIC_EN_MODEL = "ai4bharat/indictrans2-indic-en"
EN_INDIC_MODEL = "ai4bharat/indictrans2-en-indic"


class MultilingualNLP:
    def __init__(self) -> None:
        # Lazy-init pipelines to speed up first render
        self._qa_pipe = None
        self._en_to_indic_pipe = None
        self._indic_to_en_pipe = None
        # Load IndicBERT tokenizer/model to ensure availability in environment (optional usage)
        try:
            self._indicbert_tokenizer = AutoTokenizer.from_pretrained("ai4bharat/IndicBERTv2-MLM-only")
            self._indicbert_model = AutoModel.from_pretrained("ai4bharat/IndicBERTv2-MLM-only")
        except Exception:
            self._indicbert_tokenizer = None
            self._indicbert_model = None

    def _ensure_pipelines(self):
        if self._qa_pipe is None:
            try:
                self._qa_pipe = pipeline("text2text-generation", model=DEFAULT_QA_MODEL)
            except Exception:
                # Fallback smaller model
                self._qa_pipe = pipeline("text2text-generation", model="google/flan-t5-small")
        if self._en_to_indic_pipe is None:
            try:
                self._en_to_indic_pipe = pipeline(
                    "translation", model=EN_INDIC_MODEL
                )
            except Exception:
                self._en_to_indic_pipe = None
        if self._indic_to_en_pipe is None:
            try:
                self._indic_to_en_pipe = pipeline(
                    "translation", model=INDIC_EN_MODEL
                )
            except Exception:
                self._indic_to_en_pipe = None

    def detect_language(self, text: str) -> str:
        try:
            return detect(text)
        except Exception:
            # Default to English
            return "en"

    def translate_to_english(self, text: str) -> str:
        self._ensure_pipelines()
        if self._indic_to_en_pipe is None:
            return text
        try:
            out = self._indic_to_en_pipe(text, max_length=512)
            return out[0]["translation_text"]
        except Exception:
            return text

    def translate_from_english(self, text: str, target_hint_lang_code: str) -> str:
        self._ensure_pipelines()
        if self._en_to_indic_pipe is None:
            return text
        # The model selects target language token internally; we pass as prompt hint
        prompt = f">>{target_hint_lang_code}<< {text}"
        try:
            out = self._en_to_indic_pipe(prompt, max_length=512)
            return out[0]["translation_text"]
        except Exception:
            return text

    def respond_in_user_language(self, user_text: str, english_reply: str) -> str:
        lang = self.detect_language(user_text)
        if lang.startswith("en"):
            return english_reply
        # Map langdetect codes to model language hints if needed
        code_map = {"hi": "hin_Deva", "mr": "mar_Deva"}
        target = code_map.get(lang, "hin_Deva")
        return self.translate_from_english(english_reply, target)

    def generate_answer(self, user_text: str) -> str:
        self._ensure_pipelines()
        lang = self.detect_language(user_text)
        # Translate to English if not English for better Q&A model understanding
        text_en = user_text
        if not lang.startswith("en"):
            text_en = self.translate_to_english(user_text)
        try:
            result = self._qa_pipe(text_en, max_length=256, do_sample=False)
            answer_en = result[0]["generated_text"].strip()
        except Exception:
            answer_en = "I'm unable to generate a response right now."
        # Translate back to user's language
        return self.respond_in_user_language(user_text, answer_en)
