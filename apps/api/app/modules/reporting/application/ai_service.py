import os
import logging
from typing import Dict, Any
from app.core.config import settings
from app.modules.shared.domain.exceptions import ValidationError

logger = logging.getLogger(__name__)

class AIService:
    """
    Handles AI capabilities like Speech-to-Text and OCR.
    """
    def __init__(self, db):
        self.db = db
        self.openai_key = settings.OPENAI_API_KEY

    async def transcribe_audio(self, user: dict, audio_base64: str) -> str:
        """
        Transcribes base64 audio data using OpenAI Whisper.
        """
        if not self.openai_key:
            logger.warning("AI_STT: No API key found, returning mock transcription.")
            return "Sample Voice Summary (Mock): Foundations for Sector 7 are 100% complete. Starting steel reinforcement tomorrow."

        try:
            from openai import AsyncOpenAI
            import base64
            import tempfile

            client = AsyncOpenAI(api_key=self.openai_key)
            
            # Handle Data URL prefix if present
            if "," in audio_base64:
                audio_base64 = audio_base64.split(",")[1]
                
            # Decode base64 to binary
            audio_binary = base64.b64decode(audio_base64)
            
            with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
                tmp.write(audio_binary)
                tmp_path = tmp.name

            try:
                with open(tmp_path, "rb") as audio_file:
                    transcription = await client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file
                    )
                return transcription.text
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.error(f"AI_STT_FAIL: {e}")
            raise ValidationError(f"Transcription failed: {str(e)}")
