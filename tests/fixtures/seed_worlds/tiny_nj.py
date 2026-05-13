# tests/fixtures/seed_worlds/tiny_nj.py
# Test fixture — minimum seed world for HAJ-202 orchestrator validation.
#
# NOT PRODUCTION DATA. Real NJ 1960 worldgen is Track 3 work with proper
# demographic distributions, the Cranford anchor, regional partitioning,
# etc. This fixture is a hand-stubbed tiny world that exercises every
# year-tick code path in src/orchestrator.py with a fixed seed.
#
# Composition (per HAJ-202 acceptance criteria):
#   - 4 dojos in NJ
#   - 8 senseis (4 head + 4 assistant)
#   - 40 judoka total (10 per dojo: 1 head + 1 assistant + 8 students)
#   - Belt distribution spans white through shodan (adult ladder)
#   - Each judoka has 0–20 populated TechniqueRecord entries with tiers
#     matching belt rank
#   - Each judoka has a teaching_aptitude value
#   - One regional competition per year (1960–1964) with seeding-based
#     entrants
#   - Pre-seeded chronicle history giving the Cranford head sensei a
#     legendary qualification for te_waza_0 that fires in 1960
#   - Pre-seeded disuse-candidate techniques to validate decay logic
#
# The synthesised catalog (`_build_test_catalog`) is 20 techniques across
# all five families. It is deliberately *not* the data/techniques.yaml
# sample catalog because the promotion threshold table needs more breadth
# than the 4-technique sample offers. Production catalog authoring is
# HAJ-205.

from __future__ import annotations

from random import Random

from chronicle import (
    Chronicle,
    DurationBand,
    MatchOutcome,
    MilestoneTriggerType,
    ScoreType,
    TechniqueMilestone,
)
from orchestrator import (
    Competition,
    Dojo,
    WorldJudoka,
    WorldState,
)
from technique_catalog import (
    AcquisitionSource,
    CanonicalGripSignature,
    FailedThrowConsequence,
    GripDepth,
    GripHand,
    GripSpec,
    GripTargetRegion,
    KodokanStatus,
    ProficiencyTier,
    TechniqueDefinition,
    TechniqueFamily,
    TechniqueRecord,
    UkePostureRequirement,
)


FIXTURE_SEED: int = 1960_01_01
START_YEAR: int = 1959                              # before first advance
FIRST_TICK_YEAR: int = 1960
LAST_TICK_YEAR: int = 1964


# ---------------------------------------------------------------------------
# CATALOG — 20 techniques, 4 per family
# ---------------------------------------------------------------------------
_FAMILIES: tuple[TechniqueFamily, ...] = (
    TechniqueFamily.TE_WAZA,
    TechniqueFamily.KOSHI_WAZA,
    TechniqueFamily.ASHI_WAZA,
    TechniqueFamily.SUTEMI_WAZA,
    TechniqueFamily.NE_WAZA,
)


def _build_test_catalog() -> dict[str, TechniqueDefinition]:
    catalog: dict[str, TechniqueDefinition] = {}
    for family in _FAMILIES:
        for j in range(4):
            tid = f"{family.value}_{j}"
            catalog[tid] = TechniqueDefinition(
                technique_id=tid,
                name_japanese=f"Test-{family.value}-{j}",
                name_english=f"Synthetic {family.value} #{j}",
                family=family,
                subfamily="forward_throw",
                kodokan_status=KodokanStatus.GOKYO_NO_WAZA,
                canonical_grip_signature=CanonicalGripSignature(
                    tori_required_grips=[
                        GripSpec(
                            hand=GripHand.TORI_RIGHT,
                            target_region=GripTargetRegion.UKE_LAPEL_HIGH,
                            minimum_depth=GripDepth.CONTROLLED,
                        ),
                    ],
                ),
                kuzushi_vector=["forward_pure"],
                couple_type="placeholder",
                posture_requirements=UkePostureRequirement.ANY,
                base_difficulty=40 + j * 5,
                failed_throw_consequence=FailedThrowConsequence.TORI_TO_KNEES,
                era_introduced=1895,
            )
    return catalog


_ALL_TECHNIQUE_IDS: list[str] = [
    f"{family.value}_{j}" for family in _FAMILIES for j in range(4)
]


# ---------------------------------------------------------------------------
# VOCABULARY BUILDERS
# Each helper returns a vocab dict populated to roughly match a belt rank,
# tilted slightly *above* the threshold for the rank's next belt so the
# 5-year run sees real promotions. last_used_year is set to the start year
# minus 1, so techniques are "current" and won't immediately decay.
# ---------------------------------------------------------------------------
def _record(
    technique_id: str,
    tier: ProficiencyTier,
    *,
    progress: int = 0,
    source: AcquisitionSource = AcquisitionSource.SENSEI_TAUGHT,
    acquired_from: str | None = None,
    year_acquired: int = 1950,
    last_used_year: int = START_YEAR,
    executed_attempts: int = 0,
    executed_successes: int = 0,
    defended_attempts: int = 0,
    defended_successes: int = 0,
) -> TechniqueRecord:
    return TechniqueRecord(
        technique_id=technique_id,
        proficiency_tier=tier,
        proficiency_progress=progress,
        teaching_tier=tier,
        source_of_acquisition=source,
        year_acquired=year_acquired,
        acquired_from=acquired_from,
        last_used_year=last_used_year,
        executed_attempts=executed_attempts,
        executed_successes=executed_successes,
        defended_attempts=defended_attempts,
        defended_successes=defended_successes,
    )


def _vocab_white() -> dict[str, TechniqueRecord]:
    """White belt sitting at the yellow threshold (3 proficient+ in 2
    families). Promotes to yellow in year 1.

    Disuse decay is exercised separately by curriculum gaps — techniques
    that drop out of the active drilling rotation decay naturally over the
    5-year run. No explicit `last_used_year` seeding is needed.
    """
    return {
        "te_waza_0":     _record("te_waza_0",     ProficiencyTier.PROFICIENT),
        "te_waza_1":     _record("te_waza_1",     ProficiencyTier.PROFICIENT),
        "koshi_waza_0":  _record("koshi_waza_0",  ProficiencyTier.PROFICIENT),
        "koshi_waza_1":  _record("koshi_waza_1",  ProficiencyTier.NOVICE, progress=60),
    }


def _vocab_yellow() -> dict[str, TechniqueRecord]:
    """Yellow belt at the green threshold (7 proficient+ + 2 intermediate+
    + 4 families)."""
    vocab: dict[str, TechniqueRecord] = {}
    profs = [
        "te_waza_0", "te_waza_1",
        "koshi_waza_0", "koshi_waza_1",
        "ashi_waza_0", "ashi_waza_1",
        "sutemi_waza_0",   # 4th family at proficient
    ]
    for tid in profs:
        vocab[tid] = _record(tid, ProficiencyTier.PROFICIENT)
    inters = ["te_waza_2", "koshi_waza_2"]
    for tid in inters:
        vocab[tid] = _record(tid, ProficiencyTier.INTERMEDIATE)
    return vocab


def _vocab_green() -> dict[str, TechniqueRecord]:
    """Green belt at the brown_3 threshold (11 proficient+, 5 intermediate+,
    2 competitive+, 3 families)."""
    vocab: dict[str, TechniqueRecord] = {}
    profs = [
        "te_waza_0", "te_waza_1",
        "koshi_waza_0", "koshi_waza_1",
        "ashi_waza_0", "ashi_waza_1",
        "sutemi_waza_0",
    ]
    inters = ["te_waza_2", "te_waza_3", "koshi_waza_2", "ashi_waza_2"]
    comps = ["koshi_waza_3", "ashi_waza_3"]
    for tid in profs:
        vocab[tid] = _record(tid, ProficiencyTier.PROFICIENT)
    for tid in inters:
        vocab[tid] = _record(tid, ProficiencyTier.INTERMEDIATE)
    for tid in comps:
        vocab[tid] = _record(tid, ProficiencyTier.COMPETITIVE)
    return vocab


def _vocab_brown() -> dict[str, TechniqueRecord]:
    """Brown_2 at the brown_1 threshold (15 proficient+, 9 intermediate+,
    4 competitive+, 1 expert+, 3 families)."""
    vocab: dict[str, TechniqueRecord] = {}
    experts = ["te_waza_0"]
    comps = ["te_waza_1", "koshi_waza_0", "ashi_waza_0", "ne_waza_0"]
    inters = [
        "te_waza_2", "te_waza_3",
        "koshi_waza_1", "koshi_waza_2",
        "ashi_waza_1",
    ]
    profs = [
        "koshi_waza_3", "ashi_waza_2", "ashi_waza_3",
        "sutemi_waza_0", "sutemi_waza_1",
        "ne_waza_1",
    ]
    for tid in experts:
        vocab[tid] = _record(tid, ProficiencyTier.EXPERT)
    for tid in comps:
        vocab[tid] = _record(tid, ProficiencyTier.COMPETITIVE)
    for tid in inters:
        vocab[tid] = _record(tid, ProficiencyTier.INTERMEDIATE)
    for tid in profs:
        vocab[tid] = _record(tid, ProficiencyTier.PROFICIENT)
    return vocab


def _vocab_shodan() -> dict[str, TechniqueRecord]:
    """Shodan-level vocabulary tilted toward an eventual nidan promotion."""
    vocab = {}
    # 11 at intermediate, 5 at competitive, 2 at expert — meets shodan and
    # approaches nidan.
    expert_ids = ["te_waza_0", "koshi_waza_0"]
    competitive_ids = ["te_waza_1", "koshi_waza_1", "ashi_waza_0", "ashi_waza_1", "ne_waza_0"]
    intermediate_ids = ["te_waza_2", "te_waza_3", "koshi_waza_2", "koshi_waza_3",
                        "ashi_waza_2", "ashi_waza_3",
                        "sutemi_waza_0", "sutemi_waza_1",
                        "ne_waza_1", "ne_waza_2", "ne_waza_3"]
    for tid in expert_ids:
        vocab[tid] = _record(tid, ProficiencyTier.EXPERT, progress=20)
    for tid in competitive_ids:
        vocab[tid] = _record(tid, ProficiencyTier.COMPETITIVE, progress=30)
    for tid in intermediate_ids:
        vocab[tid] = _record(tid, ProficiencyTier.INTERMEDIATE, progress=40)
    return vocab


def _vocab_assistant_sensei(is_cranford: bool) -> dict[str, TechniqueRecord]:
    """Assistant sensei — shodan-equivalent. The Cranford assistant holds
    te_waza_0 at COMPETITIVE so the Cranford head sensei has a lineage
    inheritor for the legendary qualification check."""
    vocab = _vocab_shodan()
    if is_cranford:
        vocab["te_waza_0"] = _record(
            "te_waza_0", ProficiencyTier.COMPETITIVE, progress=20,
        )
    return vocab


def _vocab_head_sensei(is_cranford: bool) -> dict[str, TechniqueRecord]:
    """Sandan-level head sensei vocabulary. Cranford head holds te_waza_0
    at MASTER — the pre-seeded legendary candidate."""
    vocab = {}
    # Full catalog coverage, tiered: 2 master (or expert), 4 expert, 7
    # competitive, 7 intermediate.
    master_ids = ["te_waza_0", "koshi_waza_0"] if is_cranford else ["te_waza_0"]
    expert_ids = ["koshi_waza_1", "ashi_waza_0", "ne_waza_0", "ashi_waza_1"]
    if not is_cranford:
        expert_ids = ["koshi_waza_0"] + expert_ids
    competitive_ids = ["te_waza_1", "te_waza_2", "koshi_waza_2",
                       "ashi_waza_2", "ne_waza_1", "sutemi_waza_0"]
    intermediate_ids = ["te_waza_3", "koshi_waza_3", "ashi_waza_3",
                        "sutemi_waza_1", "sutemi_waza_2", "sutemi_waza_3",
                        "ne_waza_2", "ne_waza_3"]
    for tid in master_ids:
        vocab[tid] = _record(tid, ProficiencyTier.MASTER, progress=10)
    for tid in expert_ids:
        vocab[tid] = _record(tid, ProficiencyTier.EXPERT, progress=20)
    for tid in competitive_ids:
        vocab[tid] = _record(tid, ProficiencyTier.COMPETITIVE, progress=30)
    for tid in intermediate_ids:
        vocab[tid] = _record(tid, ProficiencyTier.INTERMEDIATE, progress=40)
    return vocab


# ---------------------------------------------------------------------------
# JUDOKA BUILDERS
# ---------------------------------------------------------------------------
def _make_judoka(
    judoka_id: str,
    dojo_id: str,
    *,
    age: int,
    belt_rank: str,
    vocab: dict[str, TechniqueRecord],
    teaching_aptitude: int,
    rng: Random,
    year_last_promoted: int | None = None,
) -> WorldJudoka:
    # Spread the four base stats around the belt's expected mean to give
    # the resolver something to bite on while staying deterministic.
    base = 30 + min(90, age * 2) + rng.randint(-10, 10)
    base = max(20, min(90, base))
    return WorldJudoka(
        judoka_id=judoka_id,
        tachiwaza=base + rng.randint(-10, 10),
        ne_waza=base + rng.randint(-10, 10),
        conditioning=base + rng.randint(-15, 5),     # bias toward less cond
        fight_iq=base + rng.randint(-5, 15),         # bias toward more iq
        vocabulary=vocab,
        age=age,
        belt_rank=belt_rank,
        teaching_aptitude=teaching_aptitude,
        dojo_id=dojo_id,
        year_started_training=START_YEAR - age + 14,
        year_last_promoted=year_last_promoted,
    )


_DOJO_SPECS: tuple[tuple[str, str, str], ...] = (
    ("cranford_jkc",  "Cranford JKC",         "cranford_nj"),
    ("newark_judo",   "Newark Judo Club",     "newark_nj"),
    ("trenton_yc",    "Trenton YMCA Judo",    "trenton_nj"),
    ("paterson_dojo", "Paterson Judo",        "paterson_nj"),
)

# Student slots per dojo. Two white, two yellow, two green, one brown, one
# shodan — 8 total. Plus 1 head + 1 assistant = 10 per dojo × 4 dojos = 40.
_STUDENT_BELT_AGES: tuple[tuple[str, int], ...] = (
    ("white",    16),
    ("white",    17),
    ("yellow",   19),
    ("yellow",   20),
    ("green",    23),
    ("green",    25),
    ("brown_2",  30),
    ("shodan",   38),
)

_VOCAB_BUILDERS = {
    "white":   _vocab_white,
    "yellow":  _vocab_yellow,
    "green":   _vocab_green,
    "brown_2": _vocab_brown,
    "shodan":  _vocab_shodan,
}


# ---------------------------------------------------------------------------
# PRE-SEEDED CHRONICLE HISTORY for legendary qualification
# ---------------------------------------------------------------------------
def _seed_legendary_history(world: WorldState) -> None:
    """Plant the chronicle entries Cranford head sensei needs to qualify
    for legendary in te_waza_0 by 1960.

    Section 7 criteria:
        (1) Currently MASTER — set on the vocab record.
        (2) >= 15 tier-weighted competition points with te_waza_0 —
            5 pre-seeded MatchOutcome wins at tier_weight 4.0 = 20 points.
        (3) >= 1 student at competitive+ — Cranford assistant has it.
        (4) >= 5 years master tenure — milestone seeded for 1955.
    """
    # Master-tier milestone in 1955 so 1960 - 1955 = 5 satisfies tenure.
    world.chronicle.add(TechniqueMilestone(
        entry_id="preseed:milestone:cranford_head:te_waza_0:1955",
        year=1955,
        judoka_id="sensei_cranford_jkc",
        technique_id="te_waza_0",
        new_tier=ProficiencyTier.MASTER,
        previous_tier=ProficiencyTier.EXPERT,
        triggering_event_type=MilestoneTriggerType.MATCH_USE,
    ))

    # Pre-1960 regional competitions with their tier weights, plus one
    # winning match each.
    for year in (1955, 1956, 1957, 1958, 1959):
        comp_id = f"nj_state_{year}"
        world.competitions_by_year.setdefault(year, []).append(Competition(
            competition_id=comp_id,
            name=f"NJ State Open {year}",
            year=year,
            tier_weight=4.0,
            entrant_ids=["sensei_cranford_jkc", "sensei_newark_judo"],
        ))
        world.chronicle.add(MatchOutcome(
            entry_id=f"preseed:match:{year}",
            year=year,
            winner_id="sensei_cranford_jkc",
            loser_id="sensei_newark_judo",
            score_type=ScoreType.IPPON,
            score_value=10,
            duration_band=DurationBand.SHORT,
            tournament_id=comp_id,
            era_stamp="1950s",
            technique_id="te_waza_0",
        ))


# ---------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------------
def build_tiny_nj_world(seed: int = FIXTURE_SEED) -> WorldState:
    """Construct the tiny_nj seed world. Deterministic given `seed`."""
    rng = Random(seed)
    catalog = _build_test_catalog()
    chronicle = Chronicle()

    judoka: dict[str, WorldJudoka] = {}
    dojos: dict[str, Dojo] = {}

    for d_idx, (dojo_id, name, location) in enumerate(_DOJO_SPECS):
        # Head sensei — sandan-level, age 48–54.
        head_id = f"sensei_{dojo_id}"
        head_age = 48 + d_idx * 2
        judoka[head_id] = _make_judoka(
            head_id, dojo_id,
            age=head_age, belt_rank="sandan",
            vocab=_vocab_head_sensei(is_cranford=(d_idx == 0)),
            teaching_aptitude=70 + rng.randint(-10, 10),
            rng=rng,
            # Promoted to sandan a decade ago.
            year_last_promoted=START_YEAR - 10,
        )

        # Assistant sensei — shodan, age 28–34.
        asst_id = f"asst_{dojo_id}"
        asst_age = 28 + d_idx * 2
        judoka[asst_id] = _make_judoka(
            asst_id, dojo_id,
            age=asst_age, belt_rank="shodan",
            vocab=_vocab_assistant_sensei(is_cranford=(d_idx == 0)),
            teaching_aptitude=55 + rng.randint(-10, 10),
            rng=rng,
            year_last_promoted=START_YEAR - 3,
        )

        member_ids: set[str] = {head_id, asst_id}

        for s_idx, (belt, age) in enumerate(_STUDENT_BELT_AGES):
            sid = f"{dojo_id}_student_{s_idx}"
            vocab_builder = _VOCAB_BUILDERS[belt]
            judoka[sid] = _make_judoka(
                sid, dojo_id,
                age=age,
                belt_rank=belt,
                vocab=vocab_builder(),
                teaching_aptitude=30 + rng.randint(0, 40),
                rng=rng,
                year_last_promoted=None,             # implicit tenure met
            )
            member_ids.add(sid)

        # Curriculum: emphasis on te_waza + koshi_waza (the workhorse
        # families for tachiwaza drilling). Senseis above proficient on
        # these will teach them.
        curriculum = [
            "te_waza_0", "te_waza_1", "te_waza_2",
            "koshi_waza_0", "koshi_waza_1",
            "ashi_waza_0",
        ]

        dojos[dojo_id] = Dojo(
            dojo_id=dojo_id,
            name=name,
            location=location,
            head_sensei_id=head_id,
            member_ids=member_ids,
            curriculum=curriculum,
        )

    # Schedule one regional competition per year 1960–1964 with the top
    # competitors from each dojo (head, assistant, shodan student,
    # brown-belt student → 16 entrants → round-robin yields 120 matches/yr).
    competitions_by_year: dict[int, list[Competition]] = {}
    for year in range(FIRST_TICK_YEAR, LAST_TICK_YEAR + 1):
        entrants = []
        for spec in _DOJO_SPECS:
            dojo_id = spec[0]
            entrants.append(f"sensei_{dojo_id}")
            entrants.append(f"asst_{dojo_id}")
            entrants.append(f"{dojo_id}_student_7")  # shodan
            entrants.append(f"{dojo_id}_student_6")  # brown_2
        competitions_by_year[year] = [Competition(
            competition_id=f"nj_state_{year}",
            name=f"NJ State Open {year}",
            year=year,
            tier_weight=4.0,
            entrant_ids=entrants,
            is_championship=(year == LAST_TICK_YEAR),
        )]

    world = WorldState(
        year=START_YEAR,
        catalog=catalog,
        judoka=judoka,
        dojos=dojos,
        competitions_by_year=competitions_by_year,
        chronicle=chronicle,
        seed=seed,
    )

    # Plant the pre-1960 chronicle history for the legendary check.
    _seed_legendary_history(world)
    return world
