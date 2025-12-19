# backend/app/audio_transcription.py
import os
import tempfile
from typing import Dict, Any
from fastapi import UploadFile
from openai import OpenAI


async def transcribe_audio(file: UploadFile, client: OpenAI = None) -> Dict[str, Any]:
    """Transcribe audio using OpenAI Whisper."""
    if not client:
        return {"text": ""}

    try:
        audio_bytes = await file.read()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    response_format="text"
                )
            return {"text": transcript.strip()}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        return {"text": "", "error": str(e)}