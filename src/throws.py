# throws.py
# Defines the Throw and Combo data types, the JudokaThrowProfile (which stores
# how effective a specific judoka is with a specific throw from each side), and
# the two global registries that the rest of the simulation looks things up from.

from dataclasses import dataclass  # dataclass auto-generates __init__, __repr__, etc.
from enum import Enum, auto        # Enum for strongly-typed throw/combo identifiers


# ---------------------------------------------------------------------------
# THROW IDs
# An enum entry for every throw in the Phase 1 registry.
# Using an enum (not raw strings) means a typo in a throw name becomes a Python
# error at import time, not a silent miss at runtime.
# ---------------------------------------------------------------------------
class ThrowID(Enum):
    SEOI_NAGE   = auto()  # Shoulder throw — Tanaka's signature
    UCHI_MATA   = auto()  # Inner thigh reap — Sato's signature
    O_SOTO_GARI = auto()  # Major outer reap
    O_UCHI_GARI = auto()  # Major inner reap
    KO_UCHI_GARI = auto() # Minor inner reap — short, sneaky; great combo opener
    HARAI_GOSHI = auto()  # Hip sweep
    TAI_OTOSHI  = auto()  # Body drop — no hip contact; works as a combo finisher
    SUMI_GAESHI = auto()  # Corner sacrifice — mirrored-stance favourite


# ---------------------------------------------------------------------------
# COMBO IDs
# Three judo-realistic two-throw chains. Combos are drilled sequences; when a
# judoka attempts the first throw and it doesn't land cleanly, they may chain
# into the second throw before the opponent fully recovers.
# ---------------------------------------------------------------------------
class ComboID(Enum):
    KO_UCHI_TO_SEOI      = auto()  # Ankle reap → shoulder throw
    O_UCHI_TO_UCHI_MATA  = auto()  # Major inner reap → inner thigh sweep
    HARAI_TO_TAI_OTOSHI  = auto()  # Hip sweep → body drop (switch when hip is read)


# ---------------------------------------------------------------------------
# THROW
# The global registry entry for a throw. Stores display name and a one-line
# description. This is reference data — not fighter-specific.
# ---------------------------------------------------------------------------
@dataclass
class Throw:
    """Global registry entry. Describes what a throw IS, not how well anyone does it."""
    throw_id: ThrowID  # The enum key that identifies this throw
    name: str          # Human-readable display name (e.g. "Seoi-nage")
    description: str   # One-line description for tooltips / log reference


# ---------------------------------------------------------------------------
# COMBO
# The global registry entry for a combo chain. Stores the ordered sequence of
# ThrowIDs and a chain_bonus — the probability boost applied when a judoka
# who has drilled this combo attempts the second throw after the first.
# ---------------------------------------------------------------------------
@dataclass
class Combo:
    """Global registry entry. Describes a two-throw chain sequence."""
    combo_id: ComboID          # The enum key that identifies this combo
    name: str                  # Human-readable name (e.g. "Ko-uchi → Seoi-nage")
    sequence: list[ThrowID]    # Ordered list: [opener, finisher]
    chain_bonus: float         # Extra chain probability (0.0–1.0) when this is a signature combo


# ---------------------------------------------------------------------------
# JUDOKA THROW PROFILE
# This lives in a judoka's Capability layer — it records how effective THAT
# specific fighter is with a given throw from their dominant side vs. off-side.
# Same throw, very different ratings for different fighters.
# ---------------------------------------------------------------------------
@dataclass
class JudokaThrowProfile:
    """Capability layer — per-judoka, per-throw effectiveness ratings."""
    throw_id: ThrowID              # Which throw this profile describes
    effectiveness_dominant: int    # 0–10: how good from the dominant (strong) side
    effectiveness_off_side: int    # 0–10: how good from the off (weak) side
    # Note: a true two-sided fighter might be 8/7 — rare. A one-dimensional
    # specialist (like Tanaka's seoi-nage) might be 9/3.


# ---------------------------------------------------------------------------
# THROW REGISTRY
# The global lookup table for all eight Phase 1 throws. Indexed by ThrowID.
# Add new throws here when expanding the vocabulary in later phases.
# ---------------------------------------------------------------------------
THROW_REGISTRY: dict[ThrowID, Throw] = {

    ThrowID.SEOI_NAGE: Throw(
        throw_id=ThrowID.SEOI_NAGE,
        name="Seoi-nage",
        description=(
            "Shoulder throw. Right-side entry; the attacker turns in, "
            "loads the opponent across the back, and lifts them over."
        ),
    ),

    ThrowID.UCHI_MATA: Throw(
        throw_id=ThrowID.UCHI_MATA,
        name="Uchi-mata",
        description=(
            "Inner thigh reap. The attacking leg sweeps up the inside of "
            "the opponent's thigh while pulling them forward and over."
        ),
    ),

    ThrowID.O_SOTO_GARI: Throw(
        throw_id=ThrowID.O_SOTO_GARI,
        name="O-soto-gari",
        description=(
            "Major outer reap. The attacker sweeps the opponent's outside "
            "leg from behind while driving them backward."
        ),
    ),

    ThrowID.O_UCHI_GARI: Throw(
        throw_id=ThrowID.O_UCHI_GARI,
        name="O-uchi-gari",
        description=(
            "Major inner reap. Hooks and reaps the inside of the opponent's "
            "right leg — excellent as a combo opener because it disturbs weight transfer."
        ),
    ),

    ThrowID.KO_UCHI_GARI: Throw(
        throw_id=ThrowID.KO_UCHI_GARI,
        name="Ko-uchi-gari",
        description=(
            "Minor inner reap. Small, fast reap of the opponent's ankle. "
            "Low commitment; its value is mostly as a setup for a follow-on throw."
        ),
    ),

    ThrowID.HARAI_GOSHI: Throw(
        throw_id=ThrowID.HARAI_GOSHI,
        name="Harai-goshi",
        description=(
            "Hip sweep. Hip-to-hip contact; the attacker's leg sweeps both "
            "of the opponent's legs while the hips act as a fulcrum."
        ),
    ),

    ThrowID.TAI_OTOSHI: Throw(
        throw_id=ThrowID.TAI_OTOSHI,
        name="Tai-otoshi",
        description=(
            "Body drop. No hip contact — the attacker blocks the opponent's "
            "lead leg and rotates them over. Natural finisher when harai-goshi is read."
        ),
    ),

    ThrowID.SUMI_GAESHI: Throw(
        throw_id=ThrowID.SUMI_GAESHI,
        name="Sumi-gaeshi",
        description=(
            "Corner sacrifice throw. Attacker falls backward, hooking the opponent's "
            "inner thigh with the foot and flipping them over. Especially effective "
            "in mirrored-stance matchups."
        ),
    ),
}


# ---------------------------------------------------------------------------
# COMBO REGISTRY
# Three drillable chains. Indexed by ComboID.
# 'chain_bonus' represents the probability boost for chaining the second throw
# when this combo is listed in a judoka's signature_combos. Non-signature
# attempts still have a base chain chance — just lower.
# ---------------------------------------------------------------------------
COMBO_REGISTRY: dict[ComboID, Combo] = {

    ComboID.KO_UCHI_TO_SEOI: Combo(
        combo_id=ComboID.KO_UCHI_TO_SEOI,
        name="Ko-uchi → Seoi-nage",
        sequence=[ThrowID.KO_UCHI_GARI, ThrowID.SEOI_NAGE],
        # The ankle reap forces the opponent to shift weight; that weight shift
        # creates the kuzushi window the shoulder throw needs.
        chain_bonus=0.25,  # +25% chain probability on top of base rate
    ),

    ComboID.O_UCHI_TO_UCHI_MATA: Combo(
        combo_id=ComboID.O_UCHI_TO_UCHI_MATA,
        name="O-uchi → Uchi-mata",
        sequence=[ThrowID.O_UCHI_GARI, ThrowID.UCHI_MATA],
        # Both throws attack the same side; the o-uchi draws the opponent's
        # weight onto the left foot, which is exactly where uchi-mata wants it.
        chain_bonus=0.30,  # Highest bonus — the kuzushi transfer is very clean
    ),

    ComboID.HARAI_TO_TAI_OTOSHI: Combo(
        combo_id=ComboID.HARAI_TO_TAI_OTOSHI,
        name="Harai-goshi → Tai-otoshi",
        sequence=[ThrowID.HARAI_GOSHI, ThrowID.TAI_OTOSHI],
        # If the opponent reads the harai and pulls their hips back, they walk
        # straight into tai-otoshi's blocking leg. A classic read-and-switch chain.
        chain_bonus=0.20,
    ),
}
