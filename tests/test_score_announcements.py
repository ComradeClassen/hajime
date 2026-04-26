# tests/test_score_announcements.py
# HAJ-45 — single unified scoring event covering both throw and pin sources.
#
# Pre-HAJ-45, a scored throw emitted two events on the same tick:
#   1. THROW_LANDING with description "[score] ... → waza-ari ..."
#   2. WAZA_ARI_AWARDED with description "[ref: ...] Waza-ari! ..."
# A pin waza-ari emitted only the [ref] line (no [score] line at all).
# Pin ippon emitted two IPPON_AWARDED events.
#
# Post-HAJ-45 there is exactly one event per scoring action, with consistent
# `outcome`, `source`, and `data` fields across throw and pin paths.

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from referee import build_suzuki


def test_announce_score_throw_waza_ari_unified() -> None:
    ref = build_suzuki()
    ev = ref.announce_score(
        outcome="WAZA_ARI", scorer_id="Sato", count=1, tick=42,
        source="throw", technique="Uchi-mata", detail="hip-loaded variant",
        execution_quality=0.71, quality_band="GOOD",
    )
    assert ev.event_type == "WAZA_ARI_AWARDED"
    assert "Waza-ari!" in ev.description
    assert "Sato" in ev.description
    assert "(1/2)" in ev.description
    assert "Uchi-mata" in ev.description
    assert "[score]" not in ev.description
    assert ev.data["outcome"] == "WAZA_ARI"
    assert ev.data["source"] == "throw"
    assert ev.data["technique"] == "Uchi-mata"
    assert ev.data["execution_quality"] == 0.71
    assert ev.data["quality_band"] == "GOOD"
    assert ev.data["count"] == 1


def test_announce_score_throw_ippon_unified() -> None:
    ref = build_suzuki()
    ev = ref.announce_score(
        outcome="IPPON", scorer_id="Tanaka", tick=99,
        source="throw", technique="Seoi-nage", detail="clean dorsal landing",
        execution_quality=0.92, quality_band="ELITE",
    )
    assert ev.event_type == "IPPON_AWARDED"
    assert "Ippon!" in ev.description
    assert "Tanaka" in ev.description
    assert "Seoi-nage" in ev.description
    assert "[score]" not in ev.description
    assert ev.data["outcome"] == "IPPON"
    assert ev.data["source"] == "throw"


def test_announce_score_pin_waza_ari_now_emits() -> None:
    """Pre-HAJ-45 a pin waza-ari had no [score] line at all. Now it produces
    a unified WAZA_ARI_AWARDED event with source='pin' and the hold time."""
    ref = build_suzuki()
    ev = ref.announce_score(
        outcome="WAZA_ARI", scorer_id="Tanaka", count=1, tick=80,
        source="pin", detail="10s hold",
    )
    assert ev.event_type == "WAZA_ARI_AWARDED"
    assert "Waza-ari!" in ev.description
    assert "by pin" in ev.description
    assert "10s hold" in ev.description
    assert ev.data["source"] == "pin"
    assert ev.data["outcome"] == "WAZA_ARI"


def test_announce_score_pin_ippon_unified() -> None:
    """Pin ippon used to fire IPPON_AWARDED twice. Now: one event."""
    ref = build_suzuki()
    ev = ref.announce_score(
        outcome="IPPON", scorer_id="Tanaka", tick=145,
        source="pin", detail="20s hold",
    )
    assert ev.event_type == "IPPON_AWARDED"
    assert "Ippon!" in ev.description
    assert "by pin" in ev.description
    assert "20s hold" in ev.description
    assert ev.data["source"] == "pin"


def test_no_legacy_score_helpers() -> None:
    """The pre-HAJ-45 split helpers are gone — only announce_score remains."""
    ref = build_suzuki()
    assert not hasattr(ref, "announce_waza_ari")
    assert not hasattr(ref, "announce_ippon")
