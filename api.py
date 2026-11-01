from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from tts_engine import VOICES, EMOTIONS, RECAP_STYLES, resolve_settings, synthesize_batch

app = FastAPI(title="Before Editing Swe010 TTS Backend", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Cue(BaseModel):
    index: int = 0
    text: str = Field(min_length=1, max_length=4096)

class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    voice_id: str = "v1"
    style_id: str = "Normal"
    emotion_id: str = "NARRATIVE"
    rate: int | None = Field(default=None, ge=-100, le=200)
    pitch: int | None = Field(default=None, ge=-100, le=200)

class BatchRequest(BaseModel):
    voice_id: str = "v1"
    style_id: str = "Normal"
    emotion_id: str = "NARRATIVE"
    rate: int | None = Field(default=None, ge=-100, le=200)
    pitch: int | None = Field(default=None, ge=-100, le=200)
    cues: list[Cue] = Field(min_length=1, max_length=1000)
    workers: int = Field(default=15, ge=3, le=30)


def check_token(token: str | None) -> None:
    expected = os.getenv("BACKEND_TOKEN", "").strip()
    if expected and token != expected:
        raise HTTPException(status_code=401, detail="Invalid backend token")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "tts"}


@app.get("/presets")
def presets() -> dict[str, Any]:
    return {"voices": VOICES, "styles": RECAP_STYLES, "emotions": EMOTIONS}


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest, x_app_token: str | None = Header(default=None)) -> dict[str, Any]:
    check_token(x_app_token)
    settings = resolve_settings(request.voice_id, request.style_id, request.emotion_id, request.rate, request.pitch)
    items = await synthesize_batch([{"index": 0, "text": request.text}], settings["voice"], settings["rate"], settings["pitch"], workers=1)
    return {"index": 0, "audioBase64": items[0]["audioBase64"], "bytes": items[0]["bytes"], "voice": settings["voice"], "rate": settings["rate"], "pitch": settings["pitch"]}


@app.post("/synthesize-batch")
async def synthesize_batch_endpoint(request: BatchRequest, x_app_token: str | None = Header(default=None)) -> dict[str, Any]:
    check_token(x_app_token)
    settings = resolve_settings(request.voice_id, request.style_id, request.emotion_id, request.rate, request.pitch)
    items = await synthesize_batch([cue.model_dump() for cue in request.cues], settings["voice"], settings["rate"], settings["pitch"], workers=request.workers)
    return {"items": items, "voice": settings["voice"], "rate": settings["rate"], "pitch": settings["pitch"], "count": len(items)}
