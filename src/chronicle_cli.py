# chronicle_cli.py
# Developer-facing chronicle dump tool (HAJ-203).
#
# The first reading surface for Ring 2. Builds the tiny_nj seed world,
# runs the year-tick orchestrator across 1960–1964, and emits the
# resulting chronicle as plain text — filterable by year/quarter/decade/
# range and by entity/event-type/dojo/technique.
#
# Usage (from repo root):
#
#   python src/chronicle_cli.py dump
#   python src/chronicle_cli.py dump --year 1960
#   python src/chronicle_cli.py dump --decade 1960s --event-type promotion
#   python src/chronicle_cli.py dump --technique te_waza_0
#   python src/chronicle_cli.py dump --entity-type dojo --entity-id cranford_jkc
#
# Filters compose with AND. With no filters the full chronicle prints.
#
# This is the substrate-is-real moment named in the ticket. It is *not*
# the legends-rendering layer — renderings here are naive
# `{actor} {verb} {target}` style; templated prose is Track 4 polish work.

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Callable, Iterable, Optional

# Make src/ and tests/ importable when invoked directly.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
if str(_REPO_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tests"))

from chronicle import (  # noqa: E402  — sys.path adjustment must precede
    Birth,
    Chronicle,
    ChronicleEntry,
    ChronicleEntryType,
    CohortFormation,
    Death,
    DojoClose,
    DojoOpen,
    LegendaryRecognition,
    MatchOutcome,
    PhotoEvent,
    Promotion,
    PromotionTestHeld,
    Quarter,
    Retirement,
    SeminarAttended,
    SeminarHeld,
    TechniqueComeback,
    TechniqueDisuseDrop,
    TechniqueLearned,
    TechniqueMilestone,
    TechniqueNamePropagated,
    TechniqueNamed,
)


# ===========================================================================
# FILTER MODEL
# ===========================================================================
ENTITY_TYPES: tuple[str, ...] = ("judoka", "sensei", "dojo", "tournament")


@dataclass
class DumpFilters:
    """Structured filter set. Built from parsed CLI args; consumed by
    `filter_chronicle()`. Each field is optional — `None` means "no
    constraint along this axis"."""
    year: Optional[int] = None
    quarter: Optional[tuple[int, Quarter]] = None
    decade_start: Optional[int] = None              # e.g. 1960 for "1960s"
    year_range: Optional[tuple[int, int]] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    event_type: Optional[ChronicleEntryType] = None
    dojo: Optional[str] = None
    technique: Optional[str] = None


# ===========================================================================
# ARGUMENT PARSING
# ===========================================================================
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chronicle",
        description="Dump the Ring 2 chronicle as plain text.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    dump = subparsers.add_parser("dump", help="Dump chronicle entries.")

    grain = dump.add_mutually_exclusive_group()
    grain.add_argument("--year", type=int, metavar="YYYY",
                       help="Show entries for one calendar year.")
    grain.add_argument("--quarter", metavar="YYYY-QN",
                       help="Show entries for one calendar quarter "
                            "(e.g. 1962-Q2).")
    grain.add_argument("--decade", metavar="YYYYs",
                       help="Show entries for one decade (e.g. 1960s).")
    grain.add_argument("--range", dest="range_arg", metavar="YYYY-YYYY",
                       help="Show entries across an explicit year range.")

    dump.add_argument("--entity-type", choices=ENTITY_TYPES,
                      help="Entity index to look up --entity-id against.")
    dump.add_argument("--entity-id",
                      help="Entity id to filter against (use with "
                           "--entity-type to disambiguate).")
    dump.add_argument("--event-type",
                      help="One of the ChronicleEntryType values "
                           "(e.g. promotion, match_outcome, "
                           "technique_milestone, legendary_recognition, ...)")
    dump.add_argument("--dojo", help="Filter to entries referencing this dojo.")
    dump.add_argument("--technique",
                      help="Filter to entries referencing this technique_id.")

    return parser


def _parse_quarter(raw: str) -> tuple[int, Quarter]:
    parts = raw.split("-")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"--quarter must be YYYY-QN, got '{raw}'"
        )
    try:
        year = int(parts[0])
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--quarter year part must be an integer, got '{parts[0]}'"
        )
    label = parts[1].upper()
    try:
        quarter = Quarter(label)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--quarter quarter part must be one of Q1/Q2/Q3/Q4, got '{label}'"
        )
    return year, quarter


def _parse_decade(raw: str) -> int:
    cleaned = raw.lower().rstrip("s")
    try:
        start = int(cleaned)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--decade must be YYYYs, got '{raw}'"
        )
    if start % 10 != 0:
        raise argparse.ArgumentTypeError(
            f"--decade must start on a decade boundary (e.g. 1960s), got '{raw}'"
        )
    return start


def _parse_year_range(raw: str) -> tuple[int, int]:
    parts = raw.split("-")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"--range must be YYYY-YYYY, got '{raw}'"
        )
    try:
        start = int(parts[0])
        end = int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--range bounds must be integers, got '{raw}'"
        )
    if end < start:
        raise argparse.ArgumentTypeError(
            f"--range end year ({end}) must be >= start year ({start})"
        )
    return start, end


def _parse_event_type(raw: str) -> ChronicleEntryType:
    try:
        return ChronicleEntryType(raw)
    except ValueError:
        valid = ", ".join(t.value for t in ChronicleEntryType)
        raise argparse.ArgumentTypeError(
            f"--event-type '{raw}' not recognised; expected one of: {valid}"
        )


def parse_filters(argv: Optional[list[str]]) -> DumpFilters:
    """Parse a `dump` subcommand argv into a DumpFilters object.

    Raises SystemExit (via argparse) on malformed input.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command != "dump":
        parser.error(f"unsupported command '{args.command}'")

    filters = DumpFilters()
    try:
        if args.year is not None:
            filters.year = args.year
        if args.quarter:
            filters.quarter = _parse_quarter(args.quarter)
        if args.decade:
            filters.decade_start = _parse_decade(args.decade)
        if args.range_arg:
            filters.year_range = _parse_year_range(args.range_arg)
        if args.event_type:
            filters.event_type = _parse_event_type(args.event_type)
    except argparse.ArgumentTypeError as err:
        # The helpers raise ArgumentTypeError so the message names the
        # offending flag; surface as a clean parser.error → SystemExit.
        parser.error(str(err))

    if args.entity_id and not args.entity_type:
        # Default to "judoka" when only an id is given. The ticket allows
        # entity-type to be omitted in normal use; this keeps the CLI
        # forgiving for the common case of "show this person's history".
        filters.entity_type = "judoka"
    elif args.entity_type and not args.entity_id:
        parser.error("--entity-type requires --entity-id")
    filters.entity_type = args.entity_type or filters.entity_type
    filters.entity_id = args.entity_id

    filters.dojo = args.dojo
    filters.technique = args.technique

    return filters


# ===========================================================================
# FILTER PREDICATE
# ===========================================================================
def _matches(entry: ChronicleEntry, filters: DumpFilters) -> bool:
    if filters.year is not None and entry.year != filters.year:
        return False
    if filters.quarter is not None:
        q_year, q = filters.quarter
        if entry.year != q_year:
            return False
        if entry.quarter is None or entry.quarter is not q:
            return False
    if filters.decade_start is not None:
        if not (filters.decade_start <= entry.year < filters.decade_start + 10):
            return False
    if filters.year_range is not None:
        start, end = filters.year_range
        if not (start <= entry.year <= end):
            return False
    if filters.event_type is not None and entry.ENTRY_TYPE is not filters.event_type:
        return False
    if filters.entity_id is not None:
        target = filters.entity_id
        if filters.entity_type == "dojo":
            if target not in entry.dojo_ids():
                return False
        elif filters.entity_type == "tournament":
            if target not in entry.tournament_ids():
                return False
        else:
            # "judoka" and "sensei" both resolve against the entity index.
            # Senseis ARE judoka — the ticket separates them as a
            # convenience, but the underlying entity model is shared.
            if target not in entry.entity_ids():
                return False
    if filters.dojo is not None and filters.dojo not in entry.dojo_ids():
        return False
    if filters.technique is not None and filters.technique not in entry.technique_ids():
        return False
    return True


def filter_chronicle(
    chronicle: Chronicle,
    filters: DumpFilters,
) -> list[ChronicleEntry]:
    """Return entries matching `filters`, sorted by (year, entry_id)."""
    matched = [entry for entry in chronicle if _matches(entry, filters)]
    return sorted(matched, key=lambda e: (e.year, e.entry_id))


# ===========================================================================
# RENDERING
# ===========================================================================
# Each entry type gets a one-line renderer. Format is `{actor} {verb}
# {target}` per the ticket — not load-bearing, iterate from here. Naming
# overlay rendering (custom dojo-local technique names) is out of scope;
# canonical ids are used throughout.

def _render_match_outcome(e: MatchOutcome) -> str:
    via = f" via {e.technique_id}" if e.technique_id else ""
    tournament = f"{e.tournament_id}: " if e.tournament_id else ""
    return (
        f"{tournament}{e.winner_id} def. {e.loser_id} by "
        f"{e.score_type.value}{via} ({e.duration_band.value})"
    )


def _render_promotion(e: Promotion) -> str:
    sensei = f", awarded by {e.awarding_sensei_id}" if e.awarding_sensei_id else ""
    return f"Promotion: {e.judoka_id} {e.from_rank} → {e.to_rank}{sensei}"


def _render_promotion_test(e: PromotionTestHeld) -> str:
    cond = f" — note: {e.conditions_noted}" if e.conditions_noted else ""
    return (
        f"Promotion test: {e.judoka_id} for {e.to_belt} → "
        f"{e.outcome.value} (examiner {e.examiner_id}, "
        f"{e.examiner_type.value}){cond}"
    )


def _render_retirement(e: Retirement) -> str:
    return f"Retirement: {e.judoka_id} ({e.reason.value})"


def _render_death(e: Death) -> str:
    return f"Death: {e.entity_id} at age {e.age} ({e.cause.value})"


def _render_birth(e: Birth) -> str:
    parents = ", ".join(e.parent_ids) if e.parent_ids else "unknown parents"
    return f"Birth: {e.child_id} ({parents})"


def _render_dojo_open(e: DojoOpen) -> str:
    senseis = ", ".join(e.founding_sensei_ids) if e.founding_sensei_ids else "?"
    location = f" in {e.location_id}" if e.location_id else ""
    return f"Dojo opened: {e.dojo_id} ({e.discipline}) by {senseis}{location}"


def _render_dojo_close(e: DojoClose) -> str:
    return f"Dojo closed: {e.dojo_id} ({e.reason.value})"


def _render_photo_event(e: PhotoEvent) -> str:
    n = len(e.participant_ids)
    return f"Photo: {e.dojo_id} — {e.occasion} ({n} subjects, {e.era_visual_style})"


def _render_cohort_formation(e: CohortFormation) -> str:
    n = len(e.founding_member_ids)
    return f"Cohort formed: {e.cohort_id} at {e.dojo_id} ({n} founding members)"


def _render_technique_learned(e: TechniqueLearned) -> str:
    via = f" via {e.source_pathway.value}"
    src = f" (from {e.source_entity_id})" if e.source_entity_id else ""
    return (
        f"Learned: {e.judoka_id} acquired {e.technique_id}{via}{src} "
        f"at {e.starting_tier.value}"
    )


def _render_technique_milestone(e: TechniqueMilestone) -> str:
    return (
        f"Milestone: {e.judoka_id} on {e.technique_id} "
        f"{e.previous_tier.value} → {e.new_tier.value} "
        f"(via {e.triggering_event_type.value})"
    )


def _render_technique_disuse_drop(e: TechniqueDisuseDrop) -> str:
    return (
        f"Disuse decay: {e.judoka_id} on {e.technique_id} "
        f"{e.previous_tier.value} → {e.new_tier.value} "
        f"({e.years_since_last_use}y unused)"
    )


def _render_technique_comeback(e: TechniqueComeback) -> str:
    return (
        f"Comeback: {e.judoka_id} on {e.technique_id} regained "
        f"{e.regained_tier.value}"
    )


def _render_technique_named(e: TechniqueNamed) -> str:
    return (
        f"Named: {e.dojo_id} renames {e.technique_id} to "
        f"'{e.custom_name}' ({e.naming_type.value}, by {e.naming_judoka_id})"
    )


def _render_technique_name_propagated(e: TechniqueNamePropagated) -> str:
    return (
        f"Name propagated: '{e.custom_name}' ({e.technique_id}) "
        f"{e.source_dojo_id} → {e.target_dojo_id} "
        f"(via {e.propagation_pathway.value})"
    )


def _render_seminar_held(e: SeminarHeld) -> str:
    return (
        f"Seminar held: {e.host_judoka_id} taught {e.technique_id} at "
        f"{e.host_dojo_id} in {e.season.value} — "
        f"{e.attendee_count} attendees from {e.attendee_dojo_count} dojos"
    )


def _render_seminar_attended(e: SeminarAttended) -> str:
    return (
        f"Seminar attended: {e.attendee_judoka_id} ({e.attendee_dojo_id}) "
        f"on {e.technique_id} → {e.outcome_tier_change.value}"
    )


def _render_legendary_recognition(e: LegendaryRecognition) -> str:
    inheritors = ", ".join(e.qualifying_lineage_inheritor_ids) or "—"
    return (
        f"Legendary: {e.judoka_id} recognised in {e.technique_id} "
        f"({e.qualifying_competition_score:.1f} tier-weighted comp pts, "
        f"inheritors: {inheritors}, {e.tenure_years_at_master}y at master)"
    )


_RENDERERS: dict[type[ChronicleEntry], Callable[[ChronicleEntry], str]] = {
    MatchOutcome:             _render_match_outcome,
    Promotion:                _render_promotion,
    PromotionTestHeld:        _render_promotion_test,
    Retirement:               _render_retirement,
    Death:                    _render_death,
    Birth:                    _render_birth,
    DojoOpen:                 _render_dojo_open,
    DojoClose:                _render_dojo_close,
    PhotoEvent:               _render_photo_event,
    CohortFormation:          _render_cohort_formation,
    TechniqueLearned:         _render_technique_learned,
    TechniqueMilestone:       _render_technique_milestone,
    TechniqueDisuseDrop:      _render_technique_disuse_drop,
    TechniqueComeback:        _render_technique_comeback,
    TechniqueNamed:           _render_technique_named,
    TechniqueNamePropagated:  _render_technique_name_propagated,
    SeminarHeld:              _render_seminar_held,
    SeminarAttended:          _render_seminar_attended,
    LegendaryRecognition:     _render_legendary_recognition,
}


def render_entry(entry: ChronicleEntry) -> str:
    """Render an entry body. Falls back to a placeholder for types
    without a registered renderer — guards against future entry types
    breaking the dump."""
    renderer = _RENDERERS.get(type(entry))
    if renderer is None:
        return f"<{entry.ENTRY_TYPE.value} entry {entry.entry_id}>"
    return renderer(entry)


def format_entry(entry: ChronicleEntry) -> str:
    """`[YYYY-QN] body` — the per-line format the dump emits."""
    q_tag = entry.quarter.value if entry.quarter is not None else "----"
    return f"[{entry.year}-{q_tag}] {render_entry(entry)}"


# ===========================================================================
# OUTPUT
# ===========================================================================
EMPTY_MESSAGE: str = "(no entries match the given filters)"


def write_dump(entries: Iterable[ChronicleEntry], stream: IO[str]) -> None:
    """Write entries grouped by year. Empty result emits a clean message
    rather than nothing."""
    entries = list(entries)
    if not entries:
        stream.write(EMPTY_MESSAGE + "\n")
        return

    current_year: Optional[int] = None
    for entry in entries:
        if entry.year != current_year:
            if current_year is not None:
                stream.write("\n")
            stream.write(f"=== {entry.year} ===\n")
            current_year = entry.year
        stream.write(format_entry(entry) + "\n")


# ===========================================================================
# DEFAULT WORLD BUILDER
# Builds the tiny_nj fixture and runs the 5-year orchestrator to produce a
# populated chronicle. Tests inject their own chronicle to avoid the
# (cheap but non-trivial) simulation cost.
# ===========================================================================
def build_default_chronicle() -> Chronicle:
    from fixtures.seed_worlds.tiny_nj import (  # local import — fixture
        FIRST_TICK_YEAR,                          # is a test artifact
        LAST_TICK_YEAR,
        build_tiny_nj_world,
    )
    from orchestrator import advance_year

    world = build_tiny_nj_world()
    for year in range(FIRST_TICK_YEAR, LAST_TICK_YEAR + 1):
        advance_year(world, year)
    return world.chronicle


# ===========================================================================
# ENTRY POINT
# ===========================================================================
def main(
    argv: Optional[list[str]] = None,
    chronicle: Optional[Chronicle] = None,
    stream: Optional[IO[str]] = None,
) -> int:
    """Programmatic entry point. The `chronicle` and `stream` kwargs exist
    for testability — the CLI itself passes neither and uses the default
    tiny_nj-driven build + stdout output."""
    filters = parse_filters(argv)
    if chronicle is None:
        chronicle = build_default_chronicle()
    if stream is None:
        stream = sys.stdout
    entries = filter_chronicle(chronicle, filters)
    write_dump(entries, stream)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
