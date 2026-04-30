# chase_decision.py
# HAJ-152 — tori's post-score chase decision.
#
# After a non-match-ending waza-ari award, tori chooses between three
# follow-up actions:
#
#   - CHASE         : drop into ne-waza, transition to a top position
#                     (GUARD_TOP / SIDE_CONTROL / etc.) and look for
#                     osaekomi or a sub.
#   - STAND         : get back to standing, prepare for tachi-waza
#                     re-engagement after an explicit matte.
#   - DEFENSIVE_CHASE: only available after sacrifice throws — tori is
#                     on the bottom; rather than retreating, tori plays
#                     bottom-game defense while the engagement remains
#                     live.
#
# The decision is probabilistic and attribute-driven. The factors are
# weighted per the HAJ-152 design notes; calibration is v0.2 against
# match telemetry.

from __future__ import annotations
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

from enums import BodyArchetype, LandingProfile

if TYPE_CHECKING:
    from judoka import Judoka
    from throws import ThrowID


# ---------------------------------------------------------------------------
# CHASE DECISION
# ---------------------------------------------------------------------------
class ChaseDecision(Enum):
    CHASE            = auto()
    STAND            = auto()
    DEFENSIVE_CHASE  = auto()


# ---------------------------------------------------------------------------
# CHASE DECISION RESULT
# ---------------------------------------------------------------------------
@dataclass
class ChaseDecisionResult:
    """Output of make_chase_decision.

    `decision` is the chosen action; `probability` is the chase
    probability that was rolled against (CHASE / DEFENSIVE_CHASE
    threshold); `factors` captures the per-component contributions for
    the engineering log so the test suite (and the debug overlay) can
    inspect why a decision came out the way it did.
    """
    decision: ChaseDecision
    probability: float
    factors: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# TUNING — calibration stubs (v0.2 will tune against simulation)
# ---------------------------------------------------------------------------
# Base chase probability for a neutral fighter on a neutral throw.
CHASE_BASE: float = 0.50

# Weight on `post_score_chase_advantage` field of the throw.
W_THROW_ADVANTAGE: float = 0.40

# Weight on tori's ne-waza skill (0–10 scaled to 0–1).
W_NE_WAZA_SKILL: float = 0.25

# Per-archetype additive bonus (or penalty) on chase probability.
ARCHETYPE_BONUS: dict[BodyArchetype, float] = {
    BodyArchetype.GROUND_SPECIALIST: +0.30,
    BodyArchetype.MOTOR:             +0.05,
    BodyArchetype.LEVER:             +0.00,
    BodyArchetype.EXPLOSIVE:         +0.05,
    BodyArchetype.GRIP_FIGHTER:      -0.05,
}

# Personality-facet weights. `aggressive` raises chase; `confident`
# raises chase; both 0–10 scaled to ±0.10 around baseline.
W_AGGRESSIVE: float = 0.10
W_CONFIDENT:  float = 0.10

# Fatigue penalty: tired legs / hands / cardio eat the chase.
W_FATIGUE:    float = 0.20

# Match-context modifiers (applied additively after base computation).
TRAILING_BONUS:  float = +0.15  # tori behind on score before this waza-ari
LEADING_PENALTY: float = -0.20  # tori ahead on score before this waza-ari

# Clock-pressure modifiers (HAJ-151's clock-pressure pattern).
CLOCK_LOW_TICKS:           int   = 30   # last 30 seconds of regulation
CLOCK_LOW_TRAILING_BONUS:  float = +0.40  # urgency
CLOCK_LOW_LEADING_PENALTY: float = -0.40  # run the clock


# ---------------------------------------------------------------------------
# MAKE CHASE DECISION
# ---------------------------------------------------------------------------
def make_chase_decision(
    tori: "Judoka",
    throw_id: "ThrowID",
    *,
    landing_profile: LandingProfile,
    chase_advantage: float,
    score_diff_before: int,
    clock_remaining: int,
    rng: Optional[random.Random] = None,
) -> ChaseDecisionResult:
    """Pick CHASE / STAND / DEFENSIVE_CHASE for tori after a waza-ari.

    Args:
        tori: the scorer.
        throw_id: the throw that just scored (for the engineering event).
        landing_profile: the throw's landing profile. SACRIFICE routes
            chase outcomes to DEFENSIVE_CHASE (tori is on the bottom).
        chase_advantage: the throw's `post_score_chase_advantage` value
            (0.0–1.0). Higher → more chase pressure.
        score_diff_before: tori's score minus uke's score *before* this
            waza-ari was awarded. Negative means tori was trailing.
        clock_remaining: ticks left on the match clock.
        rng: explicit RNG for reproducibility; falls back to the module
            random.

    Returns:
        ChaseDecisionResult with the chosen action, the rolled
        probability, and the factor breakdown for the engineering log.
    """
    r = rng if rng is not None else random

    factors: dict[str, float] = {}
    factors["base"] = CHASE_BASE

    # Throw-class chase advantage — single biggest factor, centered
    # around 0.5 so a neutral 0.5 advantage is a no-op.
    advantage_mod = (chase_advantage - 0.5) * W_THROW_ADVANTAGE * 2.0
    factors["throw_advantage"] = advantage_mod

    # Tori's ne-waza skill (0–10 → 0–1, centered).
    skill = max(0, min(10, int(tori.capability.ne_waza_skill))) / 10.0
    skill_mod = (skill - 0.5) * W_NE_WAZA_SKILL * 2.0
    factors["ne_waza_skill"] = skill_mod

    # Archetype.
    arch_bonus = ARCHETYPE_BONUS.get(tori.identity.body_archetype, 0.0)
    factors["archetype"] = arch_bonus

    # Personality facets (0–10 scaled to ±W).
    facets = tori.identity.personality_facets
    aggressive = max(0, min(10, int(facets.get("aggressive", 5))))
    confident  = max(0, min(10, int(facets.get("confident",  5))))
    factors["aggressive"] = (aggressive - 5) / 5.0 * W_AGGRESSIVE
    factors["confident"]  = (confident  - 5) / 5.0 * W_CONFIDENT

    # Fatigue penalty — average of leg/hand fatigue, weighted by W_FATIGUE.
    body = tori.state.body
    fat_parts = ("right_leg", "left_leg", "right_hand", "left_hand")
    fatigues = [body[p].fatigue for p in fat_parts if p in body]
    avg_fat = sum(fatigues) / len(fatigues) if fatigues else 0.0
    factors["fatigue"] = -avg_fat * W_FATIGUE

    # Match-context: trailing → urgency; leading → safety.
    if score_diff_before < 0:
        factors["match_context"] = TRAILING_BONUS
    elif score_diff_before > 0:
        factors["match_context"] = LEADING_PENALTY
    else:
        factors["match_context"] = 0.0

    # Clock-pressure (HAJ-151 pattern). Low-clock + trailing now wants
    # to convert the waza-ari to ippon; low-clock + leading wants to
    # run out the clock standing.
    score_diff_after = score_diff_before + 1  # this waza-ari just landed
    if clock_remaining <= CLOCK_LOW_TICKS:
        if score_diff_after <= 0:
            # Still tied or trailing after this score — push for ippon.
            factors["clock_pressure"] = CLOCK_LOW_TRAILING_BONUS
        else:
            # Now leading — run the clock.
            factors["clock_pressure"] = CLOCK_LOW_LEADING_PENALTY
    else:
        factors["clock_pressure"] = 0.0

    probability = sum(factors.values())
    probability = max(0.02, min(0.98, probability))

    # Roll. SACRIFICE landing profile routes positive rolls to
    # DEFENSIVE_CHASE — tori is on the bottom and can't do a clean
    # forward chase, but the engagement is still live and tori's
    # bottom game keeps it going.
    rolled = r.random()
    if rolled < probability:
        if landing_profile == LandingProfile.SACRIFICE:
            decision = ChaseDecision.DEFENSIVE_CHASE
        else:
            decision = ChaseDecision.CHASE
    else:
        decision = ChaseDecision.STAND

    return ChaseDecisionResult(
        decision=decision,
        probability=probability,
        factors=factors,
    )
