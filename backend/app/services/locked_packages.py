from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

LEGACY_FINAL_PACKAGE_SHA256 = "153549767fd3588a4b5694494b2495f7e030b4f9a7c12e9c5ca674a5680a90dc"
FINAL_PACKAGE_SHA256 = "7ae729205ddcfc942cf6eb5db60adbd3cd957ea3e30a29be2c675e75c2e4146b"



def verified_package(path: str | Path, expected_sha256: str) -> tuple[Path, bytes]:
    package_path = Path(path).expanduser().resolve(strict=True)
    content = package_path.read_bytes()
    digest = sha256(content).hexdigest()
    if digest != expected_sha256:
        raise ValueError(
            f"Package SHA-256 mismatch: expected {expected_sha256}, received {digest}."
        )
    return package_path, content


def package_members(content: bytes) -> list[str]:
    with ZipFile(BytesIO(content)) as archive:
        return archive.namelist()


def read_package_member(content: bytes, suffix: str) -> bytes:
    normalized = suffix.replace("\\", "/").casefold()
    with ZipFile(BytesIO(content)) as archive:
        matches = [
            name for name in archive.namelist()
            if name.replace("\\", "/").casefold().endswith(normalized)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one package member ending in {suffix!r}; found {len(matches)}."
            )
        return archive.read(matches[0])


def read_package_json(content: bytes, suffix: str) -> dict:
    value = json.loads(read_package_member(content, suffix).decode("utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Package member {suffix!r} must contain a JSON object.")
    return value


def read_package_csv(content: bytes, suffix: str) -> pd.DataFrame:
    return pd.read_csv(BytesIO(read_package_member(content, suffix)))


def csv_members_under(content: bytes, directory: str) -> list[tuple[str, pd.DataFrame]]:
    normalized = directory.replace("\\", "/").strip("/").casefold() + "/"
    result: list[tuple[str, pd.DataFrame]] = []
    with ZipFile(BytesIO(content)) as archive:
        for name in sorted(archive.namelist()):
            comparable = name.replace("\\", "/").casefold()
            if normalized in comparable and comparable.endswith(".csv"):
                result.append((name, pd.read_csv(BytesIO(archive.read(name)))))
    return result
