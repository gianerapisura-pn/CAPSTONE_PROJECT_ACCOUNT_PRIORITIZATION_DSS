from __future__ import annotations

from pathlib import Path


OBSOLETE_TERMS = [
    "Settlement Behavior Score",
    "Moderate Inactivity Risk",
    "75% RFM",
    "25% Settlement",
    "60/40",
    "70/30",
    "80/20",
    "Stronger Account Pattern",
]


def test_production_ui_has_no_obsolete_methodology_terms():
    frontend = Path("../frontend")
    source_roots = [frontend / "app", frontend / "components", frontend / "lib", frontend / "types"]
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in source_roots
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".css"}
    )
    for term in OBSOLETE_TERMS:
        assert term not in text
