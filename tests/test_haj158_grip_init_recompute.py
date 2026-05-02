# tests/test_haj158_grip_init_recompute.py
# HAJ-158 — initiative recompute on FAILED / STUFFED resolutions.
#
# Pre-fix: `[grip_init]` only fires when `_resolve_engagement` reaches
# `edge_count == 0` (grips actually broke). A failed throw that doesn't
# break grips never triggers a fresh initiative cascade, so HAJ-151's
# "per-exchange" intent collapses to "first exchange varies; everything
# after is mirror." Post-fix: every FAILED / STUFFED resolution schedules
# a GRIP_INIT_RECOMPUTE consequence on tick+1; the handler emits a fresh
# `[grip_init]` event using current state (so the post-failure composure
# dip on tori expresses on the next initiative roll).
#
# Seven AC scenarios from the issue:
#   1. Failed throws trigger fresh initiative on tick+1.
#   2. Stuffed throws trigger fresh initiative on tick+1.
#   3. Composure dip from repeated failure is reflected in the recompute.
#   4. Multi-failure match has multiple `[grip_init]` events.
#   5. HAJ-144-style reproduction — every failure produces a recompute.
#   6. No regression on initiative-at-hajime.
#   7. No regression on edge_count==0 path (matte / disengage trigger
#      initiative as they did before).

from __future__ import annotations
import contextlib
import io
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from enums import (
    BeltRank, BodyPart, GripTypeV2, GripDepth, GripMode, GripTarget,
    Position, SubLoopState,
)
from body_state import place_judoka
from grip_graph import GripGraph, GripEdge
from throws import ThrowID
from match import Match
from referee import build_suzuki
from grip_initiative import (
    RESP_DISENGAGE, ALL_RESPONSE_KINDS, GripResponseChoice,
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


def _elite_match(seed: int = 0):
    """Both fighters elite (N=1), grips seated, ready for direct
    _resolve_commit_throw / consequence-driven resolution."""
    random.seed(seed)
    t, s = _pair()
    t.identity.belt_rank = BeltRank.BLACK_5
    s.identity.belt_rank = BeltRank.BLACK_5
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=seed)
    m.position = Position.GRIPPING
    _seat_deep_grips(m.grip_graph, t, s)
    _seat_deep_grips(m.grip_graph, s, t)
    return t, s, m


def _drive_failed_throw(m, t, s, throw_id, commit_tick):
    """Drive an N=1 throw to a forced FAILED outcome through the
    HAJ-148 / HAJ-157 N+3 chain. Returns the cumulative event list
    spanning commit_tick → commit_tick + 4 (so the GRIP_INIT_RECOMPUTE
    on commit_tick + 4 lands in the returned list)."""
    real_resolve = match_module.resolve_throw
    match_module.resolve_throw = lambda *a, **kw: ("FAILED", -5.0)
    collected: list = []
    try:
        collected.extend(m._resolve_commit_throw(t, s, throw_id, tick=commit_tick))
        collected.extend(m._advance_throws_in_progress(tick=commit_tick + 1))
        collected.extend(m._advance_throws_in_progress(tick=commit_tick + 2))
        m._resolve_consequences(tick=commit_tick + 3, events=collected)
        # Tick + 4: GRIP_INIT_RECOMPUTE consequence fires.
        m._resolve_consequences(tick=commit_tick + 4, events=collected)
    finally:
        match_module.resolve_throw = real_resolve
    return collected


def _drive_stuffed_throw(m, t, s, throw_id, commit_tick):
    """Drive an N=1 throw to a forced STUFFED outcome (no commit
    motivation, so we hit the dedicated STUFFED branch in
    _apply_throw_result that emits the STUFFED event)."""
    real_resolve = match_module.resolve_throw
    match_module.resolve_throw = lambda *a, **kw: ("STUFFED", -2.0)
    collected: list = []
    try:
        collected.extend(m._resolve_commit_throw(t, s, throw_id, tick=commit_tick))
        collected.extend(m._advance_throws_in_progress(tick=commit_tick + 1))
        collected.extend(m._advance_throws_in_progress(tick=commit_tick + 2))
        m._resolve_consequences(tick=commit_tick + 3, events=collected)
        m._resolve_consequences(tick=commit_tick + 4, events=collected)
    finally:
        match_module.resolve_throw = real_resolve
    return collected


# ===========================================================================
# AC#1 — failed throws trigger fresh initiative on tick + 1
# ===========================================================================
def test_failed_throw_emits_grip_init_recompute_on_next_tick() -> None:
    t, s, m = _elite_match(seed=0)
    events = _drive_failed_throw(m, t, s, ThrowID.UCHI_MATA, commit_tick=10)
    failed_events = [e for e in events if e.event_type == "FAILED"]
    assert failed_events, "expected a FAILED event in the chain"
    failed_tick = failed_events[0].tick
    init_events = [
        e for e in events
        if e.event_type == "GRIP_INITIATIVE"
        and e.data.get("from_recompute") is True
    ]
    assert init_events, (
        "expected a GRIP_INIT_RECOMPUTE event after the FAILED resolution"
    )
    assert init_events[0].tick == failed_tick + 1, (
        f"recompute on tick {init_events[0].tick} but FAILED on "
        f"{failed_tick} — must fire on FAILED+1 per HAJ-148 N+1 contract"
    )
    assert init_events[0].data.get("from_consequence_queue") is True


# ===========================================================================
# AC#2 — stuffed throws trigger fresh initiative on tick + 1
# ===========================================================================
def test_stuffed_throw_emits_grip_init_recompute_on_next_tick() -> None:
    t, s, m = _elite_match(seed=1)
    events = _drive_stuffed_throw(m, t, s, ThrowID.SEOI_NAGE, commit_tick=10)
    stuffed_events = [e for e in events if e.event_type == "STUFFED"]
    assert stuffed_events, "expected a STUFFED event in the chain"
    stuffed_tick = stuffed_events[0].tick
    init_events = [
        e for e in events
        if e.event_type == "GRIP_INITIATIVE"
        and e.data.get("from_recompute") is True
    ]
    assert init_events, (
        "expected a GRIP_INIT_RECOMPUTE event after the STUFFED resolution"
    )
    assert init_events[0].tick == stuffed_tick + 1


# ===========================================================================
# AC#3 — composure dip from repeated failures lowers the recompute score
# ===========================================================================
def test_composure_dip_reduces_recompute_initiative() -> None:
    """Drive three forced failures on the same fighter; the recompute
    after the third failure shows a measurably lower initiative score
    for the failing fighter than a fresh-state baseline. This verifies
    the existing HAJ-151 composure weight has a chance to express
    (since recompute reads current composure)."""
    # Baseline: fresh fighters, single forced failure.
    t1, s1, m1 = _elite_match(seed=10)
    events1 = _drive_failed_throw(m1, t1, s1, ThrowID.UCHI_MATA, commit_tick=10)
    base_inits = [
        e for e in events1
        if e.event_type == "GRIP_INITIATIVE"
        and e.data.get("from_recompute") is True
    ]
    assert base_inits
    # Look up tori's score in the baseline event.
    base = base_inits[0].data
    if base["leader"] == t1.identity.name:
        base_score = base["leader_init"]
    else:
        base_score = base["follower_init"]

    # Comparison: same fighters, but tori has eaten three failures'
    # worth of composure first. The recompute reads current state, so
    # the score should drop measurably.
    t2, s2, m2 = _elite_match(seed=10)
    # Cumulative drop from three failures: each FAILED applies the
    # failure_resolution composure delta on tori. Approximate by
    # zeroing composure directly (tests the recompute, not the bleed).
    t2.state.composure_current = 0.5
    events2 = _drive_failed_throw(m2, t2, s2, ThrowID.UCHI_MATA, commit_tick=10)
    drop_inits = [
        e for e in events2
        if e.event_type == "GRIP_INITIATIVE"
        and e.data.get("from_recompute") is True
    ]
    assert drop_inits
    drop = drop_inits[0].data
    if drop["leader"] == t2.identity.name:
        drop_score = drop["leader_init"]
    else:
        drop_score = drop["follower_init"]
    assert drop_score < base_score, (
        f"composure-degraded tori scored {drop_score:.3f} vs fresh "
        f"baseline {base_score:.3f} — recompute should reflect dip"
    )


# ===========================================================================
# AC#4 — multi-failure match has multiple [grip_init] events
# ===========================================================================
def test_multiple_failures_yield_multiple_grip_init_events() -> None:
    """Drive five sequential forced failures; verify a recompute event
    fires after each one (5 recomputes from failures; the opening
    [grip_init] at hajime is independent)."""
    t, s, m = _elite_match(seed=42)
    all_events: list = []
    real_resolve = match_module.resolve_throw
    match_module.resolve_throw = lambda *a, **kw: ("FAILED", -5.0)
    try:
        commit_tick = 10
        for i in range(5):
            # Use distinct throws so commit_motivation/state doesn't
            # accumulate across the loop in a way that confuses the
            # routing.
            tid = ThrowID.UCHI_MATA if i % 2 == 0 else ThrowID.O_UCHI_GARI
            all_events.extend(
                m._resolve_commit_throw(t, s, tid, tick=commit_tick)
            )
            all_events.extend(m._advance_throws_in_progress(tick=commit_tick + 1))
            all_events.extend(m._advance_throws_in_progress(tick=commit_tick + 2))
            m._resolve_consequences(tick=commit_tick + 3, events=all_events)
            m._resolve_consequences(tick=commit_tick + 4, events=all_events)
            # Ensure the fighter is unstuck for the next commit (clear
            # stun, compromised tag, in-progress entry).
            t.state.stun_ticks = 0
            m._compromised_states.pop(t.identity.name, None)
            m._throws_in_progress.pop(t.identity.name, None)
            commit_tick += 6
    finally:
        match_module.resolve_throw = real_resolve
    recomputes = [
        e for e in all_events
        if e.event_type == "GRIP_INITIATIVE"
        and e.data.get("from_recompute") is True
    ]
    assert len(recomputes) == 5, (
        f"expected 5 recompute events (one per failure); got "
        f"{len(recomputes)}"
    )


# ===========================================================================
# AC#5 — HAJ-144-style reproduction: failure followed by recompute
# ===========================================================================
def test_haj144_reproduction_recompute_after_each_failure() -> None:
    """For a forced sequence of failures, every failure event in the
    log is followed by a GRIP_INIT_RECOMPUTE event on the very next
    tick. Mirrors the V6 audit reproduction (27-tick / 9-failure run
    that produced exactly one [grip_init] pre-fix)."""
    t, s, m = _elite_match(seed=144)
    all_events: list = []
    real_resolve = match_module.resolve_throw
    match_module.resolve_throw = lambda *a, **kw: ("FAILED", -5.0)
    try:
        commit_tick = 5
        for _ in range(4):
            all_events.extend(
                m._resolve_commit_throw(
                    t, s, ThrowID.UCHI_MATA, tick=commit_tick,
                )
            )
            all_events.extend(m._advance_throws_in_progress(tick=commit_tick + 1))
            all_events.extend(m._advance_throws_in_progress(tick=commit_tick + 2))
            m._resolve_consequences(tick=commit_tick + 3, events=all_events)
            m._resolve_consequences(tick=commit_tick + 4, events=all_events)
            t.state.stun_ticks = 0
            m._compromised_states.pop(t.identity.name, None)
            m._throws_in_progress.pop(t.identity.name, None)
            commit_tick += 6
    finally:
        match_module.resolve_throw = real_resolve
    failure_ticks = [e.tick for e in all_events if e.event_type == "FAILED"]
    recompute_ticks = {
        e.tick for e in all_events
        if e.event_type == "GRIP_INITIATIVE"
        and e.data.get("from_recompute") is True
    }
    assert failure_ticks, "test must produce at least one failure"
    for ftick in failure_ticks:
        assert ftick + 1 in recompute_ticks, (
            f"failure on tick {ftick} not followed by recompute on {ftick + 1}"
        )


# ===========================================================================
# AC#6 — opening [grip_init] at hajime continues to fire
# ===========================================================================
def test_initiative_at_hajime_unchanged() -> None:
    """The opening cascade at the start of the match still emits a
    GRIP_INITIATIVE event without the from_recompute flag — so existing
    HAJ-151 acceptance criteria continue to hold."""
    random.seed(0)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=20, seed=0,
    )
    captured: list = []
    m._print_events = lambda evs: captured.extend(evs)
    m.begin()
    while m.position == Position.STANDING_DISTANT and m.ticks_run < 20:
        m.step()
    while m._grip_cascade is not None and m.ticks_run < 25:
        m.step()
    inits = [e for e in captured if e.event_type == "GRIP_INITIATIVE"]
    assert inits, "no opening [grip_init] event"
    # The opening event must NOT carry the recompute flag — that's
    # reserved for the HAJ-158 path.
    assert inits[0].data.get("from_recompute") is not True


# ===========================================================================
# AC#7 — edge_count==0 path still triggers initiative (matte / disengage)
# ===========================================================================
def test_disengage_path_still_triggers_fresh_initiative() -> None:
    """Force a DISENGAGE response after the opening cascade; verify
    the dyad re-engages and a *second* opening-style cascade fires
    (not a recompute) when grips break and the engagement floor
    elapses again. This covers the HAJ-151 path that HAJ-158 must
    NOT regress."""
    random.seed(0)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=60, seed=0,
    )
    captured: list = []
    m._print_events = lambda evs: captured.extend(evs)
    forced = GripResponseChoice(
        kind=RESP_DISENGAGE,
        weights={k: 1.0 for k in ALL_RESPONSE_KINDS},
        rolled=0.0,
    )
    real_select = match_module.select_response
    match_module.select_response = lambda *a, **kw: forced
    try:
        m.begin()
        # Run long enough for the disengage + closing-phase floor to
        # elapse and a second cascade to stage.
        while m.ticks_run < 40:
            m.step()
    finally:
        match_module.select_response = real_select
    inits = [
        e for e in captured
        if e.event_type == "GRIP_INITIATIVE"
        and e.data.get("from_recompute") is not True
    ]
    assert len(inits) >= 2, (
        f"expected ≥2 opening-style [grip_init] events from disengage / "
        f"re-engage cycle; got {len(inits)}"
    )


# ===========================================================================
# Familiarity bookkeeping — survivor counter increments on recompute
# ===========================================================================
def test_recompute_increments_survivor_familiarity() -> None:
    """Per HAJ-158 open question 2 (lean: yes), the recompute bumps
    the survivor's familiarity counter — uke scouted tori's preference
    by surviving the attack."""
    t, s, m = _elite_match(seed=21)
    pre = m._grip_familiarity.get(s.identity.name, 0)
    _drive_failed_throw(m, t, s, ThrowID.UCHI_MATA, commit_tick=10)
    post = m._grip_familiarity.get(s.identity.name, 0)
    assert post == pre + 1, (
        f"survivor familiarity should bump by 1 on recompute; "
        f"pre={pre} post={post}"
    )


# ===========================================================================
# Recompute is enqueued via the consequence queue (HAJ-148 contract)
# ===========================================================================
def test_recompute_consequence_enqueued_on_failed_branch() -> None:
    """The fix path schedules a GRIP_INIT_RECOMPUTE _Consequence at
    the end of _apply_throw_result's FAILED branch — verify directly."""
    t, s, m = _elite_match(seed=3)
    real_resolve = match_module.resolve_throw
    match_module.resolve_throw = lambda *a, **kw: ("FAILED", -5.0)
    try:
        m._resolve_commit_throw(t, s, ThrowID.UCHI_MATA, tick=10)
        m._advance_throws_in_progress(tick=11)
        m._advance_throws_in_progress(tick=12)
        scratch: list = []
        m._resolve_consequences(tick=13, events=scratch)
    finally:
        match_module.resolve_throw = real_resolve
    pending = [
        c for c in m._consequence_queue
        if c.kind == "GRIP_INIT_RECOMPUTE"
    ]
    assert pending, "expected a queued GRIP_INIT_RECOMPUTE after FAILED"
    assert pending[0].due_tick == 14
    assert pending[0].payload["survivor_name"] == s.identity.name
    assert pending[0].payload["failed_attacker_name"] == t.identity.name


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
