# tests/test_haj166_head_steer_prose.py
# HAJ-166 — outcome-bound prose for collar-grip head-as-output BPEs.
#
# HAJ-146 substrate emits a HEAD_AS_OUTPUT BodyPartEvent on the victim
# whenever an opposing grip with current_intent="STEER" is on them.
# HAJ-161 tightened the substrate so only is_collar() grips drive head
# state — lapel grips no longer steer the head, mechanically. This
# ticket adds the prose template that consumes those BPEs:
#
#   AC#1 — Effective back-collar steer cites the back-collar grip and
#          downward head movement.
#   AC#2 — Effective side-collar steer cites the side-collar grip and
#          rotational head movement.
#   AC#3 — Blocked steer (grip strength below threshold) substitutes
#          a "stays planted" line.
#   AC#4 — Lapel grips with STEER intent never trigger the template
#          (HAJ-161's substrate filter is respected; no HEAD_AS_OUTPUT
#          BPE fires for lapel-only steering).
#   AC#5 — Test coverage for back-collar, side-collar, blocked, lapel
#          (this file).
#   AC#6 — Debug stream preserved: the HEAD_AS_OUTPUT BPE substrate is
#          unchanged; modifiers / steer_direction still emit at full
#          fidelity.

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from body_part_decompose import compute_head_state
from body_part_events import BodyPartHigh
from enums import (
    BodyPart, GripDepth, GripMode, GripTarget, GripTypeV2, Position,
)
from grip_graph import GripEdge
from match import Match
from narration.altitudes.mat_side import MatSideNarrator, _head_steer_prose
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
    return t, s, m


def _seat_collar_steer(
    graph, grasper, victim, *,
    grip_type_v2: GripTypeV2,
    target_location: GripTarget,
    strength: float = 0.9,
) -> GripEdge:
    """Hand-seat a collar grip with STEER intent on the victim. Returns
    the edge so tests can mutate it (strength, intent) directly."""
    edge = GripEdge(
        grasper_id=grasper.identity.name,
        grasper_part=BodyPart.RIGHT_HAND,
        target_id=victim.identity.name,
        target_location=target_location,
        grip_type_v2=grip_type_v2,
        depth_level=GripDepth.STANDARD,
        strength=strength,
        established_tick=0,
        mode=GripMode.DRIVING,
    )
    edge.current_intent = "STEER"
    edge.steer_direction = frozenset({"DOWN"})
    graph.add_edge(edge)
    return edge


def _consume(narrator, m, tick: int):
    """Compute head BPEs against the live grip graph and feed them to
    the narrator. Returns (entries, bpes)."""
    bpes = compute_head_state(
        m.fighter_a, m.grip_graph, tick,
        grasper_resolver=m._fighter_by_name,
    )
    bpes.extend(compute_head_state(
        m.fighter_b, m.grip_graph, tick,
        grasper_resolver=m._fighter_by_name,
    ))
    # Prime the narrator's phase so the (closing → grip_war) line
    # doesn't co-fire and steal the slot.
    narrator._last_phase = "grip_war"
    m.position = Position.GRIPPING
    entries = narrator.consume_tick(tick, [], bpes, m)
    return entries, bpes


# ===========================================================================
# AC#1 — effective back-collar steer
# ===========================================================================
def test_effective_back_collar_renders_downward_head_movement() -> None:
    t, s, m = _new_match()
    _seat_collar_steer(
        m.grip_graph, t, s,
        grip_type_v2=GripTypeV2.COLLAR_BACK,
        target_location=GripTarget.BACK_COLLAR,
        strength=0.9,
    )
    narrator = MatSideNarrator()
    entries, bpes = _consume(narrator, m, tick=10)
    head_steer = [e for e in entries if e.source == "head_steer"]
    assert head_steer, "expected a head_steer entry from the back-collar grip"
    line = head_steer[0].prose
    assert t.identity.name in line and s.identity.name in line
    assert "back collar" in line.lower()
    assert "down" in line.lower()
    # Substrate preserved — HEAD_AS_OUTPUT BPE still fires (AC#6).
    assert any(b.source == "HEAD_AS_OUTPUT" and b.actor == s.identity.name
               for b in bpes)


# ===========================================================================
# AC#2 — effective side-collar steer
# ===========================================================================
def test_effective_side_collar_renders_rotational_head_movement() -> None:
    t, s, m = _new_match()
    _seat_collar_steer(
        m.grip_graph, t, s,
        grip_type_v2=GripTypeV2.COLLAR_SIDE,
        target_location=GripTarget.SIDE_COLLAR,
        strength=0.9,
    )
    narrator = MatSideNarrator()
    entries, _ = _consume(narrator, m, tick=10)
    head_steer = [e for e in entries if e.source == "head_steer"]
    assert head_steer
    line = head_steer[0].prose
    assert "side collar" in line.lower()
    # Rotational cue — "turn"/"chin" word appears.
    assert "chin" in line.lower() or "turn" in line.lower()


# ===========================================================================
# AC#3 — blocked steer
# ===========================================================================
def test_blocked_steer_renders_stays_planted_substitute() -> None:
    """A collar grip with STEER intent but low strength (force absorbed,
    posture stiff) renders the substitute line."""
    t, s, m = _new_match()
    _seat_collar_steer(
        m.grip_graph, t, s,
        grip_type_v2=GripTypeV2.COLLAR_BACK,
        target_location=GripTarget.BACK_COLLAR,
        strength=0.3,  # below the 0.5 threshold
    )
    narrator = MatSideNarrator()
    entries, _ = _consume(narrator, m, tick=10)
    head_steer = [e for e in entries if e.source == "head_steer"]
    assert head_steer
    line = head_steer[0].prose
    assert "stays planted" in line.lower() or "planted" in line.lower()
    # Does NOT promise a successful steer.
    assert "pulls" not in line.lower()


# ===========================================================================
# AC#4 — lapel grips never trigger the head-steer template
# ===========================================================================
def test_lapel_steer_does_not_trigger_head_steer_prose() -> None:
    """A LAPEL_HIGH grip with STEER intent doesn't emit a HEAD_AS_OUTPUT
    BPE (HAJ-161 is_collar() filter) — so the prose template never
    fires. This pins the substrate-level guarantee at the prose layer."""
    t, s, m = _new_match()
    edge = GripEdge(
        grasper_id=t.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=s.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.STANDARD,
        strength=0.9, established_tick=0, mode=GripMode.DRIVING,
    )
    edge.current_intent = "STEER"
    edge.steer_direction = frozenset({"FORWARD"})
    m.grip_graph.add_edge(edge)
    narrator = MatSideNarrator()
    entries, bpes = _consume(narrator, m, tick=10)
    # No HEAD_AS_OUTPUT BPE at all (substrate filtered).
    head_bpes = [b for b in bpes if b.source == "HEAD_AS_OUTPUT"]
    assert head_bpes == []
    # And no head_steer prose entries.
    head_steer = [e for e in entries if e.source == "head_steer"]
    assert head_steer == []


# ===========================================================================
# Additional coverage — resolver returns None when no collar steer
# ===========================================================================
def test_head_steer_prose_returns_none_with_no_collar_steer() -> None:
    """The resolver itself returns None when no collar grip with STEER
    intent is on the victim, even if other (lapel / sleeve) edges exist.
    Defensive — a HEAD_AS_OUTPUT BPE shouldn't appear without a collar
    steerer, but the resolver guards in case of out-of-band callers."""
    t, s, m = _new_match()
    # Lapel STEER edge — does not satisfy is_collar(), prose returns None.
    edge = GripEdge(
        grasper_id=t.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=s.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.STANDARD,
        strength=0.9, established_tick=0, mode=GripMode.DRIVING,
    )
    edge.current_intent = "STEER"
    m.grip_graph.add_edge(edge)
    assert _head_steer_prose(m, s.identity.name) is None


# ===========================================================================
# Rate limit — the head-steer line doesn't spam every tick
# ===========================================================================
def test_head_steer_line_is_rate_limited_per_actor() -> None:
    """Two consecutive ticks of head-steer BPEs produce one prose line,
    not two — the rate limiter (6 ticks per actor + source) collapses
    the second."""
    t, s, m = _new_match()
    _seat_collar_steer(
        m.grip_graph, t, s,
        grip_type_v2=GripTypeV2.COLLAR_BACK,
        target_location=GripTarget.BACK_COLLAR,
        strength=0.9,
    )
    narrator = MatSideNarrator()
    entries_t1, _ = _consume(narrator, m, tick=10)
    entries_t2, _ = _consume(narrator, m, tick=11)
    head_t1 = [e for e in entries_t1 if e.source == "head_steer"]
    head_t2 = [e for e in entries_t2 if e.source == "head_steer"]
    assert len(head_t1) == 1
    assert len(head_t2) == 0


# ===========================================================================
# AC#6 — substrate fidelity preserved
# ===========================================================================
def test_substrate_modifiers_and_steer_direction_preserved() -> None:
    """The HEAD_AS_OUTPUT BPE still carries modifiers and steer_direction
    even after the prose layer consumes it. AC#6 — debug stream lossless."""
    t, s, m = _new_match()
    _seat_collar_steer(
        m.grip_graph, t, s,
        grip_type_v2=GripTypeV2.COLLAR_BACK,
        target_location=GripTarget.BACK_COLLAR,
        strength=0.9,
    )
    narrator = MatSideNarrator()
    _, bpes = _consume(narrator, m, tick=10)
    head_bpes = [b for b in bpes if b.source == "HEAD_AS_OUTPUT"]
    assert head_bpes
    h = head_bpes[0]
    assert h.part is BodyPartHigh.HEAD
    assert h.steer_direction is not None
    # Modifiers bundle is populated (some axis non-None) — confirms
    # the substrate's grasper_resolver path still runs.
    assert h.modifiers is not None


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
