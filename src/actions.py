# actions.py
# Physics-substrate Part 3.2: the action space.
#
# A judoka's tick-action is a list of up to two Actions (plus an optional
# compound COMMIT_THROW that supersedes the two-action cap). Each Action
# is a discriminated union keyed by `kind`; unused fields stay None.
#
# Part 3 tick update consumes these in four buckets (matching spec 3.2):
#   - GRIP actions     : REACH / DEEPEN / STRIP / STRIP_TWO_ON_ONE / DEFEND_GRIP /
#                        REPOSITION_GRIP / RELEASE
#   - FORCE actions    : PULL / PUSH / LIFT / COUPLE / HOLD_CONNECTIVE / FEINT
#   - BODY actions     : STEP / PIVOT / DROP_COM / RAISE_COM / SWEEP_LEG /
#                        BLOCK_LEG / LOAD_HIP / ABSORB / BLOCK_HIP
#   - COMPOUND actions : COMMIT_THROW
#
# v0.1 implements the kinds we need to keep matches running end-to-end
# (REACH, DEEPEN, STRIP, RELEASE, PULL, PUSH, HOLD_CONNECTIVE, STEP, COMMIT_THROW).
# The remaining kinds are defined so that Parts 4–5 (worked throws) can add
# them without introducing new enum values mid-stream.

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple, TYPE_CHECKING

from enums import GripTypeV2, GripTarget
from throws import ThrowID

if TYPE_CHECKING:
    from grip_graph import GripEdge
    from commit_motivation import CommitMotivation


# ---------------------------------------------------------------------------
# ACTION KIND (Part 3.2)
# ---------------------------------------------------------------------------
class ActionKind(Enum):
    # Grip actions
    REACH            = auto()
    DEEPEN           = auto()
    STRIP            = auto()
    STRIP_TWO_ON_ONE = auto()
    DEFEND_GRIP      = auto()
    REPOSITION_GRIP  = auto()
    RELEASE          = auto()
    # Force actions
    PULL             = auto()
    PUSH             = auto()
    LIFT             = auto()
    COUPLE           = auto()
    HOLD_CONNECTIVE  = auto()
    FEINT            = auto()
    # Body actions
    STEP             = auto()
    PIVOT            = auto()
    DROP_COM         = auto()
    RAISE_COM        = auto()
    SWEEP_LEG        = auto()
    BLOCK_LEG        = auto()
    LOAD_HIP         = auto()
    ABSORB           = auto()
    BLOCK_HIP        = auto()        # HAJ-57 — uke's defensive hip drive (denies hip-loading throws)
    # HAJ-133 — FOOT_ATTACK action family. Per grip-as-cause.md §3.5,
    # foot attacks are a kuzushi-generating action family parallel to PULL,
    # not just terminal throws. They emit KuzushiEvents into uke's buffer
    # that compose with pulls to support foot-throw commits.
    FOOT_SWEEP_SETUP = auto()        # Probing sweep — lateral-down kuzushi.
    LEG_ATTACK_SETUP = auto()        # Ko-uchi/o-uchi probing — rear-corner kuzushi.
    DISRUPTIVE_STEP  = auto()        # Positional step that forces uke foot reaction.
    # Compound
    COMMIT_THROW     = auto()


# Kind-bucket helpers — used by the tick update to split a judoka's chosen
# actions into the four processing buckets.
GRIP_KINDS: frozenset[ActionKind] = frozenset({
    ActionKind.REACH, ActionKind.DEEPEN, ActionKind.STRIP,
    ActionKind.STRIP_TWO_ON_ONE, ActionKind.DEFEND_GRIP,
    ActionKind.REPOSITION_GRIP, ActionKind.RELEASE,
})
FORCE_KINDS: frozenset[ActionKind] = frozenset({
    ActionKind.PULL, ActionKind.PUSH, ActionKind.LIFT, ActionKind.COUPLE,
    ActionKind.HOLD_CONNECTIVE, ActionKind.FEINT,
})
BODY_KINDS: frozenset[ActionKind] = frozenset({
    ActionKind.STEP, ActionKind.PIVOT, ActionKind.DROP_COM,
    ActionKind.RAISE_COM, ActionKind.SWEEP_LEG, ActionKind.BLOCK_LEG,
    ActionKind.LOAD_HIP, ActionKind.ABSORB, ActionKind.BLOCK_HIP,
})
DRIVING_FORCE_KINDS: frozenset[ActionKind] = frozenset({
    ActionKind.PULL, ActionKind.PUSH, ActionKind.LIFT,
    ActionKind.COUPLE, ActionKind.FEINT,
})
# HAJ-133 — FOOT_ATTACK family. Used by match.py to dispatch foot-attack
# kuzushi emission alongside body-action processing. Distinct from BODY
# kinds so terminal throws (de-ashi-harai etc., which already exist as
# COMMIT_THROW) and foot-setup actions can be reasoned about separately.
FOOT_ATTACK_KINDS: frozenset[ActionKind] = frozenset({
    ActionKind.FOOT_SWEEP_SETUP,
    ActionKind.LEG_ATTACK_SETUP,
    ActionKind.DISRUPTIVE_STEP,
})

# HAJ-148 — substantive action kinds.
#
# An action is "substantive" if it gates the per-tick action ladder under the
# causal-tick-ordering rule: at most one substantive action per fighter per
# tick, with consequences resolving on tick N+1. Non-substantive actions
# (posture micro-adjustments, fatigue accumulation, prose markers, debug,
# referee personality observation) can co-occur freely.
#
# The ladder kinds that map to substantive (from the issue's list — grip
# seat / grip strip / grip change, PULL execution, FOOT_ATTACK execution,
# throw commit, defensive stuff/block/counter):
SUBSTANTIVE_KINDS: frozenset[ActionKind] = frozenset({
    # Grip changes — every grip action mutates the graph.
    ActionKind.REACH, ActionKind.DEEPEN, ActionKind.STRIP,
    ActionKind.STRIP_TWO_ON_ONE, ActionKind.DEFEND_GRIP,
    ActionKind.REPOSITION_GRIP, ActionKind.RELEASE,
    # Force — PULL is the canonical kuzushi-driving action; PUSH/LIFT/COUPLE
    # are not surfaced as their own substantive events in v0.1.
    ActionKind.PULL,
    # Foot attacks.
    ActionKind.FOOT_SWEEP_SETUP, ActionKind.LEG_ATTACK_SETUP,
    ActionKind.DISRUPTIVE_STEP, ActionKind.SWEEP_LEG,
    # Defensive blocks.
    ActionKind.BLOCK_HIP, ActionKind.BLOCK_LEG,
    # Throw commit.
    ActionKind.COMMIT_THROW,
})


# ---------------------------------------------------------------------------
# ACTION
# Flat discriminated union. Most fields are optional; which ones are valid
# depends on `kind`. The alternative (separate subclasses per kind) adds a
# lot of boilerplate for no tick-loop benefit.
# ---------------------------------------------------------------------------
@dataclass
class Action:
    kind: ActionKind
    hand: Optional[str] = None                           # "right_hand" / "left_hand"
    foot: Optional[str] = None                           # "right_foot" / "left_foot"
    direction: Optional[Tuple[float, float]] = None      # 2D unit vector (x, y)
    magnitude: float = 0.0                               # Newtons for force actions, meters for steps
    throw_id: Optional[ThrowID] = None                   # for COMMIT_THROW
    grip_type: Optional[GripTypeV2] = None               # for REACH
    target_location: Optional[GripTarget] = None         # for REACH / REPOSITION_GRIP
    edge: Optional["GripEdge"] = None                    # for DEEPEN / STRIP / DEFEND_GRIP / RELEASE
    is_feint: bool = False                               # FEINT marker (3.6)
    # HAJ-35/36 — desperation + gate-bypass metadata for COMMIT_THROW. Lets
    # Match surface "(desperation)" / "(gate bypassed: X)" on the commit
    # line without reconsulting the ladder.
    offensive_desperation: bool = False
    defensive_desperation: bool = False
    gate_bypass_reason: Optional[str] = None             # non-None only when the gate was bypassed
    gate_bypass_kind: Optional[str] = None               # "offensive" | "defensive" | None
    # HAJ-67 — non-scoring commit motivation (CLOCK_RESET, GRIP_ESCAPE,
    # SHIDO_FARMING, STAMINA_DESPERATION). None for normal and desperation
    # commits. See src/commit_motivation.py. Replaces the HAJ-49
    # `intentional_false_attack: bool` (the legacy flag collapses to
    # `commit_motivation == CommitMotivation.CLOCK_RESET`).
    commit_motivation: Optional["CommitMotivation"] = None
    # HAJ-156 — tactical / strategic intent attached to STEP actions.
    # One of the TACTICAL_INTENT_* constants. The action selector
    # classifies the chosen step's intent (PRESSURE / GIVE_GROUND /
    # CIRCLE / HOLD_CENTER), and the new strategic-intent layer can tag
    # GAIN_ANGLE / RUN_CLOCK / CATCH_BREATH / BAIT / CATCH_MOMENT.
    # Surfaced on the MOVE engine event so prose / viewer / HAJ-149
    # perception can read what kind of step it was.
    tactical_intent: Optional[str] = None

    @property
    def intentional_false_attack(self) -> bool:
        """HAJ-49 compatibility shim — any non-scoring motivation counts
        as an intentional false attack from the physics/failure-routing
        perspective. The specific motivation is on `commit_motivation`."""
        return self.commit_motivation is not None


# ---------------------------------------------------------------------------
# CONVENIENCE CONSTRUCTORS
# ---------------------------------------------------------------------------
def reach(hand: str, grip_type: GripTypeV2, target: GripTarget) -> Action:
    return Action(kind=ActionKind.REACH, hand=hand,
                  grip_type=grip_type, target_location=target)

def deepen(edge: "GripEdge") -> Action:
    return Action(kind=ActionKind.DEEPEN, edge=edge,
                  hand=edge.grasper_part.value)

def strip(hand: str, opponent_edge: "GripEdge") -> Action:
    return Action(kind=ActionKind.STRIP, hand=hand, edge=opponent_edge)

def release(edge: "GripEdge") -> Action:
    return Action(kind=ActionKind.RELEASE, edge=edge,
                  hand=edge.grasper_part.value)

def pull(hand: str, direction: Tuple[float, float], magnitude: float) -> Action:
    return Action(kind=ActionKind.PULL, hand=hand,
                  direction=direction, magnitude=magnitude)

def push(hand: str, direction: Tuple[float, float], magnitude: float) -> Action:
    return Action(kind=ActionKind.PUSH, hand=hand,
                  direction=direction, magnitude=magnitude)

def hold_connective(hand: str) -> Action:
    return Action(kind=ActionKind.HOLD_CONNECTIVE, hand=hand)

def feint(hand: str, direction: Tuple[float, float], magnitude: float) -> Action:
    return Action(kind=ActionKind.FEINT, hand=hand,
                  direction=direction, magnitude=magnitude, is_feint=True)

def step(
    foot: str, direction: Tuple[float, float], magnitude: float,
    *, tactical_intent: Optional[str] = None,
) -> Action:
    return Action(kind=ActionKind.STEP, foot=foot,
                  direction=direction, magnitude=magnitude,
                  tactical_intent=tactical_intent)


# ---------------------------------------------------------------------------
# HAJ-156 — TACTICAL & STRATEGIC MOVEMENT INTENTS
# ---------------------------------------------------------------------------
# Tactical intents classify what kind of step the fighter is taking.
# Layered on top of HAJ-128's PositionalStyle (HOLD_CENTER / PRESSURE /
# DEFENSIVE_EDGE) which is a fighter-level disposition — the per-tick
# step also carries one of these intents so the engine event log,
# prose narration, and HAJ-149 perception layer can all see the kind
# of step that was taken on this specific tick.
#
# Edge-relative tactical intents (extend HAJ-128's three styles):
TACTICAL_INTENT_PRESSURE     = "pressure"        # advance into opponent
TACTICAL_INTENT_GIVE_GROUND  = "give_ground"     # retreat
TACTICAL_INTENT_CIRCLE       = "circle"          # lateral angle-finding
TACTICAL_INTENT_HOLD_CENTER  = "hold_center"     # anchor / re-center

# Strategic intents — additive, not edge-driven (per HAJ-156 review
# comment). Composable with the tactical intents above; a step may be
# `circle` tactically AND `gain_angle` strategically. v0.1 surfaces
# them as the per-step intent label; the perception / counter layer is
# follow-up work.
TACTICAL_INTENT_GAIN_ANGLE   = "gain_angle"      # lateral for attack line
TACTICAL_INTENT_RUN_CLOCK    = "run_clock"       # leading + late match
TACTICAL_INTENT_CATCH_MOMENT = "catch_moment"    # close on a posture break
TACTICAL_INTENT_BAIT         = "bait"            # expose to draw attack
TACTICAL_INTENT_CATCH_BREATH = "catch_breath"    # cardio-recovery shuffle

# Set of all known intents. Used by tests and the viewer state pill.
TACTICAL_INTENTS = frozenset({
    TACTICAL_INTENT_PRESSURE,
    TACTICAL_INTENT_GIVE_GROUND,
    TACTICAL_INTENT_CIRCLE,
    TACTICAL_INTENT_HOLD_CENTER,
    TACTICAL_INTENT_GAIN_ANGLE,
    TACTICAL_INTENT_RUN_CLOCK,
    TACTICAL_INTENT_CATCH_MOMENT,
    TACTICAL_INTENT_BAIT,
    TACTICAL_INTENT_CATCH_BREATH,
})


# HAJ-133 — FOOT_ATTACK family constructors. Each takes the attacking
# foot ("right_foot" / "left_foot") and a 2D direction vector in the mat
# frame indicating the *attack vector* (where the sweeping leg or step
# is going). Magnitude is in meters of foot motion, parallel to STEP, and
# is also used by the kuzushi-event emitter to scale event magnitude.
def foot_sweep_setup(
    foot: str, direction: Tuple[float, float], magnitude: float = 0.25,
) -> Action:
    """Probing foot sweep — emits a low-magnitude lateral-down KuzushiEvent
    into uke's buffer. Sweeping leg lifts off the mat for the duration of
    the action; HAJ-134 will declare the formal exposure window."""
    return Action(kind=ActionKind.FOOT_SWEEP_SETUP, foot=foot,
                  direction=direction, magnitude=magnitude)


def leg_attack_setup(
    foot: str, direction: Tuple[float, float], magnitude: float = 0.25,
) -> Action:
    """Ko-uchi / o-uchi-style probing leg attack — emits a rear-corner
    KuzushiEvent. Attacker briefly stands on one foot."""
    return Action(kind=ActionKind.LEG_ATTACK_SETUP, foot=foot,
                  direction=direction, magnitude=magnitude)


def disruptive_step(
    foot: str, direction: Tuple[float, float], magnitude: float = 0.25,
) -> Action:
    """Intentional positional step that forces uke foot reaction. The
    kuzushi vector emitted is opposite the attacker's step direction —
    uke's CoM yields the way the attacker pushed past."""
    return Action(kind=ActionKind.DISRUPTIVE_STEP, foot=foot,
                  direction=direction, magnitude=magnitude)


def block_hip() -> Action:
    """HAJ-57 — uke's defensive hip-drive-forward block.

    Denies tori the geometry of any in-progress hip-loading throw (a throw
    whose body_part_requirement.hip_loading is True). Resolved Match-side
    against tori's mid-flight attempt; the throw fails into a stance reset
    and the dyad falls back to grip battle. Posture-gated at action-
    selection time: a bent-over uke (trunk_sagittal > 0) cannot generate
    the forward hip drive."""
    return Action(kind=ActionKind.BLOCK_HIP)

def commit_throw(
    throw_id: ThrowID,
    *,
    offensive_desperation: bool = False,
    defensive_desperation: bool = False,
    gate_bypass_reason: Optional[str] = None,
    gate_bypass_kind: Optional[str] = None,
    commit_motivation: Optional["CommitMotivation"] = None,
) -> Action:
    return Action(
        kind=ActionKind.COMMIT_THROW, throw_id=throw_id,
        offensive_desperation=offensive_desperation,
        defensive_desperation=defensive_desperation,
        gate_bypass_reason=gate_bypass_reason,
        gate_bypass_kind=gate_bypass_kind,
        commit_motivation=commit_motivation,
    )
