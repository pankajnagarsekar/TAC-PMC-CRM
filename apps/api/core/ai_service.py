"""
PHASE 2 WAVE 3 - PILLAR C: AI INTEGRATION LAYER

Implements:
- OCR Service (extract vendor, invoice, date, amount)
- STT Service (speech-to-text for voice logs)
- Vision Tagging Service (suggest CODE from images)

RULES:
- AI must NOT modify financial calculations
- Use mock provider if API keys absent
- Store raw + structured results
- Allow manual override with audit
"""

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
from datetime import datetime, timezone
from typing import Optional, Dict, List
from bson import ObjectId
from abc import ABC, abstractmethod
import logging
import json

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Raised when AI service fails"""
    pass


# =============================================================================
# PROVIDER ABSTRACTION
# =============================================================================

class AIProvider(ABC):
    """Abstract base class for AI providers"""

    @abstractmethod
    async def run_ocr(self, file_content: bytes, file_type: str) -> Dict:
        """Extract text and structured data from image/PDF"""
        pass

    @abstractmethod
    async def run_stt(self, audio_content: bytes, audio_format: str) -> Dict:
        """Convert speech to text"""
        pass

    @abstractmethod
    async def run_vision_tag(self, image_content: bytes) -> Dict:
        """Tag image with relevant labels"""
        pass

    @abstractmethod
    async def run_schedule_prediction(self, wbs_text: str) -> Dict:
        """Predict duration and category from WBS text"""
        pass

    @abstractmethod
    async def run_mom_extraction(self, meeting_notes: str) -> Dict:
        """Extract action items from meeting notes"""
        pass

class MockAIProvider(AIProvider):
    """Mock AI provider for testing when API keys absent"""

    async def run_ocr(self, file_content: bytes, file_type: str) -> Dict:
        """Mock OCR extraction"""
        logger.info("[AI:MOCK] Running mock OCR")
        return {
            "raw_text": "MOCK INVOICE\nVendor: Test Vendor Co.\nInvoice #: INV-2024-001\nDate: 2024-01-15\nAmount: $10,000.00",
            "structured": {
                "vendor_name": "Test Vendor Co.",
                "invoice_number": "INV-2024-001",
                "invoice_date": "2024-01-15",
                "amount": 10000.00,
                "currency": "USD"},
            "confidence": 0.85,
            "provider": "MOCK"}

    async def run_stt(self, audio_content: bytes, audio_format: str) -> Dict:
        """Mock STT"""
        logger.info("[AI:MOCK] Running mock STT")
        return {
            "transcript": "This is a mock transcript for testing purposes. Progress update for concrete work.",
            "confidence": 0.90,
            "duration_seconds": 15.0,
            "keywords_detected": [
                "progress",
                "concrete"],
            "provider": "MOCK"}

    async def run_vision_tag(self, image_content: bytes) -> Dict:
        """Mock vision tagging"""
        logger.info("[AI:MOCK] Running mock vision tagging")
        return {
            "tags": [
                {"label": "construction", "confidence": 0.95},
                {"label": "concrete", "confidence": 0.88},
                {"label": "foundation", "confidence": 0.75}
            ],
            "suggested_code": "CONCRETE-WORK",
            "confidence": 0.85,
            "provider": "MOCK"
        }

    async def run_schedule_prediction(self, wbs_text: str) -> Dict:
        """Mock schedule prediction"""
        logger.info(f"[AI:MOCK] Running schedule prediction for: {wbs_text[:30]}...")
        return {
            "suggested_duration": 5,
            "suggested_category": "CIV",
            "confidence": 0.78,
            "reasoning": "Standard excavation task based on historical averages.",
            "provider": "MOCK"
        }

    async def run_mom_extraction(self, meeting_notes: str) -> Dict:
        """Mock MoM extraction"""
        logger.info("[AI:MOCK] Running MoM extraction")
        return {
            "action_items": [
                {
                    "task": "Complete foundation pouring",
                    "assignee": "Contractor Alpha",
                    "deadline": "2024-04-15",
                    "priority": "HIGH"
                },
                {
                    "task": "Submit MEP drawings",
                    "assignee": "MEP Consultant",
                    "deadline": "2024-04-20",
                    "priority": "MEDIUM"
                }
            ],
            "summary": "Meeting discussed progress on foundation and next steps for MEP.",
            "confidence": 0.82,
            "provider": "MOCK"
        }


class EmergentAIProvider(AIProvider):
    """
    Emergent LLM integration for AI services.
    Uses Emergent Universal Key.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def run_ocr(self, file_content: bytes, file_type: str) -> Dict:
        """OCR using Emergent/OpenAI vision"""
        try:
            # Use OpenAI GPT-4 vision for OCR
            import base64
            from emergentintegrations.llm.openai import chat_completion, Message

            # Convert to base64
            b64_content = base64.b64encode(file_content).decode('utf-8')

            prompt = """Analyze this invoice/document image and extract:
1. Vendor Name
2. Invoice Number
3. Invoice Date (YYYY-MM-DD format)
4. Total Amount (numeric only)

Return JSON format:
{
    "vendor_name": "...",
    "invoice_number": "...",
    "invoice_date": "YYYY-MM-DD",
    "amount": 0.00,
    "raw_text": "full text visible in image"
}"""

            messages = [
                Message(
                    role="user", content=[
                        {
                            "type": "text", "text": prompt}, {
                            "type": "image_url", "image_url": {
                                "url": f"data:image/{file_type};base64,{b64_content}"}}])]

            response = await chat_completion(
                api_key=self.api_key,
                messages=messages,
                model="gpt-4o"
            )

            # Parse response
            result = json.loads(response.content)
            result["confidence"] = 0.90
            result["provider"] = "EMERGENT_OPENAI"
            return result

        except ImportError:
            logger.warning(
                "[AI] emergentintegrations not available, falling back to mock")
            return await MockAIProvider().run_ocr(file_content, file_type)
        except Exception as e:
            logger.error(f"[AI] OCR failed: {e}")
            raise AIServiceError(f"OCR failed: {e}")

    async def run_stt(self, audio_content: bytes, audio_format: str) -> Dict:
        """STT using OpenAI Whisper API with translation to English"""
        try:
            import httpx

            # Determine file extension
            ext_map = {
                'webm': 'webm',
                'mp3': 'mp3',
                'mp4': 'mp4',
                'm4a': 'm4a',
                'wav': 'wav',
                'mpeg': 'mpeg',
                'mpga': 'mpga',
                'ogg': 'ogg',
            }
            file_ext = ext_map.get(audio_format.lower(), 'mp3')

            # Use OpenAI Whisper API for transcription + translation
            async with httpx.AsyncClient(timeout=60.0) as client:
                # First, try translation endpoint (auto-detects language and
                # translates to English)
                files = {
                    'file': (
                        f'audio.{file_ext}',
                        audio_content,
                        f'audio/{file_ext}'),
                    'model': (
                        None,
                        'whisper-1'),
                }

                response = await client.post(
                    'https://api.openai.com/v1/audio/translations',
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    files=files,
                )

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "transcript": result.get('text', ''),
                        "language": "en",  # Translation always outputs English
                        "confidence": 0.95,
                        "provider": "OPENAI_WHISPER"
                    }
                else:
                    logger.error(
                        f"[AI] Whisper API error: {response.status_code} - {response.text}")
                    raise AIServiceError(
                        f"Whisper API failed: {
                            response.text}")

        except httpx.TimeoutException:
            logger.error("[AI] Whisper API timeout")
            raise AIServiceError("Speech transcription timed out")
        except Exception as e:
            logger.error(f"[AI] STT failed: {e}")
            raise AIServiceError(f"STT failed: {e}")

    async def run_vision_tag(self, image_content: bytes) -> Dict:
        """Vision tagging using Emergent/OpenAI"""
        try:
            import base64
            from emergentintegrations.llm.openai import chat_completion, Message

            b64_content = base64.b64encode(image_content).decode('utf-8')

            prompt = """Analyze this construction site image and:
1. List relevant tags (construction activities visible)
2. Suggest the most likely construction work code category

Return JSON:
{
    "tags": [{"label": "...", "confidence": 0.0-1.0}],
    "suggested_code": "CATEGORY-NAME",
    "description": "brief description"
}"""

            messages = [
                Message(role="user", content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_content}"}}
                ])
            ]

            response = await chat_completion(
                api_key=self.api_key,
                messages=messages,
                model="gpt-4o"
            )

            result = json.loads(response.content)
            result["confidence"] = 0.85
            result["provider"] = "EMERGENT_OPENAI"
            return result

        except ImportError:
            logger.warning(
                "[AI] emergentintegrations not available, falling back to mock")
            return await MockAIProvider().run_vision_tag(image_content)
        except Exception as e:
            logger.error(f"[AI] Vision tagging failed: {e}")
    async def run_schedule_prediction(self, wbs_text: str) -> Dict:
        """Predict duration and category from WBS text using GPT-4o"""
        try:
            from emergentintegrations.llm.openai import chat_completion, Message

            prompt = f"""Predict construction duration and category for this WBS item:
Task Name/Description: "{wbs_text}"

Return JSON format:
{{
    "suggested_duration": <integer_days>,
    "suggested_category": "<CIV|MEP|STR|FIN|EXT|INT>",
    "reasoning": "brief explanation",
    "confidence": 0.0-1.0
}}"""

            messages = [Message(role="user", content=prompt)]

            response = await chat_completion(
                api_key=self.api_key,
                messages=messages,
                model="gpt-4o"
            )

            result = json.loads(response.content)
            result["provider"] = "EMERGENT_OPENAI"
            return result

        except Exception as e:
            logger.error(f"[AI] Schedule prediction failed: {e}")
            raise AIServiceError(f"Schedule prediction failed: {e}")

    async def run_mom_extraction(self, meeting_notes: str) -> Dict:
        """Extract action items from meeting notes using GPT-4o"""
        try:
            from emergentintegrations.llm.openai import chat_completion, Message

            prompt = f"""Extract action items from these construction meeting notes:
---
{meeting_notes}
---
Return JSON format:
{{
    "action_items": [
        {{
            "task": "...",
            "assignee": "...",
            "deadline": "YYYY-MM-DD | null",
            "priority": "LOW|MEDIUM|HIGH"
        }}
    ],
    "summary": "one sentence meeting summary",
    "confidence": 0.0-1.0
}}"""

            messages = [Message(role="user", content=prompt)]

            response = await chat_completion(
                api_key=self.api_key,
                messages=messages,
                model="gpt-4o"
            )

            result = json.loads(response.content)
            result["provider"] = "EMERGENT_OPENAI"
            return result

        except Exception as e:
            logger.error(f"[AI] MoM extraction failed: {e}")
            raise AIServiceError(f"MoM extraction failed: {e}")


# =============================================================================
# AI SERVICE
# =============================================================================

class AIService:
    """
    AI Service Abstraction Layer.

    Features:
    - Provider abstraction (mock/real)
    - Result storage
    - Manual override with audit
    - NO modification of financial calculations
    """

    ISSUE_KEYWORDS = [
        "problem",
        "issue",
        "damage",
        "delay",
        "accident",
        "safety",
        "urgent"]

    def __init__(
            self,
            db: AsyncIOMotorDatabase,
            client: Optional[AsyncIOMotorClient] = None,
            api_key: Optional[str] = None):
        from core.database import db_manager
        self.client = client if client is not None else db_manager.client
        self.db = db

        # Select provider based on API key availability
        if api_key:
            self.provider = EmergentAIProvider(api_key)
            logger.info("[AI] Using Emergent AI provider")
        else:
            self.provider = MockAIProvider()
            logger.info("[AI] Using Mock AI provider (no API key)")

    # =========================================================================
    # OCR SERVICE
    # =========================================================================

    async def run_ocr(
        self,
        file_content: bytes,
        file_type: str,
        organisation_id: str,
        user_id: str,
        project_id: Optional[str] = None
    ) -> Dict:
        """
        Run OCR on document.

        RULES:
        - Extract vendor, invoice number, date, amount
        - Return confidence score
        - Do NOT auto-create PC
        - Store raw text + structured result
        """
        # Run OCR
        result = await self.provider.run_ocr(file_content, file_type)

        # Store result
        ocr_doc = {
            "organisation_id": organisation_id,
            "project_id": project_id,
            "file_type": file_type,
            "file_size": len(file_content),
            "raw_text": result.get("raw_text", ""),
            "structured_data": result.get("structured", {}),
            "confidence": result.get("confidence", 0),
            "provider": result.get("provider", "UNKNOWN"),
            "extracted_by": user_id,
            "extracted_at": datetime.now(timezone.utc),
            "manually_verified": False,
            "verified_data": None
        }

        db_result = await self.db.ocr_results.insert_one(ocr_doc)
        ocr_id = str(db_result.inserted_id)

        logger.info(
            f"[AI:OCR] Completed: {ocr_id} confidence={
                result.get('confidence')}")

        return {
            "ocr_id": ocr_id,
            **result
        }

    async def verify_ocr_result(
        self,
        ocr_id: str,
        verified_data: Dict,
        user_id: str,
        organisation_id: str
    ):
        """
        Manually verify/correct OCR result.
        Logs override event.
        """
        ocr_doc = await self.db.ocr_results.find_one({"_id": ObjectId(ocr_id)})

        if not ocr_doc:
            raise ValueError(f"OCR result {ocr_id} not found")

        old_data = ocr_doc.get("structured_data", {})

        await self.db.ocr_results.update_one(
            {"_id": ObjectId(ocr_id)},
            {
                "$set": {
                    "manually_verified": True,
                    "verified_data": verified_data,
                    "verified_by": user_id,
                    "verified_at": datetime.now(timezone.utc)
                }
            }
        )

        # Audit log override
        await self._log_audit(
            organisation_id=organisation_id,
            entity_type="OCR_RESULT",
            entity_id=ocr_id,
            action="MANUAL_OVERRIDE",
            user_id=user_id,
            old_value={"structured_data": old_data},
            new_value={"verified_data": verified_data}
        )

        logger.info(f"[AI:OCR] Verified: {ocr_id} by {user_id}")

    # =========================================================================
    # STT SERVICE
    # =========================================================================

    async def run_stt(
        self,
        audio_content: bytes,
        audio_format: str,
        organisation_id: str,
        user_id: str,
        project_id: str,
        code_id: Optional[str] = None
    ) -> Dict:
        """
        Run speech-to-text on audio.

        RULES:
        - Store transcript and confidence
        - Bind to selected CODE
        - If keyword detected -> create Issue
        """
        # Run STT
        result = await self.provider.run_stt(audio_content, audio_format)

        transcript = result.get("transcript", "")

        # Check for issue keywords
        detected_keywords = []
        for keyword in self.ISSUE_KEYWORDS:
            if keyword.lower() in transcript.lower():
                detected_keywords.append(keyword)

        # Store result
        stt_doc = {
            "organisation_id": organisation_id,
            "project_id": project_id,
            "code_id": code_id,
            "audio_format": audio_format,
            "audio_size": len(audio_content),
            "transcript": transcript,
            "confidence": result.get("confidence", 0),
            "duration_seconds": result.get("duration_seconds", 0),
            "keywords_detected": detected_keywords,
            "provider": result.get("provider", "UNKNOWN"),
            "transcribed_by": user_id,
            "transcribed_at": datetime.now(timezone.utc),
            "issue_created": False,
            "issue_id": None
        }

        db_result = await self.db.stt_results.insert_one(stt_doc)
        stt_id = str(db_result.inserted_id)

        # Auto-create issue if keywords detected
        issue_id = None
        if detected_keywords:
            issue_id = await self._create_issue_from_stt(
                organisation_id=organisation_id,
                project_id=project_id,
                code_id=code_id,
                transcript=transcript,
                keywords=detected_keywords,
                user_id=user_id,
                stt_id=stt_id
            )

            await self.db.stt_results.update_one(
                {"_id": ObjectId(stt_id)},
                {"$set": {"issue_created": True, "issue_id": issue_id}}
            )

        logger.info(
            f"[AI:STT] Completed: {stt_id} keywords={detected_keywords}")

        return {
            "stt_id": stt_id,
            "transcript": transcript,
            "confidence": result.get("confidence", 0),
            "keywords_detected": detected_keywords,
            "issue_created": issue_id is not None,
            "issue_id": issue_id
        }

    async def _create_issue_from_stt(
        self,
        organisation_id: str,
        project_id: str,
        code_id: Optional[str],
        transcript: str,
        keywords: List[str],
        user_id: str,
        stt_id: str
    ) -> str:
        """Create issue from STT keyword detection"""
        issue_doc = {
            "organisation_id": organisation_id,
            "project_id": project_id,
            "code_id": code_id,
            "title": "Issue detected from voice log",
            "description": f"Keywords detected: {
                ', '.join(keywords)}\n\nTranscript:\n{transcript}",
            "source": "STT_AUTO",
            "stt_id": stt_id,
            "status": "OPEN",
            "priority": "MEDIUM" if "urgent" not in keywords else "HIGH",
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc)}

        result = await self.db.issues.insert_one(issue_doc)
        issue_id = str(result.inserted_id)

        # Audit log
        await self._log_audit(
            organisation_id=organisation_id,
            entity_type="ISSUE",
            entity_id=issue_id,
            action="AUTO_CREATE_FROM_STT",
            user_id="SYSTEM",
            new_value={"keywords": keywords, "stt_id": stt_id}
        )

        logger.info(f"[AI:STT] Issue auto-created: {issue_id}")

        return issue_id

    # =========================================================================
    # VISION TAGGING SERVICE
    # =========================================================================

    async def run_vision_tag(
        self,
        image_content: bytes,
        organisation_id: str,
        user_id: str,
        project_id: str
    ) -> Dict:
        """
        Run vision tagging on image.

        RULES:
        - Suggest CODE based on image
        - Store confidence
        - Allow manual override
        """
        # Run vision tagging
        result = await self.provider.run_vision_tag(image_content)

        # Store result
        tag_doc = {
            "organisation_id": organisation_id,
            "project_id": project_id,
            "image_size": len(image_content),
            "tags": result.get("tags", []),
            "suggested_code": result.get("suggested_code"),
            "confidence": result.get("confidence", 0),
            "provider": result.get("provider", "UNKNOWN"),
            "tagged_by": user_id,
            "tagged_at": datetime.now(timezone.utc),
            "manually_overridden": False,
            "override_code": None
        }

        db_result = await self.db.vision_tags.insert_one(tag_doc)
        tag_id = str(db_result.inserted_id)

        logger.info(
            f"[AI:VISION] Completed: {tag_id} suggested={
                result.get('suggested_code')}")

        return {
            "tag_id": tag_id,
            **result
        }

    async def override_vision_tag(
        self,
        tag_id: str,
        override_code: str,
        user_id: str,
        organisation_id: str
    ):
        """
        Manually override vision tag suggestion.
        Logs override event.
        """
        tag_doc = await self.db.vision_tags.find_one({"_id": ObjectId(tag_id)})

        if not tag_doc:
            raise ValueError(f"Vision tag {tag_id} not found")

        old_code = tag_doc.get("suggested_code")

        await self.db.vision_tags.update_one(
            {"_id": ObjectId(tag_id)},
            {
                "$set": {
                    "manually_overridden": True,
                    "override_code": override_code,
                    "overridden_by": user_id,
                    "overridden_at": datetime.now(timezone.utc)
                }
            }
        )

        # Audit log override
        await self._log_audit(
            organisation_id=organisation_id,
            entity_type="VISION_TAG",
            entity_id=tag_id,
            action="MANUAL_OVERRIDE",
            user_id=user_id,
            old_value={"suggested_code": old_code},
            new_value={"override_code": override_code}
        )

        logger.info(
            f"[AI:VISION] Overridden: {tag_id} {old_code} -> {override_code}")

    # =========================================================================
    # SCHEDULE PREDICTION SERVICE
    # =========================================================================

    async def run_schedule_prediction(
        self,
        wbs_text: str,
        organisation_id: str,
        user_id: str,
        project_id: str,
        task_id: Optional[str] = None
    ) -> Dict:
        """
        Predict duration and category for a WBS item.
        Result is stored for audit and feedback loop.
        """
        try:
            result = await self.provider.run_schedule_prediction(wbs_text)

            prediction_doc = {
                "organisation_id": organisation_id,
                "project_id": project_id,
                "task_id": task_id,
                "input_text": wbs_text,
                "suggested_duration": result.get("suggested_duration"),
                "suggested_category": result.get("suggested_category"),
                "confidence": result.get("confidence", 0),
                "reasoning": result.get("reasoning", ""),
                "provider": result.get("provider", "UNKNOWN"),
                "created_by": user_id,
                "created_at": datetime.now(timezone.utc),
                "manually_confirmed": False
            }

            db_result = await self.db.schedule_predictions.insert_one(prediction_doc)
            prediction_id = str(db_result.inserted_id)

            logger.info(f"[AI:SCHEDULE] Prediction completed for task {task_id or 'new'}")

            return {
                "prediction_id": prediction_id,
                **result
            }
        except Exception as e:
            logger.warning(f"[AI:SCHEDULE] Prediction failed: {e}")
            # Graceful degradation logic handled by caller (returns empty suggestion)
            raise

    # =========================================================================
    # MoM EXTRACTION SERVICE
    # =========================================================================

    async def run_mom_extraction(
        self,
        meeting_notes: str,
        organisation_id: str,
        user_id: str,
        project_id: str,
        task_id: Optional[str] = None
    ) -> Dict:
        """
        Extract action items from meeting notes.
        Result is stored for audit.
        """
        try:
            result = await self.provider.run_mom_extraction(meeting_notes)

            mom_doc = {
                "organisation_id": organisation_id,
                "project_id": project_id,
                "task_id": task_id,
                "raw_notes": meeting_notes,
                "extracted_actions": result.get("action_items", []),
                "summary": result.get("summary", ""),
                "confidence": result.get("confidence", 0),
                "provider": result.get("provider", "UNKNOWN"),
                "created_by": user_id,
                "created_at": datetime.now(timezone.utc)
            }

            db_result = await self.db.mom_extractions.insert_one(mom_doc)
            mom_id = str(db_result.inserted_id)

            logger.info(f"[AI:MoM] Extraction completed for task {task_id or 'project'}")

            return {
                "mom_id": mom_id,
                **result
            }
        except Exception as e:
            logger.warning(f"[AI:MoM] Extraction failed: {e}")
            raise


    # =========================================================================
    # HELPER
    # =========================================================================

    async def _log_audit(
        self,
        organisation_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        user_id: str,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None
    ):
        """Log audit entry"""
        audit_doc = {
            "organisation_id": organisation_id,
            "module_name": "AI_SERVICE",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action_type": action,
            "old_value_json": old_value,
            "new_value_json": new_value,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc)
        }
        await self.db.audit_logs.insert_one(audit_doc)

    async def create_indexes(self):
        """Create indexes for AI results"""
        try:
            await self.db.ocr_results.create_index(
                [("organisation_id", 1), ("extracted_at", -1)],
                name="ocr_lookup"
            )
            await self.db.stt_results.create_index(
                [("organisation_id", 1), ("project_id", 1), ("transcribed_at", -1)],
                name="stt_lookup"
            )
            await self.db.vision_tags.create_index(
                [("organisation_id", 1), ("project_id", 1), ("tagged_at", -1)],
                name="vision_tag_lookup"
            )
            await self.db.issues.create_index(
                [("organisation_id", 1), ("project_id", 1), ("status", 1)],
                name="issue_lookup"
            )
            logger.info("AI service indexes created")
        except Exception as e:
            logger.warning(f"AI index creation: {e}")
