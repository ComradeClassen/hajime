# tests/test_haj161_collar_grip.py
# HAJ-161 — collar grip as a full grip vocabulary entry.
#
# The bare `COLLAR` value was a stub. The real grip splits two ways:
#   - COLLAR_BACK  (oku-eri, nape grip)         — max head-steering authority.
#   - COLLAR_SIDE  (kata-eri, trapezius line)   — hybrid lapel / collar.
#
# Acceptance criteria from the ticket:
#   AC#1 — Grip type exists. COLLAR sub-types are legal GripTypeV2 values
#          and integrate with the GripGraph + force envelope.
#   AC#3 — Throw declarations updated. UCHI_MATA, HARAI_GOSHI,
#          HARAI_GOSHI_CLASSICAL, O_GURUMA accept either collar variant
#          alongside LAPEL_HIGH (the user direction extending beyond the
#          three throws originally listed in the ticket).
#   AC#4 — Head-as-output computation reads collar grips, not lapel.
#          A LAPEL_HIGH STEER no longer drives uke's HEAD body-part state.
#   AC#5 — No regressions for existing snap/drive throws.

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from enums import (
    BodyPart, GripDepth, GripMode, GripTarget, GripTypeV2,
)
from grip_graph import GripEdge
from force_envelope import FORCE_ENVELOPES
from body_part_decompose import compute_head_state
from body_part_events import BodyPartHigh
from match import Match
from referee import build_suzuki
from worked_throws import (
    UCHI_MATA, HARAI_GOSHI, HARAI_GOSHI_CLASSICAL, O_GURUMA,
)
import main as main_module
from body_state import place_judoka


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------
def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _new_match():
    import random
    random.seed(0)
    t, s = _pair()
    return t, s, Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(), max_ticks=5,
    )


# ===========================================================================
# AC#1 — vocabulary
# ===========================================================================
def test_collar_sub_types_are_legal_grip_types() -> None:
    """COLLAR_BACK and COLLAR_SIDE are first-class GripTypeV2 values."""
    assert GripTypeV2.COLLAR_BACK is not None
    assert GripTypeV2.COLLAR_SIDE is not None


def test_bare_collar_value_was_removed() -> None:
    """The pre-HAJ-161 `COLLAR` stub was removed in favor of the split.
    Any code that referenced `GripTypeV2.COLLAR` directly should have
    been migrated to the appropriate sub-type."""
    assert not hasattr(GripTypeV2, "COLLAR")


def test_is_collar_helper_classifies_both_sub_types() -> None:
    """The is_collar() helper mirrors is_sleeve() — both sub-types
    test True; nothing else does."""
    assert GripTypeV2.COLLAR_BACK.is_collar()
    assert GripTypeV2.COLLAR_SIDE.is_collar()
    for gt in GripTypeV2:
        if gt in (GripTypeV2.COLLAR_BACK, GripTypeV2.COLLAR_SIDE):
            continue
        assert not gt.is_collar(), (
            f"{gt} should not be classified as collar"
        )


def test_force_envelopes_define_both_collar_sub_types() -> None:
    """Both collar sub-types live in FORCE_ENVELOPES with distinct profiles."""
    assert GripTypeV2.COLLAR_BACK in FORCE_ENVELOPES
    assert GripTypeV2.COLLAR_SIDE in FORCE_ENVELOPES
    back = FORCE_ENVELOPES[GripTypeV2.COLLAR_BACK]
    side = FORCE_ENVELOPES[GripTypeV2.COLLAR_SIDE]
    # COLLAR_BACK has higher rotation authority (max head-steering grip).
    assert back.rotation_authority > side.rotation_authority


def test_collar_grip_can_be_added_to_graph() -> None:
    """A COLLAR_BACK edge round-trips through GripGraph cleanly."""
    t, s, m = _new_match()
    edge = GripEdge(
        grasper_id=t.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=s.identity.name, target_location=GripTarget.BACK_COLLAR,
        grip_type_v2=GripTypeV2.COLLAR_BACK, depth_level=GripDepth.STANDARD,
        strength=1.0, established_tick=0, mode=GripMode.DRIVING,
    )
    m.grip_graph.add_edge(edge)
    owned = m.grip_graph.edges_owned_by(t.identity.name)
    assert any(e.grip_type_v2 is GripTypeV2.COLLAR_BACK for e in owned)


# ===========================================================================
# AC#3 — throw declarations accept collar tsurite
# ===========================================================================
def test_uchi_mata_accepts_both_collar_variants_as_tsurite() -> None:
    """The user's direction: collar grip should be a valid uchi-mata
    tsurite alongside the classical LAPEL_HIGH. High-collar uchi-mata
    is a competitive variant where the over-the-shoulder grip drives
    the head-forward kuzushi."""
    tsurite = next(g for g in UCHI_MATA.force_grips if g.hand == "right_hand")
    assert GripTypeV2.LAPEL_HIGH in tsurite.grip_type
    assert GripTypeV2.COLLAR_BACK in tsurite.grip_type
    assert GripTypeV2.COLLAR_SIDE in tsurite.grip_type


def test_harai_goshi_accepts_both_collar_variants_as_tsurite() -> None:
    """Same deal for harai-goshi — high-collar harai is canonical."""
    tsurite = next(g for g in HARAI_GOSHI.force_grips if g.hand == "right_hand")
    assert GripTypeV2.COLLAR_BACK in tsurite.grip_type
    assert GripTypeV2.COLLAR_SIDE in tsurite.grip_type


def test_harai_goshi_classical_accepts_both_collar_variants() -> None:
    """The hip-fulcrum classical form accepts collar tsurite too."""
    tsurite = next(
        g for g in HARAI_GOSHI_CLASSICAL.force_grips if g.hand == "right_hand"
    )
    assert GripTypeV2.COLLAR_BACK in tsurite.grip_type
    assert GripTypeV2.COLLAR_SIDE in tsurite.grip_type


def test_o_guruma_accepts_both_collar_variants() -> None:
    """O-guruma's extended-leg fulcrum loads uke through the same
    upper-torso pull as harai/uchi-mata; collar tsurite is valid."""
    tsurite = next(g for g in O_GURUMA.force_grips if g.hand == "right_hand")
    assert GripTypeV2.COLLAR_BACK in tsurite.grip_type
    assert GripTypeV2.COLLAR_SIDE in tsurite.grip_type


# ===========================================================================
# AC#4 — head-as-output filters on collar grips
# ===========================================================================
def test_head_as_output_does_not_fire_off_lapel_grip() -> None:
    """The pre-HAJ-161 bug: a STEER-intent LAPEL_HIGH grip emitted a
    HEAD body-part event ("Renard's head is steered"). That was
    mechanically dishonest — a lapel steers the torso, not the head.
    Post-fix the head-as-output gate filters on COLLAR grips only."""
    t, s, m = _new_match()
    edge = GripEdge(
        grasper_id=t.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=s.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.STANDARD,
        strength=1.0, established_tick=0,
    )
    edge.current_intent = "STEER"
    edge.steer_direction = frozenset({"FORWARD", "DOWN"})
    m.grip_graph.add_edge(edge)
    head_bpes = compute_head_state(
        s, m.grip_graph, tick=2, grasper_resolver=m._fighter_by_name,
    )
    # No HEAD event from a lapel grip.
    assert head_bpes == [], (
        f"LAPEL_HIGH STEER should not drive head state; got {head_bpes}"
    )


def test_head_as_output_fires_off_collar_back_grip() -> None:
    """COLLAR_BACK is the canonical head-steering grip — the head-as-
    output computation produces a HEAD event when one is present and
    has STEER intent."""
    t, s, m = _new_match()
    edge = GripEdge(
        grasper_id=t.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=s.identity.name, target_location=GripTarget.BACK_COLLAR,
        grip_type_v2=GripTypeV2.COLLAR_BACK, depth_level=GripDepth.STANDARD,
        strength=1.0, established_tick=0,
    )
    edge.current_intent = "STEER"
    edge.steer_direction = frozenset({"FORWARD", "DOWN"})
    m.grip_graph.add_edge(edge)
    head_bpes = compute_head_state(
        s, m.grip_graph, tick=2, grasper_resolver=m._fighter_by_name,
    )
    assert len(head_bpes) == 1
    assert head_bpes[0].part is BodyPartHigh.HEAD


def test_head_as_output_fires_off_collar_side_grip() -> None:
    """COLLAR_SIDE is the trapezius-line variant — partial head-steering,
    but it still drives the HEAD body-part state. The is_collar() gate
    accepts both sub-types."""
    t, s, m = _new_match()
    edge = GripEdge(
        grasper_id=t.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=s.identity.name, target_location=GripTarget.SIDE_COLLAR,
        grip_type_v2=GripTypeV2.COLLAR_SIDE, depth_level=GripDepth.STANDARD,
        strength=1.0, established_tick=0,
    )
    edge.current_intent = "STEER"
    edge.steer_direction = frozenset({"FORWARD"})
    m.grip_graph.add_edge(edge)
    head_bpes = compute_head_state(
        s, m.grip_graph, tick=2, grasper_resolver=m._fighter_by_name,
    )
    assert len(head_bpes) == 1
    assert head_bpes[0].part is BodyPartHigh.HEAD


def test_head_as_output_ignores_non_collar_steerers_when_collar_present() -> None:
    """Mixed grip set: a LAPEL_HIGH steerer alongside a COLLAR_BACK
    steerer. The head event reflects only the collar's steer direction
    (the lapel contribution drops out)."""
    t, s, m = _new_match()
    lapel_edge = GripEdge(
        grasper_id=t.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=s.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.STANDARD,
        strength=1.0, established_tick=0,
    )
    lapel_edge.current_intent = "STEER"
    lapel_edge.steer_direction = frozenset({"DOWN"})
    m.grip_graph.add_edge(lapel_edge)

    collar_edge = GripEdge(
        grasper_id=t.identity.name, grasper_part=BodyPart.LEFT_HAND,
        target_id=s.identity.name, target_location=GripTarget.BACK_COLLAR,
        grip_type_v2=GripTypeV2.COLLAR_BACK, depth_level=GripDepth.STANDARD,
        strength=1.0, established_tick=0,
    )
    collar_edge.current_intent = "STEER"
    collar_edge.steer_direction = frozenset({"FORWARD"})
    m.grip_graph.add_edge(collar_edge)

    head_bpes = compute_head_state(
        s, m.grip_graph, tick=2, grasper_resolver=m._fighter_by_name,
    )
    assert len(head_bpes) == 1
    # Only the collar steerer's direction lands.
    assert "FORWARD" in {d.name for d in (head_bpes[0].steer_direction or ())}
    assert "DOWN" not in {d.name for d in (head_bpes[0].steer_direction or ())}


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
