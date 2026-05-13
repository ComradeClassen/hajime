# resolver.py
# Ring 2 abstracted match resolver (HAJ-201).
#
# Collapses a full match between two judoka into a single MatchOutcome
# chronicle entry. The deep engine in src/match.py is too expensive to run
# for every off-screen match across 66 simulated years; this resolver runs
# in microseconds per match and produces results consistent enough with the
# deep engine that the world feels coherent across the boundary.
#
# Implements:
#   - Ring2Judoka — abstract judoka representation (four base stats +
#     vocabulary + precomputed signals)
#   - MatchContext — tournament, year, era, rules-version, round number
#   - PrecomputedSignals — top-5, breadth, defensive specialty, ledger
#     breadth, legendary flags
#   - signature_strength() — derived per the Section 10 formula
#   - precompute_signals() — refreshed when vocabulary changes (rare event)
#   - resolve() — naive weighted sum + Gaussian noise → MatchOutcome
#
# Schema is locked by:
#   - design-notes/ring-2-worldgen-spec-v2.md Part II ("The abstracted match
#     resolver")
#   - design-notes/triage/technique-vocabulary-system.md Section 10
#     ("Resolver input mapping") — the canonical signature_strength formula
#   - design-notes/triage/technique-vocabulary-system.md Section 7
#     (legendary modifiers — composure dip and finish-quality bonus)
#
# Out of scope for this ticket (deferred per HAJ-201):
#   - Calibration corpus and side-by-side comparison with the deep engine
#   - Era-specific behaviour (1.0 stamps era but treats matches as
#     modern-rules; era_filter is a no-op stub)
#   - Stage 1 / Stage 2 grip-and-kuzushi resolution (deep-engine concern)
#   - In-match injury / condition changes

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import log
from random import Random
from typing import Optional

from chronicle import (
    DurationBand,
    MatchOutcome,
    ScoreType,
)
from technique_catalog import (
    PROFICIENCY_ORDER,
    ProficiencyTier,
    TechniqueDefinition,
    TechniqueFamily,
    TechniqueRecord,
)


# ===========================================================================
# CONSTANTS
# These are first-draft tuning values. Section 11 of the vocabulary system
# doc names calibration as deferred work; keep them in one place so the
# downstream calibration ticket can sweep them without scattered edits.
# ===========================================================================
# Four base dimensions plus signature strength, equal weights per the
# ticket's "Out-of-the-box weights: equal across the five" mandate.
DIMENSION_WEIGHTS: tuple[float, float, float, float, float] = (0.2, 0.2, 0.2, 0.2, 0.2)

# Gaussian noise applied to each judoka's composite score. Larger values
# produce more upsets; smaller values produce more deterministic outcomes.
# 8.0 against a 0–100 stat scale gives a meaningful but not overwhelming
# upset rate.
NOISE_STDDEV: float = 8.0

# Section 10 — log-shaped breadth bonus once a judoka has >5 techniques at
# intermediate or higher.
BREADTH_WEIGHT: float = 1.0

# Section 10 — defensive-specialty signal modulates tachiwaza; ledger-
# breadth signal modulates fight IQ. Skeleton multipliers — calibration
# pending.
DEFENSIVE_TACHI_WEIGHT: float = 10.0
LEDGER_BREADTH_IQ_WEIGHT: float = 0.5

# Signature strength is a sum of (tier_value * execution_ratio) over the
# top-5 techniques. Tier values run 0–7; execution ratios run 0–1; so the
# raw signature-strength base maxes at 5 * 7 * 1 = 35. Normalise to roughly
# the same 0–100 scale as the four base stats so equal weights mean what
# they say.
SIGNATURE_NORMALIZER: float = 100.0 / 35.0

# Score-type thresholds on |delta|. With NOISE_STDDEV = 8 the combined
# noise SD on delta is ~11; these thresholds yield a non-degenerate
# distribution across all four score types over a population of matchups.
IPPON_THRESHOLD: float = 18.0
WAZA_ARI_THRESHOLD: float = 8.0
DECISION_THRESHOLD: float = 2.0

# Default 'modern' point values. era_stamp is recorded on the outcome so a
# downstream era-aware resolver can rewrite these.
IPPON_VALUE: int = 10
WAZA_ARI_VALUE: int = 7

# Legendary effects (Section 7).
LEGENDARY_OPPONENT_IQ_PENALTY: float = 5.0     # composure dip in high-stakes
LEGENDARY_FINISH_BUMP_PROB: float = 0.10       # waza-ari → ippon roll bonus


# Tier → integer value, used everywhere tier strength needs to be a number.
TIER_VALUE: dict[ProficiencyTier, int] = {
    tier: i for i, tier in enumerate(PROFICIENCY_ORDER)
}


def tier_value(tier: ProficiencyTier) -> int:
    return TIER_VALUE[tier]


def execution_ratio(record: TechniqueRecord) -> float:
    """How reliably this judoka lands this technique when they try it.

    Naive prior of 0.5 when there is no execution history yet — Section 5
    talks about the ratio in the context of large samples, but for new
    techniques in the vocabulary we need a sensible starting value so the
    signature-strength signal isn't dominated by stochastic early reps.
    """
    if record.executed_attempts == 0:
        return 0.5
    return record.executed_successes / record.executed_attempts


# ===========================================================================
# PRECOMPUTED SIGNALS
# Section 10: "Precomputation matters at scale — Ring 2 worldgen runs
# thousands of matches per simulated year. Computing top-5 and aggregates
# on a per-judoka basis at vocabulary-change time (rare events) rather
# than per-match (frequent events) is the right tradeoff."
# ===========================================================================
@dataclass(frozen=True)
class PrecomputedSignals:
    top_techniques: tuple[TechniqueRecord, ...]
    signature_strength_base: float                  # Σ tier*ratio over top-5
    breadth_bonus: float                            # log breadth bonus
    defensive_specialty_signal: float               # weighted avg, tachiwaza
    ledger_breadth_signal: float                    # count of techniques faced
    legendary_techniques: frozenset[str]            # technique_ids at legendary

    @property
    def signature_strength_raw(self) -> float:
        """Section 10 formula: base + breadth + era adjustment.

        Era adjustment is a no-op in the skeleton (per ticket: "1.0 stamps
        era but treats all matches as modern-rules").
        """
        return self.signature_strength_base + self.breadth_bonus


def precompute_signals(
    vocabulary: dict[str, TechniqueRecord],
    catalog: dict[str, TechniqueDefinition],
    *,
    breadth_weight: float = BREADTH_WEIGHT,
) -> PrecomputedSignals:
    """Refresh the resolver-consumed signals for one judoka.

    The orchestrator calls this whenever a judoka's vocabulary changes
    (tier transition, new technique acquired, disuse decay, etc.). The
    resolver itself never touches the catalog or the full vocabulary —
    it reads only the precomputed signals.
    """
    records = list(vocabulary.values())

    # Top-5 by tier * execution_ratio (Section 10 formula).
    ranked = sorted(
        records,
        key=lambda r: tier_value(r.proficiency_tier) * execution_ratio(r),
        reverse=True,
    )
    top = tuple(ranked[:5])
    signature_base = sum(
        tier_value(r.proficiency_tier) * execution_ratio(r) for r in top
    )

    # Breadth bonus — log-shaped, kicks in once intermediate-or-higher
    # count exceeds 5.
    intermediate_threshold = tier_value(ProficiencyTier.INTERMEDIATE)
    intermediate_or_higher = sum(
        1 for r in records
        if tier_value(r.proficiency_tier) >= intermediate_threshold
    )
    breadth_bonus = log(max(1, intermediate_or_higher - 5)) * breadth_weight

    # Defensive specialty signal — weighted average of defended_success
    # ratios across *tachiwaza* techniques only (Section 10: it modulates
    # the tachiwaza dimension, not ne-waza). Weighting by log(1 + attempts)
    # so a single defended attempt doesn't dominate.
    tachi_families = {
        TechniqueFamily.TE_WAZA,
        TechniqueFamily.KOSHI_WAZA,
        TechniqueFamily.ASHI_WAZA,
        TechniqueFamily.SUTEMI_WAZA,
    }
    weighted_total = 0.0
    weight_sum = 0.0
    for r in records:
        defn = catalog.get(r.technique_id)
        if defn is None or defn.family not in tachi_families:
            continue
        if r.defended_attempts == 0:
            continue
        weight = log(1 + r.defended_attempts)
        ratio = r.defended_successes / r.defended_attempts
        weighted_total += weight * ratio
        weight_sum += weight
    defensive_signal = weighted_total / weight_sum if weight_sum > 0 else 0.0

    # Ledger breadth — count of distinct techniques this judoka has faced.
    ledger_breadth = float(sum(1 for r in records if r.defended_attempts > 0))

    legendary = frozenset(
        r.technique_id for r in records
        if r.proficiency_tier is ProficiencyTier.LEGENDARY
    )

    return PrecomputedSignals(
        top_techniques=top,
        signature_strength_base=signature_base,
        breadth_bonus=breadth_bonus,
        defensive_specialty_signal=defensive_signal,
        ledger_breadth_signal=ledger_breadth,
        legendary_techniques=legendary,
    )


def signature_strength(
    vocabulary: dict[str, TechniqueRecord],
    catalog: dict[str, TechniqueDefinition],
) -> float:
    """Convenience wrapper for callers that want the scalar value directly.

    The orchestrator and resolver normally read from `PrecomputedSignals`;
    this entry point exists for ad-hoc inspection and tests.
    """
    return precompute_signals(vocabulary, catalog).signature_strength_raw


# ===========================================================================
# RING 2 JUDOKA
# ===========================================================================
@dataclass
class Ring2Judoka:
    """Abstract judoka representation for the Ring 2 resolver.

    This is *not* the deep-engine Judoka (src/judoka.py) — the deep engine
    carries body-state, grip graph, capability vectors, and per-tick state
    that the abstracted resolver doesn't need. Keeping the two separate
    keeps Ring 2 worldgen at the >1000-matches-per-simulated-year throughput
    the design budget demands.
    """
    judoka_id: str
    tachiwaza: int                                   # 0–100
    ne_waza: int                                     # 0–100
    conditioning: int                                # 0–100
    fight_iq: int                                    # 0–100
    vocabulary: dict[str, TechniqueRecord] = field(default_factory=dict)
    signals: Optional[PrecomputedSignals] = None

    def refresh_signals(self, catalog: dict[str, TechniqueDefinition]) -> None:
        """Recompute precomputed signals from the current vocabulary.

        Call this exactly when vocabulary mutates — the orchestrator's tier-
        transition, learn, decay, and comeback paths are the call sites.
        """
        self.signals = precompute_signals(self.vocabulary, catalog)


# ===========================================================================
# MATCH CONTEXT
# ===========================================================================
@dataclass(frozen=True)
class MatchContext:
    """Per-match context the resolver consumes.

    `seed` is the deterministic randomness source — given the same context
    and same judoka, the resolver produces the same outcome. The orchestrator
    derives a seed per match (typically from world seed + year + round +
    judoka ids); the resolver does not try to be smart about seed derivation
    itself.

    `high_stakes` flags the contexts where legendary composure-dip and
    finish-quality effects activate (Section 7) — championship rounds,
    close-score situations, golden score. The orchestrator sets this; the
    resolver consumes it.
    """
    year: int
    era: str
    rules_version: str
    seed: int
    round_number: int = 1
    tournament_id: Optional[str] = None
    high_stakes: bool = False


# ===========================================================================
# RESOLVER
# ===========================================================================
class ResolverError(Exception):
    """Resolver pre-condition failed — typically a judoka with no
    precomputed signals."""


def _composite_score(
    judoka: Ring2Judoka,
    opponent: Ring2Judoka,
    context: MatchContext,
    rng: Random,
) -> float:
    """The weighted-sum core: five dimensions, derived modulations, noise.

    Section 10's derived modulations apply at this layer:
      - tachiwaza is lifted by defensive-specialty depth across tachiwaza
        techniques
      - fight IQ is lifted by ledger breadth
      - composure dip from a legendary opponent in high-stakes context
        reduces effective fight IQ
    """
    signals = judoka.signals
    assert signals is not None, "signals must be precomputed"

    # Base + derived modulations
    tachi = judoka.tachiwaza + signals.defensive_specialty_signal * DEFENSIVE_TACHI_WEIGHT
    iq = judoka.fight_iq + signals.ledger_breadth_signal * LEDGER_BREADTH_IQ_WEIGHT

    # Composure dip — Section 7: opponents of legendary holders carry a
    # small fight-IQ penalty in high-stakes context.
    opponent_signals = opponent.signals
    if (
        context.high_stakes
        and opponent_signals is not None
        and opponent_signals.legendary_techniques
    ):
        iq -= LEGENDARY_OPPONENT_IQ_PENALTY

    sig_normalized = signals.signature_strength_raw * SIGNATURE_NORMALIZER

    w_tachi, w_ne, w_cond, w_iq, w_sig = DIMENSION_WEIGHTS
    raw = (
        w_tachi * tachi
        + w_ne * judoka.ne_waza
        + w_cond * judoka.conditioning
        + w_iq * iq
        + w_sig * sig_normalized
    )
    return raw + rng.gauss(0, NOISE_STDDEV)


def _classify_score_type(delta_abs: float) -> tuple[ScoreType, int]:
    """Map delta magnitude to score type + point value.

    Thresholds chosen against the combined noise SD so the score-type
    distribution is non-degenerate across the calibration population.
    """
    if delta_abs >= IPPON_THRESHOLD:
        return ScoreType.IPPON, IPPON_VALUE
    if delta_abs >= WAZA_ARI_THRESHOLD:
        return ScoreType.WAZA_ARI, WAZA_ARI_VALUE
    if delta_abs >= DECISION_THRESHOLD:
        return ScoreType.DECISION, 0
    return ScoreType.GOLDEN_SCORE, 0


def _duration_band(
    score_type: ScoreType,
    cond_avg: float,
    rng: Random,
) -> DurationBand:
    """Duration follows score type, with a conditioning kicker.

    Well-conditioned pairs trend toward longer matches even within the
    same score-type bucket — Section 10 names conditioning as the
    dominant dimension in long matches, so let the duration reflect it.
    """
    if score_type is ScoreType.GOLDEN_SCORE:
        return DurationBand.GOLDEN_SCORE
    if score_type is ScoreType.DECISION:
        return DurationBand.LONG
    # IPPON or WAZA_ARI: short/medium/long, biased by combined conditioning.
    cond_p = cond_avg / 100.0
    if score_type is ScoreType.IPPON:
        return DurationBand.MEDIUM if rng.random() < cond_p else DurationBand.SHORT
    # WAZA_ARI
    return DurationBand.LONG if rng.random() < cond_p else DurationBand.MEDIUM


def _select_scoring_technique(
    winner: Ring2Judoka,
    rng: Random,
) -> Optional[str]:
    """Choose which top-5 technique scored for the winner.

    Weighted by tier * execution_ratio — the same key the precomputed
    ranking already uses, but instead of just taking the top we sample
    to give variety. Returns None if the winner has no usable vocabulary.
    """
    signals = winner.signals
    assert signals is not None
    if not signals.top_techniques:
        return None
    weights = [
        tier_value(r.proficiency_tier) * execution_ratio(r)
        for r in signals.top_techniques
    ]
    if sum(weights) <= 0:
        return None
    pick = rng.choices(signals.top_techniques, weights=weights, k=1)[0]
    return pick.technique_id


def _build_entry_id(judoka_a: Ring2Judoka, judoka_b: Ring2Judoka, context: MatchContext) -> str:
    """Deterministic entry id derived from the inputs.

    The orchestrator can override by setting `entry_id` on the returned
    outcome before writing to the chronicle. The default makes ad-hoc
    resolve() calls round-trip into the chronicle without an external id
    counter.
    """
    tournament = context.tournament_id or "no_tournament"
    return (
        f"match:{context.year}:{tournament}:r{context.round_number}"
        f":{judoka_a.judoka_id}_v_{judoka_b.judoka_id}:s{context.seed}"
    )


def resolve(
    judoka_a: Ring2Judoka,
    judoka_b: Ring2Judoka,
    context: MatchContext,
) -> MatchOutcome:
    """The abstracted resolver — returns a MatchOutcome chronicle entry.

    Both judoka must have precomputed signals (call `refresh_signals()` on
    each before resolving). Determinism: identical inputs and identical
    `context.seed` produce identical outcomes.
    """
    if judoka_a.signals is None or judoka_b.signals is None:
        raise ResolverError(
            "Ring2Judoka.signals is None — call refresh_signals(catalog) "
            "before resolve()"
        )

    rng = Random(context.seed)

    score_a = _composite_score(judoka_a, judoka_b, context, rng)
    score_b = _composite_score(judoka_b, judoka_a, context, rng)

    if score_a >= score_b:
        winner, loser = judoka_a, judoka_b
        delta = score_a - score_b
    else:
        winner, loser = judoka_b, judoka_a
        delta = score_b - score_a

    score_type, score_value = _classify_score_type(delta)
    cond_avg = (judoka_a.conditioning + judoka_b.conditioning) / 2.0
    duration = _duration_band(score_type, cond_avg, rng)

    # Technique selection only when an actual throw scored.
    if score_type in (ScoreType.IPPON, ScoreType.WAZA_ARI):
        technique_id = _select_scoring_technique(winner, rng)
    else:
        technique_id = None

    # Section 7 — finish quality bonus when a legendary technique fires in
    # a high-stakes context: small probability bump waza-ari → ippon.
    if (
        technique_id is not None
        and context.high_stakes
        and score_type is ScoreType.WAZA_ARI
        and winner.signals is not None
        and technique_id in winner.signals.legendary_techniques
    ):
        if rng.random() < LEGENDARY_FINISH_BUMP_PROB:
            score_type = ScoreType.IPPON
            score_value = IPPON_VALUE
            # Re-roll duration since the score type changed.
            duration = _duration_band(score_type, cond_avg, rng)

    return MatchOutcome(
        entry_id=_build_entry_id(judoka_a, judoka_b, context),
        year=context.year,
        tournament_id=context.tournament_id,
        winner_id=winner.judoka_id,
        loser_id=loser.judoka_id,
        score_type=score_type,
        score_value=score_value,
        duration_band=duration,
        era_stamp=context.rules_version,
        technique_id=technique_id,
    )
