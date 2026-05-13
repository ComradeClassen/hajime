# test_chronicle.py — HAJ-200 acceptance tests.
#
# Exercises src/chronicle.py against a hand-constructed multi-year, multi-
# dojo fixture covering every entry type from the Linear ticket. Per the
# acceptance criteria:
#   - All entry types have dataclass implementations (constructed below)
#   - All five query primitives return expected results
#   - Tests cover entity lookup, year filtering, event-type filtering,
#     technique filtering, empty-chronicle behaviour
#   - Test fixture is hand-constructed (no orchestrator)

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chronicle import (
    Birth,
    Chronicle,
    ChronicleEntry,
    ChronicleEntryType,
    CohortFormation,
    Death,
    DeathCause,
    DojoClose,
    DojoCloseReason,
    DojoOpen,
    DurationBand,
    ExaminerType,
    LegendaryRecognition,
    MatchOutcome,
    MilestoneTriggerType,
    PhotoEvent,
    Promotion,
    PromotionTestHeld,
    PromotionTestOutcome,
    PropagationPathway,
    Quarter,
    Retirement,
    RetirementReason,
    ScoreType,
    Season,
    SeminarAttended,
    SeminarHeld,
    SeminarOutcome,
    TechniqueComeback,
    TechniqueDisuseDrop,
    TechniqueLearned,
    TechniqueMilestone,
    TechniqueNamed,
    TechniqueNamePropagated,
)
from technique_catalog import AcquisitionSource, NamingType, ProficiencyTier


# ---------------------------------------------------------------------------
# FIXTURE
# A small but representative slice: two dojos (Cranford JKC and Newark Judo),
# three judoka (Tanaka, Yamada, Okada), a tournament, two techniques
# (uchi_mata, seoi_nage), 1962–1985. Constructed by hand — no orchestrator —
# per the ticket's "hand-constructed (not orchestrator-driven)" requirement.
# ---------------------------------------------------------------------------
@pytest.fixture
def populated_chronicle() -> Chronicle:
    c = Chronicle()
    c.extend([
        # 1962 — Cranford JKC opens.
        DojoOpen(
            entry_id="e_dojo_cranford_open",
            year=1962,
            quarter=Quarter.Q3,
            dojo_id="cranford_jkc",
            founding_sensei_ids=["sensei_yonezuka"],
            discipline="judo",
            location_id="cranford_nj",
        ),
        # 1964 — first cohort forms.
        CohortFormation(
            entry_id="e_cohort_1964",
            year=1964,
            dojo_id="cranford_jkc",
            cohort_id="cranford_1964",
            founding_member_ids=["tanaka", "yamada"],
            intake_year=1964,
        ),
        # 1965 — Tanaka learns uchi_mata from his sensei (Section 4 Pathway 1).
        TechniqueLearned(
            entry_id="e_tanaka_learned_uchi",
            year=1965,
            judoka_id="tanaka",
            technique_id="uchi_mata",
            source_pathway=AcquisitionSource.SENSEI_TAUGHT,
            source_entity_id="sensei_yonezuka",
            starting_tier=ProficiencyTier.KNOWN,
        ),
        # 1968 — Tanaka beats Yamada with uchi_mata at the NJ State Open.
        MatchOutcome(
            entry_id="e_match_1968_state_open",
            year=1968,
            quarter=Quarter.Q4,
            winner_id="tanaka",
            loser_id="yamada",
            score_type=ScoreType.IPPON,
            score_value=10,
            duration_band=DurationBand.MEDIUM,
            tournament_id="nj_state_open_1968",
            era_stamp="ijf_1967_rules",
            technique_id="uchi_mata",
        ),
        # 1969 — Tanaka's uchi_mata milestones to intermediate.
        TechniqueMilestone(
            entry_id="e_tanaka_uchi_intermediate",
            year=1969,
            judoka_id="tanaka",
            technique_id="uchi_mata",
            new_tier=ProficiencyTier.INTERMEDIATE,
            previous_tier=ProficiencyTier.PROFICIENT,
            triggering_event_type=MilestoneTriggerType.MATCH_USE,
            triggering_event_id="e_match_1968_state_open",
        ),
        # 1970 — Tanaka earns shodan, with vocabulary snapshot.
        Promotion(
            entry_id="e_tanaka_shodan",
            year=1970,
            judoka_id="tanaka",
            from_rank="brown_1",
            to_rank="shodan",
            awarding_sensei_id="sensei_yonezuka",
            vocabulary_snapshot={
                "uchi_mata": ProficiencyTier.INTERMEDIATE,
                "seoi_nage": ProficiencyTier.PROFICIENT,
            },
        ),
        # 1970 — promotion test entry, same year, same judoka.
        PromotionTestHeld(
            entry_id="e_tanaka_shodan_test",
            year=1970,
            judoka_id="tanaka",
            from_belt="brown_1",
            to_belt="shodan",
            examiner_id="sensei_yonezuka",
            examiner_type=ExaminerType.SENSEI,
            outcome=PromotionTestOutcome.PASS_STANDARD,
            vocabulary_snapshot_at_test={
                "uchi_mata": ProficiencyTier.INTERMEDIATE,
                "seoi_nage": ProficiencyTier.PROFICIENT,
            },
        ),
        # 1972 — Okada is born (a future student).
        Birth(
            entry_id="e_okada_born",
            year=1972,
            child_id="okada",
            parent_ids=["okada_father", "okada_mother"],
        ),
        # 1972 — Cranford team photo.
        PhotoEvent(
            entry_id="e_photo_1972",
            year=1972,
            dojo_id="cranford_jkc",
            occasion="1972 NJ State Open team photo",
            participant_ids=["tanaka", "yamada", "sensei_yonezuka"],
            era_visual_style="1970s_color",
        ),
        # 1975 — Newark Judo opens, a rival dojo.
        DojoOpen(
            entry_id="e_dojo_newark_open",
            year=1975,
            dojo_id="newark_judo",
            founding_sensei_ids=["sensei_watanabe"],
            discipline="judo",
            location_id="newark_nj",
        ),
        # 1976 — Yamada thrown by Tanaka's uchi_mata, picks it up.
        TechniqueLearned(
            entry_id="e_yamada_learned_uchi",
            year=1976,
            judoka_id="yamada",
            technique_id="uchi_mata",
            source_pathway=AcquisitionSource.THROWN_BY_OPPONENT,
            source_entity_id="tanaka",
            source_event_id="e_match_1968_state_open",
            starting_tier=ProficiencyTier.KNOWN,
        ),
        # 1980 — Tanaka named uchi_mata within Cranford ("Cranford's uchi-mata").
        TechniqueNamed(
            entry_id="e_uchi_named_cranford",
            year=1980,
            dojo_id="cranford_jkc",
            technique_id="uchi_mata",
            custom_name="Cranford's uchi-mata",
            naming_judoka_id="tanaka",
            naming_type=NamingType.DOJO,
        ),
        # 1981 — Tanaka recognised legendary in uchi_mata.
        LegendaryRecognition(
            entry_id="e_tanaka_legendary",
            year=1981,
            judoka_id="tanaka",
            technique_id="uchi_mata",
            qualifying_competition_score=18.5,
            qualifying_lineage_inheritor_ids=["yamada"],
            tenure_years_at_master=6,
        ),
        # 1982 — Tanaka hosts a seminar at Cranford.
        SeminarHeld(
            entry_id="e_tanaka_seminar_1982",
            year=1982,
            seminar_event_id="seminar_1982_cranford",
            host_judoka_id="tanaka",
            host_dojo_id="cranford_jkc",
            technique_id="uchi_mata",
            season=Season.SPRING,
            attendee_count=24,
            attendee_dojo_count=6,
        ),
        # 1982 — Newark-judoka Okada attends the seminar (cross-dojo propagation).
        SeminarAttended(
            entry_id="e_okada_attended_1982",
            year=1982,
            seminar_event_id="seminar_1982_cranford",
            attendee_judoka_id="okada",
            attendee_dojo_id="newark_judo",
            technique_id="uchi_mata",
            outcome_tier_change=SeminarOutcome.ADVANCED_TO_PROFICIENT,
        ),
        # 1982 — name propagates from Cranford to Newark via the seminar.
        TechniqueNamePropagated(
            entry_id="e_uchi_name_propagated_newark",
            year=1982,
            source_dojo_id="cranford_jkc",
            target_dojo_id="newark_judo",
            technique_id="uchi_mata",
            custom_name="Cranford's uchi-mata",
            propagation_pathway=PropagationPathway.SEMINAR_ATTENDANCE,
        ),
        # 1983 — Yamada lets seoi_nage rust; disuse drop.
        TechniqueDisuseDrop(
            entry_id="e_yamada_seoi_decay",
            year=1983,
            judoka_id="yamada",
            technique_id="seoi_nage",
            new_tier=ProficiencyTier.INTERMEDIATE,
            previous_tier=ProficiencyTier.COMPETITIVE,
            years_since_last_use=3,
        ),
        # 1984 — Yamada returns to drilling, comeback fires.
        TechniqueComeback(
            entry_id="e_yamada_seoi_comeback",
            year=1984,
            judoka_id="yamada",
            technique_id="seoi_nage",
            regained_tier=ProficiencyTier.COMPETITIVE,
        ),
        # 1985 — Tanaka retires.
        Retirement(
            entry_id="e_tanaka_retired",
            year=1985,
            judoka_id="tanaka",
            reason=RetirementReason.AGE,
        ),
        # 1985 — Newark Judo closes; founder leaves.
        DojoClose(
            entry_id="e_newark_closed",
            year=1985,
            dojo_id="newark_judo",
            reason=DojoCloseReason.FOUNDER_DEPARTURE,
        ),
        # 1986 — old Yamada-father dies (a non-active entity, but in chronicle).
        Death(
            entry_id="e_yamada_father_died",
            year=1986,
            entity_id="yamada_father",
            cause=DeathCause.NATURAL,
            age=78,
            era_stamp="1980s",
        ),
    ])
    return c


# ===========================================================================
# Dataclass shape
# ===========================================================================
def test_every_entry_type_has_a_concrete_class():
    """Every value in `ChronicleEntryType` is reachable through a concrete
    dataclass — guards against an entry-type enum growing without an
    implementation behind it."""
    implemented = {
        cls.ENTRY_TYPE
        for cls in ChronicleEntry.__subclasses__()
    }
    assert implemented == set(ChronicleEntryType)


def test_match_outcome_records_winner_loser_and_technique():
    match = MatchOutcome(
        entry_id="m1",
        year=1970,
        winner_id="a",
        loser_id="b",
        score_type=ScoreType.WAZA_ARI,
        score_value=7,
        duration_band=DurationBand.SHORT,
        era_stamp="ijf_1967_rules",
        technique_id="seoi_nage",
    )
    assert match.entity_ids() == {"a", "b"}
    assert match.technique_ids() == {"seoi_nage"}
    assert match.tournament_ids() == set()


def test_match_outcome_without_technique_returns_empty_technique_ids():
    match = MatchOutcome(
        entry_id="m2",
        year=1970,
        winner_id="a",
        loser_id="b",
        score_type=ScoreType.DECISION,
        score_value=0,
        duration_band=DurationBand.LONG,
        era_stamp="ijf_1967_rules",
    )
    assert match.technique_ids() == set()


# ===========================================================================
# Empty-chronicle behaviour
# ===========================================================================
class TestEmptyChronicle:
    def test_length_zero(self):
        assert len(Chronicle()) == 0

    def test_entity_lookup_empty(self):
        assert Chronicle().entries_for("nobody") == []

    def test_year_lookup_empty(self):
        assert Chronicle().matches_in_year(1972) == []

    def test_type_lookup_empty(self):
        assert Chronicle().events_of_type(ChronicleEntryType.PROMOTION) == []

    def test_dojo_lookup_empty(self):
        assert Chronicle().dojo_history("nowhere") == []

    def test_technique_lookup_empty(self):
        assert Chronicle().technique_events("nothing") == []

    def test_unknown_entry_id_yields_none(self):
        assert Chronicle().get("missing") is None
        assert "missing" not in Chronicle()


# ===========================================================================
# Mutation
# ===========================================================================
def test_duplicate_entry_id_is_rejected():
    c = Chronicle()
    c.add(Death(
        entry_id="d1", year=1970, entity_id="x",
        cause=DeathCause.NATURAL, age=80, era_stamp="1970s",
    ))
    with pytest.raises(ValueError, match="duplicate"):
        c.add(Death(
            entry_id="d1", year=1971, entity_id="y",
            cause=DeathCause.NATURAL, age=70, era_stamp="1970s",
        ))


# ===========================================================================
# Entity lookup (forward + inverse) + year bounds
# ===========================================================================
class TestEntityLookup:
    def test_judoka_referenced_in_many_entry_types(self, populated_chronicle):
        # Tanaka appears as winner, learner, milestone subject, promotee,
        # photo participant, namer, legendary holder, seminar host, retiree.
        entries = populated_chronicle.entries_for("tanaka")
        kinds = {e.ENTRY_TYPE for e in entries}
        assert ChronicleEntryType.MATCH_OUTCOME in kinds
        assert ChronicleEntryType.TECHNIQUE_LEARNED in kinds
        assert ChronicleEntryType.TECHNIQUE_MILESTONE in kinds
        assert ChronicleEntryType.PROMOTION in kinds
        assert ChronicleEntryType.PHOTO_EVENT in kinds
        assert ChronicleEntryType.TECHNIQUE_NAMED in kinds
        assert ChronicleEntryType.LEGENDARY_RECOGNITION in kinds
        assert ChronicleEntryType.SEMINAR_HELD in kinds
        assert ChronicleEntryType.RETIREMENT in kinds

    def test_since_until_bound_inclusively(self, populated_chronicle):
        entries = populated_chronicle.entries_for("tanaka", since=1970, until=1972)
        years = sorted(e.year for e in entries)
        # 1970 promotion + promotion-test + 1972 photo. 1968 match is excluded.
        assert min(years) == 1970 and max(years) == 1972
        for e in entries:
            assert 1970 <= e.year <= 1972

    def test_since_only_bound(self, populated_chronicle):
        entries = populated_chronicle.entries_for("tanaka", since=1980)
        assert all(e.year >= 1980 for e in entries)
        assert any(e.year == 1985 for e in entries)  # retirement included

    def test_until_only_bound(self, populated_chronicle):
        entries = populated_chronicle.entries_for("tanaka", until=1968)
        assert all(e.year <= 1968 for e in entries)

    def test_inverse_entity_lookup(self, populated_chronicle):
        # entities_in() is the inverse half — given an entry, what entities
        # does it reference? Match outcome has winner + loser only.
        entities = populated_chronicle.entities_in("e_match_1968_state_open")
        assert entities == {"tanaka", "yamada"}

    def test_inverse_entity_lookup_accepts_entry_object(self, populated_chronicle):
        entry = populated_chronicle.get("e_photo_1972")
        assert populated_chronicle.entities_in(entry) == {
            "tanaka", "yamada", "sensei_yonezuka",
        }

    def test_inverse_lookup_for_unknown_id_is_empty(self, populated_chronicle):
        assert populated_chronicle.entities_in("not_an_entry_id") == set()


# ===========================================================================
# Year filtering — matches_in_year
# ===========================================================================
class TestMatchesInYear:
    def test_finds_the_1968_match(self, populated_chronicle):
        matches = populated_chronicle.matches_in_year(1968)
        assert len(matches) == 1
        assert matches[0].entry_id == "e_match_1968_state_open"
        assert matches[0].technique_id == "uchi_mata"

    def test_quiet_year_returns_empty_list(self, populated_chronicle):
        # 1969 has a milestone but no match.
        assert populated_chronicle.matches_in_year(1969) == []

    def test_year_with_other_events_only_returns_matches(self, populated_chronicle):
        # 1982 has a seminar pair, not a match.
        assert populated_chronicle.matches_in_year(1982) == []


# ===========================================================================
# Event-type filtering — events_of_type
# ===========================================================================
class TestEventsOfType:
    def test_returns_only_target_type(self, populated_chronicle):
        promotions = populated_chronicle.events_of_type(ChronicleEntryType.PROMOTION)
        assert len(promotions) == 1
        assert promotions[0].entry_id == "e_tanaka_shodan"

    def test_year_range_inclusive(self, populated_chronicle):
        techs_learned = populated_chronicle.events_of_type(
            ChronicleEntryType.TECHNIQUE_LEARNED,
            year_range=(1960, 1970),
        )
        # 1965 Tanaka, but 1976 Yamada is excluded.
        assert len(techs_learned) == 1
        assert techs_learned[0].entry_id == "e_tanaka_learned_uchi"

    def test_year_range_excludes_boundaries_outside_window(self, populated_chronicle):
        seminars = populated_chronicle.events_of_type(
            ChronicleEntryType.SEMINAR_HELD,
            year_range=(1990, 2000),
        )
        assert seminars == []

    def test_dojo_open_entry_type(self, populated_chronicle):
        opens = populated_chronicle.events_of_type(ChronicleEntryType.DOJO_OPEN)
        ids = {e.entry_id for e in opens}
        assert ids == {"e_dojo_cranford_open", "e_dojo_newark_open"}


# ===========================================================================
# Dojo history
# ===========================================================================
class TestDojoHistory:
    def test_cranford_history_includes_open_cohort_photo_named_seminar(self, populated_chronicle):
        cranford = populated_chronicle.dojo_history("cranford_jkc")
        types = {e.ENTRY_TYPE for e in cranford}
        assert ChronicleEntryType.DOJO_OPEN in types
        assert ChronicleEntryType.COHORT_FORMATION in types
        assert ChronicleEntryType.PHOTO_EVENT in types
        assert ChronicleEntryType.TECHNIQUE_NAMED in types
        assert ChronicleEntryType.SEMINAR_HELD in types
        # The propagation entry should appear under *both* source and target
        # dojo histories.
        assert any(e.entry_id == "e_uchi_name_propagated_newark" for e in cranford)

    def test_newark_history_includes_open_close_attended_propagated(self, populated_chronicle):
        newark = populated_chronicle.dojo_history("newark_judo")
        ids = {e.entry_id for e in newark}
        assert "e_dojo_newark_open" in ids
        assert "e_newark_closed" in ids
        assert "e_okada_attended_1982" in ids
        assert "e_uchi_name_propagated_newark" in ids

    def test_unknown_dojo_returns_empty(self, populated_chronicle):
        assert populated_chronicle.dojo_history("philadelphia_dojo") == []


# ===========================================================================
# Technique filtering — technique_events
# ===========================================================================
class TestTechniqueEvents:
    def test_uchi_mata_spans_match_milestone_learned_named_seminars(self, populated_chronicle):
        uchi = populated_chronicle.technique_events("uchi_mata")
        types = {e.ENTRY_TYPE for e in uchi}
        # The full vocabulary lifecycle should be queryable in one call:
        assert ChronicleEntryType.MATCH_OUTCOME in types
        assert ChronicleEntryType.TECHNIQUE_LEARNED in types
        assert ChronicleEntryType.TECHNIQUE_MILESTONE in types
        assert ChronicleEntryType.TECHNIQUE_NAMED in types
        assert ChronicleEntryType.TECHNIQUE_NAME_PROPAGATED in types
        assert ChronicleEntryType.SEMINAR_HELD in types
        assert ChronicleEntryType.SEMINAR_ATTENDED in types
        assert ChronicleEntryType.LEGENDARY_RECOGNITION in types

    def test_seoi_nage_isolated_to_disuse_and_comeback(self, populated_chronicle):
        seoi = populated_chronicle.technique_events("seoi_nage")
        # Both promotion entries reference seoi_nage via vocabulary_snapshot,
        # plus the disuse + comeback events.
        ids = {e.entry_id for e in seoi}
        assert "e_yamada_seoi_decay" in ids
        assert "e_yamada_seoi_comeback" in ids
        assert "e_tanaka_shodan" in ids                 # via vocabulary snapshot
        assert "e_tanaka_shodan_test" in ids            # via vocabulary snapshot

    def test_year_range_filter(self, populated_chronicle):
        uchi_late = populated_chronicle.technique_events(
            "uchi_mata", year_range=(1980, 1985),
        )
        years = [e.year for e in uchi_late]
        assert all(1980 <= y <= 1985 for y in years)

    def test_unknown_technique_returns_empty(self, populated_chronicle):
        assert populated_chronicle.technique_events("kani_basami") == []


# ===========================================================================
# Tournament passthrough (named-index sanity)
# ===========================================================================
def test_tournament_index(populated_chronicle):
    matches = populated_chronicle.tournament_entries("nj_state_open_1968")
    assert len(matches) == 1
    assert matches[0].entry_id == "e_match_1968_state_open"
    # Empty bucket → empty list (no KeyError).
    assert populated_chronicle.tournament_entries("not_a_tournament") == []


# ===========================================================================
# Vocabulary-snapshot fields preserve ProficiencyTier enums
# ===========================================================================
def test_promotion_carries_vocabulary_snapshot_as_proficiency_tiers(populated_chronicle):
    entry = populated_chronicle.get("e_tanaka_shodan")
    assert isinstance(entry, Promotion)
    assert entry.vocabulary_snapshot == {
        "uchi_mata": ProficiencyTier.INTERMEDIATE,
        "seoi_nage": ProficiencyTier.PROFICIENT,
    }


def test_promotion_test_carries_vocabulary_snapshot(populated_chronicle):
    entry = populated_chronicle.get("e_tanaka_shodan_test")
    assert isinstance(entry, PromotionTestHeld)
    assert entry.vocabulary_snapshot_at_test["uchi_mata"] is ProficiencyTier.INTERMEDIATE


# ===========================================================================
# Defaults — Section "Out of scope" promises visibility flags exist as typed
# fields but are not yet filtered against.
# ===========================================================================
def test_base_entry_defaults_are_safe():
    entry = Death(
        entry_id="d_solo", year=1990, entity_id="x",
        cause=DeathCause.NATURAL, age=80, era_stamp="1990s",
    )
    assert entry.quarter is None
    assert entry.visibility_flags == frozenset()
    assert entry.created_at_tick == 0
