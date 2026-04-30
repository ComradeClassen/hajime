# tests/test_haj153_viewer_parity.py
# HAJ-153 — viewer wire-up parity regression tests.
#
# These tests focus on the data-shape side of the viewer: ViewState
# capture and the per-tick state pill / event-driven cue fields.
# Pygame rendering is tested manually against the audit doc; the
# pure-data pieces are tested here so review-mode scrubbing produces
# the same visual cues as live mode.

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from enums import (
    BodyArchetype, BodyPart, GripDepth, GripMode, GripTarget, GripTypeV2,
    Position, SubLoopState,
)
from grip_graph import GripEdge
from match import Match
from match_viewer import (
    capture_view_state, FighterView, ViewState,
    GRIP_SEAT_THRESHOLD,
)
from referee import build_suzuki
from throws import ThrowID
import main as main_module
import match as match_module


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------
def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _seat_grips(m, owner, target):
    m.grip_graph.add_edge(GripEdge(
        grasper_id=owner.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=target.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.STANDARD,
        strength=0.8, established_tick=0, mode=GripMode.DRIVING,
    ))
    m.grip_graph.add_edge(GripEdge(
        grasper_id=owner.identity.name, grasper_part=BodyPart.LEFT_HAND,
        target_id=target.identity.name, target_location=GripTarget.RIGHT_SLEEVE,
        grip_type_v2=GripTypeV2.SLEEVE_HIGH, depth_level=GripDepth.STANDARD,
        strength=0.8, established_tick=0, mode=GripMode.DRIVING,
    ))


def _pair_match(seed: int = 1):
    random.seed(seed)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=seed)
    return t, s, m


# ===========================================================================
# F1 — per-fighter state pill
# ===========================================================================
def test_state_pill_shows_grip_count_when_gripping() -> None:
    t, s, m = _pair_match()
    m.position = Position.GRIPPING
    _seat_grips(m, t, s)
    view = capture_view_state(m, tick=5, events=[])
    assert view.fighter_a.state_pill == "GRIPS 2"
    # Sato has no edges yet.
    assert view.fighter_b.state_pill is None
    assert view.fighter_a.own_edge_count == 2
    assert view.fighter_b.own_edge_count == 0


def test_state_pill_shows_throw_when_attempting() -> None:
    t, s, m = _pair_match()
    m.position = Position.GRIPPING
    _seat_grips(m, t, s)
    real = match_module.resolve_throw
    match_module.resolve_throw = lambda *a, **kw: ("FAILED", -1.0)
    try:
        m._resolve_commit_throw(t, s, ThrowID.UCHI_MATA, tick=10)
        view = capture_view_state(m, tick=10, events=[])
    finally:
        match_module.resolve_throw = real
    assert view.fighter_a.state_pill == "THROW"


def test_state_pill_shows_stun_when_stunned() -> None:
    t, s, m = _pair_match()
    t.state.stun_ticks = 4
    view = capture_view_state(m, tick=1, events=[])
    assert view.fighter_a.state_pill == "STUN 4"


def test_state_pill_priority_order() -> None:
    """Mid-throw should outrank stun, desperation, and grip count."""
    t, s, m = _pair_match()
    m.position = Position.GRIPPING
    _seat_grips(m, t, s)
    t.state.stun_ticks = 3
    m._defensive_desperation_active[t.identity.name] = True
    real = match_module.resolve_throw
    match_module.resolve_throw = lambda *a, **kw: ("FAILED", -1.0)
    try:
        m._resolve_commit_throw(t, s, ThrowID.UCHI_MATA, tick=2)
        view = capture_view_state(m, tick=2, events=[])
    finally:
        match_module.resolve_throw = real
    assert view.fighter_a.state_pill == "THROW"


# ===========================================================================
# F4 — MATTE_CALLED captured into ViewState
# ===========================================================================
def test_matte_event_surfaces_on_view_state() -> None:
    from grip_graph import Event
    t, s, m = _pair_match()
    matte_ev = Event(
        tick=5, event_type="MATTE_CALLED",
        description="[ref: Suzuki-sensei] Matte! (post-score reset)",
        data={"reason": "POST_SCORE_FOLLOW_UP_END"},
    )
    view = capture_view_state(m, tick=5, events=[matte_ev])
    assert view.matte_reason == "POST_SCORE_FOLLOW_UP_END"


# ===========================================================================
# F6 — STUFFED victims captured
# ===========================================================================
def test_stuff_event_surfaces_attacker_in_view_state() -> None:
    from grip_graph import Event
    t, s, m = _pair_match()
    stuff_ev = Event(
        tick=8, event_type="STUFFED",
        description=(
            f"[throw] {t.identity.name} stuffed on Uchi-mata — "
            f"{s.identity.name} defends. Ne-waza window open."
        ),
        data={},
    )
    view = capture_view_state(m, tick=8, events=[stuff_ev])
    assert t.identity.name in view.stuff_victims
    assert s.identity.name not in view.stuff_victims


# ===========================================================================
# F5 — multi-grip-seat anomaly captured
# ===========================================================================
def test_multi_grip_seat_count_surfaces_for_audit_finding() -> None:
    """When 4 GRIP_ESTABLISH events fire on the same tick (HAJ-144 t003),
    the snapshot's grip_seat_count crosses GRIP_SEAT_THRESHOLD so the
    F5 warning ring renders."""
    from grip_graph import Event
    t, s, m = _pair_match()
    events = [
        Event(tick=3, event_type="GRIP_ESTABLISH",
              description="seat", data={})
        for _ in range(4)
    ]
    view = capture_view_state(m, tick=3, events=events)
    assert view.grip_seat_count == 4
    assert view.grip_seat_count >= GRIP_SEAT_THRESHOLD


# ===========================================================================
# F9 — HAJ-152 follow-up window state surfaces
# ===========================================================================
def test_follow_up_window_state_in_view_state() -> None:
    t, s, m = _pair_match()
    m._post_score_follow_up = {
        "tori_name":   t.identity.name,
        "uke_name":    s.identity.name,
        "throw_id":    ThrowID.UCHI_MATA,
        "score_tick":  29,
        "reason":      "waza-ari",
        "force_stand": False,
        "decision":    "CHASE",
        "stage":       "NE_WAZA_LIVE",
    }
    view = capture_view_state(m, tick=30, events=[])
    assert view.follow_up_scorer == t.identity.name
    assert view.follow_up_decision == "CHASE"
    assert view.follow_up_stage == "NE_WAZA_LIVE"


def test_follow_up_state_clears_when_no_window() -> None:
    t, s, m = _pair_match()
    view = capture_view_state(m, tick=1, events=[])
    assert view.follow_up_scorer is None
    assert view.follow_up_decision is None
    assert view.follow_up_stage is None


# ===========================================================================
# F8 — ne-waza top-fighter surfaces for the schematic
# ===========================================================================
def test_ne_waza_top_name_captured_when_ground_active() -> None:
    t, s, m = _pair_match()
    m.sub_loop_state = SubLoopState.NE_WAZA
    m.position = Position.GUARD_TOP
    m.ne_waza_top_id = t.identity.name
    view = capture_view_state(m, tick=15, events=[])
    assert view.ne_waza_top_name == t.identity.name
    assert view.sub_loop_name == "NE_WAZA"


def test_ne_waza_top_name_none_when_standing() -> None:
    t, s, m = _pair_match()
    view = capture_view_state(m, tick=1, events=[])
    assert view.ne_waza_top_name is None


# ===========================================================================
# F10 — counter-commit endpoints captured
# ===========================================================================
def test_counter_commit_captured_with_attacker_and_target() -> None:
    from grip_graph import Event
    t, s, m = _pair_match()
    counter_ev = Event(
        tick=12, event_type="COUNTER_COMMIT",
        description="[counter] Sato counters Tanaka.",
        data={
            "attacker": t.identity.name,
            "defender": s.identity.name,
            "counter_throw":  "DE_ASHI_HARAI",
            "attacker_throw": "UCHI_MATA",
        },
    )
    view = capture_view_state(m, tick=12, events=[counter_ev])
    assert view.counter_attacker == s.identity.name   # Sato fired the counter
    assert view.counter_target   == t.identity.name


# ===========================================================================
# F11 — interpolation helpers (pure; pygame-free)
# ===========================================================================
def test_interpolation_alpha_zero_in_review() -> None:
    """Review mode disables interpolation — the renderer should always
    treat alpha as 1.0 so each scrub-step lands on a discrete snapshot."""
    from match_viewer import PygameMatchRenderer
    # Construct without start() so no pygame display is opened.
    try:
        r = PygameMatchRenderer()
    except ImportError:
        # pygame not installed in this environment; skip cleanly.
        return
    r._review_mode = True
    assert r._interp_alpha() == 1.0


def test_interpolation_falls_through_with_no_snapshots() -> None:
    """When no snapshots are captured yet, interpolation should not
    crash; the renderer just returns the live view's CoM."""
    from match_viewer import PygameMatchRenderer
    try:
        r = PygameMatchRenderer()
    except ImportError:
        return
    t, s, m = _pair_match()
    view = capture_view_state(m, tick=0, events=[])
    com = r._interpolated_com(view, "a")
    assert com == view.fighter_a.com_position


def test_interpolation_tweens_between_two_snapshots() -> None:
    """With two snapshots in the buffer and the renderer paused at
    alpha=0.5, the interpolated CoM should be the midpoint of the two
    snapshot CoMs."""
    from match_viewer import PygameMatchRenderer
    try:
        r = PygameMatchRenderer()
    except ImportError:
        return
    t, s, m = _pair_match()
    snap1 = capture_view_state(m, tick=0, events=[])
    # Move tanaka before the second snapshot.
    t.state.body_state.com_position = (0.0, 0.5)
    snap2 = capture_view_state(m, tick=1, events=[])
    r._snapshots = [snap1, snap2]
    # Force alpha = 0.5 by patching _interp_alpha.
    r._interp_alpha = lambda: 0.5
    com = r._interpolated_com(snap2, "a")
    expected_x = (snap1.fighter_a.com_position[0] + snap2.fighter_a.com_position[0]) / 2.0
    expected_y = (snap1.fighter_a.com_position[1] + snap2.fighter_a.com_position[1]) / 2.0
    assert abs(com[0] - expected_x) < 1e-9
    assert abs(com[1] - expected_y) < 1e-9


# ===========================================================================
# AC#11 — no simulation regression. The viewer changes are pure additions
# to the snapshot data; the simulation should not see anything new.
# ===========================================================================
def test_view_state_capture_does_not_mutate_match() -> None:
    """capture_view_state must not write to live match state — it's a
    read-only snapshot."""
    t, s, m = _pair_match()
    m.position = Position.GRIPPING
    _seat_grips(m, t, s)
    pre_position = m.position
    pre_edges = list(m.grip_graph.edges)
    capture_view_state(m, tick=5, events=[])
    assert m.position is pre_position
    assert list(m.grip_graph.edges) == pre_edges


# ===========================================================================
# Backward compatibility — existing fields still populated
# ===========================================================================
def test_view_state_preserves_existing_fields() -> None:
    """The HAJ-153 additions are extensions; the original ViewState /
    FighterView shape is unchanged. Spot-check a few existing fields."""
    t, s, m = _pair_match()
    view = capture_view_state(m, tick=1, events=[])
    assert view.tick == 1
    assert view.fighter_a.name == t.identity.name
    assert view.fighter_b.name == s.identity.name
    assert isinstance(view.fighter_a.com_position, tuple)
    assert isinstance(view.fighter_a.facing, tuple)


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    import traceback
    passed = 0
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                passed += 1
                print(f"PASS  {name}")
            except Exception:
                failed += 1
                print(f"FAIL  {name}")
                traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
