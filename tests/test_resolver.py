# test_resolver.py — HAJ-201 acceptance tests.
#
# Exercises src/resolver.py against synthetic Ring2Judoka populations plus
# the small sample catalog from data/techniques.yaml.
#
# Acceptance criteria from the ticket:
#   - resolve() returns valid MatchOutcome objects compatible with HAJ-200
#   - Signature strength reads from vocabulary (HAJ-204 schema)
#   - Across 100 random matchups: higher-aggregate-stat wins >60% but not
#     all; score type and duration distributions are non-degenerate
#   - Determinism: same inputs + same seed → same outcome
#   - Precomputation refresh logic works (signals invalidated → recomputed)

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chronicle import DurationBand, MatchOutcome, ScoreType
from resolver import (
    DIMENSION_WEIGHTS,
    MatchContext,
    PrecomputedSignals,
    ResolverError,
    Ring2Judoka,
    precompute_signals,
    resolve,
    signature_strength,
    tier_value,
)
from technique_catalog import (
    AcquisitionSource,
    ProficiencyTier,
    TechniqueRecord,
    load_catalog,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CATALOG = REPO_ROOT / "data" / "techniques.yaml"


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def catalog():
    return load_catalog(SAMPLE_CATALOG)


def _record(
    technique_id: str,
    tier: ProficiencyTier,
    *,
    attempts: int = 0,
    successes: int = 0,
    defended_attempts: int = 0,
    defended_successes: int = 0,
) -> TechniqueRecord:
    """Convenience constructor — tests stay readable without keyword spam."""
    return TechniqueRecord(
        technique_id=technique_id,
        proficiency_tier=tier,
        executed_attempts=attempts,
        executed_successes=successes,
        defended_attempts=defended_attempts,
        defended_successes=defended_successes,
    )


def _build_judoka(
    judoka_id: str,
    catalog,
    *,
    tachi: int = 60,
    ne: int = 60,
    cond: int = 60,
    iq: int = 60,
    vocabulary: dict | None = None,
) -> Ring2Judoka:
    judoka = Ring2Judoka(
        judoka_id=judoka_id,
        tachiwaza=tachi, ne_waza=ne, conditioning=cond, fight_iq=iq,
        vocabulary=vocabulary or {},
    )
    judoka.refresh_signals(catalog)
    return judoka


def _ctx(seed: int, **overrides) -> MatchContext:
    defaults = dict(
        year=1975,
        era="1970s",
        rules_version="ijf_1967_rules",
        seed=seed,
        round_number=1,
        tournament_id="test_tournament",
        high_stakes=False,
    )
    defaults.update(overrides)
    return MatchContext(**defaults)


# ===========================================================================
# PRECOMPUTED SIGNALS — Section 10 formula
# ===========================================================================
class TestPrecomputeSignals:
    def test_empty_vocabulary_produces_zero_signals(self, catalog):
        signals = precompute_signals({}, catalog)
        assert signals.signature_strength_base == 0
        assert signals.breadth_bonus == 0
        assert signals.top_techniques == ()
        assert signals.defensive_specialty_signal == 0.0
        assert signals.ledger_breadth_signal == 0.0
        assert signals.legendary_techniques == frozenset()

    def test_top_five_ranking_uses_tier_times_execution_ratio(self, catalog):
        # Six techniques with varying tiers and ratios. Top-5 should be in
        # descending order of tier_value * execution_ratio.
        vocab = {
            "uchi_mata": _record(
                "uchi_mata", ProficiencyTier.MASTER, attempts=100, successes=80,
            ),  # 6 * 0.8 = 4.8
            "seoi_nage": _record(
                "seoi_nage", ProficiencyTier.EXPERT, attempts=100, successes=90,
            ),  # 5 * 0.9 = 4.5
            "o_soto_gari": _record(
                "o_soto_gari", ProficiencyTier.COMPETITIVE, attempts=100, successes=70,
            ),  # 4 * 0.7 = 2.8
            "tomoe_nage": _record(
                "tomoe_nage", ProficiencyTier.INTERMEDIATE, attempts=100, successes=60,
            ),  # 3 * 0.6 = 1.8
            "extra1": _record(
                "extra1", ProficiencyTier.PROFICIENT, attempts=100, successes=40,
            ),  # 2 * 0.4 = 0.8
            "extra2": _record(
                "extra2", ProficiencyTier.KNOWN, attempts=0, successes=0,
            ),  # 0 — excluded by ranking
        }
        signals = precompute_signals(vocab, catalog)
        assert len(signals.top_techniques) == 5
        # Top-5 ids in descending order:
        top_ids = [r.technique_id for r in signals.top_techniques]
        assert top_ids[0] == "uchi_mata"
        assert top_ids[1] == "seoi_nage"
        assert top_ids[2] == "o_soto_gari"
        # signature base is sum across all 5 entries.
        # 4.8 + 4.5 + 2.8 + 1.8 + 0.8 = 14.7
        assert signals.signature_strength_base == pytest.approx(14.7, abs=0.01)

    def test_execution_ratio_default_for_zero_attempts(self, catalog):
        # A novice with zero history gets the 0.5 prior — otherwise a brand-
        # new vocabulary entry would collapse to 0 signature contribution
        # and inflate-the-old / dampen-the-new dynamics would be too strong.
        vocab = {
            "uchi_mata": _record("uchi_mata", ProficiencyTier.PROFICIENT),
        }
        signals = precompute_signals(vocab, catalog)
        # tier_value(PROFICIENT) = 2, ratio = 0.5 → 1.0
        assert signals.signature_strength_base == pytest.approx(1.0)

    def test_breadth_bonus_zero_at_or_below_five_intermediate(self, catalog):
        vocab = {
            f"t{i}": _record("uchi_mata", ProficiencyTier.INTERMEDIATE)
            for i in range(5)
        }
        signals = precompute_signals(vocab, catalog)
        assert signals.breadth_bonus == 0.0  # log(max(1, 0)) = 0

    def test_breadth_bonus_kicks_in_above_five(self, catalog):
        # 10 intermediates → log(5) * BREADTH_WEIGHT > 0
        vocab = {
            f"t{i}": _record("uchi_mata", ProficiencyTier.INTERMEDIATE)
            for i in range(10)
        }
        signals = precompute_signals(vocab, catalog)
        assert signals.breadth_bonus > 0

    def test_defensive_signal_aggregates_over_tachiwaza_only(self, catalog):
        # uchi_mata is koshi_waza (tachiwaza) — counts.
        # An imaginary ne_waza technique would not count, but our sample
        # catalog has only tachiwaza so the exclusion path is tested via
        # the "no catalog entry" branch (an unknown technique_id).
        vocab = {
            "uchi_mata": _record(
                "uchi_mata", ProficiencyTier.COMPETITIVE,
                defended_attempts=50, defended_successes=45,
            ),
            "unknown_to_catalog": _record(
                "unknown_to_catalog", ProficiencyTier.COMPETITIVE,
                defended_attempts=100, defended_successes=10,
            ),
        }
        signals = precompute_signals(vocab, catalog)
        # The unknown technique is dropped (no catalog → can't classify
        # family); only the uchi-mata defence ratio (0.9) survives.
        assert signals.defensive_specialty_signal == pytest.approx(0.9, abs=0.01)

    def test_ledger_breadth_counts_distinct_defended_techniques(self, catalog):
        vocab = {
            "uchi_mata": _record(
                "uchi_mata", ProficiencyTier.COMPETITIVE,
                defended_attempts=10, defended_successes=8,
            ),
            "seoi_nage": _record(
                "seoi_nage", ProficiencyTier.PROFICIENT,
                defended_attempts=5, defended_successes=3,
            ),
            "o_soto_gari": _record(
                "o_soto_gari", ProficiencyTier.NOVICE,
                # never defended → not in ledger breadth
            ),
        }
        signals = precompute_signals(vocab, catalog)
        assert signals.ledger_breadth_signal == 2

    def test_legendary_flags_collected(self, catalog):
        vocab = {
            "uchi_mata": _record("uchi_mata", ProficiencyTier.LEGENDARY),
            "seoi_nage": _record("seoi_nage", ProficiencyTier.MASTER),
        }
        signals = precompute_signals(vocab, catalog)
        assert signals.legendary_techniques == frozenset({"uchi_mata"})


def test_signature_strength_helper_matches_signals(catalog):
    vocab = {
        "uchi_mata": _record(
            "uchi_mata", ProficiencyTier.EXPERT, attempts=100, successes=70,
        ),
    }
    direct = signature_strength(vocab, catalog)
    from_signals = precompute_signals(vocab, catalog).signature_strength_raw
    assert direct == pytest.approx(from_signals)


# ===========================================================================
# RESOLVER — basic contract
# ===========================================================================
class TestResolverContract:
    def test_returns_match_outcome(self, catalog):
        a = _build_judoka("a", catalog, tachi=70, ne=70, cond=70, iq=70)
        b = _build_judoka("b", catalog, tachi=50, ne=50, cond=50, iq=50)
        result = resolve(a, b, _ctx(seed=42))
        assert isinstance(result, MatchOutcome)
        assert result.winner_id in {"a", "b"}
        assert result.loser_id in {"a", "b"}
        assert result.winner_id != result.loser_id
        assert isinstance(result.score_type, ScoreType)
        assert isinstance(result.duration_band, DurationBand)
        assert result.year == 1975
        assert result.era_stamp == "ijf_1967_rules"
        assert result.tournament_id == "test_tournament"

    def test_unprecomputed_signals_raises(self, catalog):
        a = Ring2Judoka("a", 60, 60, 60, 60)  # signals=None by default
        b = _build_judoka("b", catalog)
        with pytest.raises(ResolverError, match="refresh_signals"):
            resolve(a, b, _ctx(seed=1))

    def test_decision_and_golden_score_have_null_technique(self, catalog):
        # Two nearly identical judoka with no vocabulary — outcomes should
        # mostly cluster around DECISION / GOLDEN_SCORE and have no
        # technique attached.
        a = _build_judoka("a", catalog, tachi=60, ne=60, cond=60, iq=60)
        b = _build_judoka("b", catalog, tachi=60, ne=60, cond=60, iq=60)
        decisions = 0
        for seed in range(200):
            r = resolve(a, b, _ctx(seed=seed))
            if r.score_type in (ScoreType.DECISION, ScoreType.GOLDEN_SCORE):
                assert r.technique_id is None
                decisions += 1
        assert decisions > 0  # the formula does produce decisions


# ===========================================================================
# DETERMINISM
# ===========================================================================
class TestDeterminism:
    def test_same_seed_same_outcome(self, catalog):
        a = _build_judoka("a", catalog, tachi=70)
        b = _build_judoka("b", catalog, tachi=55)
        ctx = _ctx(seed=12345)
        first = resolve(a, b, ctx)
        second = resolve(a, b, ctx)
        assert first.winner_id == second.winner_id
        assert first.score_type == second.score_type
        assert first.score_value == second.score_value
        assert first.duration_band == second.duration_band
        assert first.technique_id == second.technique_id

    def test_different_seeds_eventually_diverge(self, catalog):
        # Not asserting per-seed difference — Gaussian noise can collide on
        # the score-type threshold. Asserting *some* divergence across a
        # batch is the right shape.
        a = _build_judoka("a", catalog, tachi=65, ne=65, cond=65, iq=65)
        b = _build_judoka("b", catalog, tachi=55, ne=55, cond=55, iq=55)
        outcomes = {resolve(a, b, _ctx(seed=s)).score_type for s in range(50)}
        assert len(outcomes) > 1


# ===========================================================================
# DISTRIBUTION — the "100 random matchups" acceptance criterion
# ===========================================================================
class TestDistribution:
    @staticmethod
    def _aggregate(j: Ring2Judoka) -> float:
        return j.tachiwaza + j.ne_waza + j.conditioning + j.fight_iq

    def test_higher_aggregate_wins_majority_but_not_all(self, catalog):
        """Acceptance: across 100 random matchups, the judoka with the
        higher base-stat aggregate wins >60% but not 100% — upsets must
        exist."""
        rng = random.Random(2026_05_12)
        higher_wins = 0
        equal = 0
        for i in range(100):
            stats_a = [rng.randint(40, 90) for _ in range(4)]
            stats_b = [rng.randint(40, 90) for _ in range(4)]
            a = _build_judoka("a", catalog,
                              tachi=stats_a[0], ne=stats_a[1],
                              cond=stats_a[2], iq=stats_a[3])
            b = _build_judoka("b", catalog,
                              tachi=stats_b[0], ne=stats_b[1],
                              cond=stats_b[2], iq=stats_b[3])
            agg_a = self._aggregate(a)
            agg_b = self._aggregate(b)
            if agg_a == agg_b:
                equal += 1
                continue
            higher_judoka = "a" if agg_a > agg_b else "b"
            outcome = resolve(a, b, _ctx(seed=i))
            if outcome.winner_id == higher_judoka:
                higher_wins += 1

        rated = 100 - equal
        win_rate = higher_wins / rated
        # Acceptance criterion: >60%, and at least some upsets.
        assert win_rate > 0.60, f"higher-aggregate win rate {win_rate:.2f} below 60%"
        assert higher_wins < rated, "no upsets at all — variance is wrong"

    def test_score_type_distribution_non_degenerate(self, catalog):
        rng = random.Random(2026_05_13)
        score_types: Counter[ScoreType] = Counter()
        for i in range(200):
            stats_a = [rng.randint(40, 90) for _ in range(4)]
            stats_b = [rng.randint(40, 90) for _ in range(4)]
            a = _build_judoka("a", catalog, tachi=stats_a[0], ne=stats_a[1],
                              cond=stats_a[2], iq=stats_a[3])
            b = _build_judoka("b", catalog, tachi=stats_b[0], ne=stats_b[1],
                              cond=stats_b[2], iq=stats_b[3])
            score_types[resolve(a, b, _ctx(seed=i)).score_type] += 1

        # At least three of the four score types must occur — the
        # threshold structure should produce real variety, not just
        # ippon-vs-decision binary outcomes.
        present = {t for t, c in score_types.items() if c > 0}
        assert len(present) >= 3, f"only {len(present)} score types observed: {score_types}"

    def test_duration_band_distribution_non_degenerate(self, catalog):
        rng = random.Random(2026_05_14)
        durations: Counter[DurationBand] = Counter()
        for i in range(200):
            stats_a = [rng.randint(40, 90) for _ in range(4)]
            stats_b = [rng.randint(40, 90) for _ in range(4)]
            a = _build_judoka("a", catalog, tachi=stats_a[0], ne=stats_a[1],
                              cond=stats_a[2], iq=stats_a[3])
            b = _build_judoka("b", catalog, tachi=stats_b[0], ne=stats_b[1],
                              cond=stats_b[2], iq=stats_b[3])
            durations[resolve(a, b, _ctx(seed=i)).duration_band] += 1

        present = {d for d, c in durations.items() if c > 0}
        assert len(present) >= 3, f"only {len(present)} duration bands observed: {durations}"


# ===========================================================================
# PRECOMPUTATION REFRESH
# ===========================================================================
class TestSignalsRefresh:
    def test_refresh_signals_picks_up_vocabulary_change(self, catalog):
        a = _build_judoka("a", catalog, vocabulary={
            "uchi_mata": _record("uchi_mata", ProficiencyTier.PROFICIENT),
        })
        baseline = a.signals.signature_strength_base

        # Mutate vocabulary in-place (orchestrator-style update) without
        # refreshing — signals are stale.
        a.vocabulary["uchi_mata"] = _record(
            "uchi_mata", ProficiencyTier.MASTER, attempts=100, successes=80,
        )
        assert a.signals.signature_strength_base == baseline  # stale

        # Now refresh. Signals reflect the new tier+ratio.
        a.refresh_signals(catalog)
        assert a.signals.signature_strength_base > baseline

    def test_legendary_flag_appears_after_refresh(self, catalog):
        a = _build_judoka("a", catalog, vocabulary={
            "uchi_mata": _record("uchi_mata", ProficiencyTier.MASTER),
        })
        assert a.signals.legendary_techniques == frozenset()

        a.vocabulary["uchi_mata"] = _record(
            "uchi_mata", ProficiencyTier.LEGENDARY, attempts=200, successes=180,
        )
        a.refresh_signals(catalog)
        assert a.signals.legendary_techniques == frozenset({"uchi_mata"})


# ===========================================================================
# LEGENDARY MODIFIERS — Section 7
# ===========================================================================
class TestLegendaryModifiers:
    def _legendary_pair(self, catalog):
        legendary_vocab = {
            "uchi_mata": _record(
                "uchi_mata", ProficiencyTier.LEGENDARY,
                attempts=200, successes=180,
            ),
        }
        ordinary_vocab = {
            "uchi_mata": _record(
                "uchi_mata", ProficiencyTier.PROFICIENT,
                attempts=50, successes=20,
            ),
        }
        legend = _build_judoka("legend", catalog, tachi=70, ne=70, cond=70, iq=70,
                               vocabulary=legendary_vocab)
        ordinary = _build_judoka("ordinary", catalog, tachi=70, ne=70, cond=70, iq=70,
                                 vocabulary=ordinary_vocab)
        return legend, ordinary

    def test_signature_strength_higher_for_legendary_holder(self, catalog):
        legend, ordinary = self._legendary_pair(catalog)
        assert legend.signals.signature_strength_base > ordinary.signals.signature_strength_base

    def test_legendary_holder_wins_more_in_high_stakes(self, catalog):
        """Composure dip + finish bonus mean a legendary holder should win
        a *higher* fraction of high-stakes matches than non-high-stakes,
        all else equal."""
        legend, ordinary = self._legendary_pair(catalog)

        normal_wins = sum(
            resolve(legend, ordinary, _ctx(seed=s, high_stakes=False)).winner_id == "legend"
            for s in range(300)
        )
        stakes_wins = sum(
            resolve(legend, ordinary, _ctx(seed=s, high_stakes=True)).winner_id == "legend"
            for s in range(300)
        )
        # The effect is small (5 IQ points + 10% finish bump) so we look
        # for any positive lift — a stricter inequality would be brittle.
        assert stakes_wins >= normal_wins, (
            f"legendary holder did not benefit from high_stakes: "
            f"normal={normal_wins}, stakes={stakes_wins}"
        )
