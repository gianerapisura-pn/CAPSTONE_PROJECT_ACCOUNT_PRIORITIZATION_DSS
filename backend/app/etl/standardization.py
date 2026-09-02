from __future__ import annotations

import re


def standardize_account_name(raw_name: object) -> str:
    """Preserve the supplied account label after whitespace-only cleanup."""
    return re.sub(r"\s+", " ", str(raw_name or "").strip())


def possible_alias_key(raw_name: object) -> str:
    text = standardize_account_name(raw_name).upper()
    return re.sub(r"[^A-Z0-9]", "", text)
