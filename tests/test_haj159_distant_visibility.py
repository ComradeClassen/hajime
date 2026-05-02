# tests/test_haj159_distant_visibility.py
# HAJ-159 — STANDING_DISTANT spatial visibility:
#   - wider seated separation at match start + every matte/post-score reset
#   - STEP_IN actions during the closing phase emit MOVE events
#     (tactical_intent="closing"), giving the viewer per-tick CoM motion
#     to interpolate instead of teleporting at engagement
#
# Acceptance criteria:
#   1. Closing-phase MOVE events. Match start emits at least one MOVE
#      event per fighter during the closing phase.
#   2. Visible viewer spacing. Rendered fighter CoMs at STANDING_DISTANT
#      are visibly farther apart than at STANDING_ENGAGED.
#   3. Visible motion during closing. Closing-phase CoMs interpolate
#      from distant to engagement; no teleportation.
#   4. Matte recovery parity. All three properties hold for post-matte
#      resume, not only match start.
#   5. Regression tests covering the above.

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from match import (
    Match, STANDING_DISTANT_SEPARATION_M,
)
from action_selection import (
    select_actions, ENGAGEMENT_DISTANCE_M, CLOSING_STEP_MAGNITUDE_M,
    _closing_step_action,
)
from actions import (
    Action, ActionKind, TACTICAL_INTENT_CLOSING, TACTICAL_INTENTS,
)
from enums import Position
from grip_graph import GripGraph
from referee import build_suzuki
import main as main_module


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------
def _pair_at_default():
    """The placement main.py uses (1 m apart) — what callers do before
    constructing the match. begin() will reseat them at the wider distant
    pose."""
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _build_match(seed: int = 1, max_ticks: int = 30):
    random.seed(seed)
    t, s = _pair_at_default()
    m = Match(t, s, build_suzuki(), max_ticks=max_ticks, seed=seed)
    m._print_events = lambda evs: None
    m._print_header = lambda: None
    return t, s, m


def _gap(a, b) -> float:
    ax, ay = a.state.body_state.com_position
    bx, by = b.state.body_state.com_position
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def _run_collecting(m, ticks: int) -> list:
    captured: list = []
    real = m._print_events
    m._print_events = lambda evs: (captured.extend(evs), real(evs))[0]
    m.begin()
    for _ in range(ticks):
        if m.is_done():
            break
        m.step()
    return captured


# ===========================================================================
# Sanity — TACTICAL_INTENT_CLOSING is wired into the intent set
# ===========================================================================
def test_closing_intent_is_a_known_tactical_intent() -> None:
    assert TACTICAL_INTENT_CLOSING == "closing"
    assert TACTICAL_INTENT_CLOSING in TACTICAL_INTENTS


# ===========================================================================
# AC#2 — Visible viewer spacing: seated separation at STANDING_DISTANT
# is wider than the engagement distance
# ===========================================================================
def test_begin_seats_dyad_at_distant_separation() -> None:
    """Match.begin() reseats fighters at STANDING_DISTANT_SEPARATION_M
    even when the caller placed them at a tighter pose."""
    t, s, m = _build_match()
    # Caller seeded ±0.5 (1 m). Pre-begin gap is the caller's pose.
    assert abs(_gap(t, s) - 1.0) < 1e-6
    m.begin()
    assert abs(_gap(t, s) - STANDING_DISTANT_SEPARATION_M) < 1e-6
    # And the wider gap is unambiguously > engagement distance.
    assert _gap(t, s) > ENGAGEMENT_DISTANCE_M


def test_distant_separation_is_meaningfully_wider_than_engagement() -> None:
    """Per the ticket proposal: 2.5–3× engagement distance. Encodes the
    calibration choice so a future tweak can't silently shrink it back
    into the engagement-distance band."""
    assert STANDING_DISTANT_SEPARATION_M >= 2.5 * ENGAGEMENT_DISTANCE_M


# ===========================================================================
# AC#1 — Closing-phase MOVE events from match start
# ===========================================================================
_CLOSING_PHASE_INTENTS = frozenset({
    "closing", "circle_closing", "lateral_approach", "bait_retreat",
})


def test_match_start_emits_move_per_fighter_during_closing_phase() -> None:
    """HAJ-163 — the chosen closing-phase variant may be STEP_IN
    (closing), CIRCLE_CLOSING, LATERAL_APPROACH, or BAIT_RETREAT.
    The invariant is that each fighter emits at least one MOVE with
    one of those intents during the window."""
    t, s, m = _build_match()
    events = _run_collecting(m, ticks=4)
    moves = [e for e in events if e.event_type == "MOVE"]
    assert moves, "expected MOVE events during the closing phase"
    fighters_with_move = {
        e.data.get("fighter") for e in moves
        if e.data.get("tactical_intent") in _CLOSING_PHASE_INTENTS
    }
    assert t.identity.name in fighters_with_move
    assert s.identity.name in fighters_with_move


def test_closing_move_event_carries_intent_and_position_delta() -> None:
    """The MOVE event payload follows HAJ-156's contract: tactical_intent
    set, com_before/com_after present so the viewer can interpolate.
    HAJ-163 — accepts any closing-phase intent variant."""
    t, s, m = _build_match()
    events = _run_collecting(m, ticks=2)
    closing = [
        e for e in events
        if e.event_type == "MOVE"
        and e.data.get("tactical_intent") in _CLOSING_PHASE_INTENTS
    ]
    assert closing, "expected at least one closing-phase MOVE event"
    e = closing[0]
    assert "com_before" in e.data
    assert "com_after" in e.data
    bx, by = e.data["com_before"]
    ax, ay = e.data["com_after"]
    # CoM actually moved (HAJ-159's whole point — no teleport).
    assert (bx, by) != (ax, ay)


# ===========================================================================
# AC#3 — Visible motion: gap shrinks toward engagement across closing phase
# ===========================================================================
def test_closing_phase_gap_shrinks_toward_engagement() -> None:
    """HAJ-163 — strict per-tick monotonicity no longer holds because
    BAIT_RETREAT can briefly increase the gap. The invariant we still
    need is "starts wide, ends at or near engagement distance" so the
    viewer paints a visible convergence over the window."""
    t, s, m = _build_match(seed=4)
    m.begin()
    gap_initial = _gap(t, s)
    final_gaps: list[float] = []
    for _ in range(8):
        if m.is_done():
            break
        m.step()
        final_gaps.append(_gap(t, s))
    # Initial gap is the wide pose.
    assert gap_initial > ENGAGEMENT_DISTANCE_M
    # And by the end of the window the gap reached engagement
    # distance — net convergence happened.
    assert min(final_gaps) <= ENGAGEMENT_DISTANCE_M + 1e-6, (
        f"gap never converged to engagement distance; "
        f"initial={gap_initial}, gaps={final_gaps}"
    )


# ===========================================================================
# AC#4 — Matte recovery parity
# ===========================================================================
def test_post_matte_reset_reseats_at_distant_separation() -> None:
    """A matte-driven reset must reseat the dyad at the wider pose so
    the post-matte closing phase is just as visible as the match-start
    closing phase."""
    t, s, m = _build_match()
    m.begin()
    # Move fighters together (simulate them being at engagement distance).
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    assert _gap(t, s) < STANDING_DISTANT_SEPARATION_M
    # Trigger the shared reset path — same one matte / post-score use.
    m._reset_dyad_to_distant(tick=20)
    assert m.position == Position.STANDING_DISTANT
    assert abs(_gap(t, s) - STANDING_DISTANT_SEPARATION_M) < 1e-6


def test_post_matte_closing_phase_emits_move_events() -> None:
    """After _reset_dyad_to_distant, the next ticks are STANDING_DISTANT
    closing phase — STEP_IN should fire and MOVE events should surface,
    same as at match start."""
    t, s, m = _build_match()
    m.begin()
    # Drive the match a few ticks to leave hajime behind.
    for _ in range(4):
        m.step()
    # Force a matte-style reset and collect events from the next ticks.
    m._reset_dyad_to_distant(tick=10)
    captured: list = []
    m._print_events = lambda evs: captured.extend(evs)
    for _ in range(3):
        m.step()
    closing_moves = [
        e for e in captured
        if e.event_type == "MOVE"
        and e.data.get("tactical_intent") == TACTICAL_INTENT_CLOSING
    ]
    assert closing_moves, "post-matte closing phase should emit MOVE events"
    fighters_with_move = {e.data.get("fighter") for e in closing_moves}
    assert t.identity.name in fighters_with_move
    assert s.identity.name in fighters_with_move


# ===========================================================================
# Unit: select_actions — STANDING_DISTANT branch returns REACH + STEP_IN
# ===========================================================================
def test_select_actions_distant_branch_includes_closing_step() -> None:
    t, s = _pair_at_default()
    # Push them apart so closing has work to do.
    place_judoka(t, com_position=(-1.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+1.5, 0.0), facing=(-1.0, 0.0))
    g = GripGraph()
    acts = select_actions(
        t, s, g, kumi_kata_clock=0, position=Position.STANDING_DISTANT,
    )
    kinds = [a.kind for a in acts]
    assert ActionKind.REACH in kinds
    step_acts = [a for a in acts if a.kind == ActionKind.STEP]
    assert len(step_acts) == 1
    assert step_acts[0].tactical_intent == TACTICAL_INTENT_CLOSING


def test_closing_step_capped_at_engagement_distance() -> None:
    """Inside engagement distance the helper returns None — no
    zero-magnitude *closing* step that would still pay cardio.

    HAJ-163 added lateral / circling closing-trajectory variants that can
    still emit STEP actions when the dyad is at engagement distance
    (those steps don't close, they re-orient). The original assertion
    blanket-checked "no STEP" which became sensitive to RNG-state leak
    from prior tests that pulled lateral variants through. The narrower
    assertion is on the closing-step helper itself.
    """
    t, s = _pair_at_default()
    # Already inside engagement distance.
    place_judoka(t, com_position=(-0.4, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.4, 0.0), facing=(-1.0, 0.0))
    assert _closing_step_action(t, s) is None
    g = GripGraph()
    acts = select_actions(
        t, s, g, kumi_kata_clock=0, position=Position.STANDING_DISTANT,
    )
    # No CLOSING step this tick — lateral / circling variants are
    # still allowed because they don't close the gap.
    closing_steps = [
        a for a in acts
        if a.kind == ActionKind.STEP
        and a.tactical_intent in (TACTICAL_INTENT_CLOSING, "closing")
    ]
    assert not closing_steps, (
        f"unexpected closing STEP at engagement distance: {closing_steps}"
    )


def test_closing_step_does_not_overshoot_engagement_distance() -> None:
    """Last step in the closing window is capped so the dyad lands at
    engagement distance, not past it."""
    t, s = _pair_at_default()
    # Just slightly outside engagement distance.
    place_judoka(t, com_position=(-0.6, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.6, 0.0), facing=(-1.0, 0.0))
    gap_before = _gap(t, s)  # 1.2
    step = _closing_step_action(t, s)
    assert step is not None
    # Magnitude is the per-fighter gap-to-engagement, not the full
    # CLOSING_STEP_MAGNITUDE_M (which would overshoot).
    assert step.magnitude < CLOSING_STEP_MAGNITUDE_M
    assert step.magnitude == gap_before - ENGAGEMENT_DISTANCE_M
