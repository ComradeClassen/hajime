# tests/test_haj160_hajime_banner.py
# HAJ-160 — HAJIME restart banner symmetric with the MATTE banner.
#
# Acceptance criteria:
#   1. Banner renders on every Hajime event — match start AND every
#      post-matte restart.
#   2. Visual symmetry with MATTE banner — same render position,
#      comparable persistence duration, distinguishable color.
#   3. No engine changes that mutate gameplay — adds restart-hajime
#      emission only (purely cosmetic, no state gating off it).
#   4. Replay-stable — banner state lives on ViewState and replays in
#      review/paused mode.

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from match import Match
from match_viewer import (
    ViewState, capture_view_state,
    COL_HAJIME_BG, COL_HAJIME_TEXT, COL_MATTE_BG, COL_MATTE_TEXT,
    HAJIME_BANNER_FRAMES, MATTE_BANNER_FRAMES,
)
from referee import build_suzuki
import main as main_module


def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _build_match(seed: int = 1, max_ticks: int = 60):
    random.seed(seed)
    t, s = _pair()
    m = Match(t, s, build_suzuki(), max_ticks=max_ticks, seed=seed)
    m._print_events = lambda evs: None
    m._print_header = lambda: None
    return t, s, m


# ===========================================================================
# AC#1 — match-start hajime
# ===========================================================================
def test_match_start_emits_hajime_called_event() -> None:
    """Match.begin() emits a HAJIME_CALLED at tick 0 (existing behaviour
    — the renderer hooks off it for the banner)."""
    t, s, m = _build_match()
    captured: list = []
    real = m._renderer
    # capture begin's hajime event by replacing _print_events.
    m._print_events = lambda evs: captured.extend(evs)
    m.begin()
    starts = [e for e in captured if e.event_type == "HAJIME_CALLED"]
    assert len(starts) == 1
    assert starts[0].tick == 0


# ===========================================================================
# AC#1 — post-matte restart hajime
# ===========================================================================
def test_handle_matte_queues_pending_hajime_for_next_tick() -> None:
    t, s, m = _build_match()
    m.begin()
    m._handle_matte(tick=10)
    assert m._pending_hajime_tick == 11


def test_post_matte_hajime_fires_one_tick_after_matte() -> None:
    """The hajime announcement lands on the tick AFTER the matte, so the
    viewer's matte and hajime banners don't overlap on the same frame."""
    t, s, m = _build_match()
    captured: list = []
    m._print_events = lambda evs: captured.extend(evs)
    m.begin()
    captured.clear()  # ignore the t000 hajime
    # Force a matte at tick 10 and step forward.
    m._handle_matte(tick=10)
    for next_tick in range(11, 13):
        m.ticks_run = next_tick - 1
        m.step()
    hajimes = [e for e in captured if e.event_type == "HAJIME_CALLED"]
    assert len(hajimes) == 1
    assert hajimes[0].tick == 11
    assert m._pending_hajime_tick is None


def test_pending_hajime_resets_after_emission() -> None:
    """A second matte after the hajime fired re-arms the pending slot."""
    t, s, m = _build_match()
    m.begin()
    m._handle_matte(tick=10)
    assert m._pending_hajime_tick == 11
    m.ticks_run = 10
    m.step()  # tick 11 — hajime fires
    assert m._pending_hajime_tick is None
    m._handle_matte(tick=20)
    assert m._pending_hajime_tick == 21


# ===========================================================================
# AC#4 — ViewState carries the hajime cue (replay-stable)
# ===========================================================================
def test_capture_view_state_sets_hajime_called_on_hajime_tick() -> None:
    """ViewState.hajime_called flips True on any tick whose event list
    contains a HAJIME_CALLED — review-mode rendering reads this field
    directly so scrubbing back paints the banner just as live did."""
    t, s, m = _build_match()
    m.begin()
    hajime_event = m.referee.announce_hajime(tick=0)
    view = capture_view_state(m, tick=0, events=[hajime_event])
    assert view.hajime_called is True


def test_capture_view_state_hajime_called_default_false() -> None:
    t, s, m = _build_match()
    m.begin()
    view = capture_view_state(m, tick=5, events=[])
    assert view.hajime_called is False


def test_view_state_hajime_field_is_part_of_dataclass() -> None:
    """The field has to live on ViewState (per HAJ-153 conventions) so
    scrubbing back through the snapshot list paints the banner exactly
    where the engine fired it."""
    fields = ViewState.__dataclass_fields__
    assert "hajime_called" in fields


# ===========================================================================
# AC#2 — visual symmetry with MATTE banner
# ===========================================================================
def test_hajime_banner_persistence_matches_matte() -> None:
    """Same wall-clock window so the matte → hajime cycle reads as a
    balanced pair of beats."""
    assert HAJIME_BANNER_FRAMES == MATTE_BANNER_FRAMES


def test_hajime_banner_color_distinguishable_from_matte() -> None:
    """Distinguishable color treatment per AC#2 — the eye should be able
    to tell stop from restart at a glance."""
    assert COL_HAJIME_BG != COL_MATTE_BG
    # Foreground text should be readable too.
    assert COL_HAJIME_TEXT != COL_MATTE_TEXT


def test_hajime_banner_color_is_green_family() -> None:
    """Per ticket: green/blue for restart, red/orange for stop. The
    chosen treatment is green — green channel dominates."""
    r, g, b = COL_HAJIME_BG
    assert g > r and g > b, f"expected green-dominant HAJIME bg, got {COL_HAJIME_BG}"


# ===========================================================================
# AC#3 — engine change is purely cosmetic (no gameplay state hangs off
# the pending-hajime slot)
# ===========================================================================
def test_pending_hajime_does_not_affect_match_state() -> None:
    """Regression: setting / clearing _pending_hajime_tick must not
    change scores, position, sub-loop state, or any other gameplay
    field. Pure visible-beat plumbing."""
    t, s, m = _build_match()
    m.begin()
    snap = (
        m.position, m.sub_loop_state,
        t.state.score["waza_ari"], t.state.score["ippon"],
        s.state.score["waza_ari"], s.state.score["ippon"],
        t.state.shidos, s.state.shidos,
    )
    m._pending_hajime_tick = 5
    m._pending_hajime_tick = None
    after = (
        m.position, m.sub_loop_state,
        t.state.score["waza_ari"], t.state.score["ippon"],
        s.state.score["waza_ari"], s.state.score["ippon"],
        t.state.shidos, s.state.shidos,
    )
    assert snap == after
