# Before Editing by Swe010 TTS Backend

TTS-only backend extracted from `before-editing-by-swe010-oct26-update`.

The Android app keeps the video, translated SRT, and FFmpeg rendering on the device. This repository provides the remote Edge TTS service so the Android app does not need to connect to the Edge TTS WebSocket directly.

```text
Android app -> POST /synthesize-batch -> this backend -> Python edge-tts -> MP3 Base64
Android app -> local FFmpeg -> final MP4 + output SRT
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api:app --host 127.0.0.1 --port 8000
streamlit run app.py --server.port 8501
```

The API is available at `/health`, `/presets`, `/synthesize`, and `/synthesize-batch`. Set `BACKEND_TOKEN` in the hosting environment to require `X-App-Token`; do not put that token in the Android source repository.

`app.py` is a TTS-only Streamlit testing UI. `api.py` is the native Android integration endpoint. Both use the same `tts_engine.py` voice map, 10 styles, 11 emotions, and Edge TTS 7.3.1 logic from the Oct26 reference.

## Hosting

The Streamlit testing UI uses `requirements.txt`, which intentionally contains only the reference Streamlit/Edge TTS dependencies. FastAPI and Uvicorn are isolated in `requirements-api.txt` so Streamlit's internal Starlette middleware cannot conflict with the API's Starlette version. For an API host, install with `pip install -r requirements-api.txt` and run the `Procfile` command. Streamlit Community Cloud can host `app.py` without installing the API dependencies.

This backend uses Microsoft's public Edge TTS endpoint through `edge-tts`; it does not require an Azure API key. Availability and rate limits remain controlled by Microsoft. For personal use, keep the repository private and set `BACKEND_TOKEN` on the deployed API.
