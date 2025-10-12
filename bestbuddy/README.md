# 🎧 BestBuddy – Your Multilingual AI Assistant

BestBuddy is a simple, college-friendly text + voice AI assistant that understands English, Hindi, and Marathi. It can answer general questions and execute basic desktop tasks like opening WhatsApp, opening websites, telling the time, and locating your music folder.

- Supports English, Hindi, Marathi (auto-detects language)
- Text and Voice interaction (mic button)
- Uses open-source Hugging Face models (IndicBERT + IndicTrans2 + Flan-T5)
- Streamlit UI, runs offline after initial model downloads

## Features
- General Q&A using `transformers` pipeline (Flan-T5)
- Voice input via `speech_recognition` (with Google online fallback; Sphinx offline if available)
- Voice output via `pyttsx3` (offline) or `gTTS` (online)
- Simple commands:
  - "Open WhatsApp"
  - "Open YouTube"
  - "Open <website.com>"
  - "What’s the time?"
  - "Play music"
- Replies in the same language as the user's input

## Project Structure
```
/bestbuddy/
  ├── app.py                # Streamlit UI
  ├── assistant.py          # Core assistant logic (commands, STT, TTS)
  ├── nlp_model.py          # Language detect, translation, generation
  ├── requirements.txt      # Dependencies
  └── README.md             # This guide
```

## Installation
1. Create and activate a Python 3.9+ virtual environment.
2. Install dependencies:
```bash
pip install -r requirements.txt
```

Notes:
- `torch` will install automatically; if GPU is available, install CUDA-specific torch per PyTorch site for speed.
- `pyaudio` may require system build tools. On Ubuntu/Debian:
```bash
sudo apt-get update && sudo apt-get install -y portaudio19-dev python3-pyaudio
```

## Running
```bash
streamlit run app.py
```
Then open the local URL shown in the terminal.

## Usage
- Choose Text or Voice mode in the sidebar.
- In Voice mode, click "🎙️ Speak now" to talk.
- Ask anything, or try commands like:
  - "Open WhatsApp"
  - "Open YouTube"
  - "Open wikipedia.org"
  - "What’s the time?"
  - "Play music"

## Offline Behavior
- After models are cached, most features work offline.
- If internet is unavailable, online STT (`recognize_google`) and `gTTS` may fail; the app will fall back gracefully where possible.

## Screenshots
- [Placeholder] Home screen with title and modes
- [Placeholder] Example conversation in English
- [Placeholder] Example response in Hindi
- [Placeholder] Example response in Marathi

## Notes for Windows Labs
- No paid APIs required.
- Use `pyttsx3` for offline voice; install Microsoft SAPI5 voices if needed.
- Microphone access may need driver permissions.

## Acknowledgements
- Models from AI4Bharat: IndicBERT, IndicTrans2
- Text generation: Google Flan-T5 (open-source)
- UI: Streamlit
