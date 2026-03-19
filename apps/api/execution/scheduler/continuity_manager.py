import json
import os
from datetime import datetime

REGISTRY_PATH = ".tmp/continuity_registry.json"

def get_registry():
    if not os.path.exists(REGISTRY_PATH):
        os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
        with open(REGISTRY_PATH, "w") as f:
            json.dump({}, f)
        return {}
    
    with open(REGISTRY_PATH, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def update_milestone(project_id: str, milestone: str, status: str = "InProgress"):
    registry = get_registry()
    if project_id not in registry:
        registry[project_id] = {"milestones": {}, "last_updated": None}
    
    registry[project_id]["milestones"][milestone] = {
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    registry[project_id]["last_updated"] = datetime.now().isoformat()
    
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)

def get_project_status(project_id: str):
    registry = get_registry()
    return registry.get(project_id, {"status": "Not Started"})
