# tests/test_skill_compression.py
# Verifies Part 6.1 of design-notes/physics-substrate.md:
#   - Belt-rank → N mapping (elite 1 tick; white belt 5–6 ticks)
#   - Tokui-waza override: signature throws use N-1 (floor 1)
#   - sub_event_schedule collapses/spreads the four sub-events per spec
#     examples (N=1 single line; N=2 KA+TS+KC together; N≥5 wide gaps)
#   - Multi-tick commit emits THROW_ENTRY + sub-events across N ticks
#   - Single-tick (N=1) commit still resolves in one tick
#   - Mid-attempt stun aborts the attempt through the failed-commit pipeline
#   - Action-selection COMMIT_THROW is stripped while an attempt is in flight

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from enums import (
    BeltRank, BodyPart, GripTypeV2, GripDepth, GripMode, GripTarget,
)
from body_state import place_judoka
from grip_graph import GripGraph, GripEdge
from throws import ThrowID
from skill_compression import (
    N_BY_BELT, compression_n_for, sub_event_schedule, SubEvent,
)
from actions import Action, ActionKind, commit_throw
import main as main_module


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------
def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _seat_deep_grips(graph: GripGraph, attacker, defender) -> None:
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
# Belt → N mapping
# ---------------------------------------------------------------------------
def test_n_by_belt_monotone_elite_to_white() -> None:
    # White belt is slowest, elite is fastest.
    assert N_BY_BELT[BeltRank.WHITE]   >= N_BY_BELT[BeltRank.GREEN]
    assert N_BY_BELT[BeltRank.GREEN]   >= N_BY_BELT[BeltRank.BROWN]
    assert N_BY_BELT[BeltRank.BROWN]   >= N_BY_BELT[BeltRank.BLACK_1]
    assert N_BY_BELT[BeltRank.BLACK_1] >= N_BY_BELT[BeltRank.BLACK_5]
    assert N_BY_BELT[BeltRank.BLACK_5] == 1
    # White belt lands in the 5–6 range per spec.
    assert 5 <= N_BY_BELT[BeltRank.WHITE] <= 6


def test_tokui_waza_override_is_n_minus_one_floor_one() -> None:
    t, _ = _pair()
    # Tanaka is BLACK_1 with SEOI_NAGE in signature_throws.
    base_n    = N_BY_BELT[t.identity.belt_rank]
    sig_n     = compression_n_for(t, ThrowID.SEOI_NAGE)
    nonsig_n  = compression_n_for(t, ThrowID.UCHI_MATA)
    assert sig_n    == max(1, base_n - 1)
    assert nonsig_n == base_n


def test_tokui_waza_floor_is_one_for_elite() -> None:
    t, _ = _pair()
    t.identity.belt_rank = BeltRank.BLACK_5   # N = 1 baseline
    assert compression_n_for(t, ThrowID.SEOI_NAGE) == 1
    # Non-signature for BLACK_5 also = 1.
    assert compression_n_for(t, ThrowID.UCHI_MATA) == 1


# ---------------------------------------------------------------------------
# sub_event_schedule shapes per spec
# ---------------------------------------------------------------------------
def test_schedule_n1_spreads_across_three_offsets() -> None:
    """HAJ-157 V1/V5 — N=1 elite throws no longer collapse all four
    sub-events onto the entry tick. RK + KA pair on the kuzushi tick,
    TS on the next, KC on the next; the outcome is deferred a further
    tick via the RESOLVE_KAKE_N1 consequence so kuzushi → tsukuri →
    kake → outcome occupy 4 distinct ticks in the engine event log."""
    s = sub_event_schedule(1)
    assert s == {
        0: [SubEvent.REACH_KUZUSHI, SubEvent.KUZUSHI_ACHIEVED],
        1: [SubEvent.TSUKURI],
        2: [SubEvent.KAKE_COMMIT],
    }


def test_schedule_n2_pairs_ka_ts_together() -> None:
    s = sub_event_schedule(2)
    assert SubEvent.KUZUSHI_ACHIEVED in s[1]
    assert SubEvent.TSUKURI          in s[1]
    assert SubEvent.KAKE_COMMIT      in s[1]
    assert s[0] == [SubEvent.REACH_KUZUSHI]


def test_schedule_n4_gives_one_event_per_tick() -> None:
    s = sub_event_schedule(4)
    assert s[0] == [SubEvent.REACH_KUZUSHI]
    assert s[1] == [SubEvent.KUZUSHI_ACHIEVED]
    assert s[2] == [SubEvent.TSUKURI]
    assert s[3] == [SubEvent.KAKE_COMMIT]


def test_schedule_n5_has_silent_padding_and_tight_finish() -> None:
    s = sub_event_schedule(5)
    # REACH on tick 0, then a silent gap.
    assert s[0] == [SubEvent.REACH_KUZUSHI]
    assert 1 not in s
    # KA / TS / KC in the final three ticks.
    assert s[2] == [SubEvent.KUZUSHI_ACHIEVED]
    assert s[3] == [SubEvent.TSUKURI]
    assert s[4] == [SubEvent.KAKE_COMMIT]


def test_schedule_always_ends_with_kake_commit() -> None:
    """KAKE_COMMIT lands on the final scheduled offset for every N. For
    N≥2 that's offset N-1 (the schedule's last entry); for the
    HAJ-157 N=1 spread layout it's offset 2 (the schedule's last
    entry, which differs from N-1=0)."""
    for n in range(1, 9):
        s = sub_event_schedule(n)
        last_offset = max(s.keys())
        assert SubEvent.KAKE_COMMIT in s[last_offset], (
            f"N={n}: KAKE_COMMIT should be on the final scheduled tick "
            f"(offset {last_offset}); got {s}"
        )


# ---------------------------------------------------------------------------
# Match integration — multi-tick commit
# ---------------------------------------------------------------------------
def test_multi_tick_commit_defers_resolution_until_kake() -> None:
    """Force Tanaka's commit on Uchi-mata (non-signature → N=2) and verify
    the attempt unfolds across two ticks: THROW_ENTRY at start, KAKE at end.
    """
    from match import Match
    from referee import build_suzuki
    random.seed(7)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    _seat_deep_grips(m.grip_graph, t, s)
    s.state.body_state.com_velocity = (-0.5, 0.0)

    # Uchi-mata is NOT in Tanaka's signature throws (Seoi-nage and
    # Harai-goshi are); BLACK_1 base N = 2. Expect 2-tick attempt.
    assert compression_n_for(t, ThrowID.UCHI_MATA) == 2

    tick0 = 5
    events0 = m._resolve_commit_throw(t, s, ThrowID.UCHI_MATA, tick=tick0)
    entry = [e for e in events0 if e.event_type == "THROW_ENTRY"]
    assert entry, "expected THROW_ENTRY on start tick"
    assert entry[0].data.get("compression_n") == 2
    # After start, the attempt is stashed and no THROW_LANDING / FAILED yet.
    assert t.identity.name in m._throws_in_progress
    assert not any(e.event_type in ("THROW_LANDING", "FAILED") for e in events0)

    # Advance one tick — this should emit the remaining sub-events and
    # resolve via resolve_throw.
    events1 = m._advance_throws_in_progress(tick=tick0 + 1)
    kinds = {e.event_type for e in events1}
    assert "SUB_KAKE_COMMIT" in kinds
    # Attempt cleared from the tracker after resolution.
    assert t.identity.name not in m._throws_in_progress


def test_elite_single_tick_commit_spreads_across_four_ticks() -> None:
    """HAJ-157 V1/V5 — an elite's throw (N=1) emits THROW_ENTRY + the
    kuzushi-phase sub-events (REACH_KUZUSHI + KUZUSHI_ACHIEVED) on the
    commit tick, then TSUKURI on T+1, KAKE_COMMIT on T+2, and the
    outcome (LANDED / STUFFED / FAILED) lands on T+3 from the
    RESOLVE_KAKE_N1 consequence. The four-stage chain occupies 4
    distinct ticks instead of collapsing into 2."""
    from match import Match
    from referee import build_suzuki
    random.seed(8)
    t, s = _pair()
    t.identity.belt_rank = BeltRank.BLACK_5   # N = 1
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    _seat_deep_grips(m.grip_graph, t, s)

    # T = 3: commit + offset-0 sub-events (RK, KA).
    events = m._resolve_commit_throw(t, s, ThrowID.UCHI_MATA, tick=3)
    kinds = {e.event_type for e in events}
    assert "THROW_ENTRY" in kinds
    assert "SUB_REACH_KUZUSHI" in kinds
    assert "SUB_KUZUSHI_ACHIEVED" in kinds
    # Tsukuri and kake have NOT fired yet on the commit tick.
    assert "SUB_TSUKURI" not in kinds
    assert "SUB_KAKE_COMMIT" not in kinds
    assert t.identity.name in m._throws_in_progress

    # T+1 = 4: tsukuri sub-event fires from _advance_throws_in_progress.
    advance1 = m._advance_throws_in_progress(tick=4)
    kinds1 = {e.event_type for e in advance1}
    assert "SUB_TSUKURI" in kinds1
    assert "SUB_KAKE_COMMIT" not in kinds1
    # Outcome has not fired — the tip is still in flight.
    assert t.identity.name in m._throws_in_progress

    # T+2 = 5: kake sub-event fires; the outcome is still deferred to T+3.
    advance2 = m._advance_throws_in_progress(tick=5)
    kinds2 = {e.event_type for e in advance2}
    assert "SUB_KAKE_COMMIT" in kinds2
    # The tip stays parked — RESOLVE_KAKE_N1 pops it when it fires.
    assert t.identity.name in m._throws_in_progress

    # T+3 = 6: RESOLVE_KAKE_N1 consequence fires the outcome and clears
    # the in-progress bookkeeping.
    consq_events: list = []
    m._resolve_consequences(tick=6, events=consq_events)
    assert t.identity.name not in m._throws_in_progress


def test_double_commit_by_same_fighter_is_rejected() -> None:
    """While Tanaka is mid-attempt, a second COMMIT_THROW from him is ignored."""
    from match import Match
    from referee import build_suzuki
    random.seed(9)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    _seat_deep_grips(m.grip_graph, t, s)

    m._resolve_commit_throw(t, s, ThrowID.UCHI_MATA, tick=1)
    # Sanity: in-progress.
    assert t.identity.name in m._throws_in_progress
    events = m._resolve_commit_throw(t, s, ThrowID.O_SOTO_GARI, tick=1)
    assert events == []


def test_mid_attempt_stun_aborts_through_failed_pipeline() -> None:
    """If the attacker gains stun_ticks mid-attempt, advancement aborts and
    emits a THROW_ABORTED + FAILED event pair with an outcome.
    """
    from match import Match
    from referee import build_suzuki
    random.seed(10)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    _seat_deep_grips(m.grip_graph, t, s)
    s.state.body_state.com_velocity = (-0.5, 0.0)

    m._resolve_commit_throw(t, s, ThrowID.UCHI_MATA, tick=1)
    assert t.identity.name in m._throws_in_progress

    # Stun tori before the next advancement tick.
    t.state.stun_ticks = 2
    events = m._advance_throws_in_progress(tick=2)
    kinds = [e.event_type for e in events]
    assert "THROW_ABORTED" in kinds
    assert "FAILED" in kinds
    assert t.identity.name not in m._throws_in_progress


def test_commit_strip_while_in_progress() -> None:
    """_strip_commits_if_in_progress removes COMMIT_THROW actions for a
    fighter who already has an attempt in flight.
    """
    from match import Match
    from referee import build_suzuki
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    actions = [commit_throw(ThrowID.UCHI_MATA), Action(kind=ActionKind.HOLD_CONNECTIVE)]
    # No in-progress — actions pass through untouched.
    assert m._strip_commits_if_in_progress(t.identity.name, actions) == actions
    # With in-progress — the commit is stripped.
    _seat_deep_grips(m.grip_graph, t, s)
    m._resolve_commit_throw(t, s, ThrowID.UCHI_MATA, tick=1)
    stripped = m._strip_commits_if_in_progress(t.identity.name, actions)
    assert all(a.kind != ActionKind.COMMIT_THROW for a in stripped)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
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
