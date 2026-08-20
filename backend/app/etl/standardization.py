from __future__ import annotations

import re
import unicodedata


def standardize_account_name(raw_name: object) -> str:
    """Conservatively normalize harmless formatting without fuzzy merging."""
    text = unicodedata.normalize("NFKC", str(raw_name or ""))
    text = re.sub(r"\s+", " ", text.strip())
    return text.upper()


def possible_alias_key(raw_name: object) -> str:
    text = standardize_account_name(raw_name)
    return re.sub(r"[^A-Z0-9]", "", text)
