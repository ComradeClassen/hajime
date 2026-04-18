# worked_throws.py
# Physics-substrate Part 5: parameterized instances of the Part 4 templates.
#
# Spec: design-notes/physics-substrate.md, Part 5 (sections 5.1–5.4).
#
# Four throws chosen to exercise every mechanic in Parts 1–4:
#   - Uchi-mata           — canonical forward-rotation Couple throw
#   - O-soto-gari         — canonical backward-rotation Couple throw
#   - Seoi-nage (morote)  — canonical Lever throw
#   - De-ashi-harai       — timing-window ashi-waza Couple variant
#
# The remaining v0.1 throws (HARAI_GOSHI, TAI_OTOSHI, O_UCHI_GARI, KO_UCHI_GARI,
# SUMI_GAESHI) stay on the legacy `ThrowDef`/`EdgeRequirement` path in throws.py
# until their Session-4 backfill lands.
#
# Sidedness: these are the right-sided canonical instances — they assume a
# right-dominant tori (tsurite=right, hikite=left). Left-dominant tori would
# need mirrored instances; v0.1 fighters (Tanaka, Sato) are both right-dominant.

from __future__ import annotations
import math

from enums import BodyPart, GripTypeV2, GripDepth, GripMode
from throws import ThrowID
from throw_templates import (
    CoupleThrow, LeverThrow, ThrowTemplate,
    KuzushiRequirement, GripRequirement, ForceRequirement, ForceKind,
    CoupleBodyPartRequirement, LeverBodyPartRequirement,
    UkePostureRequirement, TimingWindow,
    CoupleAxis, SupportRequirement, UkeBaseState,
    FailureOutcome, FailureSpec,
)


# ---------------------------------------------------------------------------
# UCHI-MATA (内股) — spec 5.1
# ---------------------------------------------------------------------------
UCHI_MATA: CoupleThrow = CoupleThrow(
    name="Uchi-mata",
    kuzushi_requirement=KuzushiRequirement(
        direction=(1.0, 0.3),                    # forward + slight right in uke's frame
        tolerance_rad=math.radians(30),
        min_velocity_magnitude=0.4,              # uke onto the toes
    ),
    force_grips=(
        GripRequirement(
            hand="left_hand",                    # hikite
            grip_type=(GripTypeV2.SLEEVE,),
            min_depth=GripDepth.STANDARD,
            mode=GripMode.DRIVING,
        ),
        GripRequirement(
            hand="right_hand",                   # tsurite
            grip_type=(GripTypeV2.LAPEL_HIGH, GripTypeV2.COLLAR),
            min_depth=GripDepth.STANDARD,
            mode=GripMode.DRIVING,
        ),
    ),
    couple_axis=CoupleAxis.SAGITTAL,             # forward pitch
    min_torque_nm=500.0,                         # moderate-to-high
    body_part_requirement=CoupleBodyPartRequirement(
        tori_supporting_foot="left_foot",
        tori_attacking_limb="right_leg",
        contact_point_on_uke=BodyPart.LEFT_THIGH,
        contact_height_range=(0.55, 0.90),       # upper thigh to hip crease
    ),
    uke_posture_requirement=UkePostureRequirement(
        trunk_sagittal_range=(math.radians(-5), math.radians(20)),
        trunk_frontal_range=(math.radians(-15), math.radians(25)),
        com_height_range=(0.95, 1.30),           # HIGH — weight rising onto toes
        base_state=UkeBaseState.WEIGHT_SHIFTING_FORWARD,
    ),
    commit_threshold=0.55,
    sukashi_vulnerability=0.75,                  # HIGH — uchi-mata-sukashi is real
    failure_outcome=FailureSpec(
        primary=FailureOutcome.TORI_COMPROMISED_SINGLE_SUPPORT,
        secondary=FailureOutcome.UCHI_MATA_SUKASHI,
        tertiary=FailureOutcome.STANCE_RESET,
    ),
)


# ---------------------------------------------------------------------------
# O-SOTO-GARI (大外刈) — spec 5.2
# ---------------------------------------------------------------------------
O_SOTO_GARI: CoupleThrow = CoupleThrow(
    name="O-soto-gari",
    kuzushi_requirement=KuzushiRequirement(
        direction=(-1.0, 0.5),                   # backward + rightward in uke's frame
        tolerance_rad=math.radians(25),
        min_velocity_magnitude=0.3,              # reaction to pull / step onto heel
    ),
    force_grips=(
        GripRequirement(
            hand="left_hand",                    # hikite
            grip_type=(GripTypeV2.SLEEVE,),
            min_depth=GripDepth.STANDARD,
            mode=GripMode.DRIVING,
        ),
        GripRequirement(
            hand="right_hand",                   # tsurite
            grip_type=(GripTypeV2.LAPEL_LOW, GripTypeV2.LAPEL_HIGH),
            min_depth=GripDepth.STANDARD,
            mode=GripMode.DRIVING,
        ),
    ),
    couple_axis=CoupleAxis.TRANSVERSE,           # backward pitch
    min_torque_nm=600.0,                         # high — requires strong pivot-knee extension
    body_part_requirement=CoupleBodyPartRequirement(
        tori_supporting_foot="left_foot",        # planted alongside uke's right foot
        tori_attacking_limb="right_leg",
        contact_point_on_uke=BodyPart.RIGHT_THIGH,
        contact_height_range=(0.35, 0.65),       # knee to mid-thigh
    ),
    uke_posture_requirement=UkePostureRequirement(
        trunk_sagittal_range=(math.radians(-10), math.radians(5)),
        trunk_frontal_range=(math.radians(-15), math.radians(20)),
        com_height_range=(0.88, 1.15),           # MEDIUM_HIGH — not jigotai
        base_state=UkeBaseState.WEIGHT_ON_REAPED_LEG_HEEL,
    ),
    commit_threshold=0.50,
    sukashi_vulnerability=0.35,                  # osoto-sukashi is rare
    failure_outcome=FailureSpec(
        primary=FailureOutcome.TORI_COMPROMISED_FORWARD_LEAN,
        secondary=FailureOutcome.OSOTO_GAESHI,
        tertiary=FailureOutcome.STANCE_RESET,
    ),
)


# ---------------------------------------------------------------------------
# SEOI-NAGE (背負投, morote form) — spec 5.3
# ---------------------------------------------------------------------------
SEOI_NAGE_MOROTE: LeverThrow = LeverThrow(
    name="Seoi-nage",
    kuzushi_requirement=KuzushiRequirement(
        direction=(1.0, 0.2),                    # forward, very slight right-corner
        tolerance_rad=math.radians(20),
        min_displacement_past_recoverable=0.15,  # real kuzushi, not incipient
    ),
    force_grips=(
        GripRequirement(
            hand="left_hand",                    # hikite
            grip_type=(GripTypeV2.SLEEVE,),
            min_depth=GripDepth.STANDARD,
            mode=GripMode.DRIVING,
        ),
        GripRequirement(
            hand="right_hand",                   # tsurite
            grip_type=(GripTypeV2.LAPEL_LOW, GripTypeV2.LAPEL_HIGH),
            min_depth=GripDepth.STANDARD,
            mode=GripMode.DRIVING,
        ),
    ),
    required_forces=(
        ForceRequirement(                        # hikite pull, ~30° below horizontal
            hand="left_hand", kind=ForceKind.PULL,
            direction=(1.0, 0.0, -0.58),         # forward-down across tori's body
            min_magnitude_n=300.0,
        ),
        ForceRequirement(                        # tsurite lift + forward push
            hand="right_hand", kind=ForceKind.LIFT,
            direction=(0.7, 0.0, 0.71),          # forward-up; internal shoulder rotation
            min_magnitude_n=250.0,
        ),
    ),
    min_lift_force_n=600.0,                      # HIGH — sustained through kake
    body_part_requirement=LeverBodyPartRequirement(
        fulcrum_body_part=BodyPart.RIGHT_SHOULDER,
        fulcrum_contact_on_uke=BodyPart.CORE,    # chest-and-right-armpit → simplified to CORE
        fulcrum_offset_below_uke_com_m=0.15,     # tori's hips below uke's by ≥ 0.15 m
        tori_supporting_feet=SupportRequirement.DOUBLE_SUPPORT,
    ),
    uke_posture_requirement=UkePostureRequirement(
        trunk_sagittal_range=(math.radians(0), math.radians(30)),    # upright or forward
        trunk_frontal_range=(math.radians(-15), math.radians(15)),
        com_height_range=(0.88, 1.20),           # NOT jigotai-low, NOT back-leaning
        uke_com_over_fulcrum=True,
    ),
    commit_threshold=0.70,                       # HIGH — cannot exploit partial kuzushi
    counter_vulnerability=0.55,                  # ura-nage, sode-tsurikomi-gaeshi
    failure_outcome=FailureSpec(
        primary=FailureOutcome.TORI_STUCK_WITH_UKE_ON_BACK,
        secondary=FailureOutcome.TORI_BENT_FORWARD_LOADED,
        tertiary=FailureOutcome.STANCE_RESET,
    ),
)


# ---------------------------------------------------------------------------
# DE-ASHI-HARAI (出足払) — spec 5.4
# ---------------------------------------------------------------------------
DE_ASHI_HARAI: CoupleThrow = CoupleThrow(
    name="De-ashi-harai",
    kuzushi_requirement=KuzushiRequirement(
        direction=(1.0, 0.0),                    # nominal — overridden by aligned flag
        tolerance_rad=math.radians(45),          # wide — motion is uke's own
        min_velocity_magnitude=0.3,              # uke must actually be stepping
        aligned_with_uke_velocity=True,          # catches any non-zero uke velocity
    ),
    force_grips=(
        GripRequirement(
            hand="left_hand",                    # hikite — destabilizes upper body
            grip_type=(GripTypeV2.SLEEVE,),
            min_depth=GripDepth.STANDARD,
            mode=GripMode.DRIVING,
        ),
        GripRequirement(
            hand="right_hand",                   # tsurite — light downward pull
            grip_type=(GripTypeV2.LAPEL_LOW,),
            min_depth=GripDepth.POCKET,          # pocket is enough — the foot does the work
            mode=GripMode.DRIVING,
        ),
    ),
    couple_axis=CoupleAxis.TRANSVERSE,
    min_torque_nm=150.0,                         # LOW — hands only destabilize
    body_part_requirement=CoupleBodyPartRequirement(
        tori_supporting_foot="left_foot",
        tori_attacking_limb="right_foot",
        contact_point_on_uke=BodyPart.RIGHT_FOOT,
        contact_height_range=(0.0, 0.15),
        timing_window=TimingWindow(
            target_foot="right_foot",            # uke's forward-stepping foot
            weight_fraction_range=(0.1, 0.3),    # narrow unweighting window
            window_duration_ticks=1,
        ),
    ),
    uke_posture_requirement=UkePostureRequirement(
        trunk_sagittal_range=(math.radians(-10), math.radians(15)),
        trunk_frontal_range=(math.radians(-45), math.radians(45)),   # any
        com_height_range=(0.70, 1.40),                                # any
        base_state=UkeBaseState.MID_STEP,
    ),
    commit_threshold=0.45,                       # moderate — useless without timing window
    sukashi_vulnerability=0.25,
    failure_outcome=FailureSpec(
        primary=FailureOutcome.TORI_SWEEP_BOUNCES_OFF,
        secondary=FailureOutcome.STANCE_RESET,
        tertiary=FailureOutcome.PARTIAL_THROW,
    ),
)


# ---------------------------------------------------------------------------
# REGISTRY
# Maps ThrowID → worked template. Throws not in this table fall back to the
# legacy THROW_DEFS / EdgeRequirement path in throws.py.
# ---------------------------------------------------------------------------
WORKED_THROWS: dict[ThrowID, ThrowTemplate] = {
    ThrowID.UCHI_MATA:     UCHI_MATA,
    ThrowID.O_SOTO_GARI:   O_SOTO_GARI,
    ThrowID.SEOI_NAGE:     SEOI_NAGE_MOROTE,
    ThrowID.DE_ASHI_HARAI: DE_ASHI_HARAI,
}


def worked_template_for(throw_id: ThrowID) -> ThrowTemplate | None:
    """Return the Part-5 worked template for a throw, or None if it's still
    on the legacy ThrowDef path.
    """
    return WORKED_THROWS.get(throw_id)
