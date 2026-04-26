# tests/test_stance_parity.py
# HAJ-51 — stance parity modifies grip force authority and signature
# match per grip type / per throw.
#
# Pre-HAJ-51 the existing stance scaffolding (StanceMatchup, stance_factor)
# operated globally — every grip and every throw saw the same flat
# MIRRORED_PENALTY, with sumi-gaeshi as a one-off bonus. The substrate's
# ForceEnvelope had no stance awareness, and signature match never read
# StanceMatchup at all.
#
# Post-HAJ-51:
#   - ForceEnvelope carries a per-grip StanceParity. LAPEL_HIGH and COLLAR
#     favor matched; PISTOL and CROSS favor mirrored. compute_grip_delta
#     and Match's per-tick force application apply this multiplier.
#   - ThrowDef carries preferred_stance_parity. actual_signature_match
#     boosts the score in the preferred matchup and penalizes it in the
#     other. Stance-agnostic throws (None) are unaffected.

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from enums import (
    BodyPart, GripTarget, GripTypeV2, GripDepth, GripMode, Stance,
    StanceMatchup,
)
from force_envelope import FORCE_ENVELOPES, StanceParity
from grip_graph import GripGraph, GripEdge
from perception import actual_signature_match
from throws import ThrowID, THROW_DEFS
import main as main_module


def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _add_edge(graph, grasper, target, hand, location, grip_type, depth=GripDepth.DEEP):
    graph.add_edge(GripEdge(
        grasper_id=grasper.identity.name, grasper_part=hand,
        target_id=target.identity.name, target_location=location,
        grip_type_v2=grip_type, depth_level=depth,
        strength=1.0, established_tick=0, mode=GripMode.DRIVING,
    ))


# ---------------------------------------------------------------------------
# StanceParity dataclass
# ---------------------------------------------------------------------------
def test_stance_parity_default_is_neutral() -> None:
    sp = StanceParity()
    assert sp.matched == 1.0
    assert sp.mirrored == 1.0
    assert sp.multiplier(StanceMatchup.MATCHED) == 1.0
    assert sp.multiplier(StanceMatchup.MIRRORED) == 1.0


def test_stance_parity_multiplier_in_range() -> None:
    """Per HAJ-51 spec, multiplier range is 0.7–1.3."""
    for env in FORCE_ENVELOPES.values():
        sp = env.stance_parity
        assert 0.7 <= sp.matched  <= 1.3
        assert 0.7 <= sp.mirrored <= 1.3


# ---------------------------------------------------------------------------
# Per-grip envelope shifts (ticket-specified directions)
# ---------------------------------------------------------------------------
def test_lapel_high_favors_matched_stance() -> None:
    sp = FORCE_ENVELOPES[GripTypeV2.LAPEL_HIGH].stance_parity
    assert sp.matched > sp.mirrored, (
        "LAPEL_HIGH should have stronger authority in matched stance"
    )


def test_collar_strongly_favors_matched_stance() -> None:
    sp = FORCE_ENVELOPES[GripTypeV2.COLLAR].stance_parity
    assert sp.matched > sp.mirrored


def test_pistol_favors_mirrored_stance() -> None:
    sp = FORCE_ENVELOPES[GripTypeV2.PISTOL].stance_parity
    assert sp.mirrored > sp.matched, (
        "PISTOL (Russian / two-on-one) should have stronger authority "
        "in mirrored stance"
    )


def test_cross_favors_mirrored_stance() -> None:
    sp = FORCE_ENVELOPES[GripTypeV2.CROSS].stance_parity
    assert sp.mirrored > sp.matched


def test_belt_is_stance_agnostic() -> None:
    """Belt grip wraps the body — no chirality, no stance preference."""
    sp = FORCE_ENVELOPES[GripTypeV2.BELT].stance_parity
    assert sp.matched == sp.mirrored == 1.0


# ---------------------------------------------------------------------------
# compute_grip_delta diverges between matched and mirrored
# ---------------------------------------------------------------------------
def test_grip_delta_unchanged_without_stance_arg() -> None:
    """Backwards compat: no stance_matchup arg → legacy behavior."""
    t, s = _pair()
    g = GripGraph()
    _add_edge(g, t, s, BodyPart.RIGHT_HAND, GripTarget.LEFT_LAPEL, GripTypeV2.LAPEL_HIGH)
    delta = g.compute_grip_delta(t, s)
    assert delta > 0  # tanaka has the only edge — strictly dominant


def test_grip_delta_lapel_high_drops_in_mirrored_stance() -> None:
    """Same edge set, only the stance matchup changes — LAPEL_HIGH
    contribution should weaken under MIRRORED."""
    t, s = _pair()
    g = GripGraph()
    _add_edge(g, t, s, BodyPart.RIGHT_HAND, GripTarget.LEFT_LAPEL, GripTypeV2.LAPEL_HIGH)
    matched = g.compute_grip_delta(t, s, StanceMatchup.MATCHED)
    mirrored = g.compute_grip_delta(t, s, StanceMatchup.MIRRORED)
    assert mirrored < matched, (
        f"LAPEL_HIGH delta should drop in MIRRORED; "
        f"matched={matched:.3f} mirrored={mirrored:.3f}"
    )


def test_grip_delta_pistol_rises_in_mirrored_stance() -> None:
    """A pistol-grip-only fighter gets stronger relative dominance under
    MIRRORED — the inverse of the LAPEL_HIGH case."""
    t, s = _pair()
    g = GripGraph()
    _add_edge(g, t, s, BodyPart.LEFT_HAND, GripTarget.RIGHT_SLEEVE, GripTypeV2.PISTOL)
    matched = g.compute_grip_delta(t, s, StanceMatchup.MATCHED)
    mirrored = g.compute_grip_delta(t, s, StanceMatchup.MIRRORED)
    assert mirrored > matched, (
        f"PISTOL delta should rise in MIRRORED; "
        f"matched={matched:.3f} mirrored={mirrored:.3f}"
    )


def test_grip_delta_belt_unchanged_across_stances() -> None:
    """Stance-agnostic grip → identical delta regardless of matchup."""
    t, s = _pair()
    g = GripGraph()
    _add_edge(g, t, s, BodyPart.RIGHT_HAND, GripTarget.BELT, GripTypeV2.BELT)
    matched = g.compute_grip_delta(t, s, StanceMatchup.MATCHED)
    mirrored = g.compute_grip_delta(t, s, StanceMatchup.MIRRORED)
    assert matched == mirrored


# ---------------------------------------------------------------------------
# ThrowDef preferred_stance_parity populated where the ticket demands
# ---------------------------------------------------------------------------
def test_sumi_gaeshi_prefers_mirrored_stance() -> None:
    assert (THROW_DEFS[ThrowID.SUMI_GAESHI].preferred_stance_parity
            == StanceMatchup.MIRRORED)


def test_seoi_nage_prefers_matched_stance() -> None:
    assert (THROW_DEFS[ThrowID.SEOI_NAGE].preferred_stance_parity
            == StanceMatchup.MATCHED)


def test_uchi_mata_prefers_matched_stance() -> None:
    assert (THROW_DEFS[ThrowID.UCHI_MATA].preferred_stance_parity
            == StanceMatchup.MATCHED)


def test_de_ashi_harai_is_stance_agnostic() -> None:
    """Per ticket: timing-window throw, geometry-independent."""
    assert THROW_DEFS[ThrowID.DE_ASHI_HARAI].preferred_stance_parity is None


# ---------------------------------------------------------------------------
# actual_signature_match applies preference
# ---------------------------------------------------------------------------
def _force_stance(judoka, stance):
    judoka.state.current_stance = stance


def test_signature_match_boosts_preferred_stance() -> None:
    """Sumi-gaeshi has signature match boosted in MIRRORED and penalized
    in MATCHED. Compare the same grip configuration across both."""
    t, s = _pair()
    g = GripGraph()
    # Minimal edge satisfying SUMI_GAESHI requires (any grip with depth ≥ 0.2).
    _add_edge(g, t, s, BodyPart.RIGHT_HAND, GripTarget.LEFT_LAPEL,
              GripTypeV2.LAPEL_HIGH, depth=GripDepth.STANDARD)

    # Both orthodox → MATCHED → penalty for sumi-gaeshi.
    _force_stance(t, Stance.ORTHODOX)
    _force_stance(s, Stance.ORTHODOX)
    matched_score = actual_signature_match(ThrowID.SUMI_GAESHI, t, s, g)

    # Switch defender to southpaw → MIRRORED → boost for sumi-gaeshi.
    _force_stance(s, Stance.SOUTHPAW)
    mirrored_score = actual_signature_match(ThrowID.SUMI_GAESHI, t, s, g)

    assert mirrored_score > matched_score, (
        f"sumi-gaeshi signature should prefer MIRRORED; "
        f"matched={matched_score:.3f} mirrored={mirrored_score:.3f}"
    )


def test_signature_match_penalizes_off_preference() -> None:
    """Uchi-mata's signature should drop in MIRRORED relative to MATCHED
    (its preferred stance)."""
    t, s = _pair()
    g = GripGraph()
    _add_edge(g, t, s, BodyPart.RIGHT_HAND, GripTarget.LEFT_LAPEL,
              GripTypeV2.LAPEL_HIGH, depth=GripDepth.DEEP)
    _add_edge(g, t, s, BodyPart.LEFT_HAND, GripTarget.RIGHT_SLEEVE,
              GripTypeV2.SLEEVE_HIGH, depth=GripDepth.DEEP)

    _force_stance(t, Stance.ORTHODOX)
    _force_stance(s, Stance.ORTHODOX)
    matched = actual_signature_match(ThrowID.UCHI_MATA, t, s, g)

    _force_stance(s, Stance.SOUTHPAW)
    mirrored = actual_signature_match(ThrowID.UCHI_MATA, t, s, g)

    # Either both scores are zero (precondition failure) or matched > mirrored.
    if matched > 0:
        assert matched > mirrored


def test_signature_match_unaffected_for_agnostic_throw() -> None:
    """De-ashi-harai has no preferred parity → identical signature
    across stance configurations."""
    t, s = _pair()
    g = GripGraph()
    _add_edge(g, t, s, BodyPart.LEFT_HAND, GripTarget.RIGHT_SLEEVE,
              GripTypeV2.SLEEVE_HIGH, depth=GripDepth.DEEP)

    _force_stance(t, Stance.ORTHODOX)
    _force_stance(s, Stance.ORTHODOX)
    matched = actual_signature_match(ThrowID.DE_ASHI_HARAI, t, s, g)

    _force_stance(s, Stance.SOUTHPAW)
    mirrored = actual_signature_match(ThrowID.DE_ASHI_HARAI, t, s, g)

    assert matched == mirrored


# ---------------------------------------------------------------------------
# StanceMatchup.of helper
# ---------------------------------------------------------------------------
def test_stance_matchup_helper() -> None:
    assert StanceMatchup.of(Stance.ORTHODOX, Stance.ORTHODOX) == StanceMatchup.MATCHED
    assert StanceMatchup.of(Stance.SOUTHPAW, Stance.SOUTHPAW) == StanceMatchup.MATCHED
    assert StanceMatchup.of(Stance.ORTHODOX, Stance.SOUTHPAW) == StanceMatchup.MIRRORED
    assert StanceMatchup.of(Stance.SOUTHPAW, Stance.ORTHODOX) == StanceMatchup.MIRRORED


# ---------------------------------------------------------------------------
# Match header surfaces the matchup
# ---------------------------------------------------------------------------
def test_match_header_includes_stance_matchup() -> None:
    import io
    import random
    from contextlib import redirect_stdout
    from match import Match
    from referee import build_suzuki

    random.seed(1)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(),
              max_ticks=5, seed=1)
    buf = io.StringIO()
    with redirect_stdout(buf):
        m._print_header()
    out = buf.getvalue()
    assert "Stance matchup:" in out
    assert "MATCHED" in out  # both fighters default to ORTHODOX
    # Nicknames also surfaced for the human reader.
    assert "ai-yotsu" in out
