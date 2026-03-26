import os
import shutil
from pathlib import Path
from typing import Optional
from app.core.config import settings

class StorageManager:
    def __init__(self, base_path: str = settings.STORAGE_PATH):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_file_path(self, relative_path: str) -> Path:
        return self.base_path / relative_path

    async def save_file(self, file_content: bytes, relative_path: str) -> str:
        full_path = self.get_file_path(relative_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(file_content)
        return str(relative_path)

    async def delete_file(self, relative_path: str) -> bool:
        full_path = self.get_file_path(relative_path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    async def exists(self, relative_path: str) -> bool:
        return self.get_file_path(relative_path).exists()

storage_manager = StorageManager()
