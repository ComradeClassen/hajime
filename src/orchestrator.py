# orchestrator.py
# Ring 2 year-tick orchestrator (HAJ-202).
#
# The "year happens" loop. Given a WorldState, advance_year runs every
# scheduled competition through the resolver, writes outcomes to the
# chronicle, updates offensive/defensive ledgers, awards progress from
# match exposure, processes training, evaluates disuse decay, checks
# legendary qualifications, runs vocabulary-driven promotions, ages every
# judoka by one year, and rolls retirements/deaths.
#
# This is the substrate that makes the chronicle *live*. Before this lands
# the chronicle is an empty data structure; after this lands a 5-year run
# against the tiny_nj fixture produces ~100 chronicle entries spanning
# every entry type the resolver/orchestrator can emit.
#
# Schema is locked by:
#   - design-notes/ring-2-worldgen-spec-v2.md Part II
#   - design-notes/triage/technique-vocabulary-system.md Section 4
#     (acquisition pathways), Section 5 (ledger), Section 6 (disuse decay),
#     Section 7 (legendary qualification), Section 8 (promotion thresholds)
#
# Out of scope per HAJ-202:
#   - Real NJ 1960 worldgen / state module / demographics / Cranford anchor
#   - Cohort formation, photo events, dojo open/close events
#   - Naming overlay propagation (HAJ-206)
#   - Marriages, births, lineage tracking, child-interest reveals
#   - Federation-level promotion examinations (examiner_type captured;
#     federation logic is naive)
#   - Persistence to disk
#   - Calibration of the placeholder retirement/death/decay/progress
#     curves — those numbers are first-draft and a downstream calibration
#     ticket will tune them against worldgen output.

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Optional

from chronicle import (
    Chronicle,
    Death,
    DeathCause,
    ExaminerType,
    LegendaryRecognition,
    MatchOutcome,
    MilestoneTriggerType,
    Promotion,
    PromotionTestHeld,
    PromotionTestOutcome,
    Retirement,
    RetirementReason,
    ScoreType,
    TechniqueDisuseDrop,
    TechniqueLearned,
    TechniqueMilestone,
)
from resolver import MatchContext, Ring2Judoka, resolve
from technique_catalog import (
    PROFICIENCY_ORDER,
    AcquisitionSource,
    ProficiencyTier,
    TechniqueDefinition,
    TechniqueRecord,
)


# ===========================================================================
# CONSTANTS — placeholder calibration values
# ===========================================================================
BELT_LADDER: tuple[str, ...] = (
    "white", "yellow", "green",
    "brown_3", "brown_2", "brown_1",
    "shodan", "nidan", "sandan", "yondan", "godan",
)

# Section 8 — vocabulary-driven promotion thresholds.
# Tuple shape: (proficient_plus, intermediate_plus, competitive_plus,
#               expert_plus, master_plus, families_at_proficient_plus)
PROMOTION_THRESHOLDS: dict[str, tuple[int, int, int, int, int, int]] = {
    "yellow":  (3, 0, 0, 0, 0, 2),
    "green":   (7, 2, 0, 0, 0, 4),
    "brown_3": (11, 5, 2, 0, 0, 3),
    "brown_2": (13, 7, 3, 0, 0, 3),
    "brown_1": (15, 9, 4, 1, 0, 3),
    "shodan":  (17, 11, 5, 2, 0, 4),
    "nidan":   (19, 13, 7, 3, 1, 4),
    "sandan":  (21, 15, 9, 5, 2, 4),
}

# Section 8 — minimum tenure at current belt before promotion is considered.
MIN_TENURE_YEARS: dict[str, int] = {
    "yellow":  0,
    "green":   1,
    "brown_3": 1,
    "brown_2": 1,
    "brown_1": 1,
    "shodan":  2,
    "nidan":   2,
    "sandan":  3,
}

# Section 6 — disuse decay threshold (years without use → one tier drop).
DISUSE_THRESHOLD_YEARS: int = 3

# Section 4 — per-event progress contributions. Placeholder values; the
# pathway contribution magnitudes are calibrated downstream.
PROGRESS_MATCH_EXEC_IPPON: int = 12
PROGRESS_MATCH_EXEC_WAZA_ARI: int = 6
PROGRESS_MATCH_DEFEND: int = 3
PROGRESS_SENSEI_TAUGHT_BASE: int = 15  # plus teaching aptitude bonus

# Section 7 — legendary qualification criteria.
LEGENDARY_REQUIRED_TENURE_YEARS: int = 5
LEGENDARY_REQUIRED_COMP_SCORE: float = 15.0

# Placeholder competition tier weights (Section 7).
DEFAULT_COMP_TIER_WEIGHT: float = 0.3   # club default


# ===========================================================================
# WORLD JUDOKA
# Extends Ring2Judoka with the biographical fields the orchestrator needs.
# Inheritance is the right shape here: the resolver doesn't care about age
# or belt rank, so keeping those fields out of Ring2Judoka keeps the
# resolver focused. WorldJudoka *is-a* Ring2Judoka so the resolver accepts
# it directly.
# ===========================================================================
@dataclass
class WorldJudoka(Ring2Judoka):
    age: int = 18
    belt_rank: str = "white"
    teaching_aptitude: int = 50                     # 0–100 (Section 4)
    dojo_id: Optional[str] = None
    year_started_training: Optional[int] = None
    year_last_promoted: Optional[int] = None
    is_retired: bool = False
    is_deceased: bool = False


# ===========================================================================
# WORLD STATE
# ===========================================================================
@dataclass
class Dojo:
    dojo_id: str
    name: str
    location: str
    head_sensei_id: str
    member_ids: set[str] = field(default_factory=set)
    curriculum: list[str] = field(default_factory=list)


@dataclass
class Competition:
    competition_id: str
    name: str
    year: int
    tier_weight: float                              # Section 7 weighting
    entrant_ids: list[str]
    is_championship: bool = False
    rules_version: str = "ijf_pre_2009"


@dataclass
class WorldState:
    year: int
    catalog: dict[str, TechniqueDefinition]
    judoka: dict[str, WorldJudoka]
    dojos: dict[str, Dojo]
    competitions_by_year: dict[int, list[Competition]]
    chronicle: Chronicle
    seed: int

    # Monotonic counter for deterministic chronicle entry ids. With a fixed
    # seed and same starting state, the orchestrator always increments this
    # counter in the same order, so entry_ids are reproducible.
    _entry_counter: int = 0

    def next_entry_id(self, prefix: str) -> str:
        self._entry_counter += 1
        return f"{prefix}:{self.year}:{self._entry_counter:06d}"


# ===========================================================================
# advance_year — the year-tick loop
# ===========================================================================
def advance_year(
    world: WorldState,
    year: int,
    rng: Optional[Random] = None,
) -> WorldState:
    """Advance the world by one year.

    Mutates `world` in place and returns the same object. The numbered steps
    below match the HAJ-202 ticket's 13-step decomposition.

    Determinism: with the same `world.seed` and same starting state, this
    produces the same result. The `rng` argument is optional — when omitted
    a year-rng is derived from seed+year, which is the standard path. The
    parameter exists so callers can inject a custom rng for narrow tests.
    """
    world.year = year
    year_rng = rng if rng is not None else Random(world.seed * 1_000_003 + year)

    # Refresh precomputed signals once at the start of the year. Within-year
    # vocabulary mutations affect *next year's* signals — at the year-tick
    # grain this is a reasonable approximation that avoids re-running the
    # signal computation between every match.
    for j in world.judoka.values():
        if not (j.is_retired or j.is_deceased):
            j.refresh_signals(world.catalog)

    # Step 1 + 2 — run scheduled competitions through the resolver and
    # write each MatchOutcome to the chronicle.
    matches_this_year: list[MatchOutcome] = []
    for comp in world.competitions_by_year.get(year, []):
        matches_this_year.extend(_run_competition(comp, world))

    # Step 3 — update offensive/defensive ledgers from each match outcome.
    for match in matches_this_year:
        _apply_match_ledger(match, world)

    # Step 4 — award vocabulary progress from match exposure and fire
    # `technique_milestone` entries when tier boundaries are crossed.
    for match in matches_this_year:
        _award_match_progress(match, world)

    # Step 5 — sensei-taught training. Adds techniques to vocabularies and
    # advances progress per the curriculum + teaching-aptitude shape.
    _process_training(world)

    # Step 6 — seminars (no-op in the seed world; HAJ-209 wires this up).

    # Step 7 — disuse decay.
    _process_disuse(world)

    # Step 8 — legendary qualification check.
    _process_legendary(world)

    # Step 9 — vocabulary-driven promotions + promotion-test records.
    _process_promotions(world)

    # Refresh signals again so step-10 reads consistent state, and so the
    # *next* year's match-1 has fresh signals to consume.
    for j in world.judoka.values():
        if not (j.is_retired or j.is_deceased):
            j.refresh_signals(world.catalog)

    # Step 10–12 — age every judoka, roll retirements, roll deaths.
    _process_aging_retirement_death(world, year_rng)

    return world


# ---------------------------------------------------------------------------
# Step 1 + 2 — run a competition
# ---------------------------------------------------------------------------
def _run_competition(comp: Competition, world: WorldState) -> list[MatchOutcome]:
    """Round-robin every active entrant against every other.

    Round-robin is the simplest deterministic pairing scheme and produces
    enough matches per year (N*(N-1)/2) to populate ledgers meaningfully.
    Tournament bracket logic is downstream worldgen work; the resolver
    skeleton doesn't care about bracket shape.
    """
    matches: list[MatchOutcome] = []
    entrants = [
        eid for eid in comp.entrant_ids
        if eid in world.judoka
        and not world.judoka[eid].is_retired
        and not world.judoka[eid].is_deceased
    ]
    if len(entrants) < 2:
        return matches

    for i in range(len(entrants)):
        for j in range(i + 1, len(entrants)):
            a = world.judoka[entrants[i]]
            b = world.judoka[entrants[j]]
            world._entry_counter += 1
            match_seed = world.seed * 1_000_003 + comp.year * 1000 + world._entry_counter
            ctx = MatchContext(
                year=comp.year,
                era=_era_for_year(comp.year),
                rules_version=comp.rules_version,
                seed=match_seed,
                round_number=1,
                tournament_id=comp.competition_id,
                high_stakes=comp.is_championship,
            )
            outcome = resolve(a, b, ctx)
            # Override entry_id so it follows our deterministic id scheme
            # — the resolver default is unique but verbose; the chronicle
            # prefers consistent prefixes.
            outcome.entry_id = f"match:{comp.year}:{world._entry_counter:06d}"
            world.chronicle.add(outcome)
            matches.append(outcome)
    return matches


# ---------------------------------------------------------------------------
# Step 3 — ledger updates
# ---------------------------------------------------------------------------
def _apply_match_ledger(match: MatchOutcome, world: WorldState) -> None:
    """Update offensive ledger on the winner and defensive ledger on the
    loser. If the loser doesn't know the technique yet, register it at
    `known` tier via the thrown-by-opponent acquisition pathway."""
    if match.technique_id is None:
        return  # decision / golden-score — no technique landed

    winner = world.judoka.get(match.winner_id)
    loser = world.judoka.get(match.loser_id)
    if winner is None or loser is None:
        return

    # Winner offensive ledger
    winner_rec = winner.vocabulary.get(match.technique_id)
    if winner_rec is None:
        winner_rec = TechniqueRecord(
            technique_id=match.technique_id,
            proficiency_tier=ProficiencyTier.NOVICE,
            source_of_acquisition=AcquisitionSource.ACCIDENTAL_DISCOVERY,
            year_acquired=match.year,
        )
        winner.vocabulary[match.technique_id] = winner_rec
    winner_rec.executed_attempts += 1
    winner_rec.executed_successes += 1
    if match.score_type is ScoreType.IPPON:
        winner_rec.executed_ippons += 1
    winner_rec.last_executed_year = match.year
    winner_rec.last_used_year = match.year

    # Loser defensive ledger. They failed to defend (lost), so
    # `defended_successes` does not increment.
    loser_rec = loser.vocabulary.get(match.technique_id)
    if loser_rec is None:
        loser_rec = TechniqueRecord(
            technique_id=match.technique_id,
            proficiency_tier=ProficiencyTier.KNOWN,
            source_of_acquisition=AcquisitionSource.THROWN_BY_OPPONENT,
            year_acquired=match.year,
            acquired_from=winner.judoka_id,
        )
        loser.vocabulary[match.technique_id] = loser_rec
        world.chronicle.add(TechniqueLearned(
            entry_id=world.next_entry_id("learn"),
            year=match.year,
            judoka_id=loser.judoka_id,
            technique_id=match.technique_id,
            source_pathway=AcquisitionSource.THROWN_BY_OPPONENT,
            source_entity_id=winner.judoka_id,
            source_event_id=match.entry_id,
            starting_tier=ProficiencyTier.KNOWN,
        ))
    loser_rec.defended_attempts += 1
    if match.score_type is ScoreType.IPPON:
        loser_rec.defended_ippon_losses += 1
    loser_rec.last_defended_year = match.year
    loser_rec.last_used_year = match.year


# ---------------------------------------------------------------------------
# Step 4 — match-exposure progress + milestones
# ---------------------------------------------------------------------------
def _award_match_progress(match: MatchOutcome, world: WorldState) -> None:
    if match.technique_id is None:
        return
    winner = world.judoka.get(match.winner_id)
    loser = world.judoka.get(match.loser_id)

    if winner is not None:
        exec_bump = (
            PROGRESS_MATCH_EXEC_IPPON if match.score_type is ScoreType.IPPON
            else PROGRESS_MATCH_EXEC_WAZA_ARI
        )
        _add_progress(
            winner, match.technique_id, exec_bump, world,
            MilestoneTriggerType.MATCH_USE, match.entry_id,
        )

    if loser is not None:
        _add_progress(
            loser, match.technique_id, PROGRESS_MATCH_DEFEND, world,
            MilestoneTriggerType.OPPONENT_THROWN_BY, match.entry_id,
        )


def _add_progress(
    judoka: WorldJudoka,
    technique_id: str,
    delta: int,
    world: WorldState,
    trigger_type: MilestoneTriggerType,
    trigger_event_id: Optional[str],
) -> None:
    """Add progress and fire a `technique_milestone` entry if the bump
    crosses a tier boundary. Updates teaching_tier when the proficiency
    tier exceeds the previous peak (Section 6 asymmetry)."""
    rec = judoka.vocabulary.get(technique_id)
    if rec is None:
        return
    if rec.proficiency_tier is ProficiencyTier.LEGENDARY:
        return  # at the top of the ladder

    rec.proficiency_progress += delta
    while rec.proficiency_progress >= 100:
        idx = PROFICIENCY_ORDER.index(rec.proficiency_tier)
        if idx >= len(PROFICIENCY_ORDER) - 2:
            # Don't auto-promote to LEGENDARY through progress alone —
            # legendary requires the Section 7 social criteria check.
            rec.proficiency_progress = min(rec.proficiency_progress, 99)
            break
        previous = rec.proficiency_tier
        rec.proficiency_tier = PROFICIENCY_ORDER[idx + 1]
        rec.proficiency_progress -= 100
        if PROFICIENCY_ORDER.index(rec.proficiency_tier) > PROFICIENCY_ORDER.index(rec.teaching_tier):
            rec.teaching_tier = rec.proficiency_tier
        world.chronicle.add(TechniqueMilestone(
            entry_id=world.next_entry_id("milestone"),
            year=world.year,
            judoka_id=judoka.judoka_id,
            technique_id=technique_id,
            new_tier=rec.proficiency_tier,
            previous_tier=previous,
            triggering_event_type=trigger_type,
            triggering_event_id=trigger_event_id,
        ))


# ---------------------------------------------------------------------------
# Step 5 — sensei-taught training
# ---------------------------------------------------------------------------
def _process_training(world: WorldState) -> None:
    """For each dojo, drill the curriculum: the head sensei teaches every
    technique in `dojo.curriculum` to every active member. New techniques
    enter the vocabulary at `known`; existing techniques accumulate
    progress capped at one tier below the sensei's tier."""
    for dojo in world.dojos.values():
        sensei = world.judoka.get(dojo.head_sensei_id)
        if sensei is None or sensei.is_retired or sensei.is_deceased:
            continue
        for member_id in list(dojo.member_ids):
            student = world.judoka.get(member_id)
            if student is None or student.is_retired or student.is_deceased:
                continue
            for technique_id in dojo.curriculum:
                sensei_rec = sensei.vocabulary.get(technique_id)
                # Sensei must hold the technique at proficient+ to teach it
                # (Section 4 Pathway 1: "you cannot teach what you cannot do").
                if sensei_rec is None:
                    continue
                if PROFICIENCY_ORDER.index(sensei_rec.proficiency_tier) < PROFICIENCY_ORDER.index(ProficiencyTier.PROFICIENT):
                    continue

                if technique_id not in student.vocabulary:
                    student.vocabulary[technique_id] = TechniqueRecord(
                        technique_id=technique_id,
                        proficiency_tier=ProficiencyTier.KNOWN,
                        source_of_acquisition=AcquisitionSource.SENSEI_TAUGHT,
                        year_acquired=world.year,
                        acquired_from=sensei.judoka_id,
                    )
                    world.chronicle.add(TechniqueLearned(
                        entry_id=world.next_entry_id("learn"),
                        year=world.year,
                        judoka_id=student.judoka_id,
                        technique_id=technique_id,
                        source_pathway=AcquisitionSource.SENSEI_TAUGHT,
                        source_entity_id=sensei.judoka_id,
                        starting_tier=ProficiencyTier.KNOWN,
                    ))

                rec = student.vocabulary[technique_id]
                # Section 4: lower-tier senseis cap student progression at
                # sensei tier minus one.
                cap_idx = PROFICIENCY_ORDER.index(sensei_rec.proficiency_tier) - 1
                if PROFICIENCY_ORDER.index(rec.proficiency_tier) >= cap_idx:
                    continue
                aptitude_bonus = sensei.teaching_aptitude // 10
                _add_progress(
                    student, technique_id,
                    PROGRESS_SENSEI_TAUGHT_BASE + aptitude_bonus,
                    world,
                    MilestoneTriggerType.DRILLING_THRESHOLD,
                    None,
                )
                rec.last_used_year = world.year


# ---------------------------------------------------------------------------
# Step 7 — disuse decay
# ---------------------------------------------------------------------------
def _process_disuse(world: WorldState) -> None:
    """Section 6: a technique that hasn't been used (executed, defended,
    drilled, or taught) for >= 3 years drops one tier, with a floor at
    `proficient`. `known` techniques don't decay."""
    floor_idx = PROFICIENCY_ORDER.index(ProficiencyTier.PROFICIENT)
    for judoka in world.judoka.values():
        if judoka.is_retired or judoka.is_deceased:
            continue
        for tech_id, rec in list(judoka.vocabulary.items()):
            if rec.proficiency_tier is ProficiencyTier.KNOWN:
                continue
            last_used = rec.last_used_year
            if last_used is None:
                last_used = rec.year_acquired
            if last_used is None:
                continue
            gap = world.year - last_used
            if gap < DISUSE_THRESHOLD_YEARS:
                continue
            idx = PROFICIENCY_ORDER.index(rec.proficiency_tier)
            if idx <= floor_idx:
                continue                              # at or below proficient
            previous = rec.proficiency_tier
            rec.proficiency_tier = PROFICIENCY_ORDER[idx - 1]
            rec.proficiency_progress = 50            # Section 6: reset mid-tier
            rec.last_used_year = world.year          # restart the clock
            world.chronicle.add(TechniqueDisuseDrop(
                entry_id=world.next_entry_id("disuse"),
                year=world.year,
                judoka_id=judoka.judoka_id,
                technique_id=tech_id,
                new_tier=rec.proficiency_tier,
                previous_tier=previous,
                years_since_last_use=gap,
            ))


# ---------------------------------------------------------------------------
# Step 8 — legendary qualification
# ---------------------------------------------------------------------------
def _process_legendary(world: WorldState) -> None:
    """Section 7: all four criteria must hold —
        1. currently at master tier
        2. >= 15 tier-weighted competition wins with this technique
        3. >= 1 student at competitive+ in the same technique
        4. >= 5 years tenure at master tier
    """
    for judoka in world.judoka.values():
        if judoka.is_retired or judoka.is_deceased:
            continue
        for tech_id, rec in list(judoka.vocabulary.items()):
            if rec.proficiency_tier is not ProficiencyTier.MASTER:
                continue
            master_year = _year_reached_master(world, judoka.judoka_id, tech_id)
            if master_year is None:
                continue
            tenure = world.year - master_year
            if tenure < LEGENDARY_REQUIRED_TENURE_YEARS:
                continue
            comp_score = _competition_score(world, judoka.judoka_id, tech_id)
            if comp_score < LEGENDARY_REQUIRED_COMP_SCORE:
                continue
            inheritors = _lineage_inheritors(world, judoka, tech_id)
            if not inheritors:
                continue

            rec.proficiency_tier = ProficiencyTier.LEGENDARY
            if PROFICIENCY_ORDER.index(rec.teaching_tier) < PROFICIENCY_ORDER.index(ProficiencyTier.LEGENDARY):
                rec.teaching_tier = ProficiencyTier.LEGENDARY
            world.chronicle.add(LegendaryRecognition(
                entry_id=world.next_entry_id("legend"),
                year=world.year,
                judoka_id=judoka.judoka_id,
                technique_id=tech_id,
                qualifying_competition_score=comp_score,
                qualifying_lineage_inheritor_ids=inheritors,
                tenure_years_at_master=tenure,
            ))


def _year_reached_master(
    world: WorldState, judoka_id: str, technique_id: str,
) -> Optional[int]:
    """Look up the chronicle for the year this judoka crossed into master
    tier on this technique. Pre-seeded master judoka have a hand-authored
    `technique_milestone` entry placed at world setup."""
    for entry in world.chronicle.entries_for(judoka_id):
        if isinstance(entry, TechniqueMilestone):
            if (
                entry.technique_id == technique_id
                and entry.new_tier is ProficiencyTier.MASTER
            ):
                return entry.year
    return None


def _competition_score(
    world: WorldState, judoka_id: str, technique_id: str,
) -> float:
    """Sum tier-weighted wins where this judoka beat someone with this
    technique. Section 7 weights."""
    comp_by_id: dict[str, Competition] = {}
    for year_comps in world.competitions_by_year.values():
        for c in year_comps:
            comp_by_id[c.competition_id] = c
    score = 0.0
    for entry in world.chronicle.entries_for(judoka_id):
        if not isinstance(entry, MatchOutcome):
            continue
        if entry.winner_id != judoka_id or entry.technique_id != technique_id:
            continue
        comp = comp_by_id.get(entry.tournament_id) if entry.tournament_id else None
        score += comp.tier_weight if comp else DEFAULT_COMP_TIER_WEIGHT
    return score


def _lineage_inheritors(
    world: WorldState, judoka: WorldJudoka, technique_id: str,
) -> list[str]:
    """Return judoka in the master's dojo at competitive+ on this
    technique. Section 7's "teaching lineage" is approximated as "shares a
    dojo with the master" for the skeleton — full lineage tracking is
    HAJ-206 territory."""
    if judoka.dojo_id is None:
        return []
    dojo = world.dojos.get(judoka.dojo_id)
    if dojo is None:
        return []
    competitive_idx = PROFICIENCY_ORDER.index(ProficiencyTier.COMPETITIVE)
    out: list[str] = []
    for member_id in dojo.member_ids:
        if member_id == judoka.judoka_id:
            continue
        m = world.judoka.get(member_id)
        if m is None:
            continue
        rec = m.vocabulary.get(technique_id)
        if rec is None:
            continue
        if PROFICIENCY_ORDER.index(rec.proficiency_tier) >= competitive_idx:
            out.append(member_id)
    return out


# ---------------------------------------------------------------------------
# Step 9 — promotions
# ---------------------------------------------------------------------------
def _process_promotions(world: WorldState) -> None:
    """Section 8: vocabulary-driven promotion. A judoka is promoted when
    their vocabulary depth meets the target belt's threshold *and* they've
    held the current belt for the minimum tenure."""
    for judoka in world.judoka.values():
        if judoka.is_retired or judoka.is_deceased:
            continue
        next_belt = _next_belt(judoka.belt_rank)
        if next_belt is None:
            continue
        if not _has_minimum_tenure(judoka, next_belt, world.year):
            continue
        if not _meets_belt_threshold(judoka, next_belt, world.catalog):
            continue

        sensei_id: Optional[str] = None
        if judoka.dojo_id is not None:
            dojo = world.dojos.get(judoka.dojo_id)
            if dojo is not None:
                sensei_id = dojo.head_sensei_id

        snapshot = {
            tid: rec.proficiency_tier
            for tid, rec in judoka.vocabulary.items()
        }

        world.chronicle.add(PromotionTestHeld(
            entry_id=world.next_entry_id("ptest"),
            year=world.year,
            judoka_id=judoka.judoka_id,
            from_belt=judoka.belt_rank,
            to_belt=next_belt,
            examiner_id=sensei_id or "federation",
            examiner_type=ExaminerType.SENSEI if sensei_id else ExaminerType.FEDERATION,
            outcome=PromotionTestOutcome.PASS_STANDARD,
            vocabulary_snapshot_at_test=dict(snapshot),
        ))
        world.chronicle.add(Promotion(
            entry_id=world.next_entry_id("promo"),
            year=world.year,
            judoka_id=judoka.judoka_id,
            from_rank=judoka.belt_rank,
            to_rank=next_belt,
            awarding_sensei_id=sensei_id,
            vocabulary_snapshot=dict(snapshot),
        ))
        judoka.belt_rank = next_belt
        judoka.year_last_promoted = world.year


def _next_belt(current_belt: str) -> Optional[str]:
    try:
        idx = BELT_LADDER.index(current_belt)
    except ValueError:
        return None
    return BELT_LADDER[idx + 1] if idx + 1 < len(BELT_LADDER) else None


def _has_minimum_tenure(
    judoka: WorldJudoka, next_belt: str, current_year: int,
) -> bool:
    required = MIN_TENURE_YEARS.get(next_belt, 0)
    if required == 0:
        return True
    if judoka.year_last_promoted is None:
        # Treat the start-of-training year as the implicit "last promotion"
        # so newly-created judoka can promote off white belt without tenure.
        return True
    return current_year - judoka.year_last_promoted >= required


def _meets_belt_threshold(
    judoka: WorldJudoka,
    next_belt: str,
    catalog: dict[str, TechniqueDefinition],
) -> bool:
    thresholds = PROMOTION_THRESHOLDS.get(next_belt)
    if thresholds is None:
        return False
    p_min, i_min, c_min, e_min, m_min, fam_min = thresholds
    vocab = judoka.vocabulary

    counts = _tier_counts(vocab)
    if counts[ProficiencyTier.PROFICIENT] < p_min:
        return False
    if counts[ProficiencyTier.INTERMEDIATE] < i_min:
        return False
    if counts[ProficiencyTier.COMPETITIVE] < c_min:
        return False
    if counts[ProficiencyTier.EXPERT] < e_min:
        return False
    if counts[ProficiencyTier.MASTER] < m_min:
        return False
    if _family_breadth(vocab, catalog) < fam_min:
        return False
    return True


def _tier_counts(vocab: dict[str, TechniqueRecord]) -> dict[ProficiencyTier, int]:
    """Counts at *each* threshold tier — i.e. the count for INTERMEDIATE
    includes intermediate + every tier above it. Promotion thresholds read
    "at least N at intermediate" as "at intermediate or higher"."""
    counts = {tier: 0 for tier in PROFICIENCY_ORDER}
    for rec in vocab.values():
        idx = PROFICIENCY_ORDER.index(rec.proficiency_tier)
        for i in range(idx + 1):
            counts[PROFICIENCY_ORDER[i]] += 1
    return counts


def _family_breadth(
    vocab: dict[str, TechniqueRecord],
    catalog: dict[str, TechniqueDefinition],
) -> int:
    """Count of distinct technique families covered at proficient+."""
    proficient_idx = PROFICIENCY_ORDER.index(ProficiencyTier.PROFICIENT)
    families = set()
    for rec in vocab.values():
        if PROFICIENCY_ORDER.index(rec.proficiency_tier) < proficient_idx:
            continue
        defn = catalog.get(rec.technique_id)
        if defn is None:
            continue
        families.add(defn.family)
    return len(families)


# ---------------------------------------------------------------------------
# Step 10–12 — aging, retirement, death
# ---------------------------------------------------------------------------
def _process_aging_retirement_death(world: WorldState, rng: Random) -> None:
    for judoka in list(world.judoka.values()):
        if judoka.is_deceased:
            continue
        judoka.age += 1

        if not judoka.is_retired:
            if rng.random() < _retirement_probability(judoka.age):
                judoka.is_retired = True
                reason = (
                    RetirementReason.AGE if judoka.age >= 35
                    else RetirementReason.LOSS_OF_INTEREST
                )
                world.chronicle.add(Retirement(
                    entry_id=world.next_entry_id("retire"),
                    year=world.year,
                    judoka_id=judoka.judoka_id,
                    reason=reason,
                ))

        if rng.random() < _death_probability(judoka.age):
            judoka.is_deceased = True
            world.chronicle.add(Death(
                entry_id=world.next_entry_id("death"),
                year=world.year,
                entity_id=judoka.judoka_id,
                cause=DeathCause.NATURAL,
                age=judoka.age,
                era_stamp=_era_for_year(world.year),
            ))


def _retirement_probability(age: int) -> float:
    """Naive curve — calibration deferred to a downstream ticket. Shape
    matches the design intent: zero through prime competitive years,
    rising through 30s/40s, common by 60s.
    """
    if age < 28:
        return 0.0
    if age < 35:
        return 0.02
    if age < 45:
        return 0.07
    if age < 60:
        return 0.15
    return 0.25


def _death_probability(age: int) -> float:
    if age < 30:
        return 0.0005
    if age < 60:
        return 0.003
    if age < 75:
        return 0.02
    if age < 85:
        return 0.05
    return 0.15


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _era_for_year(year: int) -> str:
    return f"{(year // 10) * 10}s"
