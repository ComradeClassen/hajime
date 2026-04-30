# tests/test_haj156_locomotion.py
# HAJ-156 — movement and locomotion substrate regression tests.
#
# This ticket extends HAJ-128's existing STEP machinery and HAJ-127's
# OOB matte with:
#   - MOVE engine events tagged with tactical_intent
#   - foot_speed attribute on Capability
#   - per-fighter effective_step_magnitude scaling
#   - entry_direction field on throws + spatial-mismatch kuzushi penalty
#   - push-out shido on retreating fighters at the edge zone
#
# These tests pin the new contracts; the HAJ-128 / HAJ-127 baseline
# tests in test_locomotion.py and test_oob.py continue to cover the
# existing infrastructure.

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from enums import (
    BodyArchetype, BodyPart, GripDepth, GripMode, GripTarget, GripTypeV2,
    Position, PositionalStyle,
)
from grip_graph import GripEdge
from match import (
    Match, MAT_HALF_WIDTH, EDGE_ZONE_M, SAFE_ZONE_M,
    _spatial_mismatch_penalty, _step_direction_sign,
)
from referee import build_suzuki, Referee
from throws import EntryDirection, ThrowID, THROW_DEFS
from actions import (
    Action, ActionKind, step,
    TACTICAL_INTENT_PRESSURE, TACTICAL_INTENT_GIVE_GROUND,
    TACTICAL_INTENT_CIRCLE, TACTICAL_INTENT_HOLD_CENTER,
    TACTICAL_INTENTS,
)
from action_selection import (
    effective_foot_speed_factor, effective_step_magnitude,
    STEP_MAGNITUDE_M,
)
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


def _pair_match(seed: int = 1):
    random.seed(seed)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=seed)
    return t, s, m


# ===========================================================================
# foot_speed attribute + effective_step_magnitude scaling
# ===========================================================================
def test_foot_speed_default_is_average() -> None:
    """Both default fighter builds carry a foot_speed in the average
    range (4–7) until the calibration tool tunes them. The attribute
    must exist on Capability so action_selection can read it."""
    t, s = _pair()
    assert hasattr(t.capability, "foot_speed")
    assert hasattr(s.capability, "foot_speed")
    assert 4 <= t.capability.foot_speed <= 7
    assert 4 <= s.capability.foot_speed <= 7


def test_effective_foot_speed_scales_with_attribute() -> None:
    """Higher foot_speed → larger effective factor; lower → smaller.
    Both should sit on either side of 1.0 around foot_speed=5."""
    t, _ = _pair()
    t.capability.foot_speed = 9
    fast = effective_foot_speed_factor(t)
    t.capability.foot_speed = 2
    slow = effective_foot_speed_factor(t)
    assert fast > slow + 0.2
    # The slow fighter still moves (factor stays positive).
    assert slow > 0.0


def test_effective_speed_drops_with_leg_fatigue() -> None:
    """Cooked legs eat at most half the effective speed."""
    t, _ = _pair()
    fresh = effective_foot_speed_factor(t)
    t.state.body["right_leg"].fatigue = 1.0
    t.state.body["left_leg"].fatigue = 1.0
    fatigued = effective_foot_speed_factor(t)
    assert fatigued < fresh
    # The cap is 0.5; fatigued can't be less than half the fresh value.
    assert fatigued >= fresh * 0.5 - 1e-6


def test_step_magnitude_scales_per_fighter() -> None:
    """Two fighters stepping with the same base magnitude end up
    with measurably different displacements according to foot_speed."""
    t, s = _pair()
    t.capability.foot_speed = 9
    s.capability.foot_speed = 2
    base = STEP_MAGNITUDE_M
    fast_disp = effective_step_magnitude(t, base)
    slow_disp = effective_step_magnitude(s, base)
    assert fast_disp > slow_disp + 0.05


# ===========================================================================
# MOVE engine events emitted at the apply-actions layer
# ===========================================================================
def test_step_application_emits_move_event() -> None:
    """Applying a STEP action through _apply_body_actions emits a
    MOVE engine event with the tactical_intent + position delta on
    its data dict."""
    t, _ = _pair()
    s = main_module.build_sato()
    place_judoka(s, com_position=(2.0, 0.0), facing=(-1.0, 0.0))
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    events: list = []
    act = step("right_foot", (1.0, 0.0), 0.30,
               tactical_intent=TACTICAL_INTENT_PRESSURE)
    m._apply_body_actions(t, [act], tick=4, events=events)
    moves = [e for e in events if e.event_type == "MOVE"]
    assert len(moves) == 1
    assert moves[0].data["fighter"] == t.identity.name
    assert moves[0].data["tactical_intent"] == TACTICAL_INTENT_PRESSURE
    com_before = moves[0].data["com_before"]
    com_after  = moves[0].data["com_after"]
    assert com_after[0] > com_before[0]   # advanced along +x


def test_move_event_has_prose_silent_flag() -> None:
    """v0.1 narration hasn't promoted MOVE events — the prose stream
    should skip them via the prose_silent flag, while debug stream
    sees them."""
    t, _ = _pair()
    s = main_module.build_sato()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    events: list = []
    m._apply_body_actions(t, [step("right_foot", (1.0, 0.0), 0.20)],
                          tick=1, events=events)
    move = next(e for e in events if e.event_type == "MOVE")
    assert move.data.get("prose_silent") is True


# ===========================================================================
# Tactical intents — alongside HAJ-128 PositionalStyle
# ===========================================================================
def test_pressure_style_tags_steps_with_pressure_intent() -> None:
    """A PRESSURE-style fighter's step carries the PRESSURE intent on
    its Action so the MOVE event surfaces what kind of step it was."""
    t, _ = _pair()
    t.identity.positional_style = PositionalStyle.PRESSURE
    s = main_module.build_sato()
    place_judoka(s, com_position=(2.0, 0.0), facing=(-1.0, 0.0))
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=1)
    from action_selection import _maybe_emit_step
    rng = random.Random(0)
    # Try multiple rolls — eventually PRESSURE fires (it's probabilistic).
    intents_seen: set = set()
    for _ in range(60):
        act = _maybe_emit_step(t, s, m.grip_graph, rng)
        if act is not None:
            intents_seen.add(act.tactical_intent)
    assert TACTICAL_INTENT_PRESSURE in intents_seen


def test_defensive_style_tags_retreats_with_give_ground() -> None:
    """A DEFENSIVE_EDGE fighter pinned near the edge tags retreats as
    GIVE_GROUND so push-out bookkeeping reads them correctly."""
    t, _ = _pair()
    t.identity.positional_style = PositionalStyle.DEFENSIVE_EDGE
    t.state.body_state.com_position = (3.5, 0.0)   # in the edge zone
    s = main_module.build_sato()
    place_judoka(s, com_position=(2.0, 0.0), facing=(-1.0, 0.0))
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=2)
    from action_selection import _maybe_emit_step
    rng = random.Random(0)
    intents_seen: set = set()
    for _ in range(60):
        act = _maybe_emit_step(t, s, m.grip_graph, rng)
        if act is not None:
            intents_seen.add(act.tactical_intent)
    assert TACTICAL_INTENT_GIVE_GROUND in intents_seen


def test_grip_war_evasion_tags_steps_with_circle() -> None:
    """During an active grip war, the evasion step (perpendicular to
    the line of attack) gets the CIRCLE intent."""
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=3)
    _seat_grips(m, t, s)
    _seat_grips(m, s, t)
    from action_selection import _maybe_emit_step
    rng = random.Random(0)
    intents_seen: set = set()
    for _ in range(60):
        act = _maybe_emit_step(t, s, m.grip_graph, rng)
        if act is not None:
            intents_seen.add(act.tactical_intent)
    assert TACTICAL_INTENT_CIRCLE in intents_seen


def test_tactical_intents_set_contains_all_known_labels() -> None:
    """The TACTICAL_INTENTS frozenset must contain all four edge-
    relative intents AND the five strategic-intent labels added by
    HAJ-156's review comment."""
    expected = {
        TACTICAL_INTENT_PRESSURE,
        TACTICAL_INTENT_GIVE_GROUND,
        TACTICAL_INTENT_CIRCLE,
        TACTICAL_INTENT_HOLD_CENTER,
        "gain_angle", "run_clock", "catch_moment", "bait", "catch_breath",
    }
    assert expected.issubset(TACTICAL_INTENTS)


# ===========================================================================
# entry_direction + spatial-mismatch kuzushi penalty
# ===========================================================================
def test_throws_carry_entry_direction_field() -> None:
    """Every throw def carries an entry_direction; the four sacrifice
    / lateral / two-phase classes are explicitly assigned (not the
    ADVANCING default)."""
    for throw_id, td in THROW_DEFS.items():
        assert hasattr(td, "entry_direction"), throw_id
        assert isinstance(td.entry_direction, EntryDirection), throw_id
    # Spot check — the four spatially distinct entries.
    assert THROW_DEFS[ThrowID.SUMI_GAESHI].entry_direction == EntryDirection.DROPPING
    assert THROW_DEFS[ThrowID.TOMOE_NAGE].entry_direction == EntryDirection.DROPPING
    assert THROW_DEFS[ThrowID.O_SOTO_GARI].entry_direction == EntryDirection.ADVANCING_LATERAL
    assert THROW_DEFS[ThrowID.O_UCHI_GARI].entry_direction == EntryDirection.ADVANCING_LATERAL
    assert THROW_DEFS[ThrowID.KO_UCHI_GARI].entry_direction == EntryDirection.RETREATING_THEN_DRIVING
    assert THROW_DEFS[ThrowID.DE_ASHI_HARAI].entry_direction == EntryDirection.RETREATING_THEN_DRIVING


def test_advancing_throw_at_edge_incurs_penalty() -> None:
    """An ADVANCING throw fired with tori in the edge zone returns a
    non-zero spatial-mismatch penalty; same throw mid-mat is zero."""
    t, s = _pair()
    td_advancing = THROW_DEFS[ThrowID.UCHI_MATA]
    assert td_advancing.entry_direction == EntryDirection.ADVANCING

    # Tori at center → no penalty.
    t.state.body_state.com_position = (0.0, 0.0)
    s.state.body_state.com_position = (1.0, 0.0)
    assert _spatial_mismatch_penalty(t, s, td_advancing) == 0.0

    # Tori in the edge zone → penalty.
    t.state.body_state.com_position = (MAT_HALF_WIDTH - 0.3, 0.0)
    pen = _spatial_mismatch_penalty(t, s, td_advancing)
    assert pen > 0.0
    assert pen <= 0.20  # ticket calls for 0.1–0.2 magnitude


def test_sacrifice_throw_no_edge_penalty() -> None:
    """SACRIFICE throws drop in place; no spatial penalty."""
    t, s = _pair()
    td_sacrifice = THROW_DEFS[ThrowID.SUMI_GAESHI]
    assert td_sacrifice.entry_direction == EntryDirection.DROPPING
    t.state.body_state.com_position = (MAT_HALF_WIDTH - 0.2, 0.0)
    assert _spatial_mismatch_penalty(t, s, td_sacrifice) == 0.0


def test_retreating_then_driving_penalty_when_uke_at_edge() -> None:
    """RETREATING_THEN_DRIVING throws need uke to have room to be
    drawn forward. Uke pinned at the edge → penalty."""
    t, s = _pair()
    td_foot_sweep = THROW_DEFS[ThrowID.DE_ASHI_HARAI]
    assert td_foot_sweep.entry_direction == EntryDirection.RETREATING_THEN_DRIVING
    s.state.body_state.com_position = (MAT_HALF_WIDTH - 0.3, 0.0)
    pen = _spatial_mismatch_penalty(t, s, td_foot_sweep)
    assert pen > 0.0


# ===========================================================================
# Push-out shido (edge zone tracking + ref strictness)
# ===========================================================================
def test_edge_zone_counter_increments_when_in_zone() -> None:
    """A fighter parked in the edge zone with retreating last-step sees
    their time_in_edge_zone counter accumulate each tick."""
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=1)
    t.state.body_state.com_position = (MAT_HALF_WIDTH - 0.3, 0.0)
    t.state.last_move_direction_sign = -1
    events: list = []
    for tick in range(1, 4):
        m._update_edge_zone_counters_and_shido(tick, events)
    assert t.state.time_in_edge_zone == 3


def test_edge_zone_counter_resets_in_safe_zone() -> None:
    """Returning to the central area resets the counter."""
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=1)
    t.state.body_state.com_position = (MAT_HALF_WIDTH - 0.3, 0.0)
    t.state.last_move_direction_sign = -1
    events: list = []
    for tick in range(1, 3):
        m._update_edge_zone_counters_and_shido(tick, events)
    assert t.state.time_in_edge_zone == 2
    # Walk back to centre.
    t.state.body_state.com_position = (0.0, 0.0)
    m._update_edge_zone_counters_and_shido(3, events)
    assert t.state.time_in_edge_zone == 0


def test_push_out_shido_fires_for_retreating_fighter_at_threshold() -> None:
    """A retreating fighter who lingers in the edge zone past the
    referee threshold draws a push-out shido. The shido goes to the
    retreater, not the pressing opponent (even if the opponent shares
    the zone)."""
    t, s = _pair()
    # Strict ref → 8-tick threshold.
    ref = Referee(name="Strict", nationality="X", mat_edge_strictness=1.0)
    m = Match(fighter_a=t, fighter_b=s, referee=ref, seed=1)
    threshold = ref._PUSH_OUT_SHIDO_TICKS
    t.state.body_state.com_position = (MAT_HALF_WIDTH - 0.3, 0.0)
    t.state.last_move_direction_sign = -1   # retreating
    s.state.body_state.com_position = (0.0, 0.0)  # central; not retreating
    events: list = []
    for tick in range(1, threshold + 2):
        m._update_edge_zone_counters_and_shido(tick, events)
        if any(e.event_type == "SHIDO_AWARDED" for e in events):
            break
    shidos = [e for e in events if e.event_type == "SHIDO_AWARDED"]
    assert shidos, "expected a push-out shido for the retreating fighter"
    assert shidos[0].data["fighter"] == t.identity.name
    assert shidos[0].data["reason"] == "push_out"
    # Sato (the pressing fighter) is unaffected.
    assert s.state.shidos == 0


def test_push_out_threshold_governed_by_mat_edge_strictness() -> None:
    """Strict ref shidos faster than a generous one. The threshold
    moves through the 8–15 tick band per ticket calibration."""
    strict = Referee(name="Strict", nationality="X", mat_edge_strictness=1.0)
    generous = Referee(name="Lenient", nationality="X", mat_edge_strictness=0.0)
    assert strict._PUSH_OUT_SHIDO_TICKS == 8
    assert generous._PUSH_OUT_SHIDO_TICKS == 15


def test_push_out_shido_skipped_for_pressing_fighter() -> None:
    """A pressing fighter (last move advancing-class) at the edge does
    NOT receive a push-out shido — they're not the one being driven."""
    t, s = _pair()
    ref = Referee(name="Strict", nationality="X", mat_edge_strictness=1.0)
    m = Match(fighter_a=t, fighter_b=s, referee=ref, seed=1)
    t.state.body_state.com_position = (MAT_HALF_WIDTH - 0.3, 0.0)
    t.state.last_move_direction_sign = +1   # advancing into a corner
    events: list = []
    for tick in range(1, 30):
        m._update_edge_zone_counters_and_shido(tick, events)
    assert not any(e.event_type == "SHIDO_AWARDED" for e in events)
    assert t.state.shidos == 0


# ===========================================================================
# step_direction_sign — pure helper
# ===========================================================================
def test_step_direction_sign_classifies_retreat_advance_lateral() -> None:
    """The helper that classifies a step's direction relative to mat
    centre: retreats register -1, advances +1, lateral 0."""
    # Retreat: moving away from origin.
    assert _step_direction_sign((0.0, 0.0), (1.0, 0.0)) == -1
    # Advance: moving toward origin.
    assert _step_direction_sign((2.0, 0.0), (1.0, 0.0)) == +1
    # Lateral / negligible: same distance.
    assert _step_direction_sign((1.0, 0.0), (1.02, 0.0)) == 0


# ===========================================================================
# Full-suite integration — fighter actually traverses with foot_speed
# ===========================================================================
def test_high_foot_speed_traverses_more_distance() -> None:
    """Two matches with the same archetypes but different foot_speed
    values: the foot_speed-9 fighter visibly traverses more distance
    than the foot_speed-3 fighter over the same window."""
    import io, contextlib, action_selection
    real_emit = action_selection._maybe_emit_foot_attack
    real_plan = action_selection._apply_plan_layer
    action_selection._maybe_emit_foot_attack = lambda *a, **kw: None
    action_selection._apply_plan_layer = lambda *a, **kw: a[5]
    try:
        # Fast fighter run.
        random.seed(1)
        t_fast = main_module.build_tanaka()
        t_fast.skill_vector.pull_execution = 0.8
        t_fast.capability.foot_speed = 9
        t_fast.identity.positional_style = PositionalStyle.PRESSURE
        s_fast = main_module.build_sato()
        place_judoka(t_fast, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
        place_judoka(s_fast, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
        m_fast = Match(fighter_a=t_fast, fighter_b=s_fast,
                       referee=build_suzuki(), max_ticks=30, seed=1)
        m_fast.ne_waza_resolver.attempt_ground_commit = lambda *a, **kw: False
        with contextlib.redirect_stdout(io.StringIO()):
            m_fast.run()
        fast_dx = abs(t_fast.state.body_state.com_position[0] - (-0.5))

        # Slow fighter run — same seed, same flags.
        random.seed(1)
        t_slow = main_module.build_tanaka()
        t_slow.skill_vector.pull_execution = 0.8
        t_slow.capability.foot_speed = 3
        t_slow.identity.positional_style = PositionalStyle.PRESSURE
        s_slow = main_module.build_sato()
        place_judoka(t_slow, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
        place_judoka(s_slow, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
        m_slow = Match(fighter_a=t_slow, fighter_b=s_slow,
                       referee=build_suzuki(), max_ticks=30, seed=1)
        m_slow.ne_waza_resolver.attempt_ground_commit = lambda *a, **kw: False
        with contextlib.redirect_stdout(io.StringIO()):
            m_slow.run()
        slow_dx = abs(t_slow.state.body_state.com_position[0] - (-0.5))
    finally:
        action_selection._maybe_emit_foot_attack = real_emit
        action_selection._apply_plan_layer = real_plan
    assert fast_dx > slow_dx, (
        f"foot_speed=9 should traverse more than foot_speed=3; "
        f"fast={fast_dx:.3f} m, slow={slow_dx:.3f} m"
    )


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
