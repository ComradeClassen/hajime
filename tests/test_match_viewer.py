# tests/test_match_viewer.py
# HAJ-125 — Renderer protocol + Match wiring + pure-math viewer pieces.
#
# Tests in this module deliberately avoid opening a pygame window. The
# RecordingRenderer fake validates the Match wiring; MatTransform and
# TrailBuffer are pure data so they're testable directly.

from __future__ import annotations
import io
import os
import random
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from match import Match, Renderer
from match_viewer import (
    MatTransform, TrailBuffer, RecordingRenderer,
    VISIBLE_MAT_M, CONTEST_M, TRAIL_LENGTH,
)
from referee import build_suzuki
import main as main_module


def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _run_match(*, renderer=None, max_ticks=12, seed=1):
    random.seed(seed)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=max_ticks, seed=seed, renderer=renderer,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    return m, buf.getvalue()


# ---------------------------------------------------------------------------
# Renderer protocol shape
# ---------------------------------------------------------------------------
def test_recording_renderer_satisfies_protocol() -> None:
    """RecordingRenderer is a structural Renderer — runtime_checkable."""
    r = RecordingRenderer()
    assert isinstance(r, Renderer)


def test_match_accepts_optional_renderer_kwarg() -> None:
    """No renderer is the default; supplying one doesn't error."""
    t, s = _pair()
    m_none = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    assert m_none._renderer is None
    t2, s2 = _pair()
    rec = RecordingRenderer()
    m_with = Match(fighter_a=t2, fighter_b=s2, referee=build_suzuki(),
                   renderer=rec)
    assert m_with._renderer is rec


# ---------------------------------------------------------------------------
# Lifecycle: start once, update once per tick, stop once.
# ---------------------------------------------------------------------------
def test_renderer_lifecycle_called_correctly() -> None:
    rec = RecordingRenderer()
    m, _ = _run_match(renderer=rec, max_ticks=10)
    assert rec.start_calls == 1, "start() should fire exactly once"
    assert rec.stop_calls == 1,  "stop() should fire exactly once"
    # update() fires once at tick 0 (initial paint) plus once per real tick.
    # Match may end early on score; just assert the count is bounded.
    assert rec.update_calls >= 1


def test_renderer_sees_tick_zero_first() -> None:
    """The viewer should paint the start state before any motion."""
    rec = RecordingRenderer()
    _run_match(renderer=rec, max_ticks=5)
    assert rec.tick_history, "renderer received no updates"
    assert rec.tick_history[0] == 0, (
        f"first update should be tick 0; got history {rec.tick_history!r}"
    )


def test_renderer_never_mutates_match_outcome() -> None:
    """Match runs identically with vs without the renderer attached
    (same seed, same outcome). Read-only contract."""
    _, out_no = _run_match(renderer=None,            max_ticks=30, seed=42)
    _, out_yes = _run_match(renderer=RecordingRenderer(), max_ticks=30, seed=42)
    # Strip random run-time differences (none expected, but be defensive
    # about timing-only artifacts). For the recording renderer, output
    # should match exactly.
    assert out_no == out_yes


# ---------------------------------------------------------------------------
# Window-close exits the loop cleanly.
# ---------------------------------------------------------------------------
def test_window_close_ends_match_gracefully() -> None:
    """When the user closes the viewer mid-match, the Match loop should
    set match_over and stop without raising."""
    class CloseAfterN(RecordingRenderer):
        def __init__(self, n):
            super().__init__()
            self._n = n

        def update(self, tick, match, events):
            super().update(tick, match, events)
            if self.update_calls >= self._n:
                self.close()

    rec = CloseAfterN(n=3)
    m, _ = _run_match(renderer=rec, max_ticks=240, seed=7)
    assert m.match_over is True
    # The match cut short well before max_ticks because the window closed.
    assert m.ticks_run < 240


# ---------------------------------------------------------------------------
# MatTransform — pure math; no pygame needed.
# ---------------------------------------------------------------------------
def test_transform_origin_lands_in_panel_center() -> None:
    T = MatTransform()
    ox, oy = T.world_to_screen(0.0, 0.0)
    # Origin sits in the center of the mat panel (left half), not the
    # whole window. Sanity-bound it.
    assert 0 < ox < (1100 - 380)
    assert 0 < oy < 760


def test_transform_y_axis_is_flipped() -> None:
    """Mat-frame +y is up; screen +y is down. A point above the origin
    has a smaller screen-y than one below."""
    T = MatTransform()
    _, sy_up   = T.world_to_screen(0.0, +1.0)
    _, sy_down = T.world_to_screen(0.0, -1.0)
    assert sy_up < sy_down


def test_transform_full_visible_mat_fits_in_panel() -> None:
    """The 14 m visible region should map to a square that fits inside
    the panel after padding."""
    T = MatTransform()
    px = T.meters_to_pixels(VISIBLE_MAT_M)
    assert px <= T.panel_w
    assert px <= T.panel_h


def test_transform_contest_smaller_than_visible() -> None:
    """Sanity: 8 m contest is smaller than 14 m visible region in pixels."""
    T = MatTransform()
    assert T.meters_to_pixels(CONTEST_M) < T.meters_to_pixels(VISIBLE_MAT_M)


def test_transform_round_trip_pixels_per_meter_consistency() -> None:
    """meters_to_pixels(d) and the world-to-screen delta agree to 1 px."""
    T = MatTransform()
    p0 = T.world_to_screen(0.0, 0.0)
    p1 = T.world_to_screen(2.0, 0.0)
    delta = abs(p1[0] - p0[0])
    assert abs(delta - T.meters_to_pixels(2.0)) <= 1


# ---------------------------------------------------------------------------
# TrailBuffer — pure data structure.
# ---------------------------------------------------------------------------
def test_trail_buffer_capped_at_length() -> None:
    tb = TrailBuffer(length=5)
    for i in range(20):
        tb.push((float(i), 0.0), (0.0, float(i)))
    assert len(tb.fighter_a()) == 5
    assert len(tb.fighter_b()) == 5
    # Most recent push is at the end.
    assert tb.fighter_a()[-1] == (19.0, 0.0)
    assert tb.fighter_b()[-1] == (0.0, 19.0)


def test_trail_buffer_default_length_matches_constant() -> None:
    tb = TrailBuffer()
    for i in range(TRAIL_LENGTH + 50):
        tb.push((0.0, 0.0), (0.0, 0.0))
    assert len(tb.fighter_a()) == TRAIL_LENGTH
