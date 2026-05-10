# tests/test_haj185_ne_waza_state_machine.py
# HAJ-185 — Ne-waza state machine: separate osaekomi, submission attempt,
# and transitional states.
#
# Bug: pre-fix, NewazaResolver could initiate a juji-gatame (or any
# submission) while the osaekomi clock was already running, so the prose
# log showed a sub attempt and the pin clock simultaneously. That's a
# state-machine error: a sub attempt is not an osaekomi position.
#
# Fix: NeWazaState enum (TRANSITIONAL / OSAEKOMI / SUBMISSION_ATTEMPT) is
# mutually exclusive. When a submission is initiated while a pin is
# active, the pin is broken (with an OSAEKOMI_TO_SUBMISSION transition
# event) before the submission begins. Pin start is gated on no active
# technique. Resolver.reset() clears both atomically.
#
# Acceptance criteria (from the ticket "Tests after fix"):
#   - When the prose log shows juji-gatame attempt, the osaekomi clock is OFF.
#   - When the prose log shows kesa-gatame pin, the osaekomi clock is ON.
#   - When the prose log shows turtle scramble, neither pin nor sub clock is firing.
#   - State transitions emit clear prose log entries.

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from enums import Position, SubLoopState
from match import Match
from ne_waza import (
    NewazaResolver, OsaekomiClock, ActiveTechnique,
    NeWazaState, NeWazaTechniqueState,
)
from referee import build_suzuki
import main as main_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _pair_match(seed: int = 1):
    random.seed(seed)
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=seed)
    return t, s, m


def _enter_ne_waza(m, top, bottom, position=Position.SIDE_CONTROL):
    m.sub_loop_state = SubLoopState.NE_WAZA
    m.position = position
    m.ne_waza_top_id = top.identity.name
    m.ne_waza_resolver.set_top_fighter(
        top.identity.name, (m.fighter_a, m.fighter_b),
    )


def _seed_armbar(resolver: NewazaResolver, top_name: str, bottom_name: str):
    resolver.active_technique = ActiveTechnique(
        name="Juji-gatame",
        technique_state=NeWazaTechniqueState.ARMBAR_ISOLATING,
        aggressor_id=top_name,
        defender_id=bottom_name,
    )


# ===========================================================================
# AC#1 — State derivation: TRANSITIONAL / OSAEKOMI / SUBMISSION_ATTEMPT
# ===========================================================================
def test_initial_state_is_transitional() -> None:
    resolver = NewazaResolver()
    osaekomi = OsaekomiClock()
    assert resolver.state(osaekomi) is NeWazaState.TRANSITIONAL


def test_state_is_osaekomi_when_pin_active() -> None:
    resolver = NewazaResolver()
    osaekomi = OsaekomiClock()
    osaekomi.start("A", Position.SIDE_CONTROL)
    assert resolver.state(osaekomi) is NeWazaState.OSAEKOMI


def test_state_is_submission_when_technique_active() -> None:
    resolver = NewazaResolver()
    osaekomi = OsaekomiClock()
    _seed_armbar(resolver, "A", "B")
    assert resolver.state(osaekomi) is NeWazaState.SUBMISSION_ATTEMPT


def test_submission_wins_over_pin_in_state_view() -> None:
    """Even if osaekomi.active is somehow True (it shouldn't be), the
    state view returns SUBMISSION_ATTEMPT — defensive contract for
    downstream consumers."""
    resolver = NewazaResolver()
    osaekomi = OsaekomiClock()
    osaekomi.start("A", Position.SIDE_CONTROL)
    _seed_armbar(resolver, "A", "B")
    assert resolver.state(osaekomi) is NeWazaState.SUBMISSION_ATTEMPT


# ===========================================================================
# AC#2 — Submission initiation while pin active breaks the pin
# ===========================================================================
def test_submission_initiation_breaks_active_pin() -> None:
    """The bug: pre-fix, starting a juji-gatame did NOT stop the osaekomi
    clock. Post-fix: pin breaks, OSAEKOMI_TO_SUBMISSION event fires, and
    the sub begins."""
    t, s, m = _pair_match(seed=42)
    _enter_ne_waza(m, top=t, bottom=s, position=Position.SIDE_CONTROL)
    m.osaekomi.start(t.identity.name, Position.SIDE_CONTROL)
    m.osaekomi.ticks_held = 5  # mid-pin

    # Force the technique-attempt branch: rng < 0.25 (TECHNIQUE_ATTEMPT_PROB).
    # Suppress escape and counter so neither short-circuits the path.
    m.ne_waza_resolver._roll_escape = lambda *a, **kw: False
    m.ne_waza_resolver._resolve_counter = lambda *a, **kw: False
    real_random = random.random
    rolls = iter([0.10, 0.99, 0.99, 0.99, 0.99])
    random.random = lambda: next(rolls, 0.99)
    try:
        events = m.ne_waza_resolver.tick_resolve(
            position=Position.SIDE_CONTROL,
            graph=m.grip_graph,
            fighters=(t, s),
            osaekomi=m.osaekomi,
            current_tick=10,
        )
    finally:
        random.random = real_random

    # Pin clock has stopped.
    assert m.osaekomi.active is False
    # State has flipped to SUBMISSION_ATTEMPT.
    assert m.ne_waza_resolver.state(m.osaekomi) is NeWazaState.SUBMISSION_ATTEMPT
    # Transition event is on the wire with the held-tick count.
    transitions = [e for e in events if e.event_type == "OSAEKOMI_TO_SUBMISSION"]
    assert len(transitions) == 1
    payload = transitions[0].data
    assert payload["former_holder"] == t.identity.name
    assert payload["ticks_held"] == 5
    # And a follow-on technique-initiated event for the sub.
    initiates = [e for e in events if e.event_type.endswith("_INITIATED")]
    assert len(initiates) == 1


# ===========================================================================
# AC#3 — Pin does not start while a submission is active
# ===========================================================================
def test_pin_does_not_start_during_submission() -> None:
    """When a submission is already active, the resolver advances the
    technique chain and never calls osaekomi.start. The pin clock stays
    OFF for the duration of the sub."""
    t, s, m = _pair_match(seed=11)
    _enter_ne_waza(m, top=t, bottom=s, position=Position.SIDE_CONTROL)
    _seed_armbar(m.ne_waza_resolver, t.identity.name, s.identity.name)
    m.ne_waza_resolver._roll_escape = lambda *a, **kw: False
    m.ne_waza_resolver._resolve_counter = lambda *a, **kw: False

    # Run several ticks; assert osaekomi never starts.
    real_random = random.random
    random.random = lambda: 0.99
    try:
        for tick in range(10, 20):
            m.ne_waza_resolver.tick_resolve(
                position=Position.SIDE_CONTROL,
                graph=m.grip_graph,
                fighters=(t, s),
                osaekomi=m.osaekomi,
                current_tick=tick,
            )
            assert m.osaekomi.active is False, (
                f"osaekomi started during submission at tick {tick}"
            )
    finally:
        random.random = real_random


# ===========================================================================
# AC#4 — Pin can start in TRANSITIONAL (no submission active)
# ===========================================================================
def test_pin_starts_in_transitional() -> None:
    """In SIDE_CONTROL with no active technique and the technique-attempt
    roll failing, the resolver starts a pin. State flips to OSAEKOMI."""
    t, s, m = _pair_match(seed=2)
    _enter_ne_waza(m, top=t, bottom=s, position=Position.SIDE_CONTROL)
    m.ne_waza_resolver._roll_escape = lambda *a, **kw: False
    m.ne_waza_resolver._resolve_counter = lambda *a, **kw: False
    assert m.osaekomi.active is False
    assert m.ne_waza_resolver.state(m.osaekomi) is NeWazaState.TRANSITIONAL

    real_random = random.random
    random.random = lambda: 0.99   # technique-attempt roll fails -> pin path
    try:
        events = m.ne_waza_resolver.tick_resolve(
            position=Position.SIDE_CONTROL,
            graph=m.grip_graph,
            fighters=(t, s),
            osaekomi=m.osaekomi,
            current_tick=10,
        )
    finally:
        random.random = real_random

    assert m.osaekomi.active is True
    assert m.ne_waza_resolver.state(m.osaekomi) is NeWazaState.OSAEKOMI
    begins = [e for e in events if e.event_type == "OSAEKOMI_BEGIN"]
    assert len(begins) == 1


# ===========================================================================
# AC#5 — Reset() clears both pin and submission atomically
# ===========================================================================
def test_reset_clears_both_pin_and_submission() -> None:
    resolver = NewazaResolver()
    osaekomi = OsaekomiClock()
    osaekomi.start("A", Position.SIDE_CONTROL)
    _seed_armbar(resolver, "A", "B")
    assert osaekomi.active is True
    assert resolver.active_technique is not None

    resolver.reset(osaekomi)
    assert osaekomi.active is False
    assert resolver.active_technique is None
    assert resolver.state(osaekomi) is NeWazaState.TRANSITIONAL


# ===========================================================================
# AC#6 — Submission resolution returns to TRANSITIONAL
# ===========================================================================
def test_submission_failure_returns_to_transitional() -> None:
    """When an armbar resolves as ARMBAR_FAILED, the resolver clears
    active_technique and the state is TRANSITIONAL again."""
    t, s, m = _pair_match(seed=99)
    _enter_ne_waza(m, top=t, bottom=s, position=Position.SIDE_CONTROL)
    _seed_armbar(m.ne_waza_resolver, t.identity.name, s.identity.name)
    # Push the chain to EXTENDING with chain_tick high enough that the
    # failure branch can fire.
    tech = m.ne_waza_resolver.active_technique
    tech.technique_state = NeWazaTechniqueState.ARMBAR_EXTENDING
    tech.chain_tick = 10
    # Force extend_prob roll to miss and the failure roll to hit.
    m.ne_waza_resolver._roll_escape = lambda *a, **kw: False
    m.ne_waza_resolver._resolve_counter = lambda *a, **kw: False
    real_random = random.random
    rolls = iter([0.99, 0.10])  # extend fails, then failure roll hits
    random.random = lambda: next(rolls, 0.99)
    try:
        m.ne_waza_resolver.tick_resolve(
            position=Position.SIDE_CONTROL,
            graph=m.grip_graph,
            fighters=(t, s),
            osaekomi=m.osaekomi,
            current_tick=20,
        )
    finally:
        random.random = real_random
    assert m.ne_waza_resolver.active_technique is None
    assert m.ne_waza_resolver.state(m.osaekomi) is NeWazaState.TRANSITIONAL


# ===========================================================================
# AC#7 — 50-iteration smoke: pin and sub never both active
# ===========================================================================
def test_smoke_50_ticks_pin_and_sub_never_co_active() -> None:
    """Drive 50 ground ticks through the resolver with random rolls; assert
    that on every tick the state is one of the three legal phases — never
    OSAEKOMI and SUBMISSION_ATTEMPT simultaneously, never a desync where
    osaekomi.active is True while active_technique is also set."""
    t, s, m = _pair_match(seed=2026)
    _enter_ne_waza(m, top=t, bottom=s, position=Position.SIDE_CONTROL)
    m.ne_waza_resolver._roll_escape = lambda *a, **kw: False
    m.ne_waza_resolver._resolve_counter = lambda *a, **kw: False
    random.seed(2026)
    for tick in range(1, 51):
        m.ne_waza_resolver.tick_resolve(
            position=Position.SIDE_CONTROL,
            graph=m.grip_graph,
            fighters=(t, s),
            osaekomi=m.osaekomi,
            current_tick=tick,
        )
        # The invariant: pin and sub are mutually exclusive at the engine
        # level. State view always returns exactly one phase.
        sub_active = m.ne_waza_resolver.active_technique is not None
        pin_active = m.osaekomi.active
        assert not (sub_active and pin_active), (
            f"tick {tick}: pin and sub both active — state-machine violation"
        )
        state = m.ne_waza_resolver.state(m.osaekomi)
        if sub_active:
            assert state is NeWazaState.SUBMISSION_ATTEMPT
        elif pin_active:
            assert state is NeWazaState.OSAEKOMI
        else:
            assert state is NeWazaState.TRANSITIONAL


# ===========================================================================
# AC#8 — Match-side reset paths route through resolver.reset
# ===========================================================================
def test_match_reset_dyad_clears_ne_waza() -> None:
    """_reset_dyad_to_distant must leave the resolver in TRANSITIONAL."""
    t, s, m = _pair_match(seed=5)
    m.osaekomi.start(t.identity.name, Position.SIDE_CONTROL)
    _seed_armbar(m.ne_waza_resolver, t.identity.name, s.identity.name)
    m._reset_dyad_to_distant(tick=10, recovery_bonus=0)
    assert m.osaekomi.active is False
    assert m.ne_waza_resolver.active_technique is None
    assert m.ne_waza_resolver.state(m.osaekomi) is NeWazaState.TRANSITIONAL
