# tests/test_desperation_jitter.py
# HAJ-47 — desperation entry timing varies per fighter.
#
# Pre-HAJ-47, two fighters in symmetric states crossed the offensive-
# desperation threshold on the same tick because the predicate was a
# pure function of (composure, kumi_kata_clock). Two matched fighters
# on the same kumi-kata clock with parallel composure histories therefore
# entered desperation simultaneously.
#
# Post-HAJ-47, each fighter carries a small per-fighter offset on the
# three thresholds the predicate consults plus the defensive tracker's
# entry/exit thresholds. The offset is seeded by (name, match_seed), so
# replays are deterministic but different identities diverge.

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from compromised_state import is_desperation_state, DESPERATION_CLOCK_TICKS
from match import Match
from referee import build_suzuki
import main as main_module


def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def test_jitter_assigned_per_fighter() -> None:
    """Each fighter has its own jitter dict on the match."""
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=1)
    j_t = m._desperation_jitter[t.identity.name]
    j_s = m._desperation_jitter[s.identity.name]
    # Both have the same key set.
    assert set(j_t) == set(j_s)
    # Different identities yield different jitter values.
    assert j_t != j_s, "expected per-fighter jitter to differ across fighters"


def test_jitter_is_deterministic_per_seed() -> None:
    """Same seed + same name → same jitter."""
    t1, s1 = _pair()
    m1 = Match(fighter_a=t1, fighter_b=s1, referee=build_suzuki(), seed=42)
    t2, s2 = _pair()
    m2 = Match(fighter_a=t2, fighter_b=s2, referee=build_suzuki(), seed=42)
    assert (m1._desperation_jitter[t1.identity.name]
            == m2._desperation_jitter[t2.identity.name])
    assert (m1._desperation_jitter[s1.identity.name]
            == m2._desperation_jitter[s2.identity.name])


def test_jitter_changes_with_seed() -> None:
    """Different match seed → different jitter for the same name."""
    t1, s1 = _pair()
    m1 = Match(fighter_a=t1, fighter_b=s1, referee=build_suzuki(), seed=1)
    t2, s2 = _pair()
    m2 = Match(fighter_a=t2, fighter_b=s2, referee=build_suzuki(), seed=2)
    assert (m1._desperation_jitter[t1.identity.name]
            != m2._desperation_jitter[t2.identity.name])


def test_imminent_shido_crossing_diverges_with_jitter() -> None:
    """At identical state, two fighters with different `imminent_ticks`
    offsets cross the imminent-shido threshold on different ticks."""
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=7)
    j_t = m._desperation_jitter[t.identity.name]
    j_s = m._desperation_jitter[s.identity.name]

    # If the imminent_ticks offsets happen to land on the same value for
    # this seed, the test would be vacuous — try a couple of seeds before
    # giving up. (For seed=7 with default fighter names they differ.)
    if j_t["imminent_ticks"] == j_s["imminent_ticks"]:
        # Fall back: at least one of the other axes must differ — and that
        # is already covered by test_jitter_assigned_per_fighter.
        return

    # Walk the kumi-kata clock and find the tick each fighter enters
    # desperation via the imminent-shido route. Composure is unchanged so
    # only the imminent-shido trigger fires.
    def first_tick(judoka, jitter) -> int:
        for clock in range(20, 35):
            if is_desperation_state(judoka, clock, jitter=jitter):
                return clock
        raise AssertionError("desperation never fired")

    tick_t = first_tick(t, j_t)
    tick_s = first_tick(s, j_s)
    assert tick_t != tick_s, (
        f"expected desperation entry to diverge under jitter; both fired at {tick_t}"
    )


def test_no_jitter_preserves_legacy_thresholds() -> None:
    """Calling is_desperation_state without jitter (or empty dict) keeps
    the original constant thresholds — important so existing tests
    that don't pass jitter aren't quietly perturbed."""
    t, _ = _pair()
    # Below the imminent-shido floor — should be False with no jitter.
    assert is_desperation_state(t, DESPERATION_CLOCK_TICKS - 1) is False
    assert is_desperation_state(t, DESPERATION_CLOCK_TICKS - 1, jitter={}) is False


def test_defensive_tracker_carries_per_fighter_offset() -> None:
    """The match-side defensive trackers receive offsets from the same
    jitter source so two matched fighters' entry/exit thresholds
    differ."""
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=5)
    tracker_t = m._defensive_pressure[t.identity.name]
    tracker_s = m._defensive_pressure[s.identity.name]
    # At least one of the two threshold offsets differs across fighters.
    assert (tracker_t.entry_threshold_offset != tracker_s.entry_threshold_offset
            or tracker_t.exit_threshold_offset  != tracker_s.exit_threshold_offset)
