# tests/test_match_viewer_ticker_altitude.py
# Narration-altitude filter for the on-screen event ticker. Per
# session feedback, the in-viewer log shouldn't surface every move
# event / SUB_TSUKURI / SUB_KAKE_COMMIT — drop those, keep narrative
# beats (kuzushi induction, grip kills, throws, scores, referee).
#
# Tests don't open a pygame window. They construct PygameMatchRenderer
# directly (it imports pygame in __init__ but doesn't init the
# display until start()) and call _absorb_tick with synthetic events
# carrying significance values, asserting which land in the ticker.

from __future__ import annotations

import io
import os
import random
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from grip_graph import Event
from match import Match
from match_viewer import (
    PygameMatchRenderer, TICKER_ALTITUDES,
)
from referee import build_suzuki
from significance import (
    THRESHOLD_MAT_SIDE, THRESHOLD_STANDS,
    THRESHOLD_REVIEW, THRESHOLD_BROADCAST,
)
import main as main_module


def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _ticker_texts(renderer: PygameMatchRenderer) -> list[str]:
    """Project the event_log to its description column."""
    return [desc for _tick, desc, _frame in renderer._event_log]


def _ev(tick: int, etype: str, desc: str, sig: int) -> Event:
    e = Event(tick=tick, event_type=etype, description=desc)
    e.significance = sig
    return e


def _renderer(threshold: int) -> PygameMatchRenderer:
    return PygameMatchRenderer(
        ticks_per_second=1.0,
        ticker_altitude_threshold=threshold,
    )


# ---------------------------------------------------------------------------
# Defaults + altitude vocabulary
# ---------------------------------------------------------------------------
def test_ticker_altitudes_dict_has_four_named_levels() -> None:
    assert TICKER_ALTITUDES == {
        "mat_side":  THRESHOLD_MAT_SIDE,
        "stands":    THRESHOLD_STANDS,
        "review":    THRESHOLD_REVIEW,
        "broadcast": THRESHOLD_BROADCAST,
    }


def test_default_threshold_is_stands() -> None:
    """Per the May 2026 feedback rebuild, the default in-viewer
    log altitude is 'stands' (4) — drops per-tick mechanics."""
    r = PygameMatchRenderer(ticks_per_second=1.0)
    assert r._ticker_altitude_threshold == THRESHOLD_STANDS


# ---------------------------------------------------------------------------
# Filter behaviour at the stands altitude (default)
# ---------------------------------------------------------------------------
def test_stands_drops_below_threshold() -> None:
    """An event with significance below STANDS shouldn't appear in
    the ticker. Move events / SUB_TSUKURI / SUB_KAKE_COMMIT all
    sit at significance 1 in the engine."""
    r = _renderer(THRESHOLD_STANDS)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), max_ticks=5)
    events = [
        _ev(1, "MOVE", "[move] Tanaka closes 0.5m.", sig=1),
        _ev(1, "SUB_TSUKURI", "[sub] tsukuri building.", sig=1),
        _ev(1, "SUB_KAKE_COMMIT", "[sub] kake commit.", sig=1),
        _ev(1, "GRIP_DEEPEN", "[grip] deepens.", sig=2),
    ]
    r._absorb_tick(1, m, events)
    assert _ticker_texts(r) == []


def test_stands_keeps_at_or_above_threshold() -> None:
    """STANDS keeps significance >= 4: kuzushi (4), grip kills (4),
    desperation enter (4), referee beats (5+), throws, scores."""
    r = _renderer(THRESHOLD_STANDS)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), max_ticks=5)
    events = [
        _ev(2, "KUZUSHI_INDUCED", "[physics] Sato off-balance.", sig=4),
        _ev(2, "GRIP_STRIPPED", "[grip] Tanaka loses lapel.", sig=4),
        _ev(2, "MATTE_CALLED", "[ref] Matte!", sig=5),
        _ev(2, "WAZA_ARI_AWARDED", "[ref] Waza-ari!", sig=9),
    ]
    r._absorb_tick(2, m, events)
    texts = _ticker_texts(r)
    assert "[physics] Sato off-balance." in texts
    assert "[grip] Tanaka loses lapel." in texts
    assert "[ref] Matte!" in texts
    assert "[ref] Waza-ari!" in texts


# ---------------------------------------------------------------------------
# Filter behaviour at other altitudes
# ---------------------------------------------------------------------------
def test_mat_side_keeps_everything_with_description() -> None:
    """Threshold MAT_SIDE = 1 — equivalent to the legacy 'show
    every event with prose' behaviour, including SUB_* and move."""
    r = _renderer(THRESHOLD_MAT_SIDE)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), max_ticks=5)
    events = [
        _ev(1, "MOVE", "[move] Tanaka closes.", sig=1),
        _ev(1, "GRIP_DEEPEN", "[grip] deepens.", sig=2),
    ]
    r._absorb_tick(1, m, events)
    assert _ticker_texts(r) == ["[move] Tanaka closes.", "[grip] deepens."]


def test_review_drops_kuzushi_keeps_throws() -> None:
    """REVIEW = 7 drops grip kills (4) + kuzushi (4) + matte (5) +
    shido (5) but keeps throws (7), counters (7), ne-waza
    transitions (7), score events (9+)."""
    r = _renderer(THRESHOLD_REVIEW)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), max_ticks=5)
    events = [
        _ev(3, "KUZUSHI_INDUCED", "[physics] off-balance.", sig=4),
        _ev(3, "MATTE_CALLED", "[ref] Matte!", sig=5),
        _ev(3, "THROW_LANDING", "[throw] Tanaka lands seoi.", sig=7),
        _ev(3, "WAZA_ARI_AWARDED", "[ref] Waza-ari!", sig=9),
    ]
    r._absorb_tick(3, m, events)
    texts = _ticker_texts(r)
    assert "[physics] off-balance." not in texts
    assert "[ref] Matte!" not in texts
    assert "[throw] Tanaka lands seoi." in texts
    assert "[ref] Waza-ari!" in texts


def test_broadcast_only_score_defining_moments() -> None:
    """BROADCAST = 9 keeps only score-defining events (waza-ari,
    ippon, time expired, match over). Throws (7) are out."""
    r = _renderer(THRESHOLD_BROADCAST)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), max_ticks=5)
    events = [
        _ev(4, "THROW_LANDING", "[throw] lands.", sig=7),
        _ev(4, "WAZA_ARI_AWARDED", "[ref] Waza-ari!", sig=9),
        _ev(4, "IPPON_AWARDED", "[ref] Ippon!", sig=10),
    ]
    r._absorb_tick(4, m, events)
    texts = _ticker_texts(r)
    assert "[throw] lands." not in texts
    assert "[ref] Waza-ari!" in texts
    assert "[ref] Ippon!" in texts


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
def test_event_without_description_is_never_ticker_pushed() -> None:
    """An event with no `description` doesn't push regardless of
    significance. The ticker shows prose."""
    r = _renderer(THRESHOLD_MAT_SIDE)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), max_ticks=5)
    events = [
        _ev(1, "GRIP_ESTABLISH", "", sig=2),  # empty description
    ]
    r._absorb_tick(1, m, events)
    assert _ticker_texts(r) == []


def test_event_missing_significance_falls_back_to_mat_side_floor() -> None:
    """Defensive default: an event without `significance` set gets
    THRESHOLD_MAT_SIDE (1). At STANDS (4) such events are dropped;
    at MAT_SIDE (1) they pass through."""
    r_stands  = _renderer(THRESHOLD_STANDS)
    r_matside = _renderer(THRESHOLD_MAT_SIDE)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), max_ticks=5)
    e = Event(tick=1, event_type="MYSTERY", description="[?] something")
    # No `e.significance = ...` — relying on the default.
    r_stands._absorb_tick(1, m, [e])
    r_matside._absorb_tick(1, m, [e])
    assert _ticker_texts(r_stands) == []
    assert _ticker_texts(r_matside) == ["[?] something"]


# ---------------------------------------------------------------------------
# Integration: the live engine still feeds the ticker correctly.
# ---------------------------------------------------------------------------
def test_live_match_ticker_dropped_low_significance() -> None:
    """Run a small real match with the default threshold; assert
    the on-screen ticker contains no '[move]' lines (those are
    significance 1)."""
    random.seed(42)
    t, s = _pair()
    rec = _renderer(THRESHOLD_STANDS)
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=20, seed=42, renderer=rec,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        m._renderer.start()
        try:
            m.begin()
            while not m.is_done():
                m.step()
            m.end()
        finally:
            m._renderer.stop()
    texts = _ticker_texts(rec)
    # At least one event in 20 ticks of Tanaka vs Sato.
    assert texts, "expected ticker entries from a 20-tick match"
    # No [move] lines (engine emits them at significance 1).
    assert not any(t.startswith("[move]") for t in texts), (
        f"unexpected [move] lines at STANDS altitude: "
        f"{[t for t in texts if t.startswith('[move]')]}"
    )


def test_live_match_ticker_at_mat_side_includes_moves() -> None:
    """Same match at MAT_SIDE threshold should have movement
    narration — confirming the filter is actually doing the work."""
    random.seed(42)
    t, s = _pair()
    rec = _renderer(THRESHOLD_MAT_SIDE)
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=20, seed=42, renderer=rec,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        m._renderer.start()
        try:
            m.begin()
            while not m.is_done():
                m.step()
            m.end()
        finally:
            m._renderer.stop()
    texts = _ticker_texts(rec)
    # mat_side passes through everything with prose, including the
    # MATCH_CLOCK / move narration that fires every tick.
    assert len(texts) > 5
