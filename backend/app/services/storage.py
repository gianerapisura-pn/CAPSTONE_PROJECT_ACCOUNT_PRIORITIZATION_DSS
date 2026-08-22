from __future__ import annotations

import re
from pathlib import Path

import httpx

from app.core.config import get_settings


def sanitize_filename(name: str) -> str:
    base = Path(name).name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return safe[:180] or "source_file"


class SourceStorage:
    def __init__(self) -> None:
        self.settings = get_settings()

    def put(self, batch_id: str, file_name: str, content: bytes) -> str:
        safe_name = sanitize_filename(file_name)
        path = f"{batch_id}/{safe_name}"
        if self.settings.demo_mode:
            target = Path(self.settings.demo_storage_path) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            return path
        url = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/{self.settings.supabase_storage_bucket}/{path}"
        headers = {"Authorization": f"Bearer {self.settings.supabase_service_role_key}",
                   "apikey": self.settings.supabase_service_role_key, "Content-Type": "application/octet-stream"}
        response = httpx.post(url, headers=headers, content=content, timeout=30)
        response.raise_for_status()
        return path

    def get(self, path: str) -> bytes:
        if self.settings.demo_mode:
            return (Path(self.settings.demo_storage_path) / path).read_bytes()
        url = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/authenticated/{self.settings.supabase_storage_bucket}/{path}"
        headers = {"Authorization": f"Bearer {self.settings.supabase_service_role_key}", "apikey": self.settings.supabase_service_role_key}
        response = httpx.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content


class ModelStorage:
    """Private persistence for validated CART artifacts."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def put(self, model_version: str, content: bytes) -> str:
        path = f"{sanitize_filename(model_version)}.joblib"
        if self.settings.demo_mode:
            target = Path(self.settings.demo_model_storage_path) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            return path
        url = (
            f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/"
            f"{self.settings.supabase_model_storage_bucket}/{path}"
        )
        headers = {
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "apikey": self.settings.supabase_service_role_key,
            "Content-Type": "application/octet-stream",
        }
        response = httpx.post(url, headers=headers, content=content, timeout=30)
        response.raise_for_status()
        return path

    def get(self, path: str) -> bytes:
        if self.settings.demo_mode:
            return (Path(self.settings.demo_model_storage_path) / path).read_bytes()
        url = (
            f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/authenticated/"
            f"{self.settings.supabase_model_storage_bucket}/{path}"
        )
        headers = {
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "apikey": self.settings.supabase_service_role_key,
        }
        response = httpx.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
