# 🎧 BestBuddy – Your Multilingual AI Assistant

BestBuddy is a text + voice-based assistant that understands English, Hindi, and Marathi. It can answer general questions and perform basic desktop actions like opening WhatsApp, opening websites, telling the time, and playing music.

## Features

- Multilingual understanding (English, Hindi, Marathi) with auto language detection
- Text and Voice interaction modes
- General Q&A via Hugging Face `transformers`
- Basic commands: open WhatsApp, open YouTube, open websites, tell time, play music
- Offline-friendly TTS with `pyttsx3` and online fallback via `gTTS`
- Speech recognition via `speech_recognition`
- Built with Streamlit for a simple UI

## Project Structure

```
/bestbuddy/
  ├── app.py                # Streamlit UI
  ├── assistant.py          # Core assistant logic
  ├── nlp_model.py          # Model setup and response generation
  ├── requirements.txt      # All dependencies
  └── README.md             # Project overview & setup guide
```

## Installation

1. Create and activate a virtual environment (recommended):
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - macOS/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   Notes:
   - `pyaudio` may require system build tools and portaudio headers. On Ubuntu/Debian:
     ```bash
     sudo apt-get update && sudo apt-get install -y portaudio19-dev python3-dev
     pip install pyaudio
     ```
   - First run will download models from Hugging Face automatically.

3. Run the app:
   ```bash
   streamlit run app.py
   ```

4. Open the URL shown by Streamlit (usually `http://localhost:8501`).

## Usage

- Choose Text or Voice mode from the sidebar.
- In Text mode, type your query and click Send.
- In Voice mode, click "Start Listening", speak your query, and wait for the response.
- BestBuddy will reply in the language it detected from your input.

### Supported Commands (Examples)

- "Open WhatsApp" / "व्हाट्सअॅप खोल" / "व्हाट्सएप खोल"
- "Open YouTube" / "यूट्यूब खोल"
- "Open google.com" / "google.com खोल"
- "What's the time?" / "समय क्या है?" / "आत्ता वेळ काय आहे?"
- "Play music" / "संगीत चलाओ" / "गाणी चालू करा"

## Models

- Translation (optional): `ai4bharat/IndicTrans2-en-indic`, `ai4bharat/IndicTrans2-indic-en`
- Text generation: `google/flan-t5-base` (fallback to `distilgpt2`)

These are loaded using `transformers` pipelines. If a model fails to load (e.g., offline), the app will display a friendly message.

## Offline Behavior

- TTS first tries offline `pyttsx3`, then falls back to `gTTS` (online).
- Speech recognition uses Google recognizer by default; if offline it will not transcribe and the app will ask you to try again.
- General Q&A requires downloaded models; after first download, it can run offline.

## Windows Notes (College Lab Friendly)

- Ensure microphone permissions are enabled.
- For `pyaudio` on Windows, consider installing prebuilt wheels from `https://www.lfd.uci.edu/~gohlke/pythonlibs/` if needed.

## Troubleshooting

- If `pyaudio` fails to install, try `pip install pipwin && pipwin install pyaudio` (Windows).
- If TTS audio does not play on Linux, install an MP3 player like `mpg123` or rely on the offline engine.
- If models fail to download, check internet connectivity and try again.

## Screenshots

- Placeholder: Add screenshots of the Streamlit UI in Text and Voice modes here.

## License

Open-source, for educational purposes.
