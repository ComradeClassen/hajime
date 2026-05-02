# tests/test_haj165_movement_prose.py
# HAJ-165 — movement prose: fill engagement-phase silence with circling /
# posture / pull-without-commit beats.
#
# Three connective-beat families consume the locomotion + posture +
# grip-without-commit substrates and render outcome-bound lines using the
# same dynamic-resolver pattern HAJ-162 established (read engine state at
# emission time, render only what's actually true).
#
# AC coverage in this file:
#   AC#1 — Circling beats fire during gripped engagement-phase locomotion
#          without a throw commit, citing the actual tactical_intent.
#   AC#2 — Posture beats fire on Posture state changes that don't go
#          through KUZUSHI_INDUCED, naming the change.
#   AC#3 — Pull-without-commit beats fire when REACH / PULL BPEs fire
#          without the actor being mid-commit, citing the grip referent
#          and uke's response.
#   AC#4 — Sample-rate matches HAJ-147 promotion rule 4: posture changes
#          always promote; circling / pull beats are rate-limited to one
#          per actor per ~6-tick window. State-change ticks (THROW_ENTRY,
#          KUZUSHI_INDUCED, MATTE, etc.) suppress the beats so the
#          existing slot owner isn't double-authored.
#   AC#5 — Compromised-state, ne-waza, ref-call, and grip-seating prose
#          unchanged (other altitude/category prose is independent of
#          the new families; ne-waza phase suppresses circling).
#   AC#6 — Test coverage for each beat type plus engagement-phase fill.
#   AC#7 — Debug stream preserved: MOVE / PULL / REACH events / BPEs
#          remain available at full fidelity.

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_part_decompose import decompose_pull, decompose_reach
from body_part_events import BodyPartEvent, BodyPartHigh, BodyPartVerb
from body_state import (
    SLIGHTLY_BENT_LIMIT_RAD, UPRIGHT_LIMIT_RAD, place_judoka,
)
from enums import (
    BodyPart, GripDepth, GripMode, GripTarget, GripTypeV2, Position,
    Posture, SubLoopState,
)
from grip_graph import Event, GripEdge
from match import Match
from narration.altitudes.mat_side import (
    MatSideNarrator, _circling_prose, _posture_change_prose,
    _pull_without_commit_prose,
)
from referee import build_suzuki
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


def _new_match(seed: int = 1):
    random.seed(seed)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=40, seed=seed, stream="prose",
    )
    m._print_header = lambda: None
    m.position = Position.GRIPPING
    return t, s, m


def _move_event(tick, fighter_name, intent, dx=0.0, dy=0.5, mag=0.2):
    return Event(
        tick=tick, event_type="MOVE",
        description=f"[move] {fighter_name} → {intent}",
        data={
            "fighter": fighter_name,
            "tactical_intent": intent,
            "direction": (dx, dy),
            "magnitude": mag,
            "base_magnitude": mag,
            "com_before": (0.0, 0.0),
            "com_after": (dx * mag, dy * mag),
            "prose_silent": True,
        },
    )


def _seat_lapel_edge(graph, grasper, victim) -> GripEdge:
    edge = GripEdge(
        grasper_id=grasper.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=victim.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.STANDARD,
        strength=1.0, established_tick=0, mode=GripMode.DRIVING,
    )
    graph.add_edge(edge)
    return edge


def _prime_baseline(narrator, m, tick: int = 0):
    """Establish baseline posture / phase so the first prose tick
    doesn't trip the 'baseline' guard."""
    narrator._last_phase = "grip_war"
    narrator.consume_tick(tick, [], [], m)


# ===========================================================================
# AC#1 — circling beats fire from MOVE events with a tactical_intent
# ===========================================================================
def test_circle_closing_beat_renders_during_grip_war() -> None:
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    move = _move_event(10, t.identity.name, "circle_closing")
    entries = narrator.consume_tick(10, [move], [], m)
    circling = [e for e in entries if e.source == "circling"]
    assert circling, "expected a circling beat from circle_closing MOVE"
    line = circling[0].prose.lower()
    assert "circle" in line or "angle" in line
    assert t.identity.name in circling[0].prose
    assert s.identity.name in circling[0].prose


def test_lateral_approach_beat_cites_lateral_movement() -> None:
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    move = _move_event(10, t.identity.name, "lateral_approach")
    entries = narrator.consume_tick(10, [move], [], m)
    circling = [e for e in entries if e.source == "circling"]
    assert circling
    line = circling[0].prose.lower()
    assert "wide" in line or "space" in line or "lateral" in line


def test_bait_retreat_beat_cites_retreat() -> None:
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    move = _move_event(10, t.identity.name, "bait_retreat")
    entries = narrator.consume_tick(10, [move], [], m)
    circling = [e for e in entries if e.source == "circling"]
    assert circling
    line = circling[0].prose.lower()
    assert "back" in line or "bait" in line


def test_unknown_tactical_intent_does_not_fire() -> None:
    """Unmapped intents return None from the resolver, so the detector
    skips them. Forward compatibility — adding a new intent doesn't
    immediately produce prose; it requires an explicit template."""
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    move = _move_event(10, t.identity.name, "uncharted_intent_xyz")
    entries = narrator.consume_tick(10, [move], [], m)
    assert not [e for e in entries if e.source == "circling"]


# ===========================================================================
# AC#2 — posture beats fire on Posture state change
# ===========================================================================
def test_posture_beat_fires_on_upright_to_slightly_bent() -> None:
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    # Mutate sato's trunk so derive_posture flips UPRIGHT → SLIGHTLY_BENT.
    s.state.body_state.trunk_sagittal = (
        UPRIGHT_LIMIT_RAD + (SLIGHTLY_BENT_LIMIT_RAD - UPRIGHT_LIMIT_RAD) / 2
    )
    entries = narrator.consume_tick(10, [], [], m)
    posture = [e for e in entries if e.source == "posture"]
    assert posture, "expected posture beat on UPRIGHT → SLIGHTLY_BENT"
    assert s.identity.name in posture[0].prose


def test_posture_beat_fires_on_slightly_bent_to_upright() -> None:
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    # Start fighter at SLIGHTLY_BENT, baseline.
    s.state.body_state.trunk_sagittal = (
        UPRIGHT_LIMIT_RAD + (SLIGHTLY_BENT_LIMIT_RAD - UPRIGHT_LIMIT_RAD) / 2
    )
    _prime_baseline(narrator, m)
    # Now straighten up.
    s.state.body_state.trunk_sagittal = 0.0
    entries = narrator.consume_tick(10, [], [], m)
    posture = [e for e in entries if e.source == "posture"]
    assert posture
    assert "straighten" in posture[0].prose.lower()


def test_posture_beat_does_not_fire_on_kuzushi_induced_tick() -> None:
    """Transitions INTO BROKEN are owned by the KUZUSHI_INDUCED prose
    line; the posture beat must NOT double-author that slot."""
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    # Push sato into BROKEN posture and fire a KUZUSHI_INDUCED event.
    s.state.body_state.trunk_sagittal = SLIGHTLY_BENT_LIMIT_RAD + 0.1
    kuzushi_ev = Event(
        tick=10, event_type="KUZUSHI_INDUCED",
        description="[kuzushi]", data={},
    )
    entries = narrator.consume_tick(10, [kuzushi_ev], [], m)
    posture = [e for e in entries if e.source == "posture"]
    assert posture == []


def test_posture_beat_does_not_fire_for_broken_entry_without_kuzushi() -> None:
    """Defensive — even if KUZUSHI_INDUCED isn't in the events (test-
    only configuration), an entry into BROKEN doesn't get a posture
    beat. The kuzushi event substrate owns that line."""
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    s.state.body_state.trunk_sagittal = SLIGHTLY_BENT_LIMIT_RAD + 0.1
    entries = narrator.consume_tick(10, [], [], m)
    posture = [e for e in entries if e.source == "posture"]
    assert posture == []


# ===========================================================================
# AC#3 — pull-without-commit beats fire when no commit is in flight
# ===========================================================================
def test_pull_without_commit_beat_fires_after_deferred_window() -> None:
    """HAJ-167 — pull-without-commit is now a deferred / windowed rule.
    Pre-decouple the line fired on the PULL tick itself; post-decouple
    it fires K ticks later only if no commit followed in between, so
    the prose is honest about the actual gap rather than narrating
    the future blind."""
    t, s, m = _new_match()
    edge = _seat_lapel_edge(m.grip_graph, t, s)
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    bpes = decompose_pull(t, edge, direction=(1.0, 0.0), magnitude=0.3, tick=10)
    # PULL tick — rule does not yet fire (waiting for the gap window).
    entries_pull = narrator.consume_tick(10, [], bpes, m)
    assert not [e for e in entries_pull if e.source == "pull_no_commit"]
    # Walk the K-tick gap with no commit. By tick 13 (PULL tick + K=3)
    # the deferred rule fires from the last consume_tick call.
    entries_t11 = narrator.consume_tick(11, [], [], m)
    entries_t12 = narrator.consume_tick(12, [], [], m)
    entries_t13 = narrator.consume_tick(13, [], [], m)
    assert not [e for e in entries_t11 if e.source == "pull_no_commit"]
    assert not [e for e in entries_t12 if e.source == "pull_no_commit"]
    pull = [e for e in entries_t13 if e.source == "pull_no_commit"]
    assert pull, (
        "expected pull_no_commit prose to land at PULL tick + K"
    )
    line = pull[0].prose
    assert t.identity.name in line and s.identity.name in line


def test_pull_without_commit_suppressed_when_commit_follows() -> None:
    """HAJ-167 gap surfacing — when a THROW_ENTRY for the same actor
    lands in the K-tick window after a PULL, the rule sees the commit
    and stays silent. Pre-decouple the line fired blindly on the PULL
    tick and could mis-narrate this case."""
    t, s, m = _new_match()
    edge = _seat_lapel_edge(m.grip_graph, t, s)
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    pull_bpes = decompose_pull(
        t, edge, direction=(1.0, 0.0), magnitude=0.3, tick=10,
    )
    narrator.consume_tick(10, [], pull_bpes, m)
    # Tick 11 — a commit for tori lands. The COMMIT-source BPE in the
    # followup window suppresses the deferred rule.
    from body_part_decompose import decompose_commit
    from worked_throws import worked_template_for as _t
    from throws import ThrowID
    template = _t(ThrowID.UCHI_MATA)
    if template is None:
        # Defensive — the test relies on a worked-throw template
        # being present; if the registry shifts, just exercise the
        # event-type path with a stub COMMIT BPE.
        from body_part_events import (
            BodyPartEvent, BodyPartHigh, BodyPartVerb, Side,
        )
        commit_bpes = [BodyPartEvent(
            tick=11, actor=t.identity.name,
            part=BodyPartHigh.HANDS, side=Side.RIGHT,
            verb=BodyPartVerb.PULL, source="COMMIT",
        )]
    else:
        commit_bpes = decompose_commit(t, s, template, tick=11)
    narrator.consume_tick(11, [], commit_bpes, m)
    # Walk through the rest of the K-tick window — rule should NOT
    # fire because the commit is in the followup.
    fired: list = []
    for n in range(12, 16):
        fired.extend(narrator.consume_tick(n, [], [], m))
    pull_lines = [e for e in fired if e.source == "pull_no_commit"]
    assert pull_lines == []


def test_reach_bpe_does_not_fire_pull_without_commit_beat() -> None:
    """HAJ-165 follow-up — REACH BPEs are 'extending the hand toward
    a target' and fire before any grip exists. The 'hauls on the
    lapel' prose template assumes a live edge; emitting it for REACH
    produces false copy (the ticket-2026-05-02 t001 reading: 'Renard
    hauls on the lapel' before either fighter has contact). REACH
    must not drive this template — only PULL (live edge required)."""
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    bpes = decompose_reach(t, "right_hand", "left_lapel", tick=10)
    entries = narrator.consume_tick(10, [], bpes, m)
    pull = [e for e in entries if e.source == "pull_no_commit"]
    assert pull == [], (
        "REACH BPEs must not produce pull_no_commit prose"
    )


def test_pull_beat_suppressed_when_actor_is_mid_commit() -> None:
    """A multi-tick attempt (entry in _throws_in_progress) means the
    actor IS committing; the pull beat would mis-narrate that as 'no
    commit.'"""
    t, s, m = _new_match()
    edge = _seat_lapel_edge(m.grip_graph, t, s)
    # Fake an in-progress entry for tori.
    m._throws_in_progress[t.identity.name] = "placeholder"
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    bpes = decompose_pull(t, edge, direction=(1.0, 0.0), magnitude=0.3, tick=10)
    entries = narrator.consume_tick(10, [], bpes, m)
    assert not [e for e in entries if e.source == "pull_no_commit"]


# ===========================================================================
# AC#4 — sampling rate / suppression
# ===========================================================================
def test_circling_beat_is_rate_limited_per_actor() -> None:
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    # Two consecutive circle ticks for the same actor — only the first
    # should produce a beat.
    e1 = narrator.consume_tick(10, [_move_event(10, t.identity.name, "circle")], [], m)
    e2 = narrator.consume_tick(11, [_move_event(11, t.identity.name, "circle")], [], m)
    assert len([e for e in e1 if e.source == "circling"]) == 1
    assert len([e for e in e2 if e.source == "circling"]) == 0


def test_movement_prose_suppressed_on_throw_entry_tick() -> None:
    """A THROW_ENTRY event on the same tick should silence circling /
    pull beats — the commit-tick prose owns the slot per HAJ-148 / 154."""
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    move = _move_event(10, t.identity.name, "circle")
    throw_entry = Event(
        tick=10, event_type="THROW_ENTRY",
        description="[throw] entry",
        data={"prose_silent": True},
    )
    entries = narrator.consume_tick(10, [move, throw_entry], [], m)
    assert not [e for e in entries if e.source in ("circling", "pull_no_commit")]


def test_movement_prose_suppressed_on_matte_tick() -> None:
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    move = _move_event(10, t.identity.name, "circle")
    matte = Event(
        tick=10, event_type="MATTE", description="[ref] matte!", data={},
    )
    entries = narrator.consume_tick(10, [move, matte], [], m)
    assert not [e for e in entries if e.source == "circling"]


def test_circling_suppressed_in_ne_waza() -> None:
    """During NE_WAZA the circling family is silent — different
    locomotion substrate."""
    t, s, m = _new_match()
    m.sub_loop_state = SubLoopState.NE_WAZA
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    move = _move_event(10, t.identity.name, "circle")
    entries = narrator.consume_tick(10, [move], [], m)
    assert not [e for e in entries if e.source == "circling"]


# ===========================================================================
# AC#6 — engagement-phase silence gap is filled
# ===========================================================================
def test_engagement_phase_silence_gap_is_filled_with_movement_prose() -> None:
    """Drive ten consecutive grip-war ticks with no throw events — only
    locomotion + a posture nudge. The narrator should emit at least
    three connective beats across that span (rate-limit caps circling
    at one per ~6-tick window, but other beats still fire)."""
    t, s, m = _new_match()
    edge = _seat_lapel_edge(m.grip_graph, t, s)
    narrator = MatSideNarrator()
    _prime_baseline(narrator, m)
    all_entries: list = []
    for n in range(1, 11):
        events = []
        bpes: list = []
        # Alternate which fighter circles each tick.
        if n % 3 == 1:
            actor = t if n % 2 else s
            events.append(_move_event(n, actor.identity.name, "circle_closing"))
        if n == 4:
            # Posture nudge halfway through.
            s.state.body_state.trunk_sagittal = (
                UPRIGHT_LIMIT_RAD
                + (SLIGHTLY_BENT_LIMIT_RAD - UPRIGHT_LIMIT_RAD) / 2
            )
        if n == 7:
            bpes = decompose_pull(
                t, edge, direction=(1.0, 0.0), magnitude=0.3, tick=n,
            )
        all_entries.extend(narrator.consume_tick(n, events, bpes, m))
    movement_sources = {"circling", "posture", "pull_no_commit"}
    movement_lines = [e for e in all_entries if e.source in movement_sources]
    assert len(movement_lines) >= 3, (
        f"engagement-phase silence not filled: only "
        f"{len(movement_lines)} movement lines across 10 ticks; "
        f"sources={[e.source for e in movement_lines]}"
    )


# ===========================================================================
# AC#7 — substrate / debug stream preserved
# ===========================================================================
def test_pull_bpe_substrate_unchanged() -> None:
    t, s, m = _new_match()
    edge = _seat_lapel_edge(m.grip_graph, t, s)
    bpes = decompose_pull(t, edge, direction=(1.0, 0.0), magnitude=0.3, tick=10)
    # The pull BPE retains its full substrate fidelity (intent /
    # direction / modifiers).
    pull_bpes = [b for b in bpes if b.source == "PULL"]
    assert pull_bpes
    assert pull_bpes[0].direction is not None
    assert pull_bpes[0].modifiers is not None


# ===========================================================================
# Resolver-level coverage
# ===========================================================================
def test_circling_prose_returns_none_for_unmapped_intent() -> None:
    assert _circling_prose("not_a_real_intent", "A", "B") is None
    assert _circling_prose(None, "A", "B") is None


def test_posture_prose_returns_none_for_no_change() -> None:
    assert _posture_change_prose("A", Posture.UPRIGHT, Posture.UPRIGHT) is None


def test_posture_prose_handles_recovery_from_broken() -> None:
    line = _posture_change_prose("A", Posture.BROKEN, Posture.SLIGHTLY_BENT)
    assert line is not None
    assert "recover" in line.lower()


def test_pull_no_commit_prose_handles_unknown_target() -> None:
    """Defensive — a PULL whose target enum doesn't match the named
    cases falls back to a generic line."""
    line = _pull_without_commit_prose("A", "B", "WRIST")
    assert "A" in line and "B" in line


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
