import os
from typing import Optional, Tuple

from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from langdetect import detect

# Optional translation support using IndicTrans2 (en<->indic). We fall back gracefully if models fail.
# Using ai4bharat/IndicTrans2-en-indic for English->Indic and ai4bharat/IndicTrans2-indic-en for Indic->English

SUPPORTED_LANGS = {
    "en": "english",
    "hi": "hindi",
    "mr": "marathi",
}


class MultilingualNLP:
    """
    Sets up a simple text-generation / general QA style model using HF pipelines.
    Also provides optional translation utilities to keep responses in user language.
    """

    def __init__(self) -> None:
        self.device = 0 if os.environ.get("CUDA_VISIBLE_DEVICES") else -1

        # Main general model: use an open small T5 model for general responses to keep it light.
        # You required ai4bharat models; we'll use IndicTrans2 for translation and keep generation generic.
        # For college-friendly demo, we use google/flan-t5-base if available without key.
        # If it fails to load, we fall back to distilgpt2 text-generation.
        self.generator = None
        self.generation_task = None

        # Translation models (optional) — load lazily on first use
        self.en_to_indic = None
        self.indic_to_en = None

        self._load_generation_model()

    def _load_generation_model(self) -> None:
        try:
            self.generator = pipeline(
                "text2text-generation",
                model="google/flan-t5-base",
                device=self.device,
            )
            self.generation_task = "text2text-generation"
        except Exception:
            try:
                self.generator = pipeline(
                    "text-generation",
                    model="distilgpt2",
                    device=self.device,
                )
                self.generation_task = "text-generation"
            except Exception:
                self.generator = None
                self.generation_task = None

    def _ensure_en_to_indic(self):
        if self.en_to_indic is not None:
            return
        try:
            self.en_to_indic = pipeline(
                task="translation",
                model="ai4bharat/IndicTrans2-en-indic",
                device=self.device,
            )
        except Exception:
            self.en_to_indic = None

    def _ensure_indic_to_en(self):
        if self.indic_to_en is not None:
            return
        try:
            self.indic_to_en = pipeline(
                task="translation",
                model="ai4bharat/IndicTrans2-indic-en",
                device=self.device,
            )
        except Exception:
            self.indic_to_en = None

    def detect_language(self, text: str) -> str:
        try:
            code = detect(text)
            if code in SUPPORTED_LANGS:
                return code
            # crude heuristic: if Devanagari script present, assume Hindi or Marathi
            if any("\u0900" <= ch <= "\u097F" for ch in text):
                # default to Hindi if ambiguous
                return "hi"
            return "en"
        except Exception:
            return "en"

    def translate_to_en(self, text: str, src_lang: str) -> str:
        if src_lang == "en":
            return text
        self._ensure_indic_to_en()
        if self.indic_to_en is None:
            return text
        try:
            out = self.indic_to_en(text)
            if isinstance(out, list) and out:
                return out[0].get("translation_text", text)
        except Exception:
            pass
        return text

    def translate_from_en(self, text: str, tgt_lang: str) -> str:
        if tgt_lang == "en":
            return text
        self._ensure_en_to_indic()
        if self.en_to_indic is None:
            return text
        try:
            out = self.en_to_indic(text, tgt_lang=tgt_lang)
            if isinstance(out, list) and out:
                return out[0].get("translation_text", text)
        except Exception:
            pass
        return text

    def generate_answer(self, prompt: str) -> str:
        if self.generator is None:
            return "I'm unable to load the language model right now. Please try again later."
        try:
            if self.generation_task == "text2text-generation":
                outputs = self.generator(prompt, max_new_tokens=128)
                return outputs[0]["generated_text"].strip()
            else:
                outputs = self.generator(prompt, max_length=128, num_return_sequences=1)
                return outputs[0]["generated_text"].strip()
        except Exception:
            return "I ran into a problem generating a response."

    def answer_in_user_language(self, user_text: str) -> Tuple[str, str]:
        src_lang = self.detect_language(user_text)
        english_query = self.translate_to_en(user_text, src_lang)
        english_answer = self.generate_answer(english_query)
        final_answer = self.translate_from_en(english_answer, src_lang)
        return final_answer, src_lang
