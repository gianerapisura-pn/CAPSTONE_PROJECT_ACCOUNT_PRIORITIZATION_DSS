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


def test_methodological_implementation_guards():
    cart = Path("app/analytics/predictive/cart.py").read_text(encoding="utf-8")
    sensitivity = Path("app/analytics/validation/sensitivity.py").read_text(encoding="utf-8")
    production_frontend = "\n".join(
        path.read_text(encoding="utf-8")
        for root in (Path("../frontend/app"), Path("../frontend/components"), Path("../frontend/lib"))
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx"}
    )
    assert "StandardScaler" not in cart
    assert '"rfm_score"' not in cart.partition("CANDIDATE_FEATURES = [")[2].partition("]")[0]
    assert "* (1 + rng.uniform(" in sensitivity
    assert "demoPriorities" not in production_frontend
