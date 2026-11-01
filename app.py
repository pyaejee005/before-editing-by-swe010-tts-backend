from __future__ import annotations

import asyncio
import json
import zipfile
from io import BytesIO

import streamlit as st

from tts_engine import EMOTIONS, RECAP_STYLES, VOICES, make_zip, resolve_settings, synthesize_batch

st.set_page_config(page_title="Before Editing TTS Backend", page_icon="🔊", layout="wide")
st.title("🔊 Before Editing • Edge TTS Backend")
st.caption("TTS-only backend extracted from before-editing-by-swe010-oct26-update. Video rendering stays on the Android device.")

voice_id = st.selectbox("Voice", options=[item["id"] for item in VOICES], format_func=lambda value: next(item["label"] for item in VOICES if item["id"] == value))
style_id = st.selectbox("Style", options=[item["id"] for item in RECAP_STYLES], format_func=lambda value: next(item["name"] for item in RECAP_STYLES if item["id"] == value))
emotion_id = st.selectbox("Emotion", options=[item["id"] for item in EMOTIONS], format_func=lambda value: next(item["name"] for item in EMOTIONS if item["id"] == value))
settings = resolve_settings(voice_id, style_id, emotion_id)
rate = st.slider("Final speed (%)", -50, 100, settings["rate"])
pitch = st.slider("Final pitch (Hz)", -50, 100, settings["pitch"])
workers = st.select_slider("TTS parallel workers", options=list(range(3, 31, 3)), value=15)
srt_file = st.file_uploader("Upload translated Myanmar SRT", type=["srt", "txt"])

if st.button("Generate TTS", type="primary", disabled=srt_file is None):
    text = srt_file.getvalue().decode("utf-8-sig")
    blocks = [block.strip().split("\n", 2) for block in text.replace("\r\n", "\n").split("\n\n") if block.strip()]
    cues = []
    for fallback_index, block in enumerate(blocks):
        if len(block) >= 3:
            try:
                index = int(block[0].strip())
            except ValueError:
                index = fallback_index
            cues.append({"index": index, "text": block[2].strip()})
    if not cues:
        st.error("No readable SRT cues found.")
    else:
        progress = st.progress(0, text="Connecting to Edge TTS...")
        async def on_progress(done: int, total: int):
            progress.progress(done / total, text=f"Generated TTS {done}/{total}")
        with st.status(f"Generating {len(cues)} cues with {workers} workers", expanded=True):
            items = asyncio.run(synthesize_batch(cues, resolve_settings(voice_id, style_id, emotion_id, rate, pitch)["voice"], rate, pitch, workers, on_progress))
        archive = make_zip(items)
        st.success(f"Generated {len(items)}/{len(cues)} MP3 files.")
        st.download_button("Download MP3 package", data=archive, file_name="tts-audio.zip", mime="application/zip")
        st.download_button("Download manifest JSON", data=json.dumps([{"index": item["index"], "bytes": item["bytes"]} for item in items], ensure_ascii=False, indent=2), file_name="manifest.json", mime="application/json")

with st.expander("Android API contract"):
    st.code("POST /synthesize-batch\n{\n  \"voice_id\": \"v1\",\n  \"style_id\": \"Normal\",\n  \"emotion_id\": \"NARRATIVE\",\n  \"rate\": 0,\n  \"pitch\": 0,\n  \"workers\": 15,\n  \"cues\": [{\"index\": 0, \"text\": \"...\"}]\n}\n\nResponse: {items: [{index, audioBase64, bytes}]}" , language="json")
