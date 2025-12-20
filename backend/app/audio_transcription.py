import os
import tempfile
from typing import Dict, Any
from fastapi import UploadFile
from openai import OpenAI


async def transcribe_audio(file: UploadFile, client: OpenAI = None) -> Dict[str, Any]:
    """Transcribe audio using OpenAI Whisper with English language preference."""
    if not client:
        return {"text": "", "error": "Transcription service unavailable"}

    try:
        audio_bytes = await file.read()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as audio:
                # Whisper auto-detects language but we specify English for better accuracy
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    language="en",  # Primary language is English
                    response_format="text"
                )

            transcript = transcript.strip()

            # Check if transcript is empty
            if not transcript:
                return {"text": "", "error": "No speech detected. Please speak clearly."}

            # Return the transcript - let the frontend handle language detection
            # Whisper is good at English transcription, so we trust it
            return {"text": transcript}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        return {"text": "", "error": f"Transcription error: {str(e)}"}