from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import streamlit as st

from tts_engine import EMOTIONS, RECAP_STYLES, VOICES, make_zip, resolve_settings, synthesize_batch

st.set_page_config(page_title="Before Editing TTS Generator", page_icon="🔊", layout="wide")
st.title("🔊 Before Editing • TTS Generator")
st.caption("SRT တင်ပြီး TTS ZIP ထုတ်ပါ။ Android app မှာ original video နဲ့ ZIP ကို local render လုပ်ပါမယ်။")


def timestamp_to_ms(value: str) -> int:
    match = re.fullmatch(r"(\d+):(\d{2}):(\d{2})[,.](\d{3})", value.strip())
    if not match:
        raise ValueError(f"Invalid SRT timestamp: {value}")
    hours, minutes, seconds, millis = (int(part) for part in match.groups())
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def parse_srt(text: str) -> list[dict[str, object]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    blocks = re.split(r"\n\s*\n", normalized.strip())
    cues: list[dict[str, object]] = []
    for fallback_index, block in enumerate(blocks, start=1):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), -1)
        if timing_index < 0 or timing_index + 1 >= len(lines):
            continue
        start_raw, end_raw = (part.strip() for part in lines[timing_index].split("-->", 1))
        try:
            start_ms, end_ms = timestamp_to_ms(start_raw), timestamp_to_ms(end_raw)
        except ValueError:
            continue
        cue_text = " ".join(lines[timing_index + 1:]).strip()
        if not cue_text or end_ms <= start_ms:
            continue
        try:
            index = int(lines[0])
        except ValueError:
            index = fallback_index
        cues.append({"index": index, "startMs": start_ms, "endMs": end_ms, "text": cue_text})
    if not cues:
        raise ValueError("No readable SRT cues found.")
    return cues


voice_id = st.selectbox("Voice", options=[item["id"] for item in VOICES], format_func=lambda value: next(item["label"] for item in VOICES if item["id"] == value))
style_id = st.selectbox("Style", options=[item["id"] for item in RECAP_STYLES], format_func=lambda value: next(item["name"] for item in RECAP_STYLES if item["id"] == value))
emotion_id = st.selectbox("Emotion", options=[item["id"] for item in EMOTIONS], format_func=lambda value: next(item["name"] for item in EMOTIONS if item["id"] == value))
settings = resolve_settings(voice_id, style_id, emotion_id)
st.info(f"Preset speed: {settings['rate']:+d}% • Preset pitch: {settings['pitch']:+d}Hz")
workers = st.select_slider("TTS parallel workers", options=list(range(3, 31, 3)), value=30)
srt_file = st.file_uploader("Upload translated Myanmar SRT", type=["srt", "txt"])

if st.button("Generate timestamped TTS ZIP", type="primary", disabled=srt_file is None):
    try:
        cues = parse_srt(srt_file.getvalue().decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as error:
        st.error(str(error))
        st.stop()

    progress = st.progress(0, text="Connecting to Edge TTS...")

    async def on_progress(done: int, total: int):
        progress.progress(done / total, text=f"Generated TTS {done}/{total}")

    with st.status(f"Generating {len(cues)} cues with {workers} parallel workers", expanded=True):
        items = asyncio.run(
            synthesize_batch(
                cues,
                settings["voice"],
                settings["rate"],
                settings["pitch"],
                workers,
                on_progress,
            )
        )
    archive = make_zip(items)
    st.success(f"Generated {len(items)}/{len(cues)} timestamped MP3 files.")
    zip_name = f"{Path(srt_file.name).stem or 'tts'}.zip"
    st.download_button("Download TTS ZIP", data=archive, file_name=zip_name, mime="application/zip")
    manifest = [
        {key: item[key] for key in ("index", "startMs", "endMs", "text", "bytes")}
        for item in items
    ]
    st.download_button("Download manifest JSON", data=json.dumps(manifest, ensure_ascii=False, indent=2), file_name="manifest.json", mime="application/json")
    st.code("Example filename:\n00-00-00.000__00-00-03.500.mp3\n\nZIP contents:\n- timestamped MP3 files\n- manifest.json", language="text")

with st.expander("How to use with Android"):
    st.markdown("1. Upload the translated SRT here and generate the ZIP.\n2. Download the complete `tts-timestamped.zip`.\n3. In the Android app, upload the original video and this TTS ZIP.\n4. Android reads `manifest.json`, maps each MP3 to its SRT timestamp, and renders locally with FFmpeg.")
