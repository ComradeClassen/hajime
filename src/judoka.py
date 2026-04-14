# judoka.py
# Defines the three-layer Judoka model: Identity, Capability, and State.
# These three dataclasses are composed into a single Judoka object.
#
# The key design principle: keep the layers structurally separate.
# Identity = who they are (static).
# Capability = what they can do when fresh (changes slowly via dojo training).
# State = what's true right now in this match (resets each match).
#
# This separation is what lets the same fighter have a great match one day
# and a terrible one the next: same Capability, different State trajectory.

from __future__ import annotations       # allows forward references in type hints
from dataclasses import dataclass, field # 'field' lets us specify defaults for mutable types
from typing import Optional              # Optional[X] means the value can be X or None

# Import all enums from the shared enums module
from enums import (
    BodyArchetype, BeltRank, DominantSide,
    Position, Posture, Stance, EmotionalState,
)
# Import throw/combo types from the throws module
from throws import ThrowID, ComboID, JudokaThrowProfile


# ---------------------------------------------------------------------------
# BODY PARTS LIST
# A single source of truth for all 15 body part names. Both Capability (which
# stores integer scores) and State (which tracks fatigue/injury) reference this
# list to stay in sync. If we ever add a 16th part, we add it here and both
# layers automatically pick it up.
# ---------------------------------------------------------------------------
BODY_PARTS: list[str] = [
    # Hands — grip security and finger strength
    "right_hand",   "left_hand",
    # Forearms — grip endurance and pulling power
    "right_forearm", "left_forearm",
    # Biceps — pulling strength, frame-breaking
    "right_bicep",  "left_bicep",
    # Shoulders — throw entry, posture maintenance
    "right_shoulder", "left_shoulder",
    # Legs — throw power and defensive base
    "right_leg",    "left_leg",
    # Feet — footwork precision and sweep accuracy
    "right_foot",   "left_foot",
    # Core — rotational power and posture stability
    "core",
    # Lower back — throw lift and posture defense
    "lower_back",
    # Neck — resistance to forward-bend kuzushi
    "neck",
]  # 15 parts total — confirmed against spec


# ---------------------------------------------------------------------------
# AGE MODIFIER (STUB)
# In Phase 2+, each attribute cluster follows its own peak-and-decline curve.
# For example: explosive power peaks at 24-28, fight IQ keeps climbing into
# the mid-30s, grip strength holds late but recovery rate declines from 25+.
# For Phase 1, this stub returns 1.0 for everything — no age effect yet.
# Real curves get added and tuned once we can watch matches and calibrate.
# ---------------------------------------------------------------------------
def age_modifier(attribute_name: str, age: int) -> float:
    """Phase 1 stub: returns 1.0 for all attributes and ages.

    Phase 2 will replace this with real bell curves per attribute cluster,
    based on the table in data-model.md (fight IQ peaks 30-35+, explosive
    power peaks 24-28, recovery rate declines from 25, etc.).
    """
    return 1.0  # No age adjustment yet — everyone performs at their raw baseline


# ---------------------------------------------------------------------------
# EFFECTIVE CAPABILITY HELPER
# Computes the age-adjusted capability value for a given attribute.
# Called at runtime rather than pre-computed, so that changing a judoka's age
# (e.g., across a multi-year career) automatically updates their effective stats.
# ---------------------------------------------------------------------------
def effective_capability(attribute_name: str, base_value: int, age: int) -> float:
    """Returns base_value scaled by the age modifier for that attribute."""
    modifier = age_modifier(attribute_name, age)  # currently always 1.0
    return base_value * modifier                  # result is float for consistency


# ===========================================================================
# LAYER 1 — IDENTITY
# Who the judoka IS. Static or near-static across a career.
# These values shape how Capability and State behave, but they don't store
# combat stats themselves. The archetype, dominant side, and personality
# are the 'DNA' that the simulation interprets.
# ===========================================================================
@dataclass
class Identity:
    """Identity layer — static attributes that define who this judoka is.

    These don't change tick-to-tick or even match-to-match. They shift slowly
    across a career (e.g., age increments annually, belt rank progresses).
    """
    name: str              # Display name used in the match log
    age: int               # 16–40; feeds the age modifier system
    weight_class: str      # e.g. "-90kg"; Phase 1 hardcodes everyone to -90kg
    height_cm: int         # 165–195; affects throw success biases in Phase 2
    body_archetype: BodyArchetype   # Primary fighting style (LEVER, MOTOR, etc.)
    belt_rank: BeltRank             # Determines throw vocabulary size ceiling
    dominant_side: DominantSide     # RIGHT or LEFT; drives the grip asymmetry system

    # Personality facets — each is a 0–10 sliding scale between two poles.
    # 0 = the left pole, 10 = the right pole.
    # Example: aggressive=2 means closer to "aggressive"; aggressive=8 means "patient".
    # These bias decision-making in close calls during combat (Phase 2+).
    personality_facets: dict[str, int] = field(default_factory=dict)
    # Keys: "aggressive" (0=aggressive ↔ 10=patient)
    #       "technical"  (0=technical  ↔ 10=athletic)
    #       "confident"  (0=confident  ↔ 10=anxious)
    #       "loyal_to_plan" (0=loyal   ↔ 10=improvisational)


# ===========================================================================
# LAYER 2 — CAPABILITY
# What this judoka's body and mind can do at their BEST — when unfatigued
# and uninjured. These values change slowly through dojo training (Ring 3+).
# Each value represents the maximum possible performance for that attribute.
#
# At runtime: effective = capability × age_modifier × (1 - fatigue)
# ===========================================================================
@dataclass
class Capability:
    """Capability layer — maximum physical and mental performance when fully fresh.

    Values on a 0–10 scale. 10 = world-class for that attribute.
    5 = solid club-level. 2 = an exploitable weak point.
    These persist between matches and change only through dojo training.
    """
    # --- BODY PARTS (0–10 each) ---
    # Declared individually (not as a dict) so they're named, type-safe, and
    # easy to assign specific values when hand-building a judoka in main.py.

    # Hands: grip security and finger strength
    right_hand: int
    left_hand: int

    # Forearms: grip endurance; how long they can hold under pulling resistance
    right_forearm: int
    left_forearm: int

    # Biceps: pulling strength; used to break an opponent's frame or posture
    right_bicep: int
    left_bicep: int

    # Shoulders: throw entry power and posture maintenance during engagement
    right_shoulder: int
    left_shoulder: int

    # Legs: the engine for throw power and the first line of defensive balance
    right_leg: int
    left_leg: int

    # Feet: footwork precision and sweeping accuracy (ko-uchi-gari, de-ashi-barai, etc.)
    right_foot: int
    left_foot: int

    # Core: rotational power (seoi-nage, harai-goshi) and posture stability
    core: int

    # Lower back: lift strength for throws and resistance to forward kuzushi
    lower_back: int

    # Neck: resistance to the opponent bending them forward into broken posture
    neck: int

    # --- CARDIO (global, not per-body-part) ---
    # Cardio is lung and heart — it affects recovery rate for every body part.
    cardio_capacity: int   # Total endurance pool; how long they last at full output
    cardio_efficiency: int # How slowly cardio drains under sustained load

    # --- MIND ---
    composure_ceiling: int  # Max composure when calm; State.composure_current starts here
    fight_iq: int           # Read speed, combo recognition, opening detection
    ne_waza_skill: int      # Ground work competence — separate from standing technique

    # --- THROW VOCABULARY ---
    # throw_vocabulary: every throw this judoka knows at all (can attempt)
    throw_vocabulary: list[ThrowID] = field(default_factory=list)

    # throw_profiles: per-throw effectiveness ratings from each side
    # Maps ThrowID → JudokaThrowProfile (dominant/off-side effectiveness)
    throw_profiles: dict[ThrowID, JudokaThrowProfile] = field(default_factory=dict)

    # signature_throws: the 2–4 throws they've truly specialised in
    # These get bonus success rates in Phase 2 combat rolls
    signature_throws: list[ThrowID] = field(default_factory=list)

    # signature_combos: drilled chains; these chain at higher probability than
    # non-signature combos when the opener partially lands
    signature_combos: list[ComboID] = field(default_factory=list)


# ===========================================================================
# STATE — BODY PART STATE
# A small dataclass for per-body-part runtime tracking.
# One BodyPartState exists for each of the 15 body parts during a match.
# ===========================================================================
@dataclass
class BodyPartState:
    """Tracks the real-time condition of one body part during a match."""
    fatigue: float = 0.0   # 0.0 = completely fresh; 1.0 = completely cooked
    injured: bool  = False  # True if a serious event (throw impact, twist) hit this part
    # When injured=True, the effective contribution of this part is capped at 30%:
    #   effective = capability_age_modified × (1 - fatigue) × (0.3 if injured else 1.0)


# ===========================================================================
# LAYER 3 — STATE
# Everything that is true RIGHT NOW, in THIS match.
# Initialized fresh from Capability at the start of each match.
# Updated every tick. Fully resets before the next match
# (with one exception: Tournament Carryover, a Ring 2+ feature).
# ===========================================================================
@dataclass
class State:
    """State layer — the live, moment-to-moment condition of a judoka in a match.

    This layer is volatile: it changes constantly during a match and is
    (mostly) discarded afterward. The same Capability can produce a wildly
    different State trajectory depending on opponent, fatigue trajectory, and
    coach instructions.
    """
    # --- BODY STATE ---
    # One BodyPartState per body part, keyed by the part's name string.
    # Using a dict here (rather than named fields) so the tick loop can
    # update parts by name: state.body["right_hand"].fatigue += 0.002
    body: dict[str, BodyPartState]

    # --- CARDIO STATE ---
    cardio_current: float  # Starts at 1.0 (full), depletes with sustained action
                           # Cardio drain is a global tax — it slows recovery for all body parts

    # --- MIND STATE ---
    composure_current: float        # Starts at composure_ceiling; drops after stuffed throws,
                                    # scoring events, or being dominated in the grip war
    last_event_emotional_weight: float  # A spike value; decays over ticks. Large events
                                        # (being thrown for waza-ari) cause a bigger spike.

    # --- MATCH POSITION STATE ---
    position: Position   # Where in the match space the judoka currently is
    posture: Posture     # How upright they are right now (broken posture = vulnerable)
    current_stance: Stance  # Can switch mid-match via a coach instruction

    # --- GRIP STATE ---
    # Which hand has what grip on which part of the opponent's gi.
    # Empty dict in Phase 1 — populated in Phase 2 when the grip graph is built.
    grip_configuration: dict  # e.g. {"right": "collar", "left": "sleeve"}

    # --- SCORING ---
    score: dict   # {"waza_ari": 0, "ippon": False} — IJF scoring
    shidos: int   # Penalty count; 3 = hansoku-make (disqualification)

    # --- INSTRUCTION TRACKING ---
    # The most recent coach instruction, and how cleanly it's being executed.
    # reception = composure × trust × fight_iq × (1 - fatigue) — computed in Phase 3.
    recent_events: list        # Last N tick events; used for short-term decision context
    current_instruction: str   # Biases decision-making until overwritten
    instruction_received_strength: float  # 0.0 = ignored; 1.0 = executing perfectly

    # --- RING 2+ HOOKS ---
    # These fields are declared now so the data model is complete from day one.
    # They are NOT used in Phase 1 — the simulation doesn't read them yet.

    # Trust and relationship with the coach — grows slowly over dojo time (Ring 3+)
    relationship_with_sensei: dict  # keys: chair_time_received, chair_time_denied,
                                    #       perceived_priority, loyalty (0.0–10.0)

    # Tournament carryover — fatigue that doesn't fully recover between matches
    # on the same tournament day. A key reason veterans fade in semi-finals.
    matches_today: int                      # How many matches they've fought today
    cumulative_fatigue_debt: dict[str, float]  # Residual fatigue per body part
    emotional_state_from_last_match: Optional[EmotionalState]  # None = fresh day

    # ---------------------------------------------------------------------------
    # CLASS METHOD: fresh()
    # Creates a brand-new State initialized from a Capability, as if the judoka
    # is walking onto the mat for a first match of the day, fully rested.
    # In Ring 2+, a second classmethod (from_residual) will initialize from
    # a previous match's leftover fatigue instead.
    # ---------------------------------------------------------------------------
    @classmethod
    def fresh(cls, capability: Capability) -> "State":
        """Initialize a clean match-start State from the judoka's Capability.

        All body parts start at 0.0 fatigue (fresh). Cardio starts at 1.0 (full).
        Composure starts at its ceiling. Position is STANDING_DISTANT.
        """
        return cls(
            # Build the body dict: one fresh BodyPartState for every named body part
            body={part: BodyPartState() for part in BODY_PARTS},
            # Cardio starts full
            cardio_current=1.0,
            # Composure starts at its maximum ceiling value
            composure_current=float(capability.composure_ceiling),
            # No emotional events have happened yet
            last_event_emotional_weight=0.0,
            # Both judoka start distant — grips not yet established
            position=Position.STANDING_DISTANT,
            posture=Posture.UPRIGHT,
            current_stance=Stance.ORTHODOX,  # everyone starts orthodox; switch via instruction
            # No grips established yet
            grip_configuration={},
            # Zero score
            score={"waza_ari": 0, "ippon": False},
            shidos=0,
            # No events have happened yet
            recent_events=[],
            current_instruction="",
            instruction_received_strength=0.0,
            # Ring 2+ fields: empty/zero for now
            relationship_with_sensei={},
            matches_today=0,
            cumulative_fatigue_debt={part: 0.0 for part in BODY_PARTS},
            emotional_state_from_last_match=None,  # None = no previous match today
        )


# ===========================================================================
# JUDOKA
# The top-level object that composes all three layers.
# Everything the simulation needs to know about a fighter lives here —
# accessed as judoka.identity, judoka.capability, or judoka.state.
# ===========================================================================
@dataclass
class Judoka:
    """A complete judoka: Identity + Capability + State composed into one object.

    The match engine reads from all three layers every tick:
    - Identity tells it *who* is fighting (archetype, dominant side, personality)
    - Capability tells it *what they can do at their best*
    - State tells it *what's true right now* (fatigue, posture, composure)
    """
    identity: Identity      # Layer 1 — static/slow: name, archetype, age, dominant side
    capability: Capability  # Layer 2 — dojo-trained: body scores, throw vocabulary
    state: State            # Layer 3 — match-volatile: fatigue, composure, position

    def effective_body_part(self, part: str) -> float:
        """Compute the effective strength of one body part right now.

        Combines all three layers into a single runtime value:
            base_capability × age_modifier × (1 - fatigue) × injury_multiplier

        This is the value the Phase 2 combat system will use for throw success rolls.
        A 9-rated right_hand with 0.4 fatigue on a 26-year-old:
            9 × 1.0 × (1 - 0.4) × 1.0 = 5.4
        """
        # Pull the raw capability score for this body part by name
        base = getattr(self.capability, part)

        # Apply the age modifier (currently always 1.0 — stub for Phase 2)
        age_mod = age_modifier(part, self.identity.age)

        # Read current fatigue for this part from State
        fatigue = self.state.body[part].fatigue

        # If injured, the part contributes only 30% of its potential
        injured_multiplier = 0.3 if self.state.body[part].injured else 1.0

        # Combine everything into one effective float
        return base * age_mod * (1.0 - fatigue) * injured_multiplier
