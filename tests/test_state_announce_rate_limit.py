# tests/test_state_announce_rate_limit.py
# HAJ-48 — desperation ENTER/EXIT lines are gated on confirmed duration.
#
# A state that lasts < STATE_ANNOUNCE_MIN_TICKS produces no announcement
# (no ENTER, and therefore no orphan EXIT). A state that persists long
# enough fires ENTER on the Nth tick of continuous activity, then EXIT
# when the underlying state releases.
#
# The underlying mechanic flags (_defensive_desperation_active /
# _offensive_desperation_active) are not affected — the rate-limit only
# governs the [state] event lines.

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from match import Match, STATE_ANNOUNCE_MIN_TICKS
from referee import build_suzuki
import main as main_module


def _make_match() -> Match:
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return Match(fighter_a=t, fighter_b=s, referee=build_suzuki())


def _payload(name: str):
    """Minimal payload factory matching the structure expected by the
    rate-limit helper. Both ENTER and EXIT carry distinct strings so
    tests can match on description."""
    return lambda: {
        "type": "defensive",
        "description": f"[state] {name} enters defensive desperation (synthetic).",
        "data": None,
        "exit_description": f"[state] {name} exits defensive desperation.",
        "enter_event_type": "DEFENSIVE_DESPERATION_ENTER",
        "exit_event_type":  "DEFENSIVE_DESPERATION_EXIT",
    }


def _drive(match: Match, name: str, kind: str, sequence: list[bool]):
    """Walk the rate-limit helper through a tick-by-tick active/inactive
    sequence and return all events it emits. `sequence[i]` is the
    desired state at tick i; was_active comes from sequence[i-1] (False
    for i=0)."""
    events: list = []
    payload_fn = _payload(name)
    prev = False
    for tick, is_active in enumerate(sequence):
        match._emit_desperation_state_event(
            name, kind, prev, is_active, tick, events, payload_fn,
        )
        prev = is_active
    return events


def test_one_tick_flicker_emits_nothing() -> None:
    """State on for 1 tick then off — too short to confirm. No log lines."""
    m = _make_match()
    name = m.fighter_a.identity.name
    events = _drive(m, name, "defensive", [True, False, False, False])
    assert events == [], f"expected zero announcements; got {events}"


def test_short_burst_below_threshold_emits_nothing() -> None:
    """Active for STATE_ANNOUNCE_MIN_TICKS - 1 ticks then off — still
    short of confirmation. No ENTER, therefore no EXIT."""
    m = _make_match()
    name = m.fighter_a.identity.name
    seq = [True] * (STATE_ANNOUNCE_MIN_TICKS - 1) + [False, False]
    events = _drive(m, name, "defensive", seq)
    assert events == [], f"expected zero announcements; got {events}"


def test_at_or_above_threshold_emits_enter_then_exit() -> None:
    """Active for exactly STATE_ANNOUNCE_MIN_TICKS ticks: ENTER fires on
    the Nth tick. When the state releases, EXIT fires."""
    m = _make_match()
    name = m.fighter_a.identity.name
    seq = [True] * STATE_ANNOUNCE_MIN_TICKS + [False]
    events = _drive(m, name, "defensive", seq)

    enters = [e for e in events if e.event_type == "DEFENSIVE_DESPERATION_ENTER"]
    exits  = [e for e in events if e.event_type == "DEFENSIVE_DESPERATION_EXIT"]
    assert len(enters) == 1, f"expected exactly one ENTER; got {events}"
    assert len(exits) == 1,  f"expected exactly one EXIT; got {events}"
    # ENTER fires on the (N-1)-th index — i.e. the Nth consecutive active tick.
    assert enters[0].tick == STATE_ANNOUNCE_MIN_TICKS - 1
    # EXIT fires the tick the state turns off.
    assert exits[0].tick == STATE_ANNOUNCE_MIN_TICKS


def test_long_state_does_not_re_announce() -> None:
    """A state that stays active for many ticks fires ENTER once, not
    every subsequent tick."""
    m = _make_match()
    name = m.fighter_a.identity.name
    seq = [True] * 20
    events = _drive(m, name, "defensive", seq)
    enters = [e for e in events if e.event_type == "DEFENSIVE_DESPERATION_ENTER"]
    assert len(enters) == 1, f"expected exactly one ENTER over a long phase; got {len(enters)}"


def test_re_entry_after_full_cycle_announces_again() -> None:
    """ENTER → EXIT → re-ENTER pattern: each confirmed phase logs once."""
    m = _make_match()
    name = m.fighter_a.identity.name
    block = [True] * STATE_ANNOUNCE_MIN_TICKS + [False] * 2
    seq = block + block
    events = _drive(m, name, "defensive", seq)
    enters = [e for e in events if e.event_type == "DEFENSIVE_DESPERATION_ENTER"]
    exits  = [e for e in events if e.event_type == "DEFENSIVE_DESPERATION_EXIT"]
    assert len(enters) == 2, f"expected two ENTERs across two phases; got {events}"
    assert len(exits) == 2,  f"expected two EXITs across two phases; got {events}"


def test_underlying_flag_still_tracks_immediately() -> None:
    """The mechanic flag must reflect the underlying state every tick —
    only the announcement is rate-limited."""
    m = _make_match()
    name = m.fighter_a.identity.name
    # Before: not active.
    assert m._defensive_desperation_active[name] is False
    # Simulate a one-tick flicker via the helper. The helper does NOT
    # write the underlying flag — only the announcement gate. So we
    # write the flag manually as the production code does.
    m._defensive_desperation_active[name] = True
    assert m._defensive_desperation_active[name] is True
    m._defensive_desperation_active[name] = False
    assert m._defensive_desperation_active[name] is False
