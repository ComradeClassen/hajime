# force_envelope.py
# Physics-substrate Part 2.3 / 2.4: force envelopes per grip type.
#
# A grip is a direction-dependent force coupling. Each GripTypeV2 carries a
# ForceEnvelope describing the maximum pull / push / lift forces transmissible
# through it, plus geometric quantities (moment arm, rotation authority) and
# defensive properties (strip resistance).
#
# Delivered force on a given tick is the baseline envelope value multiplied
# by four modifiers in [0, 1]: depth × grip_strength × fatigue × composure
# (Part 2.4).
#
# Numerical values here are CALIBRATION STUBS. The spec (2.3) commits only
# to relative ordering — the table in the spec. Phase 3 calibration will
# tune these against match observations. Relative ordering is what the
# tests lock down.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from enums import GripTypeV2, GripDepth, GripMode, StanceMatchup

if TYPE_CHECKING:
    from judoka import Judoka


# ---------------------------------------------------------------------------
# STANCE PARITY (HAJ-51)
# Multipliers on a grip's force-envelope authority based on whether the
# fighters are in matched (ai-yotsu) or mirrored (kenka-yotsu) stances.
# Range 0.7–1.3. The default StanceParity() is neutral; a grip whose
# leverage geometry is stance-dependent declares its preference here so
# Match.compute_net_force can apply it per edge.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StanceParity:
    """Per-grip authority multipliers for matched vs mirrored stance."""
    matched:  float = 1.0
    mirrored: float = 1.0

    def multiplier(self, matchup: StanceMatchup) -> float:
        if matchup == StanceMatchup.MIRRORED:
            return self.mirrored
        return self.matched


# ---------------------------------------------------------------------------
# FORCE ENVELOPE
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ForceEnvelope:
    """Baseline maximum forces transmissible through a grip (Part 2.3).

    All forces are in Newtons. A 90 kg judoka weighs ~880 N, which is the
    rough yardstick for 'can lift their opponent' calibration.
    """
    max_pull_force:        float   # toward tori (N)
    max_push_force:        float   # away from tori (N)
    max_lift_force:        float   # vertical against gravity (N)
    moment_arm_to_uke_com: float   # grip point to uke's CoM (m); longer = more torque
    rotation_authority:    float   # multiplier on torque about uke's vertical axis
    strip_resistance:      float   # how hard uke must work to strip the grip (arbitrary units)
    # HAJ-51 — stance parity multipliers. Matched (ai-yotsu) leverages most
    # gi-aligned grips; mirrored (kenka-yotsu) opens cross-grip families.
    stance_parity:         StanceParity = field(default_factory=StanceParity)


# ---------------------------------------------------------------------------
# BASELINE ENVELOPES per grip type (Part 2.3 table)
#
# Numerical levels chosen to match the relative-ordering table in spec 2.3:
#   Sleeve     — Pull High,   Push Low,    Lift Low,    Rot Med,  Strip Med
#   Lapel low  — Pull Med,    Push Med,    Lift Med,    Rot Med,  Strip Med
#   Lapel high — Pull Med,    Push Med,    Lift High,   Rot Med+, Strip Med+
#   Collar     — Pull Med,    Push High,   Lift Med,    Rot ★,    Strip High
#   Belt       — Pull High,   Push Med,    Lift ★,      Rot High, Strip VHigh
#   Pistol     — Pull Low,    Push Low,    Lift Low,    Rot Low,  Strip ★
#   Cross      — Pull Med,    Push Med,    Lift Med,    Rot Var,  Strip Low
#
# Scale: Low ≈ 150, Med ≈ 300, High ≈ 500, VHigh ≈ 700, ★ = category max (≈ 800+).
# TODO (Part 6 / Phase 3): calibrate against match telemetry.
# ---------------------------------------------------------------------------
FORCE_ENVELOPES: dict[GripTypeV2, ForceEnvelope] = {
    # HAJ-53 — sleeve sub-types. SLEEVE_HIGH inherits the prior single-SLEEVE
    # numbers (it's the standard hikite grip, ≈90% of throws prefer it).
    # SLEEVE_LOW (cuff) trades lift force and strip resistance for a longer
    # moment arm and stronger rotation authority — the cuff sits farther
    # from uke's shoulder, gives the wrist around-the-axis control, and
    # slips more readily under load.
    #
    # HAJ-51 — stance_parity declares per-grip leverage shift between
    # matched (ai-yotsu) and mirrored (kenka-yotsu). Tuning rationale below.
    GripTypeV2.SLEEVE_HIGH: ForceEnvelope(
        max_pull_force=500.0, max_push_force=150.0, max_lift_force=200.0,
        moment_arm_to_uke_com=0.50, rotation_authority=1.0, strip_resistance=350.0,
        # Standard hikite hand favors matched stance (cleaner pull line) but
        # works fine in mirrored. Mild matched preference.
        stance_parity=StanceParity(matched=1.05, mirrored=0.95),
    ),
    GripTypeV2.SLEEVE_LOW: ForceEnvelope(
        max_pull_force=500.0, max_push_force=150.0, max_lift_force=100.0,
        moment_arm_to_uke_com=0.65, rotation_authority=1.3, strip_resistance=200.0,
        # Cuff control marginally cleaner in mirrored — wrist-against-wrist
        # geometry the Russian / pistol family leverages.
        stance_parity=StanceParity(matched=1.0, mirrored=1.05),
    ),
    GripTypeV2.LAPEL_LOW: ForceEnvelope(
        max_pull_force=300.0, max_push_force=300.0, max_lift_force=300.0,
        moment_arm_to_uke_com=0.30, rotation_authority=1.0, strip_resistance=300.0,
        # Low lapel hand sits near the centerline — geometry symmetric.
        stance_parity=StanceParity(matched=1.0, mirrored=1.0),
    ),
    GripTypeV2.LAPEL_HIGH: ForceEnvelope(
        max_pull_force=300.0, max_push_force=300.0, max_lift_force=500.0,
        moment_arm_to_uke_com=0.40, rotation_authority=1.2, strip_resistance=400.0,
        # High lapel pulls along the gi seam: matched aligns the pull with
        # the construction; mirrored fights it.
        stance_parity=StanceParity(matched=1.10, mirrored=0.85),
    ),
    # HAJ-161 — collar grip splits by position. COLLAR_BACK retains the
    # prior bare `COLLAR` envelope: deep nape grip, maximum rotation
    # authority and the only grip whose physical purchase can steer the
    # head as a coupled output. COLLAR_SIDE sits between LAPEL_HIGH and
    # COLLAR_BACK — partial head-steering, more shoulder-control,
    # slightly less stance-sensitive than the nape grip.
    GripTypeV2.COLLAR_BACK: ForceEnvelope(
        max_pull_force=300.0, max_push_force=500.0, max_lift_force=300.0,
        moment_arm_to_uke_com=0.55, rotation_authority=1.8, strip_resistance=500.0,
        # Deep collar is the most stance-dependent grip in judo: the
        # rotational authority comes from the seam line, which is fully
        # served only when both fighters' lead sides agree.
        stance_parity=StanceParity(matched=1.15, mirrored=0.80),
    ),
    GripTypeV2.COLLAR_SIDE: ForceEnvelope(
        max_pull_force=300.0, max_push_force=420.0, max_lift_force=350.0,
        moment_arm_to_uke_com=0.45, rotation_authority=1.4, strip_resistance=420.0,
        # Hybrid lapel/collar — less seam-dependent than COLLAR_BACK so
        # the matched/mirrored gap narrows, but still favors matched.
        stance_parity=StanceParity(matched=1.08, mirrored=0.90),
    ),
    GripTypeV2.BELT: ForceEnvelope(
        max_pull_force=500.0, max_push_force=300.0, max_lift_force=800.0,
        moment_arm_to_uke_com=0.05, rotation_authority=1.3, strip_resistance=700.0,
        # Belt is symmetric — wraps the body, no chirality.
        stance_parity=StanceParity(matched=1.0, mirrored=1.0),
    ),
    GripTypeV2.PISTOL: ForceEnvelope(
        max_pull_force=150.0, max_push_force=150.0, max_lift_force=150.0,
        moment_arm_to_uke_com=0.55, rotation_authority=0.6, strip_resistance=800.0,
        # Pistol grip is the kenka-yotsu specialty — Russian / two-on-one
        # geometry only aligns when stances are mirrored.
        stance_parity=StanceParity(matched=0.85, mirrored=1.20),
    ),
    GripTypeV2.CROSS: ForceEnvelope(
        max_pull_force=300.0, max_push_force=300.0, max_lift_force=300.0,
        moment_arm_to_uke_com=0.40, rotation_authority=1.0, strip_resistance=200.0,
        # Cross-grip authority depends on reaching across the centerline —
        # mirrored stance makes that geometry natural.
        stance_parity=StanceParity(matched=0.80, mirrored=1.25),
    ),
}


# ---------------------------------------------------------------------------
# MODIFIER HELPERS (Part 2.4)
# ---------------------------------------------------------------------------
def grip_strength(judoka: "Judoka") -> float:
    """Per-Part 2.4: average effective output of both hands plus core,
    normalized to [0, 1]. Already folds fatigue and injury through
    effective_body_part.
    """
    parts = ("right_hand", "left_hand", "core")
    return sum(judoka.effective_body_part(p) for p in parts) / (len(parts) * 10.0)


def _composure_modifier(judoka: "Judoka") -> float:
    """Normalize composure to [0, 1] from the 0–10 scale used on Capability."""
    ceiling = max(1.0, float(judoka.capability.composure_ceiling))
    return max(0.0, min(1.0, judoka.state.composure_current / ceiling))


def _hand_fatigue_modifier(judoka: "Judoka", hand_key: str) -> float:
    """Part 2.4: hand-part fatigue multiplies directly into grip force.
    Returns (1 - fatigue) for the gripping hand.
    """
    part = judoka.state.body.get(hand_key)
    if part is None:
        return 1.0
    return max(0.0, 1.0 - part.fatigue)


# ---------------------------------------------------------------------------
# DELIVERED FORCE (Part 2.4)
# ---------------------------------------------------------------------------
def delivered_pull_force(
    grip_type: GripTypeV2,
    depth: GripDepth,
    grasper: "Judoka",
    grasper_hand_key: str,
) -> float:
    """Instantaneous pull force (N) this grip can deliver right now.

        delivered = envelope × depth × strength × fatigue × composure
    """
    env = FORCE_ENVELOPES[grip_type]
    depth_mod    = depth.modifier()
    strength_mod = grip_strength(grasper)
    fatigue_mod  = _hand_fatigue_modifier(grasper, grasper_hand_key)
    composure_mod = _composure_modifier(grasper)
    return env.max_pull_force * depth_mod * strength_mod * fatigue_mod * composure_mod


# ---------------------------------------------------------------------------
# MODE COSTS (Part 2.5)
# Fatigue multipliers applied per tick based on whether the grip is in
# connective or driving mode. Driving consumes the hand-part fast; connective
# allows recovery.
# TODO (Part 3): wire to action selection so Part 3's tick update applies
# these costs on every tick, not just through the legacy EDGE_FATIGUE_PER_TICK.
# ---------------------------------------------------------------------------
MODE_FATIGUE_MULTIPLIER: dict[GripMode, float] = {
    GripMode.CONNECTIVE: 0.3,
    GripMode.DRIVING:    2.0,
}
