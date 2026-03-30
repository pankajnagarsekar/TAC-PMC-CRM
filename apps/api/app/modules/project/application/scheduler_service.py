import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.core.utils import serialize_doc
from app.modules.shared.domain.exceptions import ValidationError

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Sovereign Scheduler Controller.
    Orchestrates deterministic scheduling logic.
    """

    def __init__(self, db):
        self.db = db
        self.collection = db["project_schedules"]

    def run_scheduler_script(self, script_name: str, input_data: dict) -> dict:
        """Orchestrate calls to standalone, deterministic Python scripts."""
        # Adjusted for movement to app/modules/project/application/
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )  # apps/api/app
        script_path = os.path.join(base_dir, "modules", "scheduler", script_name)

        try:
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=json.dumps(input_data))

            if process.returncode != 0:
                error_msg = (
                    f"Scheduler execution error for {script_name}: {stderr or stdout}"
                )
                logger.error(error_msg)
                raise Exception(error_msg)

            return json.loads(stdout)
        except Exception as e:
            raise ValidationError(str(e))

    async def calculate_schedule(
        self, project_id: str, tasks: List[Dict[str, Any]], project_start: str
    ) -> Dict[str, Any]:
        input_payload = {"tasks": tasks, "project_start": project_start}
        results = self.run_scheduler_script("calculate_critical_path.py", input_payload)

        if "error" in results:
            raise ValidationError(results["error"])

        return results

    async def save_schedule(
        self, project_id: str, organisation_id: str, user_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        schedule_doc = {
            "project_id": project_id,
            "organisation_id": organisation_id,
            "tasks": data.get("tasks", []),
            "project_start": data.get("project_start"),
            "total_cost": data.get("total_cost"),
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc),
        }

        await self.collection.update_one(
            {"project_id": project_id, "organisation_id": organisation_id},
            {"$set": schedule_doc},
            upsert=True,
        )
        return {"message": "Project schedule saved successfully"}

    async def load_schedule(
        self, project_id: str, organisation_id: str
    ) -> Dict[str, Any]:
        schedule = await self.collection.find_one(
            {"project_id": project_id, "organisation_id": organisation_id}
        )

        if not schedule:
            return {
                "project_id": project_id,
                "tasks": [],
                "project_start": None,
                "total_cost": 0,
            }

        return serialize_doc(schedule)
