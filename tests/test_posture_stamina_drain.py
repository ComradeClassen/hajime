# tests/test_posture_stamina_drain.py
# Verifies HAJ-56: posture-driven continuous stamina drain.
#
# A bent-over fighter (trunk_sagittal beyond UPRIGHT_LIMIT_RAD) burns extra
# cardio per tick on top of CARDIO_DRAIN_PER_TICK. Back-lean is exempt — it's
# the evasion posture, not muscular compensation.

from __future__ import annotations
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka, UPRIGHT_LIMIT_RAD
from match import (
    Match, CARDIO_DRAIN_PER_TICK, POSTURE_BENT_CARDIO_DRAIN,
)
from referee import build_suzuki
import main as main_module


def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def test_upright_fighter_pays_only_base_cardio_drain() -> None:
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    t.state.body_state.trunk_sagittal = 0.0
    before = t.state.cardio_current
    m._accumulate_base_fatigue(t)
    assert math.isclose(before - t.state.cardio_current, CARDIO_DRAIN_PER_TICK)


def test_bent_fighter_pays_posture_surcharge() -> None:
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    # Solidly past UPRIGHT_LIMIT_RAD (~15°): a 25° forward bend.
    t.state.body_state.trunk_sagittal = math.radians(25)
    before = t.state.cardio_current
    m._accumulate_base_fatigue(t)
    drained = before - t.state.cardio_current
    expected = CARDIO_DRAIN_PER_TICK + POSTURE_BENT_CARDIO_DRAIN
    assert math.isclose(drained, expected)


def test_back_lean_is_not_taxed() -> None:
    """Back-lean is the O-soto-defense posture — not a muscular-compensation
    state. The drain triggers on forward bend only."""
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    t.state.body_state.trunk_sagittal = math.radians(-20)
    before = t.state.cardio_current
    m._accumulate_base_fatigue(t)
    assert math.isclose(before - t.state.cardio_current, CARDIO_DRAIN_PER_TICK)


def test_threshold_boundary_is_exclusive() -> None:
    """At exactly UPRIGHT_LIMIT_RAD the fighter is still considered upright;
    surcharge fires strictly above."""
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki())
    t.state.body_state.trunk_sagittal = UPRIGHT_LIMIT_RAD
    before = t.state.cardio_current
    m._accumulate_base_fatigue(t)
    assert math.isclose(before - t.state.cardio_current, CARDIO_DRAIN_PER_TICK)


def test_drain_compounds_over_match_length() -> None:
    """Over a 4-min match (~240 ticks) a permanently-bent fighter loses
    meaningfully more cardio than an upright one. Sanity-check the
    compounding."""
    t_bent, s1 = _pair()
    t_up,   s2 = _pair()
    m_bent = Match(fighter_a=t_bent, fighter_b=s1, referee=build_suzuki())
    m_up   = Match(fighter_a=t_up,   fighter_b=s2, referee=build_suzuki())
    t_bent.state.body_state.trunk_sagittal = math.radians(25)
    t_up.state.body_state.trunk_sagittal   = 0.0
    for _ in range(240):
        m_bent._accumulate_base_fatigue(t_bent)
        m_up._accumulate_base_fatigue(t_up)
    extra = t_up.state.cardio_current - t_bent.state.cardio_current
    # 240 ticks * 0.001/tick = 0.24 cardio premium
    assert math.isclose(extra, 240 * POSTURE_BENT_CARDIO_DRAIN, rel_tol=1e-9)
