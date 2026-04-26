# tests/test_stiffness_telegraphing.py
# Verifies HAJ-58: stiffness-induced telegraphing as a perception modifier.
#
# A bent-over attacker (trunk_sagittal beyond UPRIGHT_LIMIT_RAD) broadcasts
# intent through grip tension. The defender's counter-window perception flip
# probability drops by ATTACKER_STIFFNESS_PERCEPTION_BONUS, so they read the
# attack more accurately.
#
# Three rules to lock:
#   1. Stiff attacker → fewer mispercpetions on real (non-NONE) windows.
#   2. Upright attacker → no change.
#   3. NONE windows are immune (symmetry with the desperation rule —
#      stiffness shouldn't summon ghost attacks).

from __future__ import annotations
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka, UPRIGHT_LIMIT_RAD
from counter_windows import (
    CounterWindow, perceived_counter_window,
    ATTACKER_STIFFNESS_PERCEPTION_BONUS,
)
import main as main_module


def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _count_matches(actual, defender, attacker, n=1000):
    matches = 0
    for seed in range(n):
        p = perceived_counter_window(
            actual, defender, rng=random.Random(seed),
            attacker=attacker,
        )
        if p == actual:
            matches += 1
    return matches


def test_stiff_attacker_telegraphs_more_than_upright_attacker() -> None:
    """Same defender, same window — bent-over attacker is read more accurately."""
    t, s = _pair()
    s.capability.fight_iq = 5   # mid IQ so flip_p has room to move (~0.125)
    # Upright attacker baseline.
    t.state.body_state.trunk_sagittal = 0.0
    upright_matches = _count_matches(CounterWindow.SEN_NO_SEN, s, t)
    # Bent attacker — past UPRIGHT_LIMIT_RAD (~15°).
    t.state.body_state.trunk_sagittal = math.radians(25)
    stiff_matches = _count_matches(CounterWindow.SEN_NO_SEN, s, t)
    assert stiff_matches > upright_matches


def test_back_lean_attacker_does_not_telegraph() -> None:
    """Back-lean is evasion posture, not muscular tension. No bonus."""
    t, s = _pair()
    s.capability.fight_iq = 5
    t.state.body_state.trunk_sagittal = 0.0
    upright_matches = _count_matches(CounterWindow.SEN_NO_SEN, s, t)
    t.state.body_state.trunk_sagittal = math.radians(-25)
    leaning_matches = _count_matches(CounterWindow.SEN_NO_SEN, s, t)
    assert abs(stiff_diff := leaning_matches - upright_matches) <= 30  # noise band


def test_attacker_omitted_preserves_legacy_behavior() -> None:
    """Calling without `attacker` must not change perception vs. baseline."""
    t, s = _pair()
    s.capability.fight_iq = 5
    legacy_matches = 0
    new_matches = 0
    for seed in range(500):
        p_legacy = perceived_counter_window(
            CounterWindow.SEN_NO_SEN, s, rng=random.Random(seed),
        )
        p_new = perceived_counter_window(
            CounterWindow.SEN_NO_SEN, s, rng=random.Random(seed),
            attacker=None,
        )
        if p_legacy == CounterWindow.SEN_NO_SEN:
            legacy_matches += 1
        if p_new == CounterWindow.SEN_NO_SEN:
            new_matches += 1
    assert legacy_matches == new_matches


def test_stiffness_does_not_summon_ghost_attack_on_none_window() -> None:
    """A bent-over attacker should not make the defender hallucinate
    attacks. NONE → adjacent flip probability is unaffected by stiffness."""
    t, s = _pair()
    s.capability.fight_iq = 5
    t.state.body_state.trunk_sagittal = 0.0
    upright_none_matches = _count_matches(CounterWindow.NONE, s, t)
    t.state.body_state.trunk_sagittal = math.radians(25)
    stiff_none_matches = _count_matches(CounterWindow.NONE, s, t)
    # Should be statistically indistinguishable.
    assert abs(stiff_none_matches - upright_none_matches) <= 30


def test_threshold_boundary_is_exclusive() -> None:
    """At exactly UPRIGHT_LIMIT_RAD, the attacker is still upright — no bonus."""
    t, s = _pair()
    s.capability.fight_iq = 5
    t.state.body_state.trunk_sagittal = 0.0
    upright_matches = _count_matches(CounterWindow.SEN_NO_SEN, s, t)
    t.state.body_state.trunk_sagittal = UPRIGHT_LIMIT_RAD
    boundary_matches = _count_matches(CounterWindow.SEN_NO_SEN, s, t)
    assert abs(boundary_matches - upright_matches) <= 30


def test_bonus_magnitude_is_calibrated() -> None:
    """Sanity-check: with iq=0 the flip rate is COUNTER_PERCEPTION_FLIP_PROB
    (0.25). A stiff attacker drops it by ATTACKER_STIFFNESS_PERCEPTION_BONUS
    (0.05) → ~0.20. Match-rate should rise by ~5 percentage points."""
    t, s = _pair()
    s.capability.fight_iq = 0
    n = 2000
    t.state.body_state.trunk_sagittal = 0.0
    upright_rate = _count_matches(CounterWindow.SEN_NO_SEN, s, t, n=n) / n
    t.state.body_state.trunk_sagittal = math.radians(25)
    stiff_rate = _count_matches(CounterWindow.SEN_NO_SEN, s, t, n=n) / n
    lift = stiff_rate - upright_rate
    # Expected lift is the bonus (0.05); allow ±0.02 sampling noise.
    assert abs(lift - ATTACKER_STIFFNESS_PERCEPTION_BONUS) < 0.02
