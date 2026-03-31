import os
import logging
from typing import Any, Dict

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
            return (
                "Sample Voice Summary (Mock): Foundations for Sector 7 are 100% complete. "
                "Starting steel reinforcement tomorrow."
            )

        try:
            import base64
            import tempfile

            from openai import AsyncOpenAI

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
                        model="whisper-1", file=audio_file
                    )
                return transcription.text
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.error(f"AI_STT_FAIL: {e}")
            raise ValidationError(f"Transcription failed: {str(e)}")

    async def extract_mom(
        self, project_id: str, task_id: str, raw_notes: str
    ) -> Dict[str, Any]:
        """
        Extracts action items and duration suggestions from meeting notes.
        """
        if not self.openai_key:
            logger.warning("AI_MOM: No API key found, returning mock extraction.")
            return {
                "action_items": [
                    {
                        "task_name": "Review foundations",
                        "assignee": "Architect",
                        "deadline": "Next Friday",
                    },
                    {
                        "task_name": "Order steel",
                        "assignee": "Procurement",
                        "deadline": "Monday",
                    },
                ],
                "suggested_duration_days": 5,
                "confidence_score": 0.85,
            }

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.openai_key)

            prompt = f"""
            Analyze the following meeting notes for a construction project (Task: {task_id}).
            Extract:
            1. Action items (task name, assignee, deadline).
            2. A suggested duration in working days for the next phase.

            Return output as JSON only with keys: action_items (list), suggested_duration_days (int), confidence_score (float 0-1).

            Notes:
            {raw_notes}
            """

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            import json

            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"AI_MOM_FAIL: {e}")
            raise ValidationError(f"AI Extraction failed: {str(e)}")
