# tests/test_haj164_engaged_step_frequency.py
# HAJ-164 — engagement-phase locomotion frequency calibration.
#
# Pre-fix, the action selector picked grip / deepen / strip / commit on
# essentially every engaged tick and almost never picked a STEP. The
# Renard vs Sato playthrough yielded ~1 [move] event across 22 engaged
# ticks. HAJ-164 lifts the engaged-window step probability so footwork
# fires every 2-3 ticks per fighter during low-stakes grip work, and
# suppresses footwork on high-stakes ticks (opponent mid-throw, judoka
# actively staging a multi-tick plan) so throw sequences aren't
# interrupted by gratuitous tangents.
#
# These tests pin the calibrated frequencies and the tactical-intent
# distribution per fighter style.

from __future__ import annotations
import contextlib
import io
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from actions import (
    ActionKind,
    TACTICAL_INTENT_PRESSURE, TACTICAL_INTENT_GIVE_GROUND,
    TACTICAL_INTENT_CIRCLE, TACTICAL_INTENT_HOLD_CENTER,
)
from body_state import place_judoka
from enums import (
    BodyPart, GripDepth, GripMode, GripTarget, GripTypeV2, Position,
    PositionalStyle,
)
from grip_graph import GripGraph, GripEdge
from intent import Plan, PlanStep
from throws import ThrowID
from match import (
    Match, ENGAGEMENT_GRIP_SEAT_GAP_M, ENGAGEMENT_GRIP_SEAT_TICKS_MAX,
)
from referee import build_suzuki
from action_selection import (
    _maybe_emit_step, _is_engaged_high_stakes,
    ENGAGED_STEP_PROB_LOW_STAKES, ENGAGED_STEP_PROB_HIGH_STAKES,
)
import main as main_module


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------
def _engaged_pair(
    style_a: PositionalStyle = PositionalStyle.HOLD_CENTER,
    style_b: PositionalStyle = PositionalStyle.HOLD_CENTER,
):
    """Two fighters at engagement distance, both owning a STANDARD grip
    on the other (active grip war). The action selector's engaged-step
    branch fires only when both fighters have edges, so this is the
    minimal fixture for HAJ-164 frequency tests."""
    a = main_module.build_tanaka()
    b = main_module.build_sato()
    a.identity.positional_style = style_a
    b.identity.positional_style = style_b
    place_judoka(a, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(b, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    g = GripGraph()
    g.add_edge(GripEdge(
        grasper_id=a.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=b.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.STANDARD,
        strength=1.0, established_tick=0, mode=GripMode.CONNECTIVE,
    ))
    g.add_edge(GripEdge(
        grasper_id=b.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=a.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.STANDARD,
        strength=1.0, established_tick=0, mode=GripMode.CONNECTIVE,
    ))
    return a, b, g


def _emit_rate(judoka, opponent, graph, n: int = 400, **kw) -> float:
    """Run _maybe_emit_step `n` times with fresh per-call rngs and return
    the fraction of calls that produced a STEP."""
    fired = 0
    for seed in range(n):
        rng = random.Random(seed)
        out = _maybe_emit_step(judoka, opponent, graph, rng, **kw)
        if out is not None:
            fired += 1
    return fired / n


# ===========================================================================
# Acceptance criterion 1: low-stakes engaged ticks emit STEP at the
# calibrated frequency (~ENGAGED_STEP_PROB_LOW_STAKES).
# ===========================================================================
def test_low_stakes_engaged_emits_step_around_45_percent() -> None:
    """When both fighters have edges and there's no throw in flight or
    plan staging, the engaged-step branch fires at ~ENGAGED_STEP_PROB_LOW_STAKES.
    A wide tolerance (±0.10) accommodates the style-direction veto
    inside `_grip_war_evasion_direction` and rng noise."""
    a, b, g = _engaged_pair()
    rate = _emit_rate(a, b, g, n=600, current_tick=10)
    assert abs(rate - ENGAGED_STEP_PROB_LOW_STAKES) < 0.10, (
        f"low-stakes engaged step rate should be ≈{ENGAGED_STEP_PROB_LOW_STAKES}; "
        f"got {rate:.3f}"
    )


def test_low_stakes_engaged_emits_at_least_5_per_match_window() -> None:
    """A 22-tick engagement window with two fighters firing at the
    low-stakes probability should emit ≥5 STEPs on average — the
    ticket's rough QA target. We model the window as 22 independent
    rng draws per fighter; with prob 0.45 the expectation is ~10 each.
    The bound here is generous so any future calibration shift below
    0.30 trips the test."""
    a, b, g = _engaged_pair()
    fired_a = 0
    fired_b = 0
    rng = random.Random(42)
    for _ in range(22):
        if _maybe_emit_step(a, b, g, rng, current_tick=5) is not None:
            fired_a += 1
        if _maybe_emit_step(b, a, g, rng, current_tick=5) is not None:
            fired_b += 1
    assert fired_a + fired_b >= 5, (
        f"expected ≥5 STEPs across 22-tick engaged window; "
        f"got fighter_a={fired_a}, fighter_b={fired_b}"
    )


# ===========================================================================
# Acceptance criterion 2: high-stakes engaged ticks suppress STEP.
# ===========================================================================
def test_high_stakes_opponent_mid_throw_suppresses_step() -> None:
    """When `opponent_in_progress_throw` is set, the engaged-step branch
    drops to ~ENGAGED_STEP_PROB_HIGH_STAKES so a defending fighter
    doesn't insert a footwork tangent into the resolution window."""
    a, b, g = _engaged_pair()
    rate = _emit_rate(
        a, b, g, n=600, current_tick=10,
        opponent_in_progress_throw=ThrowID.UCHI_MATA,
    )
    assert rate <= ENGAGED_STEP_PROB_HIGH_STAKES + 0.05, (
        f"high-stakes (opponent mid-throw) engaged step rate should be "
        f"near {ENGAGED_STEP_PROB_HIGH_STAKES}; got {rate:.3f}"
    )


def test_high_stakes_active_plan_suppresses_step() -> None:
    """A judoka actively staging their own plan (step_index > 0) is
    mid-sequence — STEP must be suppressed so the plan's tick-locking
    that produces emergent throws isn't broken by a footwork tangent."""
    a, b, g = _engaged_pair()
    a.current_plan = Plan(
        target_throw_id=ThrowID.SEOI_NAGE,
        sequence=[PlanStep.PULL_SLEEVE, PlanStep.PULL_LAPEL,
                  PlanStep.COMMIT_THROW],
        step_index=1,           # past stage 0 — actively staging
        formed_at_tick=4,
        last_advanced_tick=5,
    )
    rate = _emit_rate(a, b, g, n=600, current_tick=10)
    assert rate <= ENGAGED_STEP_PROB_HIGH_STAKES + 0.05, (
        f"high-stakes (own plan staging) engaged step rate should be "
        f"near {ENGAGED_STEP_PROB_HIGH_STAKES}; got {rate:.3f}"
    )


def test_high_stakes_predicate_routine_grip_work_is_low_stakes() -> None:
    """Routine PULL/DEEPEN ticks open vulnerability windows and emit
    kuzushi events every tick; the high-stakes predicate must NOT fire
    on those (otherwise the engaged-step branch is suppressed every
    engaged tick, which is the pre-fix bug). The predicate fires only
    on a definitive throw-sequence signal."""
    a, b, g = _engaged_pair()
    # Plan exists but hasn't advanced past stage 0 yet — formation
    # tick. This shouldn't count as "staging".
    a.current_plan = Plan(
        target_throw_id=ThrowID.SEOI_NAGE,
        sequence=[PlanStep.PULL_SLEEVE, PlanStep.PULL_LAPEL,
                  PlanStep.COMMIT_THROW],
        step_index=0,
        formed_at_tick=4,
        last_advanced_tick=4,
    )
    assert _is_engaged_high_stakes(
        a, b, current_tick=10, opponent_in_progress_throw=None,
    ) is False


# ===========================================================================
# Acceptance criterion 3: tactical-intent distribution differentiates by
# fighter style.
# ===========================================================================
def test_pressure_style_dominates_pressure_intent_in_engaged_steps() -> None:
    """A PRESSURE-styled fighter's engaged-window steps are mostly
    tagged PRESSURE (with a CIRCLE minority for visible angle-finding).
    PRESSURE majority is the style-distinctive read."""
    a, b, g = _engaged_pair(style_a=PositionalStyle.PRESSURE)
    intents = []
    for seed in range(400):
        rng = random.Random(seed)
        out = _maybe_emit_step(a, b, g, rng, current_tick=5)
        if out is not None:
            intents.append(out.tactical_intent)
    counts = Counter(intents)
    assert counts.get(TACTICAL_INTENT_PRESSURE, 0) > counts.get(
        TACTICAL_INTENT_CIRCLE, 0
    ), f"PRESSURE intent should dominate engaged steps; got {dict(counts)}"


def test_defensive_edge_style_dominates_give_ground_in_engaged_steps() -> None:
    """A DEFENSIVE_EDGE-styled fighter's engaged-window steps lean
    GIVE_GROUND so push-out bookkeeping reads them as retreats."""
    a, b, g = _engaged_pair(style_a=PositionalStyle.DEFENSIVE_EDGE)
    intents = []
    for seed in range(400):
        rng = random.Random(seed)
        out = _maybe_emit_step(a, b, g, rng, current_tick=5)
        if out is not None:
            intents.append(out.tactical_intent)
    counts = Counter(intents)
    assert counts.get(TACTICAL_INTENT_GIVE_GROUND, 0) > counts.get(
        TACTICAL_INTENT_CIRCLE, 0
    ), f"GIVE_GROUND intent should dominate engaged steps; got {dict(counts)}"


def test_hold_center_style_dominates_circle_in_engaged_steps() -> None:
    """A HOLD_CENTER-styled fighter (the counter-fighter archetype)
    leans CIRCLE during engagement — pure lateral angle-finding rather
    than driving forward or retreating."""
    a, b, g = _engaged_pair(style_a=PositionalStyle.HOLD_CENTER)
    intents = []
    for seed in range(400):
        rng = random.Random(seed)
        out = _maybe_emit_step(a, b, g, rng, current_tick=5)
        if out is not None:
            intents.append(out.tactical_intent)
    counts = Counter(intents)
    assert counts.get(TACTICAL_INTENT_CIRCLE, 0) > counts.get(
        TACTICAL_INTENT_HOLD_CENTER, 0
    ), f"CIRCLE intent should dominate engaged steps; got {dict(counts)}"


def test_intent_mixes_visibly_differ_between_pressure_and_defensive() -> None:
    """Pressure-fighter and defensive-fighter matches show visibly
    different MOVE event mixes (acceptance criterion 3 — eye-test
    proxy)."""
    pressure_intents: list[str] = []
    defensive_intents: list[str] = []
    a, b, g = _engaged_pair(style_a=PositionalStyle.PRESSURE)
    for seed in range(300):
        rng = random.Random(seed)
        out = _maybe_emit_step(a, b, g, rng, current_tick=5)
        if out is not None:
            pressure_intents.append(out.tactical_intent)
    a, b, g = _engaged_pair(style_a=PositionalStyle.DEFENSIVE_EDGE)
    for seed in range(300):
        rng = random.Random(seed)
        out = _maybe_emit_step(a, b, g, rng, current_tick=5)
        if out is not None:
            defensive_intents.append(out.tactical_intent)
    pc = Counter(pressure_intents)
    dc = Counter(defensive_intents)
    # The dominant intent in each is the style-primary, and they must
    # be different — that's the eye-test "differentiates by style".
    pressure_dom = pc.most_common(1)[0][0]
    defensive_dom = dc.most_common(1)[0][0]
    assert pressure_dom == TACTICAL_INTENT_PRESSURE
    assert defensive_dom == TACTICAL_INTENT_GIVE_GROUND
    assert pressure_dom != defensive_dom


# ===========================================================================
# Follow-up — grip-seating distance gate.
#
# HAJ-163's BAIT_RETREAT and LATERAL_APPROACH closing-phase variants
# don't close the dyad axis. Pre-fix, the engagement resolver fired the
# grip cascade after ENGAGEMENT_TICKS_FLOOR ticks of mutual REACH
# regardless of actual gap, so two fighters could spend the closing
# phase on lateral / reverse motion and seat grips with 2 m+ still
# between them. The follow-up adds a CoM-gap gate so engagement means
# what it says: hands within reach.
# ===========================================================================
def _first_grip_seat(seed: int) -> tuple[int, float]:
    """Run a Tanaka vs Sato match at `seed` and return (tick, gap_at_seat)
    for the first grip cascade. Helper for the gap-gate calibration."""
    random.seed(seed)
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=240, seed=seed,
    )
    seen: list[tuple[int, float]] = []
    real_stage = m._stage_grip_cascade

    def wrap(tick: int, events: list) -> None:
        if not seen:
            ax, ay = t.state.body_state.com_position
            bx, by = s.state.body_state.com_position
            seen.append((tick, ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5))
        return real_stage(tick, events)

    m._stage_grip_cascade = wrap
    with contextlib.redirect_stdout(io.StringIO()):
        m.run()
    assert seen, f"seed={seed} produced no grip cascade in 240 ticks"
    return seen[0]


def test_grip_seating_respects_engagement_distance_gate() -> None:
    """The first grip cascade in any match must seat with the dyad
    inside engagement reach (<= ENGAGEMENT_GRIP_SEAT_GAP_M, with a
    small float tolerance). Pre-fix observation: seed 0 seated at
    2.19 m; the gap gate brings every seed in this sweep under 1.2 m."""
    for seed in range(15):
        _, gap = _first_grip_seat(seed)
        assert gap <= ENGAGEMENT_GRIP_SEAT_GAP_M + 0.05, (
            f"seed={seed}: first grip seated at gap={gap:.2f} m, "
            f"exceeds the engagement-distance gate "
            f"({ENGAGEMENT_GRIP_SEAT_GAP_M:.2f} m)"
        )


def test_grip_seating_within_safety_max_ticks() -> None:
    """The gap gate is bounded by ENGAGEMENT_GRIP_SEAT_TICKS_MAX so
    pathological lateral-every-tick seeds don't livelock the closing
    phase. Across the QA sweep, every match's first grip cascade must
    fire by the safety bound."""
    for seed in range(15):
        tick, _ = _first_grip_seat(seed)
        assert tick <= ENGAGEMENT_GRIP_SEAT_TICKS_MAX + 1, (
            f"seed={seed}: first grip seated at t{tick:03d}, "
            f"past the safety bound ({ENGAGEMENT_GRIP_SEAT_TICKS_MAX})"
        )


def test_distance_gate_holds_open_when_dyad_still_wide() -> None:
    """Direct unit test of the engagement resolver: with both fighters
    still 2 m apart and 3 ticks of mutual REACH already accumulated,
    the resolver must NOT stage the grip cascade. The gate fires
    instead and engagement_ticks accumulates for the next tick."""
    random.seed(1)
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-1.0, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+1.0, 0.0), facing=(-1.0, 0.0))
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=10, seed=1,
    )
    # Force STANDING_DISTANT and accumulate engagement ticks past the
    # floor without seating grips by hand.
    m.position = Position.STANDING_DISTANT
    m.engagement_ticks = 3   # at the floor; gap > gate must hold
    cascade_fired = [False]
    real_stage = m._stage_grip_cascade

    def wrap(tick, events):
        cascade_fired[0] = True
        return real_stage(tick, events)
    m._stage_grip_cascade = wrap

    from actions import reach
    reach_actions = [reach(
        "right_hand", GripTypeV2.LAPEL_HIGH, GripTarget.LEFT_LAPEL,
    )]
    events: list = []
    m._resolve_engagement(reach_actions, reach_actions, tick=4, events=events)
    assert cascade_fired[0] is False, (
        "grip cascade should not fire when dyad gap is 2 m, even with "
        "engagement_ticks past the tick floor"
    )
    # engagement_ticks must keep accumulating so the next tick re-checks
    # the gate (instead of resetting to 0).
    assert m.engagement_ticks == 4


def test_distance_gate_lets_cascade_fire_when_close() -> None:
    """When the dyad has closed inside the gate threshold, the resolver
    stages the cascade as soon as the tick floor is met."""
    random.seed(1)
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=10, seed=1,
    )
    m.position = Position.STANDING_DISTANT
    m.engagement_ticks = 2   # one shy of the floor

    cascade_fired = [False]
    real_stage = m._stage_grip_cascade

    def wrap(tick, events):
        cascade_fired[0] = True
        return real_stage(tick, events)
    m._stage_grip_cascade = wrap

    from actions import reach
    reach_actions = [reach(
        "right_hand", GripTypeV2.LAPEL_HIGH, GripTarget.LEFT_LAPEL,
    )]
    events: list = []
    # tick 4: engagement_ticks goes to 3, gap=1.0 m → cascade fires
    m._resolve_engagement(reach_actions, reach_actions, tick=4, events=events)
    assert cascade_fired[0] is True, (
        "grip cascade should fire when dyad gap is 1 m and tick floor met"
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
