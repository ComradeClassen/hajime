# tests/test_oob.py
# HAJ-127 — out-of-bounds Matte logic + start-of-attack gate.
#
# Pre-HAJ-127 the simulator had no concept of OOB. Match starts at
# (-0.5, 0) / (+0.5, 0), no boundary check, no Matte trigger when
# fighters drift off the contest area.
#
# Post-HAJ-127:
#   - MAT_HALF_WIDTH=1.5 (interim) defines a square boundary.
#   - is_out_of_bounds(judoka) helper.
#   - should_call_matte returns OUT_OF_BOUNDS when either fighter is
#     OOB AND no throw is in flight (in-flight grace mirrors HAJ-43).
#   - _resolve_commit_throw denies commits from an OOB attacker.
#   - MatchState exposes fighter_a_oob, fighter_b_oob, any_throw_in_flight.

from __future__ import annotations
import io
import os
import random
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from enums import (
    BodyPart, GripTarget, GripTypeV2, GripDepth, GripMode, MatteReason,
)
from grip_graph import GripEdge
from match import Match, MAT_HALF_WIDTH, is_out_of_bounds
from referee import build_suzuki
from throws import ThrowID
import main as main_module


def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _new_match(*, max_ticks=20, seed=1):
    random.seed(seed)
    t, s = _pair()
    return Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=max_ticks, seed=seed,
    )


def _seat_deep_grips(graph, attacker, defender):
    graph.add_edge(GripEdge(
        grasper_id=attacker.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=defender.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.DEEP,
        strength=1.0, established_tick=0, mode=GripMode.DRIVING,
    ))
    graph.add_edge(GripEdge(
        grasper_id=attacker.identity.name, grasper_part=BodyPart.LEFT_HAND,
        target_id=defender.identity.name, target_location=GripTarget.RIGHT_SLEEVE,
        grip_type_v2=GripTypeV2.SLEEVE_HIGH, depth_level=GripDepth.DEEP,
        strength=1.0, established_tick=0, mode=GripMode.DRIVING,
    ))


# ---------------------------------------------------------------------------
# is_out_of_bounds helper
# ---------------------------------------------------------------------------
def test_is_out_of_bounds_inside_returns_false() -> None:
    t, _ = _pair()
    assert is_out_of_bounds(t) is False


def test_is_out_of_bounds_returns_true_past_x_boundary() -> None:
    t, _ = _pair()
    t.state.body_state.com_position = (MAT_HALF_WIDTH + 0.1, 0.0)
    assert is_out_of_bounds(t) is True


def test_is_out_of_bounds_returns_true_past_y_boundary() -> None:
    t, _ = _pair()
    t.state.body_state.com_position = (0.0, -(MAT_HALF_WIDTH + 0.1))
    assert is_out_of_bounds(t) is True


def test_is_out_of_bounds_strict_inequality_at_boundary() -> None:
    """Exactly on the boundary line still counts as inside."""
    t, _ = _pair()
    t.state.body_state.com_position = (MAT_HALF_WIDTH, 0.0)
    assert is_out_of_bounds(t) is False


# ---------------------------------------------------------------------------
# MatchState exposes the OOB flags + in-flight gate
# ---------------------------------------------------------------------------
def test_match_state_exposes_oob_flags() -> None:
    m = _new_match()
    state = m._build_match_state(tick=0)
    assert state.fighter_a_oob is False
    assert state.fighter_b_oob is False
    assert state.any_throw_in_flight is False
    # Push fighter_a outside.
    m.fighter_a.state.body_state.com_position = (MAT_HALF_WIDTH + 1.0, 0.0)
    state2 = m._build_match_state(tick=1)
    assert state2.fighter_a_oob is True
    assert state2.fighter_b_oob is False


# ---------------------------------------------------------------------------
# should_call_matte fires OUT_OF_BOUNDS when no throw is in flight
# ---------------------------------------------------------------------------
def test_oob_matte_fires_when_fighter_outside() -> None:
    """Place a fighter past the boundary, no throw active → Matte fires
    next tick with OUT_OF_BOUNDS."""
    m = _new_match()
    m.fighter_a.state.body_state.com_position = (MAT_HALF_WIDTH + 0.5, 0.0)
    state = m._build_match_state(tick=5)
    reason = m.referee.should_call_matte(state, current_tick=5)
    assert reason == MatteReason.OUT_OF_BOUNDS


def test_oob_matte_skipped_during_throw_in_flight() -> None:
    """The HAJ-43-style in-flight grace must suppress OOB while a throw
    is mid-flight. A fighter who started inside but tracked outside
    during a throw should not get an OOB call until the throw resolves."""
    m = _new_match()
    # Mark a throw in flight.
    m._throws_in_progress[m.fighter_a.identity.name] = object()
    # Push fighter past boundary.
    m.fighter_a.state.body_state.com_position = (MAT_HALF_WIDTH + 0.5, 0.0)
    state = m._build_match_state(tick=5)
    assert state.any_throw_in_flight is True
    reason = m.referee.should_call_matte(state, current_tick=5)
    assert reason is None


def test_oob_matte_fires_after_throw_resolves_outside() -> None:
    """The complement of the grace test: once the throw resolves and
    nothing is in flight, OOB fires immediately on the next check."""
    m = _new_match()
    m._throws_in_progress[m.fighter_a.identity.name] = object()
    m.fighter_a.state.body_state.com_position = (MAT_HALF_WIDTH + 0.5, 0.0)
    # While in flight: skipped.
    state_during = m._build_match_state(tick=5)
    assert m.referee.should_call_matte(state_during, current_tick=5) is None
    # Throw resolves — clear the in-flight marker.
    del m._throws_in_progress[m.fighter_a.identity.name]
    state_after = m._build_match_state(tick=6)
    assert m.referee.should_call_matte(state_after, current_tick=6) == (
        MatteReason.OUT_OF_BOUNDS
    )


def test_oob_either_fighter_triggers_matte() -> None:
    """The OOB check considers both fighters; B alone past boundary
    is sufficient."""
    m = _new_match()
    m.fighter_b.state.body_state.com_position = (0.0, MAT_HALF_WIDTH + 0.3)
    state = m._build_match_state(tick=2)
    assert m.referee.should_call_matte(state, current_tick=2) == (
        MatteReason.OUT_OF_BOUNDS
    )


# ---------------------------------------------------------------------------
# Start-of-attack gate denies commits from an OOB attacker
# ---------------------------------------------------------------------------
def test_oob_attacker_commit_is_denied() -> None:
    """An OOB attacker firing a commit gets the throw denied: no
    THROW_ENTRY, no score, just a single THROW_DENIED_OOB event."""
    m = _new_match()
    _seat_deep_grips(m.grip_graph, m.fighter_a, m.fighter_b)

    buf = io.StringIO()
    with redirect_stdout(buf):
        m.begin()
        # HAJ-159 — begin() reseats the dyad at the wider STANDING_DISTANT
        # pose; push the attacker past the boundary AFTER that so the
        # OOB gate sees the test-supplied position.
        m.fighter_a.state.body_state.com_position = (MAT_HALF_WIDTH + 0.2, 0.0)
        events = m._resolve_commit_throw(
            m.fighter_a, m.fighter_b, ThrowID.SEOI_NAGE, tick=3,
        )
    kinds = [e.event_type for e in events]
    assert kinds == ["THROW_DENIED_OOB"], (
        f"expected only THROW_DENIED_OOB; got {kinds}"
    )
    # No score awarded.
    assert m.fighter_a.state.score["waza_ari"] == 0
    assert m.fighter_a.state.score["ippon"] is False
    # Attacker is not registered as in-flight (denied at the gate).
    assert m.fighter_a.identity.name not in m._throws_in_progress


def test_inside_attacker_commit_proceeds_normally() -> None:
    """Sanity: the OOB gate shouldn't affect commits from inside the mat."""
    m = _new_match()
    _seat_deep_grips(m.grip_graph, m.fighter_a, m.fighter_b)
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.begin()
        events = m._resolve_commit_throw(
            m.fighter_a, m.fighter_b, ThrowID.SEOI_NAGE, tick=3,
        )
    kinds = {e.event_type for e in events}
    # At minimum, a THROW_ENTRY fires for an unblocked commit.
    assert "THROW_ENTRY" in kinds
    # And no DENIED event.
    assert "THROW_DENIED_OOB" not in kinds


def test_denied_commit_still_leaves_oob_matte_to_fire() -> None:
    """After the commit is denied, the standing-OOB check (no longer
    masked by an in-flight throw) returns OUT_OF_BOUNDS on the post-tick
    referee call."""
    m = _new_match()
    _seat_deep_grips(m.grip_graph, m.fighter_a, m.fighter_b)

    buf = io.StringIO()
    with redirect_stdout(buf):
        m.begin()
        # HAJ-159 — push past boundary AFTER begin() (which reseats the
        # dyad at the wider STANDING_DISTANT pose).
        m.fighter_a.state.body_state.com_position = (MAT_HALF_WIDTH + 0.2, 0.0)
        m._resolve_commit_throw(
            m.fighter_a, m.fighter_b, ThrowID.SEOI_NAGE, tick=3,
        )
    state = m._build_match_state(tick=4)
    assert state.any_throw_in_flight is False
    assert state.fighter_a_oob is True
    assert m.referee.should_call_matte(state, current_tick=4) == (
        MatteReason.OUT_OF_BOUNDS
    )
