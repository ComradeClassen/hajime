# defense_decision.py
# HAJ-152 — uke's post-score defense decision.
#
# When tori chases ne-waza after a waza-ari, uke chooses among:
#
#   - SCRAMBLE         : try to escape to standing or to a neutral
#                        ne-waza position.
#   - DEFEND_BOTTOM    : hold a strong defensive position (turtle,
#                        half-guard, framing) and wait for matte.
#   - SWEEP_COUNTER    : counter-attack from a position where uke
#                        ended up on top (especially after sacrifice
#                        throws). Higher-IQ + ne-waza-skill required.
#   - ACCEPT_POSITION  : low-composure / high-fatigue uke defaults to
#                        a passive defensive shape, conceding the
#                        chase.
#
# The decision is probabilistic and attribute-driven. The factors are
# weighted per the HAJ-152 design notes; calibration is v0.2.

from __future__ import annotations
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

from enums import BodyArchetype, LandingProfile

if TYPE_CHECKING:
    from judoka import Judoka


# ---------------------------------------------------------------------------
# DEFENSE DECISION
# ---------------------------------------------------------------------------
class DefenseDecision(Enum):
    SCRAMBLE         = auto()
    DEFEND_BOTTOM    = auto()
    SWEEP_COUNTER    = auto()
    ACCEPT_POSITION  = auto()


# ---------------------------------------------------------------------------
# DEFENSE DECISION RESULT
# ---------------------------------------------------------------------------
@dataclass
class DefenseDecisionResult:
    """Output of make_defense_decision.

    `decision` is the chosen action; `factors` captures the per-component
    contributions for the engineering log so the test suite (and the
    debug overlay) can inspect why a decision came out the way it did.
    The decision is the highest-scoring branch, not a probability roll
    on a single axis — uke's options are qualitatively different and
    a softmax-style pick reads better than three sequential gates.
    """
    decision: DefenseDecision
    factors: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# TUNING
# ---------------------------------------------------------------------------
# Base scores (un-modulated, before per-component modifiers).
BASE_SCRAMBLE:        float = 0.50
BASE_DEFEND_BOTTOM:   float = 0.50
BASE_SWEEP_COUNTER:   float = 0.20
BASE_ACCEPT_POSITION: float = 0.10

# Composure floor — below this, ACCEPT_POSITION dominates regardless
# of other factors.
ACCEPT_COMPOSURE_FLOOR: float = 0.30

# Fatigue ceiling — above this, ACCEPT_POSITION is favored.
ACCEPT_FATIGUE_CEILING: float = 0.85

# Sweep-counter gates. Real bottom-game counters require both
# fight_iq and ne_waza_skill above a threshold; a sacrifice-throw
# landing where uke ended up on top opens the window.
SWEEP_MIN_IQ:        int = 6
SWEEP_MIN_NE_WAZA:   int = 5

# Per-archetype scramble bonus.
ARCHETYPE_SCRAMBLE_BONUS: dict[BodyArchetype, float] = {
    BodyArchetype.GROUND_SPECIALIST: +0.15,  # comfortable on the mat
    BodyArchetype.MOTOR:             +0.10,
    BodyArchetype.LEVER:             +0.00,
    BodyArchetype.EXPLOSIVE:         +0.05,
    BodyArchetype.GRIP_FIGHTER:      -0.05,
}

# Per-archetype defend-bottom bonus (mostly the inverse of scramble).
ARCHETYPE_DEFEND_BONUS: dict[BodyArchetype, float] = {
    BodyArchetype.GROUND_SPECIALIST: +0.20,  # patient bottom game
    BodyArchetype.MOTOR:             +0.00,
    BodyArchetype.LEVER:             +0.10,
    BodyArchetype.EXPLOSIVE:         +0.00,
    BodyArchetype.GRIP_FIGHTER:      +0.10,
}

# Match-context: a trailing uke who just got scored on faces clock
# pressure to escape; a leading uke can afford to defend bottom for
# matte.
TRAILING_SCRAMBLE_BONUS: float = +0.20
LEADING_DEFEND_BONUS:    float = +0.20


# ---------------------------------------------------------------------------
# MAKE DEFENSE DECISION
# ---------------------------------------------------------------------------
def make_defense_decision(
    uke: "Judoka",
    *,
    landing_profile: LandingProfile,
    score_diff_before: int,
    clock_remaining: int,
    tori_chasing: bool,
    rng: Optional[random.Random] = None,
) -> DefenseDecisionResult:
    """Pick uke's defense action after tori's chase decision.

    Args:
        uke: the scored-on fighter.
        landing_profile: the originating throw's landing profile.
            SACRIFICE landings can leave uke on top, opening the
            SWEEP_COUNTER window if uke has the attributes for it.
        score_diff_before: uke's score minus tori's score *before* the
            waza-ari was awarded. Negative means uke was trailing.
            (Note: argument is from uke's perspective so the asymmetric
            interpretation matches the chase_decision module's
            convention from tori's perspective.)
        clock_remaining: ticks left on the match clock.
        tori_chasing: whether tori chose CHASE / DEFENSIVE_CHASE. When
            tori stands, uke's only meaningful exit is also to stand;
            this bit short-circuits the score breakdown.
        rng: optional RNG (reserved for future tie-breaking; v0.1
            picks the highest-scoring branch deterministically).

    Returns:
        DefenseDecisionResult with the chosen action and the score
        breakdown by branch.
    """
    # If tori isn't chasing, uke's decision collapses: stand and wait
    # for matte. Surface as SCRAMBLE (i.e. get back to standing) so the
    # engineering event still carries a sensible label.
    if not tori_chasing:
        return DefenseDecisionResult(
            decision=DefenseDecision.SCRAMBLE,
            factors={"tori_not_chasing": 1.0},
        )

    composure_frac = (
        uke.state.composure_current
        / max(1.0, float(uke.capability.composure_ceiling))
    )
    body = uke.state.body
    fat_parts = ("right_leg", "left_leg", "right_hand", "left_hand")
    fatigues = [body[p].fatigue for p in fat_parts if p in body]
    avg_fat = sum(fatigues) / len(fatigues) if fatigues else 0.0

    score_scramble       = BASE_SCRAMBLE
    score_defend_bottom  = BASE_DEFEND_BOTTOM
    score_sweep_counter  = BASE_SWEEP_COUNTER
    score_accept         = BASE_ACCEPT_POSITION

    arch = uke.identity.body_archetype
    score_scramble      += ARCHETYPE_SCRAMBLE_BONUS.get(arch, 0.0)
    score_defend_bottom += ARCHETYPE_DEFEND_BONUS.get(arch, 0.0)

    # ne-waza skill raises both scramble and defend-bottom (skilled uke
    # picks the right move for the position; unskilled uke is more
    # likely to default to ACCEPT).
    skill = max(0, min(10, int(uke.capability.ne_waza_skill))) / 10.0
    score_scramble       += (skill - 0.5) * 0.20
    score_defend_bottom  += (skill - 0.5) * 0.20

    # Match context — uke trailing wants to escape; uke leading can
    # afford defense for matte.
    if score_diff_before > 0:
        # Uke was leading before this waza-ari (now tied or behind by 1).
        score_defend_bottom += LEADING_DEFEND_BONUS
    elif score_diff_before < 0:
        # Uke was trailing before this waza-ari — now further behind.
        # Still trailing → must escape and re-attack.
        score_scramble += TRAILING_SCRAMBLE_BONUS

    # Sweep-counter is gated. Available only after sacrifice throws
    # where uke landed on top, and only for high-IQ / high-skill uke.
    sweep_available = (
        landing_profile == LandingProfile.SACRIFICE
        and uke.capability.fight_iq      >= SWEEP_MIN_IQ
        and uke.capability.ne_waza_skill >= SWEEP_MIN_NE_WAZA
    )
    if sweep_available:
        score_sweep_counter += 0.30
        score_sweep_counter += (skill - 0.5) * 0.20
    else:
        # Strongly suppress sweep-counter when not available so it
        # doesn't accidentally win on tie-breakers.
        score_sweep_counter = -1.0

    # Accept-position gates: low composure or high fatigue. The
    # composure floor adds a strong baseline penalty; an even lower
    # composure (sub-half of the floor) compounds the penalty so a
    # truly panicked uke concedes regardless of archetype scramble
    # bonuses.
    if composure_frac < ACCEPT_COMPOSURE_FLOOR:
        score_accept += 0.40
        if composure_frac < ACCEPT_COMPOSURE_FLOOR / 2.0:
            score_accept += 0.40
            # Suppress the alternatives so accept dominates.
            score_scramble       -= 0.30
            score_defend_bottom  -= 0.30
    if avg_fat > ACCEPT_FATIGUE_CEILING:
        score_accept += 0.30

    factors = {
        "scramble":        score_scramble,
        "defend_bottom":   score_defend_bottom,
        "sweep_counter":   score_sweep_counter,
        "accept_position": score_accept,
    }

    # Pick the highest-scoring branch. Deterministic — rng reserved
    # for future tie-breaking.
    best_label, _ = max(factors.items(), key=lambda kv: kv[1])
    decision_map = {
        "scramble":        DefenseDecision.SCRAMBLE,
        "defend_bottom":   DefenseDecision.DEFEND_BOTTOM,
        "sweep_counter":   DefenseDecision.SWEEP_COUNTER,
        "accept_position": DefenseDecision.ACCEPT_POSITION,
    }
    return DefenseDecisionResult(
        decision=decision_map[best_label],
        factors=factors,
    )
