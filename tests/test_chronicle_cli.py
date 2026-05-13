# test_chronicle_cli.py — HAJ-203 acceptance tests.
#
# Exercises src/chronicle_cli.py against:
#   - The tiny_nj-orchestrator chronicle (the canonical end-to-end check)
#   - Hand-constructed mini chronicles for filter-by-filter coverage,
#     including paths the orchestrator doesn't currently exercise
#     (quarter values, naming, comeback, etc.)
#
# Acceptance criteria from the ticket:
#   - All four time grains (year, quarter, decade, range) work
#   - All five filter dimensions (entity-type, entity-id, event-type,
#     dojo, technique) work and compose with AND
#   - Every vocabulary-system event type is filterable
#   - Empty result set produces a clean message rather than crashing

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from chronicle import (
    Birth,
    Chronicle,
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
    PropagationPathway,
    Promotion,
    PromotionTestHeld,
    PromotionTestOutcome,
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
    TechniqueNamePropagated,
    TechniqueNamed,
)
from chronicle_cli import (
    EMPTY_MESSAGE,
    DumpFilters,
    filter_chronicle,
    format_entry,
    main,
    parse_filters,
    render_entry,
    write_dump,
)
from fixtures.seed_worlds.tiny_nj import (
    FIRST_TICK_YEAR,
    LAST_TICK_YEAR,
    build_tiny_nj_world,
)
from orchestrator import advance_year
from technique_catalog import AcquisitionSource, NamingType, ProficiencyTier


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def simulated_chronicle():
    """Run the tiny_nj seed world for 5 years and return the chronicle.

    Module-scoped — the simulation runs once and is reused across all
    tests that just need a populated chronicle to read against.
    """
    world = build_tiny_nj_world()
    for year in range(FIRST_TICK_YEAR, LAST_TICK_YEAR + 1):
        advance_year(world, year)
    return world.chronicle


@pytest.fixture
def mini_chronicle():
    """Hand-built chronicle covering entry types and quarter values the
    orchestrator does not currently emit. Lets the CLI tests cover code
    paths independently of orchestrator behaviour."""
    c = Chronicle()
    c.add(DojoOpen(
        entry_id="dojo_open_1962",
        year=1962, quarter=Quarter.Q1,
        dojo_id="cranford_jkc",
        founding_sensei_ids=["sensei_y"],
        discipline="judo",
    ))
    c.add(CohortFormation(
        entry_id="cohort_1962",
        year=1962, quarter=Quarter.Q2,
        dojo_id="cranford_jkc",
        cohort_id="cranford_1962",
        founding_member_ids=["m1", "m2", "m3"],
        intake_year=1962,
    ))
    c.add(PhotoEvent(
        entry_id="photo_1962",
        year=1962, quarter=Quarter.Q4,
        dojo_id="cranford_jkc",
        occasion="1962 NJ State Open team photo",
        participant_ids=["m1", "m2"],
        era_visual_style="1960s_color",
    ))
    c.add(MatchOutcome(
        entry_id="match_1963",
        year=1963, quarter=Quarter.Q2,
        winner_id="tanaka",
        loser_id="okada",
        score_type=ScoreType.WAZA_ARI,
        score_value=7,
        duration_band=DurationBand.MEDIUM,
        tournament_id="state_open_1963",
        era_stamp="ijf_pre_2009",
        technique_id="uchi_mata",
    ))
    c.add(Promotion(
        entry_id="promo_1963",
        year=1963, quarter=Quarter.Q3,
        judoka_id="okada",
        from_rank="white", to_rank="yellow",
        awarding_sensei_id="sensei_y",
    ))
    c.add(TechniqueLearned(
        entry_id="learned_1963",
        year=1963, quarter=Quarter.Q2,
        judoka_id="okada",
        technique_id="uchi_mata",
        source_pathway=AcquisitionSource.THROWN_BY_OPPONENT,
        source_entity_id="tanaka",
        starting_tier=ProficiencyTier.KNOWN,
    ))
    c.add(TechniqueMilestone(
        entry_id="milestone_1965",
        year=1965, quarter=Quarter.Q1,
        judoka_id="tanaka",
        technique_id="uchi_mata",
        new_tier=ProficiencyTier.COMPETITIVE,
        previous_tier=ProficiencyTier.INTERMEDIATE,
        triggering_event_type=MilestoneTriggerType.MATCH_USE,
        triggering_event_id="match_1963",
    ))
    c.add(TechniqueDisuseDrop(
        entry_id="disuse_1968",
        year=1968,
        judoka_id="okada",
        technique_id="seoi_nage",
        new_tier=ProficiencyTier.INTERMEDIATE,
        previous_tier=ProficiencyTier.COMPETITIVE,
        years_since_last_use=3,
    ))
    c.add(TechniqueComeback(
        entry_id="comeback_1970",
        year=1970,
        judoka_id="okada",
        technique_id="seoi_nage",
        regained_tier=ProficiencyTier.COMPETITIVE,
    ))
    c.add(TechniqueNamed(
        entry_id="named_1971",
        year=1971,
        dojo_id="cranford_jkc",
        technique_id="uchi_mata",
        custom_name="Cranford's uchi-mata",
        naming_judoka_id="tanaka",
        naming_type=NamingType.DOJO,
    ))
    c.add(TechniqueNamePropagated(
        entry_id="propagated_1973",
        year=1973,
        source_dojo_id="cranford_jkc",
        target_dojo_id="newark_judo",
        technique_id="uchi_mata",
        custom_name="Cranford's uchi-mata",
        propagation_pathway=PropagationPathway.SEMINAR_ATTENDANCE,
    ))
    c.add(SeminarHeld(
        entry_id="seminar_held_1973",
        year=1973,
        seminar_event_id="seminar_1973",
        host_judoka_id="tanaka",
        host_dojo_id="cranford_jkc",
        technique_id="uchi_mata",
        season=Season.SPRING,
        attendee_count=20,
        attendee_dojo_count=5,
    ))
    c.add(SeminarAttended(
        entry_id="seminar_attended_1973",
        year=1973,
        seminar_event_id="seminar_1973",
        attendee_judoka_id="okada",
        attendee_dojo_id="newark_judo",
        technique_id="uchi_mata",
        outcome_tier_change=SeminarOutcome.ADVANCED_TO_PROFICIENT,
    ))
    c.add(LegendaryRecognition(
        entry_id="legendary_1975",
        year=1975,
        judoka_id="tanaka",
        technique_id="uchi_mata",
        qualifying_competition_score=18.5,
        qualifying_lineage_inheritor_ids=["okada"],
        tenure_years_at_master=6,
    ))
    c.add(PromotionTestHeld(
        entry_id="ptest_1976",
        year=1976,
        judoka_id="okada",
        from_belt="brown_1", to_belt="shodan",
        examiner_id="sensei_y",
        examiner_type=ExaminerType.SENSEI,
        outcome=PromotionTestOutcome.PASS_STANDARD,
    ))
    c.add(Retirement(
        entry_id="retire_1980",
        year=1980,
        judoka_id="tanaka",
        reason=RetirementReason.AGE,
    ))
    c.add(DojoClose(
        entry_id="close_1985",
        year=1985,
        dojo_id="newark_judo",
        reason=DojoCloseReason.FOUNDER_DEPARTURE,
    ))
    c.add(Death(
        entry_id="death_1986",
        year=1986,
        entity_id="tanaka",
        cause=DeathCause.NATURAL,
        age=78, era_stamp="1980s",
    ))
    c.add(Birth(
        entry_id="birth_1962",
        year=1962, quarter=Quarter.Q1,
        child_id="future_judoka",
        parent_ids=["tanaka", "tanaka_spouse"],
    ))
    return c


# ===========================================================================
# ARG PARSING
# ===========================================================================
class TestArgParsing:
    def test_default_dump_has_no_filters(self):
        f = parse_filters(["dump"])
        assert f.year is None and f.quarter is None
        assert f.decade_start is None and f.year_range is None
        assert f.entity_id is None and f.event_type is None
        assert f.dojo is None and f.technique is None

    def test_year_grain(self):
        assert parse_filters(["dump", "--year", "1962"]).year == 1962

    def test_quarter_grain(self):
        f = parse_filters(["dump", "--quarter", "1962-Q2"])
        assert f.quarter == (1962, Quarter.Q2)

    def test_decade_grain(self):
        assert parse_filters(["dump", "--decade", "1960s"]).decade_start == 1960

    def test_range_grain(self):
        f = parse_filters(["dump", "--range", "1960-1969"])
        assert f.year_range == (1960, 1969)

    def test_quarter_grain_rejects_malformed(self):
        with pytest.raises(SystemExit):
            parse_filters(["dump", "--quarter", "garbage"])

    def test_decade_grain_rejects_non_decade_boundary(self):
        with pytest.raises(SystemExit):
            parse_filters(["dump", "--decade", "1963s"])

    def test_range_grain_rejects_reversed_bounds(self):
        with pytest.raises(SystemExit):
            parse_filters(["dump", "--range", "1969-1960"])

    def test_grain_options_are_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            parse_filters(["dump", "--year", "1960", "--decade", "1960s"])

    def test_entity_filter(self):
        f = parse_filters(["dump", "--entity-type", "dojo", "--entity-id", "cranford_jkc"])
        assert f.entity_type == "dojo"
        assert f.entity_id == "cranford_jkc"

    def test_entity_id_alone_defaults_to_judoka(self):
        # Forgiving common-case: "show this person's history" without
        # having to type --entity-type judoka.
        f = parse_filters(["dump", "--entity-id", "tanaka"])
        assert f.entity_type == "judoka"
        assert f.entity_id == "tanaka"

    def test_entity_type_alone_errors(self):
        with pytest.raises(SystemExit):
            parse_filters(["dump", "--entity-type", "dojo"])

    def test_event_type(self):
        f = parse_filters(["dump", "--event-type", "promotion"])
        assert f.event_type is ChronicleEntryType.PROMOTION

    def test_event_type_unknown_errors(self):
        with pytest.raises(SystemExit):
            parse_filters(["dump", "--event-type", "imaginary_event"])

    def test_dojo_filter(self):
        f = parse_filters(["dump", "--dojo", "newark_judo"])
        assert f.dojo == "newark_judo"

    def test_technique_filter(self):
        f = parse_filters(["dump", "--technique", "uchi_mata"])
        assert f.technique == "uchi_mata"


# ===========================================================================
# TIME GRAINS — filter_chronicle()
# ===========================================================================
class TestTimeGrains:
    def test_year_grain(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(year=1963))
        years = {e.year for e in out}
        assert years == {1963}

    def test_quarter_grain(self, mini_chronicle):
        # 1963-Q3 should match only the Promotion entry.
        out = filter_chronicle(mini_chronicle, DumpFilters(quarter=(1963, Quarter.Q3)))
        ids = {e.entry_id for e in out}
        assert ids == {"promo_1963"}

    def test_quarter_excludes_quarter_unset_entries(self, mini_chronicle):
        # The TechniqueDisuseDrop entry has quarter=None — even though
        # 1968 matches the year part, no quarter is set so it must not
        # appear under quarter filtering.
        out = filter_chronicle(mini_chronicle, DumpFilters(quarter=(1968, Quarter.Q1)))
        assert all(e.entry_id != "disuse_1968" for e in out)

    def test_decade_grain(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(decade_start=1960))
        for e in out:
            assert 1960 <= e.year <= 1969
        # 1970s+ entries should be excluded.
        assert all(e.year < 1970 for e in out)

    def test_range_grain(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(year_range=(1963, 1971)))
        for e in out:
            assert 1963 <= e.year <= 1971
        # Inclusive on both bounds:
        years = {e.year for e in out}
        assert 1963 in years
        assert 1971 in years

    def test_no_grain_returns_everything(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters())
        assert len(out) == len(mini_chronicle)


# ===========================================================================
# FILTER DIMENSIONS — independent
# ===========================================================================
class TestFilterDimensions:
    def test_event_type_filter(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(
            event_type=ChronicleEntryType.TECHNIQUE_NAMED,
        ))
        assert {e.entry_id for e in out} == {"named_1971"}

    def test_dojo_filter(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(dojo="newark_judo"))
        ids = {e.entry_id for e in out}
        # newark_judo appears in the propagation target and the close.
        # The seminar_attended also points at newark_judo.
        assert "propagated_1973" in ids
        assert "seminar_attended_1973" in ids
        assert "close_1985" in ids

    def test_technique_filter(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(technique="uchi_mata"))
        # Every uchi_mata-touching entry: match, learned, milestone, named,
        # propagated, seminar held, seminar attended, legendary.
        ids = {e.entry_id for e in out}
        assert "match_1963" in ids
        assert "learned_1963" in ids
        assert "milestone_1965" in ids
        assert "named_1971" in ids
        assert "propagated_1973" in ids
        assert "seminar_held_1973" in ids
        assert "seminar_attended_1973" in ids
        assert "legendary_1975" in ids

    def test_entity_filter_judoka(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(
            entity_type="judoka", entity_id="tanaka",
        ))
        ids = {e.entry_id for e in out}
        # Tanaka appears as winner, milestone subject, namer, seminar
        # host, legendary holder, retiree, decedent — and as parent of
        # the 1962 birth.
        assert "match_1963" in ids
        assert "milestone_1965" in ids
        assert "named_1971" in ids
        assert "seminar_held_1973" in ids
        assert "legendary_1975" in ids
        assert "retire_1980" in ids
        assert "death_1986" in ids
        assert "birth_1962" in ids

    def test_entity_filter_sensei_resolves_against_judoka_index(self, mini_chronicle):
        # Senseis ARE judoka; the CLI separates them as a label but they
        # resolve against the same entity index.
        out = filter_chronicle(mini_chronicle, DumpFilters(
            entity_type="sensei", entity_id="sensei_y",
        ))
        ids = {e.entry_id for e in out}
        # sensei_y founds Cranford and examines okada's promotion.
        assert "dojo_open_1962" in ids
        assert "ptest_1976" in ids

    def test_entity_filter_tournament(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(
            entity_type="tournament", entity_id="state_open_1963",
        ))
        assert {e.entry_id for e in out} == {"match_1963"}


# ===========================================================================
# FILTER COMPOSITION — AND semantics
# ===========================================================================
class TestFilterComposition:
    def test_dojo_plus_event_type(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(
            dojo="cranford_jkc",
            event_type=ChronicleEntryType.PHOTO_EVENT,
        ))
        assert {e.entry_id for e in out} == {"photo_1962"}

    def test_technique_plus_year(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(
            technique="uchi_mata",
            year=1973,
        ))
        ids = {e.entry_id for e in out}
        # In 1973 uchi_mata has: propagated, seminar_held, seminar_attended.
        assert ids == {"propagated_1973", "seminar_held_1973", "seminar_attended_1973"}

    def test_entity_plus_event_type_plus_range(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(
            entity_type="judoka", entity_id="okada",
            event_type=ChronicleEntryType.TECHNIQUE_LEARNED,
            year_range=(1960, 1970),
        ))
        assert {e.entry_id for e in out} == {"learned_1963"}

    def test_composition_can_produce_empty_result(self, mini_chronicle):
        out = filter_chronicle(mini_chronicle, DumpFilters(
            dojo="cranford_jkc",
            event_type=ChronicleEntryType.DOJO_CLOSE,
        ))
        assert out == []


# ===========================================================================
# EVERY VOCABULARY ENTRY TYPE IS FILTERABLE
# ===========================================================================
@pytest.mark.parametrize("event_type,expected_id", [
    (ChronicleEntryType.TECHNIQUE_LEARNED, "learned_1963"),
    (ChronicleEntryType.TECHNIQUE_MILESTONE, "milestone_1965"),
    (ChronicleEntryType.TECHNIQUE_DISUSE_DROP, "disuse_1968"),
    (ChronicleEntryType.TECHNIQUE_COMEBACK, "comeback_1970"),
    (ChronicleEntryType.TECHNIQUE_NAMED, "named_1971"),
    (ChronicleEntryType.TECHNIQUE_NAME_PROPAGATED, "propagated_1973"),
    (ChronicleEntryType.SEMINAR_HELD, "seminar_held_1973"),
    (ChronicleEntryType.SEMINAR_ATTENDED, "seminar_attended_1973"),
    (ChronicleEntryType.LEGENDARY_RECOGNITION, "legendary_1975"),
    (ChronicleEntryType.PROMOTION_TEST_HELD, "ptest_1976"),
])
def test_vocabulary_event_types_filterable(mini_chronicle, event_type, expected_id):
    out = filter_chronicle(mini_chronicle, DumpFilters(event_type=event_type))
    assert expected_id in {e.entry_id for e in out}


# ===========================================================================
# RENDERING
# ===========================================================================
class TestRendering:
    def test_render_every_entry_in_mini_chronicle(self, mini_chronicle):
        # Every entry must render to a non-empty string — guards against
        # a renderer being missing for one of the 19 types.
        for entry in mini_chronicle:
            rendered = render_entry(entry)
            assert isinstance(rendered, str) and rendered

    def test_format_entry_includes_year_and_quarter_tag(self, mini_chronicle):
        match = mini_chronicle.get("match_1963")
        formatted = format_entry(match)
        assert formatted.startswith("[1963-Q2] ")
        assert "tanaka" in formatted and "okada" in formatted

    def test_format_entry_uses_placeholder_when_quarter_missing(self, mini_chronicle):
        disuse = mini_chronicle.get("disuse_1968")
        formatted = format_entry(disuse)
        assert formatted.startswith("[1968-----] ")


# ===========================================================================
# OUTPUT — write_dump
# ===========================================================================
class TestWriteDump:
    def test_empty_set_emits_clean_message(self):
        stream = io.StringIO()
        write_dump([], stream)
        assert stream.getvalue() == EMPTY_MESSAGE + "\n"

    def test_grouped_by_year(self, mini_chronicle):
        # Pick three years' worth of entries.
        entries = filter_chronicle(mini_chronicle, DumpFilters(year_range=(1962, 1965)))
        stream = io.StringIO()
        write_dump(entries, stream)
        output = stream.getvalue()
        assert "=== 1962 ===" in output
        assert "=== 1963 ===" in output
        assert "=== 1965 ===" in output

    def test_output_is_chronologically_ordered(self, mini_chronicle):
        entries = filter_chronicle(mini_chronicle, DumpFilters())
        stream = io.StringIO()
        write_dump(entries, stream)
        # Pull out the "=== YYYY ===" lines and verify ascending order.
        years = []
        for line in stream.getvalue().splitlines():
            if line.startswith("=== ") and line.endswith(" ==="):
                years.append(int(line[4:-4]))
        assert years == sorted(years)


# ===========================================================================
# END-TO-END — main() against simulated chronicle
# ===========================================================================
class TestMainAgainstSimulatedChronicle:
    def test_main_with_no_filters_prints_many_lines(self, simulated_chronicle):
        stream = io.StringIO()
        rc = main(["dump"], chronicle=simulated_chronicle, stream=stream)
        assert rc == 0
        output = stream.getvalue()
        # Substrate chronicle is hundreds of entries — sanity check the
        # output is not a tiny placeholder.
        assert output.count("\n") > 100
        # Every simulated year should have a header.
        for year in range(FIRST_TICK_YEAR, LAST_TICK_YEAR + 1):
            assert f"=== {year} ===" in output

    def test_main_year_filter_narrows_output(self, simulated_chronicle):
        stream = io.StringIO()
        main(["dump", "--year", str(FIRST_TICK_YEAR)],
             chronicle=simulated_chronicle, stream=stream)
        output = stream.getvalue()
        assert f"=== {FIRST_TICK_YEAR} ===" in output
        # No other year header should appear.
        for year in range(FIRST_TICK_YEAR + 1, LAST_TICK_YEAR + 1):
            assert f"=== {year} ===" not in output

    def test_main_event_type_filter(self, simulated_chronicle):
        stream = io.StringIO()
        main(["dump", "--event-type", "promotion"],
             chronicle=simulated_chronicle, stream=stream)
        output = stream.getvalue()
        # Every line in the body is either a year header or a promotion.
        body_lines = [
            line for line in output.splitlines()
            if line and not line.startswith("=== ")
        ]
        assert body_lines
        for line in body_lines:
            assert "Promotion" in line

    def test_main_technique_filter_finds_legendary_recognition(self, simulated_chronicle):
        stream = io.StringIO()
        main(["dump", "--technique", "te_waza_0"],
             chronicle=simulated_chronicle, stream=stream)
        output = stream.getvalue()
        assert "Legendary" in output
        assert "sensei_cranford_jkc" in output

    def test_main_dojo_filter(self, mini_chronicle):
        # Note: the orchestrator's chronicle has no dojo-indexed entries
        # in its current state (no TechniqueNamed / SeminarHeld /
        # PhotoEvent / etc fire during a 5-year tiny_nj run). The dojo
        # filter is exercised against the mini chronicle which has them.
        stream = io.StringIO()
        main(["dump", "--dojo", "cranford_jkc"],
             chronicle=mini_chronicle, stream=stream)
        output = stream.getvalue()
        body_lines = [
            line for line in output.splitlines()
            if line and not line.startswith("=== ")
        ]
        assert body_lines, "dojo filter should find at least one entry"
        # Every body line should reference cranford_jkc.
        for line in body_lines:
            assert "cranford_jkc" in line, f"unexpected body line: {line!r}"

    def test_main_entity_filter_pulls_cranford_head_history(self, simulated_chronicle):
        stream = io.StringIO()
        main(["dump", "--entity-id", "sensei_cranford_jkc"],
             chronicle=simulated_chronicle, stream=stream)
        output = stream.getvalue()
        body_lines = [
            line for line in output.splitlines()
            if line and not line.startswith("=== ")
        ]
        assert body_lines
        for line in body_lines:
            assert "sensei_cranford_jkc" in line

    def test_main_empty_result_emits_clean_message(self, simulated_chronicle):
        stream = io.StringIO()
        main(["dump", "--technique", "no_such_technique"],
             chronicle=simulated_chronicle, stream=stream)
        assert stream.getvalue() == EMPTY_MESSAGE + "\n"

    def test_main_decade_filter_captures_entire_range(self, simulated_chronicle):
        stream = io.StringIO()
        main(["dump", "--decade", "1960s"],
             chronicle=simulated_chronicle, stream=stream)
        output = stream.getvalue()
        # All seed-world years are in the 1960s, so this matches the
        # full chronicle.
        for year in range(FIRST_TICK_YEAR, LAST_TICK_YEAR + 1):
            assert f"=== {year} ===" in output

    def test_main_range_filter(self, simulated_chronicle):
        stream = io.StringIO()
        main(["dump", "--range", "1961-1962"],
             chronicle=simulated_chronicle, stream=stream)
        output = stream.getvalue()
        assert "=== 1961 ===" in output
        assert "=== 1962 ===" in output
        assert "=== 1960 ===" not in output
        assert "=== 1963 ===" not in output
