# chronicle.py
# Ring 2 chronicle substrate (HAJ-200).
#
# The chronicle is the world's memory — the persistent data structure that
# legends rendering reads from, succession consults, the dojo's walls render
# photographs from, and the fog-of-war system reveals layers of. Every system
# in Ring 2 that persists between weeks lives here.
#
# This module implements:
#   - ChronicleEntry base + 19 concrete entry-type dataclasses
#   - Sub-enums for entry-specific categorical fields
#   - Chronicle container with six indices and five query primitives
#
# Schema is locked by:
#   - design-notes/ring-2-worldgen-spec-v2.md Part II ("The chronicle data
#     structure"). The Linear ticket HAJ-200 supersedes Part II's preliminary
#     entry-type list (tournament_result, belt_promotion, etc.) with the
#     canonical names below.
#   - design-notes/triage/technique-vocabulary-system.md Section 9 (the ten
#     technique-vocabulary entry types).
#   - design-notes/triage/technique-vocabulary-system.md Section 8 (the
#     vocabulary_snapshot field on promotion entries).
#
# Out of scope for this ticket (deferred per HAJ-200):
#   - Prose rendering / template lookup
#   - Visibility-flag *consumption* (fog-of-war filtering) — flags exist as
#     typed data but are not yet filtered against
#   - Ledger updates from entries (HAJ-201/HAJ-202 orchestrator territory)
#   - Persistence backend choice (in-memory only; v2 OQ-8 is parked)

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Iterable, Optional

from technique_catalog import (
    AcquisitionSource,
    NamingType,
    ProficiencyTier,
)


# ===========================================================================
# ENTRY TYPE TAG
# ===========================================================================
class ChronicleEntryType(Enum):
    # Core Ring 2 substrate entries
    MATCH_OUTCOME             = "match_outcome"
    PROMOTION                 = "promotion"
    RETIREMENT                = "retirement"
    DOJO_OPEN                 = "dojo_open"
    DOJO_CLOSE                = "dojo_close"
    PHOTO_EVENT               = "photo_event"
    COHORT_FORMATION          = "cohort_formation"
    DEATH                     = "death"
    BIRTH                     = "birth"
    # Technique-vocabulary entries (technique-vocabulary-system.md Section 9)
    TECHNIQUE_LEARNED         = "technique_learned"
    TECHNIQUE_MILESTONE       = "technique_milestone"
    TECHNIQUE_DISUSE_DROP     = "technique_disuse_drop"
    TECHNIQUE_COMEBACK        = "technique_comeback"
    TECHNIQUE_NAMED           = "technique_named"
    TECHNIQUE_NAME_PROPAGATED = "technique_name_propagated"
    SEMINAR_HELD              = "seminar_held"
    SEMINAR_ATTENDED          = "seminar_attended"
    LEGENDARY_RECOGNITION     = "legendary_recognition"
    PROMOTION_TEST_HELD       = "promotion_test_held"


# ===========================================================================
# SUB-ENUMS
# Categorical fields used by one or more entry types. Sub-enums local to the
# chronicle module rather than spread across the codebase — the chronicle is
# the authoritative authoring surface for these vocabularies.
# ===========================================================================
class Quarter(Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"


class Season(Enum):
    """Seminar scheduling grain, per Section 9 (`seminar_held.season`)."""
    WINTER = "winter"
    SPRING = "spring"
    SUMMER = "summer"
    FALL   = "fall"


class ScoreType(Enum):
    """How a match terminated. Era-stamped — score categories changed under
    different IJF rule sets, but the categorical labels above are stable.
    """
    IPPON         = "ippon"
    WAZA_ARI      = "waza_ari"
    YUKO          = "yuko"             # pre-2017 rules
    KOKA          = "koka"             # pre-2009 rules
    HANSOKU_MAKE  = "hansoku_make"     # disqualification
    SHIDO_WIN     = "shido_win"        # opponent accumulated penalties
    DECISION      = "decision"         # judges' decision (era-dependent)
    GOLDEN_SCORE  = "golden_score"     # sudden-death overtime resolution


class DurationBand(Enum):
    """Coarse-grained match length. Calibration of bin boundaries is a Ring 1
    concern — these are categorical labels the chronicle stores."""
    ULTRA_SHORT  = "ultra_short"       # under ~30s
    SHORT        = "short"
    MEDIUM       = "medium"
    LONG         = "long"
    GOLDEN_SCORE = "golden_score"      # required overtime


class RetirementReason(Enum):
    AGE              = "age"
    INJURY           = "injury"
    LOSS_OF_INTEREST = "loss_of_interest"
    DEATH            = "death"


class DojoCloseReason(Enum):
    FOUNDER_DEPARTURE = "founder_departure"
    FOUNDER_DEATH     = "founder_death"
    FINANCIAL         = "financial"
    MERGED            = "merged"
    OTHER             = "other"


class DeathCause(Enum):
    NATURAL  = "natural"
    ACCIDENT = "accident"
    ILLNESS  = "illness"
    TRAGEDY  = "tragedy"               # rare in-career deaths
    OTHER    = "other"


class MilestoneTriggerType(Enum):
    """`technique_milestone.triggering_event_type` per Section 9.

    Names the breakthrough-event class — what pushed the proficiency counter
    over the tier boundary. The corresponding `triggering_event_id` resolves
    against the chronicle for prose rendering.
    """
    DRILLING_THRESHOLD     = "drilling_threshold"
    MATCH_USE              = "match_use"
    SEMINAR                = "seminar"
    SENPAI_DEMONSTRATION   = "senpai_demonstration"
    OPPONENT_THROWN_BY     = "opponent_thrown_by"
    LEGENDARY_INTERACTION  = "legendary_interaction"
    DEDICATED_STUDY        = "dedicated_study"
    ACCIDENTAL_DISCOVERY   = "accidental_discovery"


class PropagationPathway(Enum):
    """`technique_name_propagated.propagation_pathway` per Section 9."""
    SEMINAR_ATTENDANCE   = "seminar_attendance"
    LINEAGE_INHERITANCE  = "lineage_inheritance"
    REGIONAL_REPUTATION  = "regional_reputation"


class ExaminerType(Enum):
    SENSEI     = "sensei"
    FEDERATION = "federation"


class PromotionTestOutcome(Enum):
    PASS_DISTINCTION = "pass_distinction"
    PASS_STANDARD    = "pass_standard"
    PASS_CONDITIONAL = "pass_conditional"
    FAIL             = "fail"


class SeminarOutcome(Enum):
    """`seminar_attended.outcome_tier_change` per Section 9.

    Captures the attendee-side effect rather than re-encoding the resulting
    tier explicitly — Section 4 Pathway 5 already specifies the exact
    progression rules (known → novice etc.).
    """
    GAINED_AT_NOVICE    = "gained_at_novice"   # no prior vocabulary
    ADVANCED_TO_NOVICE  = "advanced_to_novice"
    ADVANCED_TO_PROFICIENT = "advanced_to_proficient"
    PROGRESS_ONLY       = "progress_only"      # at intermediate or higher


# ===========================================================================
# BASE ENTRY
# Every entry carries the common fields named in the Linear ticket: entry_id,
# year, quarter, visibility_flags, created_at_tick. The class-level
# `ENTRY_TYPE` is the discriminator the indices key on.
#
# `kw_only=True` is used so subclasses can add required fields without
# tripping over the "non-default before default" dataclass inheritance rule.
# ===========================================================================
@dataclass(kw_only=True)
class ChronicleEntry:
    entry_id: str
    year: int
    quarter: Optional[Quarter] = None
    visibility_flags: frozenset[str] = field(default_factory=frozenset)
    created_at_tick: int = 0

    ENTRY_TYPE: ClassVar[ChronicleEntryType]

    # Index contributors. Subclasses override the methods relevant to them.
    # Returning sets (not lists) so the Chronicle can dedupe in O(1) when an
    # entry references the same entity twice.
    def entity_ids(self) -> set[str]:
        """Judoka/person identifiers this entry references."""
        return set()

    def dojo_ids(self) -> set[str]:
        return set()

    def technique_ids(self) -> set[str]:
        return set()

    def tournament_ids(self) -> set[str]:
        return set()


# ---------------------------------------------------------------------------
# CORE ENTRY TYPES (Part II of ring-2-worldgen-spec-v2.md)
# ---------------------------------------------------------------------------
@dataclass(kw_only=True)
class MatchOutcome(ChronicleEntry):
    """One match between two judoka.

    `technique_id` is the new field added per technique-vocabulary-system.md
    — the offensive/defensive ledger updates in HAJ-201/HAJ-202 need to know
    *which* technique fired in the deciding score.
    """
    winner_id: str
    loser_id: str
    score_type: ScoreType
    score_value: int                                # era-dependent points
    duration_band: DurationBand
    tournament_id: Optional[str] = None
    era_stamp: str                                  # rules-era tag
    technique_id: Optional[str] = None              # what scored, when known

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.MATCH_OUTCOME

    def entity_ids(self) -> set[str]:
        return {self.winner_id, self.loser_id}

    def technique_ids(self) -> set[str]:
        return {self.technique_id} if self.technique_id else set()

    def tournament_ids(self) -> set[str]:
        return {self.tournament_id} if self.tournament_id else set()


@dataclass(kw_only=True)
class Promotion(ChronicleEntry):
    """Belt promotion.

    `vocabulary_snapshot` freezes the judoka's vocabulary at promotion time
    per Section 8 — enables retrospective chronicle prose ("when Tanaka
    earned shodan in 1971, his uchi-mata was already at competitive").
    """
    judoka_id: str
    from_rank: str
    to_rank: str
    awarding_sensei_id: Optional[str] = None
    ceremony_id: Optional[str] = None
    vocabulary_snapshot: dict[str, ProficiencyTier] = field(default_factory=dict)

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.PROMOTION

    def entity_ids(self) -> set[str]:
        ids = {self.judoka_id}
        if self.awarding_sensei_id:
            ids.add(self.awarding_sensei_id)
        return ids

    def technique_ids(self) -> set[str]:
        return set(self.vocabulary_snapshot.keys())


@dataclass(kw_only=True)
class Retirement(ChronicleEntry):
    judoka_id: str
    reason: RetirementReason
    final_state_snapshot: dict[str, object] = field(default_factory=dict)

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.RETIREMENT

    def entity_ids(self) -> set[str]:
        return {self.judoka_id}


@dataclass(kw_only=True)
class DojoOpen(ChronicleEntry):
    dojo_id: str
    founding_sensei_ids: list[str] = field(default_factory=list)
    discipline: str                                 # judo | bjj | boxing | ...
    location_id: Optional[str] = None

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.DOJO_OPEN

    def entity_ids(self) -> set[str]:
        return set(self.founding_sensei_ids)

    def dojo_ids(self) -> set[str]:
        return {self.dojo_id}


@dataclass(kw_only=True)
class DojoClose(ChronicleEntry):
    dojo_id: str
    reason: DojoCloseReason
    final_state_snapshot: dict[str, object] = field(default_factory=dict)

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.DOJO_CLOSE

    def dojo_ids(self) -> set[str]:
        return {self.dojo_id}


@dataclass(kw_only=True)
class PhotoEvent(ChronicleEntry):
    """Group photograph. Part II names this as a load-bearing chronicle
    surface — the dojo's physical walls render photographs from these
    entries (Commitment 5)."""
    dojo_id: str
    occasion: str                                   # "1972 NJ State Open team photo"
    participant_ids: list[str] = field(default_factory=list)
    era_visual_style: str                           # "1960s_color" | "1980s_polaroid" | ...

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.PHOTO_EVENT

    def entity_ids(self) -> set[str]:
        return set(self.participant_ids)

    def dojo_ids(self) -> set[str]:
        return {self.dojo_id}


@dataclass(kw_only=True)
class CohortFormation(ChronicleEntry):
    """A cohort of students enrolling within a 12-month window (v2 Part II,
    "Cohort tracking as a first-class entity")."""
    dojo_id: str
    cohort_id: str
    founding_member_ids: list[str] = field(default_factory=list)
    intake_year: int

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.COHORT_FORMATION

    def entity_ids(self) -> set[str]:
        return set(self.founding_member_ids)

    def dojo_ids(self) -> set[str]:
        return {self.dojo_id}


@dataclass(kw_only=True)
class Death(ChronicleEntry):
    entity_id: str
    cause: DeathCause
    age: int
    era_stamp: str

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.DEATH

    def entity_ids(self) -> set[str]:
        return {self.entity_id}


@dataclass(kw_only=True)
class Birth(ChronicleEntry):
    child_id: str
    parent_ids: list[str] = field(default_factory=list)

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.BIRTH

    def entity_ids(self) -> set[str]:
        return {self.child_id, *self.parent_ids}


# ---------------------------------------------------------------------------
# TECHNIQUE-VOCABULARY ENTRY TYPES (technique-vocabulary-system.md Section 9)
# ---------------------------------------------------------------------------
@dataclass(kw_only=True)
class TechniqueLearned(ChronicleEntry):
    judoka_id: str
    technique_id: str
    source_pathway: AcquisitionSource
    source_entity_id: Optional[str] = None          # sensei / opponent / host
    source_event_id: Optional[str] = None           # match / seminar entry_id
    starting_tier: ProficiencyTier

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.TECHNIQUE_LEARNED

    def entity_ids(self) -> set[str]:
        ids = {self.judoka_id}
        if self.source_entity_id:
            ids.add(self.source_entity_id)
        return ids

    def technique_ids(self) -> set[str]:
        return {self.technique_id}


@dataclass(kw_only=True)
class TechniqueMilestone(ChronicleEntry):
    """A tier boundary crossing. The triggering event is the breakthrough
    moment — the activity that pushed the counter from 98% to 100%."""
    judoka_id: str
    technique_id: str
    new_tier: ProficiencyTier
    previous_tier: ProficiencyTier
    triggering_event_type: MilestoneTriggerType
    triggering_event_id: Optional[str] = None       # references another entry

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.TECHNIQUE_MILESTONE

    def entity_ids(self) -> set[str]:
        return {self.judoka_id}

    def technique_ids(self) -> set[str]:
        return {self.technique_id}


@dataclass(kw_only=True)
class TechniqueDisuseDrop(ChronicleEntry):
    judoka_id: str
    technique_id: str
    new_tier: ProficiencyTier
    previous_tier: ProficiencyTier
    years_since_last_use: int

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.TECHNIQUE_DISUSE_DROP

    def entity_ids(self) -> set[str]:
        return {self.judoka_id}

    def technique_ids(self) -> set[str]:
        return {self.technique_id}


@dataclass(kw_only=True)
class TechniqueComeback(ChronicleEntry):
    judoka_id: str
    technique_id: str
    regained_tier: ProficiencyTier
    triggering_event_id: Optional[str] = None

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.TECHNIQUE_COMEBACK

    def entity_ids(self) -> set[str]:
        return {self.judoka_id}

    def technique_ids(self) -> set[str]:
        return {self.technique_id}


@dataclass(kw_only=True)
class TechniqueNamed(ChronicleEntry):
    """A custom name applied to a technique within a dojo's overlay
    (technique-vocabulary-system.md Section 2)."""
    dojo_id: str
    technique_id: str
    custom_name: str
    naming_judoka_id: str
    naming_type: NamingType
    triggering_event_id: Optional[str] = None       # the mastery milestone

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.TECHNIQUE_NAMED

    def entity_ids(self) -> set[str]:
        return {self.naming_judoka_id}

    def dojo_ids(self) -> set[str]:
        return {self.dojo_id}

    def technique_ids(self) -> set[str]:
        return {self.technique_id}


@dataclass(kw_only=True)
class TechniqueNamePropagated(ChronicleEntry):
    """A dojo adopts a custom name from another dojo's overlay."""
    source_dojo_id: str
    target_dojo_id: str
    technique_id: str
    custom_name: str
    propagation_pathway: PropagationPathway

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.TECHNIQUE_NAME_PROPAGATED

    def dojo_ids(self) -> set[str]:
        return {self.source_dojo_id, self.target_dojo_id}

    def technique_ids(self) -> set[str]:
        return {self.technique_id}


@dataclass(kw_only=True)
class SeminarHeld(ChronicleEntry):
    seminar_event_id: str
    host_judoka_id: str
    host_dojo_id: str
    technique_id: str
    season: Season
    attendee_count: int
    attendee_dojo_count: int

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.SEMINAR_HELD

    def entity_ids(self) -> set[str]:
        return {self.host_judoka_id}

    def dojo_ids(self) -> set[str]:
        return {self.host_dojo_id}

    def technique_ids(self) -> set[str]:
        return {self.technique_id}


@dataclass(kw_only=True)
class SeminarAttended(ChronicleEntry):
    """Per-attendee record. Both `seminar_held` and `seminar_attended`
    reference the same `seminar_event_id` so a seminar's full attendee list
    can be reconstructed by querying for the event id."""
    seminar_event_id: str
    attendee_judoka_id: str
    attendee_dojo_id: str
    technique_id: str
    outcome_tier_change: SeminarOutcome

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.SEMINAR_ATTENDED

    def entity_ids(self) -> set[str]:
        return {self.attendee_judoka_id}

    def dojo_ids(self) -> set[str]:
        return {self.attendee_dojo_id}

    def technique_ids(self) -> set[str]:
        return {self.technique_id}


@dataclass(kw_only=True)
class LegendaryRecognition(ChronicleEntry):
    judoka_id: str
    technique_id: str
    qualifying_competition_score: float             # tier-weighted points
    qualifying_lineage_inheritor_ids: list[str] = field(default_factory=list)
    tenure_years_at_master: int

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.LEGENDARY_RECOGNITION

    def entity_ids(self) -> set[str]:
        return {self.judoka_id, *self.qualifying_lineage_inheritor_ids}

    def technique_ids(self) -> set[str]:
        return {self.technique_id}


@dataclass(kw_only=True)
class PromotionTestHeld(ChronicleEntry):
    judoka_id: str
    from_belt: str
    to_belt: str
    examiner_id: str
    examiner_type: ExaminerType
    outcome: PromotionTestOutcome
    conditions_noted: Optional[str] = None
    vocabulary_snapshot_at_test: dict[str, ProficiencyTier] = field(default_factory=dict)

    ENTRY_TYPE: ClassVar[ChronicleEntryType] = ChronicleEntryType.PROMOTION_TEST_HELD

    def entity_ids(self) -> set[str]:
        return {self.judoka_id, self.examiner_id}

    def technique_ids(self) -> set[str]:
        return set(self.vocabulary_snapshot_at_test.keys())


# ===========================================================================
# CHRONICLE CONTAINER
# In-memory indexed store. Storage-backend choice (v2 OQ-8) is parked; the
# query primitives are written so a future backend swap is a contained
# change — callers do not see the index structure.
# ===========================================================================
class Chronicle:
    """The world's memory.

    Six indices (entity, year, type, dojo, tournament, technique) plus the
    forward entry table. All index values are entry_id lists in insertion
    order; the orchestrator is responsible for inserting in chronological
    order, so insertion order *is* chronological order at read time.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ChronicleEntry] = {}
        self._by_entity: dict[str, list[str]] = defaultdict(list)
        self._by_year: dict[int, list[str]] = defaultdict(list)
        self._by_type: dict[ChronicleEntryType, list[str]] = defaultdict(list)
        self._by_dojo: dict[str, list[str]] = defaultdict(list)
        self._by_tournament: dict[str, list[str]] = defaultdict(list)
        self._by_technique: dict[str, list[str]] = defaultdict(list)
        # Inverse entity index: entry_id → set of entity_ids it references.
        # Materialised at insert time so co-actor queries don't re-derive it.
        self._entry_entities: dict[str, set[str]] = {}

    # ---- mutation --------------------------------------------------------
    def add(self, entry: ChronicleEntry) -> None:
        if entry.entry_id in self._entries:
            raise ValueError(
                f"duplicate chronicle entry_id '{entry.entry_id}'"
            )
        self._entries[entry.entry_id] = entry
        self._by_year[entry.year].append(entry.entry_id)
        self._by_type[entry.ENTRY_TYPE].append(entry.entry_id)

        entity_ids = entry.entity_ids()
        self._entry_entities[entry.entry_id] = set(entity_ids)
        for eid in entity_ids:
            self._by_entity[eid].append(entry.entry_id)
        for did in entry.dojo_ids():
            self._by_dojo[did].append(entry.entry_id)
        for tid in entry.technique_ids():
            self._by_technique[tid].append(entry.entry_id)
        for tournid in entry.tournament_ids():
            self._by_tournament[tournid].append(entry.entry_id)

    def extend(self, entries: Iterable[ChronicleEntry]) -> None:
        for entry in entries:
            self.add(entry)

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, entry_id: object) -> bool:
        return entry_id in self._entries

    def get(self, entry_id: str) -> Optional[ChronicleEntry]:
        return self._entries.get(entry_id)

    # ---- inverse-entity lookup ------------------------------------------
    def entities_in(self, entry_or_id: object) -> set[str]:
        """The "inverse" half of the by-entity index: given an entry (or its
        id), return the entity ids it references. O(1)."""
        if isinstance(entry_or_id, ChronicleEntry):
            entry_id = entry_or_id.entry_id
        else:
            entry_id = entry_or_id  # type: ignore[assignment]
        return set(self._entry_entities.get(entry_id, set()))

    # ---- query primitives -----------------------------------------------
    def entries_for(
        self,
        entity_id: str,
        since: Optional[int] = None,
        until: Optional[int] = None,
    ) -> list[ChronicleEntry]:
        """All entries referencing `entity_id`, optionally bounded by year.

        `since` and `until` are inclusive year bounds.
        """
        return [
            self._entries[eid]
            for eid in self._by_entity.get(entity_id, ())
            if self._in_year_range(self._entries[eid].year, since, until)
        ]

    def matches_in_year(self, year: int) -> list[MatchOutcome]:
        """All `match_outcome` entries that occurred in `year`."""
        return [
            self._entries[eid]  # type: ignore[misc]
            for eid in self._by_year.get(year, ())
            if self._entries[eid].ENTRY_TYPE is ChronicleEntryType.MATCH_OUTCOME
        ]

    def events_of_type(
        self,
        entry_type: ChronicleEntryType,
        year_range: Optional[tuple[int, int]] = None,
    ) -> list[ChronicleEntry]:
        """All entries of `entry_type`, optionally bounded by (start, end)
        inclusive years."""
        since, until = (year_range if year_range is not None else (None, None))
        return [
            self._entries[eid]
            for eid in self._by_type.get(entry_type, ())
            if self._in_year_range(self._entries[eid].year, since, until)
        ]

    def dojo_history(self, dojo_id: str) -> list[ChronicleEntry]:
        """All entries referencing `dojo_id`."""
        return [self._entries[eid] for eid in self._by_dojo.get(dojo_id, ())]

    def technique_events(
        self,
        technique_id: str,
        year_range: Optional[tuple[int, int]] = None,
    ) -> list[ChronicleEntry]:
        """All entries referencing `technique_id`, optionally bounded."""
        since, until = (year_range if year_range is not None else (None, None))
        return [
            self._entries[eid]
            for eid in self._by_technique.get(technique_id, ())
            if self._in_year_range(self._entries[eid].year, since, until)
        ]

    # ---- tournament passthrough -----------------------------------------
    # The Linear ticket names a tournament index but no dedicated query
    # primitive; expose a thin lookup so callers don't need to reach into
    # private state.
    def tournament_entries(self, tournament_id: str) -> list[ChronicleEntry]:
        return [self._entries[eid] for eid in self._by_tournament.get(tournament_id, ())]

    # ---- helpers --------------------------------------------------------
    @staticmethod
    def _in_year_range(year: int, since: Optional[int], until: Optional[int]) -> bool:
        if since is not None and year < since:
            return False
        if until is not None and year > until:
            return False
        return True
