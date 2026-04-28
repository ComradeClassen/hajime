# tests/test_foot_attack_kuzushi.py
# HAJ-133 — FOOT_ATTACK action family emits KuzushiEvents (parallel to PULL).
#
# Per grip-as-cause.md §3.5, foot attacks (foot sweeps, leg attack setups,
# disruptive steps) are a kuzushi-generating action family parallel to
# PULL — not just terminal throws. Pre-fix they only existed as terminal
# throws (de-ashi-harai, ko-uchi-gari); never as in-fight setups.
#
# Post-fix:
#   - Three new ActionKind values: FOOT_SWEEP_SETUP, LEG_ATTACK_SETUP,
#     DISRUPTIVE_STEP.
#   - Each emits a KuzushiEvent into uke's buffer with source=FOOT_ATTACK.
#   - Direction lookup per spec: sweep → lateral; leg attack → rear-corner;
#     disruptive step → opposite of step direction.
#   - Action selection substitutes the secondary drive for a foot-attack
#     setup at fight_iq-gated probability when the grip war stalemates.
#   - Existing terminal throws unchanged.

from __future__ import annotations
import os
import random as _r
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from enums import (
    BodyPart, GripTarget, GripTypeV2, GripDepth, Position,
)
from grip_graph import GripEdge
from kuzushi import (
    KuzushiSource, foot_attack_kuzushi_event, foot_attack_kuzushi_direction,
    foot_attack_kuzushi_magnitude,
)
from match import Match
from referee import build_suzuki
from actions import (
    ActionKind, FOOT_ATTACK_KINDS,
    foot_sweep_setup, leg_attack_setup, disruptive_step,
)
from throws import ThrowID
import main as main_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _pair_match():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    return t, s, m


def _seat_grips(m, owner, target):
    m.grip_graph.add_edge(GripEdge(
        grasper_id=owner.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=target.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.STANDARD,
        strength=0.8, established_tick=0,
    ))
    m.grip_graph.add_edge(GripEdge(
        grasper_id=owner.identity.name, grasper_part=BodyPart.LEFT_HAND,
        target_id=target.identity.name, target_location=GripTarget.RIGHT_SLEEVE,
        grip_type_v2=GripTypeV2.SLEEVE_HIGH, depth_level=GripDepth.STANDARD,
        strength=0.8, established_tick=0,
    ))


# ---------------------------------------------------------------------------
# 1. ActionKinds and family membership
# ---------------------------------------------------------------------------
def test_foot_attack_kinds_registered() -> None:
    """The three new action kinds exist and are in the FOOT_ATTACK_KINDS family."""
    assert ActionKind.FOOT_SWEEP_SETUP in FOOT_ATTACK_KINDS
    assert ActionKind.LEG_ATTACK_SETUP in FOOT_ATTACK_KINDS
    assert ActionKind.DISRUPTIVE_STEP  in FOOT_ATTACK_KINDS


def test_foot_attack_constructors_produce_correct_kinds() -> None:
    a = foot_sweep_setup("right_foot", (1.0, 0.0), magnitude=0.25)
    b = leg_attack_setup("left_foot",  (0.0, 1.0), magnitude=0.30)
    c = disruptive_step("right_foot", (-1.0, 0.0), magnitude=0.20)
    assert a.kind == ActionKind.FOOT_SWEEP_SETUP
    assert b.kind == ActionKind.LEG_ATTACK_SETUP
    assert c.kind == ActionKind.DISRUPTIVE_STEP
    assert a.foot == "right_foot" and a.direction == (1.0, 0.0)


# ---------------------------------------------------------------------------
# 2. Direction lookup
# ---------------------------------------------------------------------------
def test_foot_sweep_direction_tracks_attack_vector() -> None:
    """Foot sweep kuzushi vector tracks the sweep direction."""
    v = foot_attack_kuzushi_direction(
        ActionKind.FOOT_SWEEP_SETUP, (1.0, 0.0), attacker_facing=(1.0, 0.0),
    )
    assert v == (1.0, 0.0)


def test_leg_attack_direction_blends_rear_and_lateral() -> None:
    """Leg attack vector is a blend of rear (opposite attacker facing)
    and the lateral attack vector."""
    v = foot_attack_kuzushi_direction(
        ActionKind.LEG_ATTACK_SETUP, (0.0, 1.0), attacker_facing=(1.0, 0.0),
    )
    # Rear (60% of (-1,0)) + lateral (40% of (0,1)) → roughly (-0.6, 0.4)
    # normalized. x should be negative, y positive.
    assert v[0] < 0.0
    assert v[1] > 0.0


def test_disruptive_step_inverts_step_direction() -> None:
    v = foot_attack_kuzushi_direction(
        ActionKind.DISRUPTIVE_STEP, (1.0, 0.0), attacker_facing=(1.0, 0.0),
    )
    assert v == (-1.0, 0.0)


def test_zero_attack_vector_returns_zero() -> None:
    v = foot_attack_kuzushi_direction(
        ActionKind.FOOT_SWEEP_SETUP, (0.0, 0.0),
    )
    assert v == (0.0, 0.0)


# ---------------------------------------------------------------------------
# 3. Magnitude
# ---------------------------------------------------------------------------
def test_foot_attack_magnitude_positive_for_typical_fighter() -> None:
    t, s, _ = _pair_match()
    mag = foot_attack_kuzushi_magnitude(
        attacker=t, action_kind=ActionKind.FOOT_SWEEP_SETUP, victim=s,
    )
    assert mag > 0.0


def test_leg_attack_magnitude_higher_than_disruptive_step() -> None:
    """Per the kind-weight table, LEG_ATTACK_SETUP > FOOT_SWEEP_SETUP >
    DISRUPTIVE_STEP for the same attacker/victim."""
    t, s, _ = _pair_match()
    leg = foot_attack_kuzushi_magnitude(t, ActionKind.LEG_ATTACK_SETUP, s)
    swp = foot_attack_kuzushi_magnitude(t, ActionKind.FOOT_SWEEP_SETUP, s)
    stp = foot_attack_kuzushi_magnitude(t, ActionKind.DISRUPTIVE_STEP, s)
    assert leg > swp > stp


# ---------------------------------------------------------------------------
# 4. Match-side emission into uke's buffer
# ---------------------------------------------------------------------------
def test_foot_attack_emits_kuzushi_event_into_buffer() -> None:
    """A foot-attack action produces a KuzushiEvent in uke's buffer with
    source_kind=FOOT_ATTACK."""
    t, s, m = _pair_match()
    pre_count = len(s.kuzushi_events)
    actions = [foot_sweep_setup("right_foot", (1.0, 0.0))]
    m._apply_foot_attacks(attacker=t, victim=s, actions=actions, tick=10)
    assert len(s.kuzushi_events) == pre_count + 1
    ev = s.kuzushi_events[-1]
    assert ev.source_kind == KuzushiSource.FOOT_ATTACK
    assert ev.tick_emitted == 10


def test_foot_attack_compose_with_pulls_in_buffer() -> None:
    """Multiple foot attacks accumulate kuzushi state in uke's buffer the
    same way PULLs do — meeting the 'compose to support a foot-throw
    commit' acceptance criterion."""
    from kuzushi import compromised_state
    t, s, m = _pair_match()
    # Three sweeps in a row.
    actions = [foot_sweep_setup("right_foot", (1.0, 0.0))]
    for tick in range(1, 4):
        m._apply_foot_attacks(attacker=t, victim=s, actions=actions, tick=tick)
    state = compromised_state(s.kuzushi_events, current_tick=4)
    # Compromised state should have non-trivial magnitude pointing in the
    # sweep direction.
    assert state.magnitude > 0.0
    assert state.vector[0] > 0.0   # +x bias from the sweep direction


def test_foot_attack_costs_leg_fatigue_and_cardio() -> None:
    """Each foot attack imposes a small leg-fatigue + cardio cost on the
    attacker."""
    t, s, m = _pair_match()
    pre_leg = t.state.body["right_leg"].fatigue
    pre_cardio = t.state.cardio_current
    actions = [foot_sweep_setup("right_foot", (1.0, 0.0))]
    m._apply_foot_attacks(attacker=t, victim=s, actions=actions, tick=1)
    assert t.state.body["right_leg"].fatigue > pre_leg
    assert t.state.cardio_current < pre_cardio


# ---------------------------------------------------------------------------
# 5. Action selection: foot attacks fire when grip war stalemates.
# ---------------------------------------------------------------------------
def test_action_selection_emits_foot_attacks_under_stalemate() -> None:
    """When the kumi-kata clock has been advancing (proxy for stalemate),
    a fight_iq>=threshold fighter substitutes a foot-attack setup for the
    secondary drive at non-zero rate."""
    from action_selection import select_actions
    t, s, m = _pair_match()
    _seat_grips(m, t, s)
    fired = 0
    trials = 200
    rng = _r.Random(0)
    for _ in range(trials):
        actions = select_actions(
            t, s, m.grip_graph, kumi_kata_clock=12, rng=rng,
            position=Position.GRIPPING,
        )
        if any(a.kind in FOOT_ATTACK_KINDS for a in actions):
            fired += 1
    rate = fired / trials
    assert rate > 0.05, (
        f"foot attacks should fire under stalemate; rate {rate:.2%}"
    )


def test_action_selection_no_foot_attacks_during_initial_engagement() -> None:
    """Below FOOT_ATTACK_STALEMATE_CLOCK_MIN the gate doesn't open — the
    initial grip exchange should still happen via standard pulls/deepens."""
    from action_selection import (
        select_actions, FOOT_ATTACK_STALEMATE_CLOCK_MIN,
    )
    t, s, m = _pair_match()
    _seat_grips(m, t, s)
    rng = _r.Random(1)
    for _ in range(50):
        actions = select_actions(
            t, s, m.grip_graph,
            kumi_kata_clock=FOOT_ATTACK_STALEMATE_CLOCK_MIN - 1,
            rng=rng,
            position=Position.GRIPPING,
        )
        assert all(a.kind not in FOOT_ATTACK_KINDS for a in actions)


def test_low_fight_iq_does_not_emit_foot_attacks() -> None:
    """White / yellow belts (fight_iq below threshold) don't substitute
    foot attacks — they keep firing standard pulls."""
    from action_selection import select_actions
    t, s, m = _pair_match()
    t.capability.fight_iq = 2   # below FOOT_ATTACK_MIN_FIGHT_IQ
    _seat_grips(m, t, s)
    rng = _r.Random(2)
    for _ in range(50):
        actions = select_actions(
            t, s, m.grip_graph, kumi_kata_clock=20, rng=rng,
            position=Position.GRIPPING,
        )
        assert all(a.kind not in FOOT_ATTACK_KINDS for a in actions)


# ---------------------------------------------------------------------------
# 6. Existing terminal throws unchanged.
# ---------------------------------------------------------------------------
def test_terminal_foot_throws_still_commit_actions() -> None:
    """De-ashi-harai, ko-uchi-gari etc. remain commit-level throws — they
    aren't reclassified as the new setup actions."""
    from throws import THROW_REGISTRY
    for tid in (ThrowID.DE_ASHI_HARAI, ThrowID.KO_UCHI_GARI,
                ThrowID.O_UCHI_GARI):
        assert tid in THROW_REGISTRY
    # And the new ActionKinds are NOT in the COMMIT path.
    assert ActionKind.FOOT_SWEEP_SETUP != ActionKind.COMMIT_THROW
    assert ActionKind.LEG_ATTACK_SETUP != ActionKind.COMMIT_THROW


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
