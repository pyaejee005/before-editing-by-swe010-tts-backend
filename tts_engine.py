from __future__ import annotations

import asyncio
import base64
import io
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import edge_tts

VOICES = [
    {"id": "v1", "label": "V1 ♂ Thiha (MM)", "voice": "my-MM-ThihaNeural"},
    {"id": "v2", "label": "V2 ♀ Nilar (MM)", "voice": "my-MM-NilarNeural"},
    {"id": "v3", "label": "V3 ♂ Giuseppe (IT)", "voice": "it-IT-GiuseppeMultilingualNeural"},
    {"id": "v4", "label": "V4 ♂ William (AU)", "voice": "en-AU-WilliamMultilingualNeural"},
    {"id": "v5", "label": "V5 ♂ Andrew (US)", "voice": "en-US-AndrewMultilingualNeural"},
    {"id": "v6", "label": "V6 ♀ Ava (US)", "voice": "en-US-AvaMultilingualNeural"},
    {"id": "v7", "label": "V7 ♂ Brian (US)", "voice": "en-US-BrianMultilingualNeural"},
    {"id": "v8", "label": "V8 ♀ Emma (US)", "voice": "en-US-EmmaMultilingualNeural"},
    {"id": "v9", "label": "V9 ♂ Remy (FR)", "voice": "fr-FR-RemyMultilingualNeural"},
    {"id": "v10", "label": "V10 ♀ Vivienne (FR)", "voice": "fr-FR-VivienneMultilingualNeural"},
    {"id": "v11", "label": "V11 ♀ Seraphina (DE)", "voice": "de-DE-SeraphinaMultilingualNeural"},
    {"id": "v12", "label": "V12 ♂ Florian (DE)", "voice": "de-DE-FlorianMultilingualNeural"},
    {"id": "v13", "label": "V13 ♀ Thalita (PT-BR)", "voice": "pt-BR-ThalitaMultilingualNeural"},
    {"id": "v14", "label": "V14 ♂ Hyunsu (KO)", "voice": "ko-KR-HyunsuMultilingualNeural"},
    {"id": "v15", "label": "V15 ♀ Jenny (US)", "voice": "en-US-JennyNeural"},
    {"id": "v16", "label": "V16 ♀ Aria (US)", "voice": "en-US-AriaNeural"},
    {"id": "v17", "label": "V17 ♂ Guy (US)", "voice": "en-US-GuyNeural"},
    {"id": "v18", "label": "V18 ♂ Ryan (GB)", "voice": "en-GB-RyanNeural"},
    {"id": "v19", "label": "V19 ♀ Sonia (GB)", "voice": "en-GB-SoniaNeural"},
]
VOICE_MAP = {item["id"]: item["voice"] for item in VOICES}

RECAP_STYLES = [
    {"id": "Normal", "name": "ပုံမှန်အသံ", "speed": 0, "pitch": 0},
    {"id": "NyoGyi_25", "name": "ကျားကြီး ၁", "speed": 0, "pitch": 25},
    {"id": "NyoGyi_35", "name": "ကျားကြီး ၂", "speed": 0, "pitch": 35},
    {"id": "NyoGyi_45", "name": "ကျားကြီး ၃", "speed": 0, "pitch": 45},
    {"id": "Nilar_40", "name": "နီလာ ချွဲသံ", "speed": 0, "pitch": 40},
    {"id": "Combo_15", "name": "ပေါင်းစပ် ၁၅", "speed": 15, "pitch": 15},
    {"id": "Combo_30", "name": "ပေါင်းစပ် ၃၀", "speed": 30, "pitch": 30},
    {"id": "Combo_50", "name": "ပေါင်းစပ် ၅၀", "speed": 50, "pitch": 50},
    {"id": "Pitch_20", "name": "အသံသေး ၂၀", "speed": 0, "pitch": 20},
    {"id": "Pitch_50", "name": "အသံသေး ၅၀", "speed": 0, "pitch": 50},
]
EMOTIONS = [
    {"id": "EXCITING", "name": "စိတ်လှုပ်ရှား 🤩", "speed": 15, "pitch": 10},
    {"id": "CALM", "name": "တည်ငြိမ် 😌", "speed": -10, "pitch": -5},
    {"id": "PROFESSIONAL", "name": "သတင်း 💼", "speed": 0, "pitch": -2},
    {"id": "NARRATIVE", "name": "ဇာတ်ကြောင်း 📖", "speed": -5, "pitch": 0},
    {"id": "HAPPY", "name": "ပျော်ရွှင် 😊", "speed": 10, "pitch": 15},
    {"id": "SERIOUS", "name": "လေးနက် 😠", "speed": -5, "pitch": -10},
    {"id": "WHISPER", "name": "တီးတိုး 🤫", "speed": -15, "pitch": -20},
    {"id": "SAD", "name": "ဝမ်းနည်း 😢", "speed": -15, "pitch": -15},
    {"id": "SARCASTIC", "name": "ရွဲ့ပြော 🙄", "speed": -10, "pitch": 5},
    {"id": "ANGRY", "name": "ဒေါသထွက် 🤬", "speed": 20, "pitch": -10},
    {"id": "FEAR", "name": "ကြောက်လန့် 😨", "speed": 10, "pitch": 20},
]
STYLE_MAP = {item["id"]: item for item in RECAP_STYLES}
EMOTION_MAP = {item["id"]: item for item in EMOTIONS}


def resolve_settings(voice_id: str, style_id: str, emotion_id: str, rate: int | None = None, pitch: int | None = None) -> dict[str, Any]:
    style = STYLE_MAP.get(style_id, RECAP_STYLES[0])
    emotion = EMOTION_MAP.get(emotion_id, EMOTIONS[0])
    return {
        "voice": VOICE_MAP.get(voice_id, VOICE_MAP["v1"]),
        "rate": int(style["speed"] + emotion["speed"] if rate is None else rate),
        "pitch": int(style["pitch"] + emotion["pitch"] if pitch is None else pitch),
    }


async def synthesize_bytes(text: str, voice: str, rate: int, pitch: int) -> bytes:
    if not text or not text.strip():
        raise ValueError("Cannot synthesize an empty subtitle cue")
    rate_value = f"{rate:+d}%"
    pitch_value = f"{pitch:+d}Hz"
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as handle:
        output = Path(handle.name)
    try:
        communicate = edge_tts.Communicate(text.strip(), voice, rate=rate_value, pitch=pitch_value)
        await communicate.save(str(output))
        return output.read_bytes()
    finally:
        output.unlink(missing_ok=True)


async def synthesize_batch(cues: list[dict[str, Any]], voice: str, rate: int, pitch: int, workers: int = 15, on_progress=None) -> list[dict[str, Any]]:
    limit = max(1, min(30, int(workers)))
    semaphore = asyncio.Semaphore(limit)
    results: list[dict[str, Any] | None] = [None] * len(cues)
    completed = 0
    progress_lock = asyncio.Lock()

    async def one(index: int, cue: dict[str, Any]) -> None:
        nonlocal completed
        async with semaphore:
            audio = await synthesize_bytes(str(cue.get("text", "")), voice, rate, pitch)
        async with progress_lock:
            completed += 1
            if on_progress:
                await on_progress(completed, len(cues))
        results[index] = {"index": int(cue.get("index", index)), "audioBase64": base64.b64encode(audio).decode("ascii"), "bytes": len(audio)}

    await asyncio.gather(*(one(index, cue) for index, cue in enumerate(cues)))
    return [item for item in results if item is not None]


def make_zip(items: list[dict[str, Any]]) -> bytes:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest = []
        for item in items:
            name = f"audio_{int(item['index']):05d}.mp3"
            zf.writestr(name, base64.b64decode(item["audioBase64"]))
            manifest.append({"index": item["index"], "file": name, "bytes": item["bytes"]})
        import json
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return archive.getvalue()
