# tests/test_haj95_time_expired.py
# HAJ-95 — Time-expiration event at max_ticks.
#
# Acceptance criteria:
#   - A regulation match reaching the regulation boundary emits exactly
#     one TIME_EXPIRED event.
#   - Unequal waza-ari at the boundary produces MATCH_ENDED with
#     method="decision" and the correct winner.
#   - Equal waza-ari at the boundary does NOT produce MATCH_ENDED;
#     produces the golden-score transition (handed to HAJ-93).
#   - Both paths are visible in the coach stream — the description on
#     each event names what just happened.

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from match import Match
from referee import build_suzuki
import main as main_module


def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _match(regulation_ticks: int = 240, max_ticks: int | None = None,
           seed: int = 1) -> tuple:
    random.seed(seed)
    t, s = _pair()
    if max_ticks is None:
        max_ticks = regulation_ticks
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        regulation_ticks=regulation_ticks, max_ticks=max_ticks, seed=seed,
    )
    return t, s, m


# ===========================================================================
# AC#1 — TIME_EXPIRED fires exactly once at the regulation boundary
# ===========================================================================
def test_time_expired_emitted_at_regulation_end() -> None:
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    events: list = []
    m._check_regulation_end(tick=240, events=events)

    expired = [e for e in events if e.event_type == "TIME_EXPIRED"]
    assert len(expired) == 1
    payload = expired[0].data
    assert payload["tick"] == 240
    assert payload["a_waza_ari"] == 0
    assert payload["b_waza_ari"] == 0


def test_time_expired_carries_score_state() -> None:
    """Payload includes the waza-ari counts at expiration so downstream
    consumers don't have to re-read the match state."""
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    t.state.score["waza_ari"] = 1
    s.state.score["waza_ari"] = 0
    events: list = []
    m._check_regulation_end(tick=240, events=events)

    expired = next(e for e in events if e.event_type == "TIME_EXPIRED")
    assert expired.data["a_waza_ari"] == 1
    assert expired.data["b_waza_ari"] == 0


# ===========================================================================
# AC#2 — unequal waza-ari → TIME_EXPIRED then MATCH_ENDED(decision)
# ===========================================================================
def test_unequal_waza_ari_at_boundary_resolves_to_decision() -> None:
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    t.state.score["waza_ari"] = 1
    s.state.score["waza_ari"] = 0
    events: list = []
    m._check_regulation_end(tick=240, events=events)

    types = [e.event_type for e in events]
    # Exactly one of each, in the right order.
    assert types.count("TIME_EXPIRED") == 1
    assert types.count("MATCH_ENDED") == 1
    assert types.index("TIME_EXPIRED") < types.index("MATCH_ENDED")
    # No golden-score start on this branch.
    assert "GOLDEN_SCORE_START" not in types

    ended = next(e for e in events if e.event_type == "MATCH_ENDED")
    assert ended.data["winner"] == t.identity.name
    assert ended.data["method"] == "decision"
    assert ended.data["golden_score"] is False


# ===========================================================================
# AC#3 — equal waza-ari → TIME_EXPIRED + GOLDEN_SCORE_START, no MATCH_ENDED
# ===========================================================================
def test_equal_waza_ari_at_boundary_transitions_to_golden_score() -> None:
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    # 0-0 path
    events: list = []
    m._check_regulation_end(tick=240, events=events)

    types = [e.event_type for e in events]
    assert types.count("TIME_EXPIRED") == 1
    assert types.count("GOLDEN_SCORE_START") == 1
    assert types.index("TIME_EXPIRED") < types.index("GOLDEN_SCORE_START")
    # No match-end on this branch — clock continues into golden score.
    assert "MATCH_ENDED" not in types
    assert m.match_over is False
    assert m.golden_score is True


def test_equal_waza_ari_1_1_at_boundary_transitions_to_golden_score() -> None:
    """1-1 ties also go to golden score, not draw."""
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    t.state.score["waza_ari"] = 1
    s.state.score["waza_ari"] = 1
    events: list = []
    m._check_regulation_end(tick=240, events=events)

    types = [e.event_type for e in events]
    assert "TIME_EXPIRED" in types
    assert "GOLDEN_SCORE_START" in types
    assert "MATCH_ENDED" not in types


# ===========================================================================
# AC#4 — coach-stream visibility: descriptions name what happened
# ===========================================================================
def test_time_expired_description_is_human_readable() -> None:
    """Coach stream readers see a clear time-expiration line. The
    description includes the score state so the next event makes sense
    in context."""
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    t.state.score["waza_ari"] = 1
    events: list = []
    m._check_regulation_end(tick=240, events=events)

    expired = next(e for e in events if e.event_type == "TIME_EXPIRED")
    assert "Time" in expired.description
    assert "1-0" in expired.description


def test_golden_score_start_description_names_the_transition() -> None:
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    events: list = []
    m._check_regulation_end(tick=240, events=events)
    gs = next(e for e in events if e.event_type == "GOLDEN_SCORE_START")
    assert "golden score" in gs.description.lower()


def test_decision_match_ended_description_names_the_winner() -> None:
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    s.state.score["waza_ari"] = 1
    events: list = []
    m._check_regulation_end(tick=240, events=events)
    ended = next(e for e in events if e.event_type == "MATCH_ENDED")
    assert s.identity.name in ended.description
    assert "decision" in ended.description


# ===========================================================================
# Idempotency — second call produces no further TIME_EXPIRED
# ===========================================================================
def test_check_regulation_end_is_idempotent() -> None:
    """Once golden score has started (or the match has ended) the gate
    must not re-fire TIME_EXPIRED on subsequent ticks."""
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    events: list = []
    m._check_regulation_end(tick=240, events=events)
    m._check_regulation_end(tick=241, events=events)
    m._check_regulation_end(tick=300, events=events)
    assert sum(1 for e in events if e.event_type == "TIME_EXPIRED") == 1


def test_check_regulation_end_skipped_when_match_already_over() -> None:
    """If a score / shido already ended the match before the regulation
    boundary tick, TIME_EXPIRED does not fire."""
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    # Simulate match ended by ippon mid-regulation.
    m.match_over = True
    m.winner = t
    m.win_method = "ippon"
    events: list = []
    m._check_regulation_end(tick=240, events=events)
    assert not any(e.event_type == "TIME_EXPIRED" for e in events)


# ===========================================================================
# Integration — running the match end-to-end emits TIME_EXPIRED at the
# boundary tick and routes to the right downstream branch
# ===========================================================================
def test_full_match_emits_time_expired_at_boundary() -> None:
    """Drive a match forward to the regulation boundary and confirm the
    TIME_EXPIRED event fires from inside the tick loop (not just by
    direct call)."""
    t, s, m = _match(regulation_ticks=5, max_ticks=200)
    captured: list = []
    real_print = m._print_events
    m._print_events = lambda evs: (captured.extend(evs), real_print(evs))[0]
    # Suppress chatter.
    m._print_events = lambda evs: captured.extend(evs)
    m._print_header = lambda: None
    m.begin()
    while m.ticks_run < 5 and not m.is_done():
        m.step()

    expired = [e for e in captured if e.event_type == "TIME_EXPIRED"]
    assert len(expired) == 1
    assert expired[0].tick == 5
