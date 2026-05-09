# tests/test_haj74_golden_score_environment.py
# HAJ-74 — Golden score as a distinct strategic environment.
#
# Promoted to Urgent / Ring 2 calibration prerequisite per
# ring-2-worldgen-spec-v2.md Part II. Without these mechanics modeled in
# the deep engine the calibration corpus systematically under-weights
# conditioning, because the matches that go to overtime are exactly the
# matches where conditioning matters most.
#
# Acceptance criteria covered by this file:
#   1. Cardio drain rate is higher in golden score and escalates linearly
#      with elapsed GS time (BASE at GS entry, BASE+RAMP at full ramp).
#   2. The cardio-drain multiplier is shaved by cardio_efficiency: a
#      high-conditioned judoka burns less per tick in GS than a
#      low-conditioned one at the same elapsed GS time.
#   3. The ne-waza stalemate matte threshold scales up ~25% in golden
#      score (real refs let the only score-deciding ground exchange cook
#      a little longer).
#   4. STAMINA_DESPERATION fires more aggressively in GS — the shido
#      prerequisite is dropped, the cardio ceiling rises, and the
#      per-tick probability is higher.
#   5. SHIDO_FARMING is damped in GS — the v2 spec calls for technique
#      commitment over shido-baiting once regulation is over.
#   6. Shido counts persist across the regulation -> GS boundary (the
#      "two-shido leak" — already covered by HAJ-93 but re-asserted here
#      as part of HAJ-74's contract).
#   7. golden_score flows through MatchState into the referee.

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from enums import Position, SubLoopState
from match import (
    Match, golden_score_cardio_multiplier,
    GOLDEN_SCORE_CARDIO_BASE_MULT, GOLDEN_SCORE_CARDIO_RAMP_MULT,
    GOLDEN_SCORE_RAMP_TICKS, CARDIO_DRAIN_PER_TICK,
)
from referee import (
    MatchState, build_suzuki, GOLDEN_SCORE_STALEMATE_SCALE,
)
from action_selection import (
    _should_fire_stamina_desperation,
    _should_fire_shido_farming,
    SHIDO_FARMING_OPP_CLOCK,
    GS_STAMINA_DESPERATION_CARDIO_MAX,
    GS_SHIDO_FARMING_DAMPER, SHIDO_FARMING_PER_TICK_PROB,
)
import main as main_module


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------
def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _match(regulation_ticks: int = 240, max_ticks: int = 600,
           seed: int = 1) -> tuple:
    random.seed(seed)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        regulation_ticks=regulation_ticks, max_ticks=max_ticks, seed=seed,
    )
    return t, s, m


# ===========================================================================
# AC#1 — Cardio drain escalates linearly with elapsed GS time
# ===========================================================================
def test_cardio_multiplier_at_gs_entry_is_base() -> None:
    """At elapsed_gs_ticks=0 the multiplier equals BASE_MULT (no ramp yet)."""
    m = golden_score_cardio_multiplier(
        elapsed_gs_ticks=0, cardio_efficiency=5,
    )
    assert abs(m - GOLDEN_SCORE_CARDIO_BASE_MULT) < 1e-9


def test_cardio_multiplier_ramps_linearly() -> None:
    """At half ramp, half the RAMP_MULT is added to BASE_MULT."""
    half_ticks = GOLDEN_SCORE_RAMP_TICKS // 2
    m = golden_score_cardio_multiplier(
        elapsed_gs_ticks=half_ticks, cardio_efficiency=5,
    )
    expected = GOLDEN_SCORE_CARDIO_BASE_MULT + 0.5 * GOLDEN_SCORE_CARDIO_RAMP_MULT
    assert abs(m - expected) < 0.05  # int-floor tolerance


def test_cardio_multiplier_caps_at_full_ramp() -> None:
    """Past RAMP_TICKS the multiplier saturates at BASE + RAMP."""
    far = GOLDEN_SCORE_RAMP_TICKS * 3
    m = golden_score_cardio_multiplier(
        elapsed_gs_ticks=far, cardio_efficiency=5,
    )
    expected = GOLDEN_SCORE_CARDIO_BASE_MULT + GOLDEN_SCORE_CARDIO_RAMP_MULT
    assert abs(m - expected) < 1e-9


def test_cardio_drain_higher_in_gs_than_regulation() -> None:
    """Drive _accumulate_base_fatigue once in regulation and once in GS;
    GS drain must exceed regulation drain at the same starting cardio."""
    t, s, m = _match(regulation_ticks=240)
    t.state.cardio_current = 0.8
    s.state.cardio_current = 0.8
    # Regulation drain
    m._accumulate_base_fatigue(t)
    reg_drain = 0.8 - t.state.cardio_current

    # GS drain (entry tick)
    t.state.cardio_current = 0.8
    m.golden_score = True
    m.golden_score_start_tick = 240
    m.ticks_run = 240  # entry tick — multiplier == BASE_MULT (eff-shaved)
    m._accumulate_base_fatigue(t)
    gs_entry_drain = 0.8 - t.state.cardio_current

    assert gs_entry_drain > reg_drain
    # Sanity: drain ratio matches the entry-tick multiplier for THIS
    # fighter's cardio_efficiency (Tanaka isn't neutral, so we compute
    # against the per-fighter expectation rather than the raw constant).
    expected_mult = golden_score_cardio_multiplier(
        elapsed_gs_ticks=0,
        cardio_efficiency=t.capability.cardio_efficiency,
    )
    ratio = gs_entry_drain / reg_drain if reg_drain > 0 else 0.0
    assert abs(ratio - expected_mult) < 0.05


def test_cardio_drain_escalates_inside_gs() -> None:
    """Same fighter, same starting cardio, drain at GS+0 < drain at GS+ramp."""
    t, _, m = _match(regulation_ticks=240)
    m.golden_score = True
    m.golden_score_start_tick = 240

    # Entry tick.
    t.state.cardio_current = 0.8
    m.ticks_run = 240
    m._accumulate_base_fatigue(t)
    entry_drain = 0.8 - t.state.cardio_current

    # Full-ramp tick.
    t.state.cardio_current = 0.8
    m.ticks_run = 240 + GOLDEN_SCORE_RAMP_TICKS
    m._accumulate_base_fatigue(t)
    ramped_drain = 0.8 - t.state.cardio_current

    assert ramped_drain > entry_drain


# ===========================================================================
# AC#2 — Conditioning shaves the GS multiplier
# ===========================================================================
def test_high_conditioning_drains_less_in_gs() -> None:
    """At the same elapsed GS time, cardio_efficiency=10 < cardio_efficiency=1."""
    high = golden_score_cardio_multiplier(
        elapsed_gs_ticks=GOLDEN_SCORE_RAMP_TICKS, cardio_efficiency=10,
    )
    low = golden_score_cardio_multiplier(
        elapsed_gs_ticks=GOLDEN_SCORE_RAMP_TICKS, cardio_efficiency=1,
    )
    assert high < low
    # And the neutral 5 sits between.
    neutral = golden_score_cardio_multiplier(
        elapsed_gs_ticks=GOLDEN_SCORE_RAMP_TICKS, cardio_efficiency=5,
    )
    assert high < neutral < low


def test_multiplier_never_below_unity() -> None:
    """Even cardio_efficiency=10 at full ramp must not produce a multiplier
    below 1.0 — golden score should never be *easier* than regulation."""
    m = golden_score_cardio_multiplier(
        elapsed_gs_ticks=GOLDEN_SCORE_RAMP_TICKS, cardio_efficiency=10,
    )
    assert m >= 1.0


# ===========================================================================
# AC#3 — Stalemate matte threshold scaled up in GS
# ===========================================================================
def test_referee_stalemate_threshold_scaled_in_gs() -> None:
    """Same stalemate_ticks count: regulation calls matte, GS does not
    (until the scaled threshold is reached)."""
    ref = build_suzuki()
    base = ref._NEWAZA_MATTE_TICKS
    scaled = int(round(base * GOLDEN_SCORE_STALEMATE_SCALE))
    assert scaled > base  # sanity

    # At the regulation threshold exactly: regulation fires, GS does not.
    state_reg = MatchState(
        tick=300, position=Position.SIDE_CONTROL,
        sub_loop_state=SubLoopState.NE_WAZA,
        fighter_a_id="A", fighter_b_id="B",
        fighter_a_score={"waza_ari": 0, "ippon": 0, "yuko": 0, "koka": 0},
        fighter_b_score={"waza_ari": 0, "ippon": 0, "yuko": 0, "koka": 0},
        fighter_a_last_attack_tick=0, fighter_b_last_attack_tick=0,
        fighter_a_shidos=0, fighter_b_shidos=0,
        ne_waza_active=True, osaekomi_holder_id=None, osaekomi_ticks=0,
        stalemate_ticks=base, stuffed_throw_tick=0,
        golden_score=False,
    )
    assert ref.should_call_matte(state_reg, 300) is not None

    state_gs = MatchState(
        tick=300, position=Position.SIDE_CONTROL,
        sub_loop_state=SubLoopState.NE_WAZA,
        fighter_a_id="A", fighter_b_id="B",
        fighter_a_score={"waza_ari": 0, "ippon": 0, "yuko": 0, "koka": 0},
        fighter_b_score={"waza_ari": 0, "ippon": 0, "yuko": 0, "koka": 0},
        fighter_a_last_attack_tick=0, fighter_b_last_attack_tick=0,
        fighter_a_shidos=0, fighter_b_shidos=0,
        ne_waza_active=True, osaekomi_holder_id=None, osaekomi_ticks=0,
        stalemate_ticks=base, stuffed_throw_tick=0,
        golden_score=True,
    )
    assert ref.should_call_matte(state_gs, 300) is None

    # At the scaled threshold: GS finally fires.
    state_gs_at_scaled = MatchState(
        tick=300, position=Position.SIDE_CONTROL,
        sub_loop_state=SubLoopState.NE_WAZA,
        fighter_a_id="A", fighter_b_id="B",
        fighter_a_score={"waza_ari": 0, "ippon": 0, "yuko": 0, "koka": 0},
        fighter_b_score={"waza_ari": 0, "ippon": 0, "yuko": 0, "koka": 0},
        fighter_a_last_attack_tick=0, fighter_b_last_attack_tick=0,
        fighter_a_shidos=0, fighter_b_shidos=0,
        ne_waza_active=True, osaekomi_holder_id=None, osaekomi_ticks=0,
        stalemate_ticks=scaled, stuffed_throw_tick=0,
        golden_score=True,
    )
    assert ref.should_call_matte(state_gs_at_scaled, 300) is not None


def test_match_state_carries_golden_score_flag() -> None:
    """_build_match_state surfaces the golden_score field for the ref."""
    _, _, m = _match(regulation_ticks=240)
    state = m._build_match_state(tick=10)
    assert state.golden_score is False
    m.golden_score = True
    state = m._build_match_state(tick=250)
    assert state.golden_score is True


# ===========================================================================
# AC#4 — Stamina desperation gates relax in GS
# ===========================================================================
def test_stamina_desperation_does_not_fire_at_normal_cardio_in_regulation() -> None:
    """Cardio at 0.6 (above regulation 0.50 ceiling, below GS 0.65 ceiling)
    plus zero shidos: regulation gate fails. (Forced rng=None means the
    function returns True if and only if all gates pass.)"""
    t, _, _ = _match()
    t.state.cardio_current = 0.6
    t.state.shidos = 0
    # Force hand-fatigue above the regulation floor so that's not the
    # discriminator under test.
    for hand in ("right_hand", "left_hand"):
        t.state.body[hand].fatigue = 0.50
    assert _should_fire_stamina_desperation(
        t, rng=None, golden_score=False,
    ) is False


def test_stamina_desperation_can_fire_at_normal_cardio_in_gs() -> None:
    """Same fighter at the same cardio (0.6), zero shidos — GS gate passes
    where regulation gate failed: the cardio ceiling rose AND the shido
    prerequisite was dropped."""
    t, _, _ = _match()
    t.state.cardio_current = 0.6
    t.state.shidos = 0
    for hand in ("right_hand", "left_hand"):
        t.state.body[hand].fatigue = 0.30
    assert t.state.cardio_current <= GS_STAMINA_DESPERATION_CARDIO_MAX
    assert _should_fire_stamina_desperation(
        t, rng=None, golden_score=True,
    ) is True


def test_stamina_desperation_higher_per_tick_probability_in_gs() -> None:
    """Over many trials the GS firing rate exceeds the regulation rate."""
    t, _, _ = _match()
    # Set cardio low enough that BOTH gates pass on the hard checks; the
    # only discriminator left is the per-tick probability.
    t.state.cardio_current = 0.4
    t.state.shidos = 1
    for hand in ("right_hand", "left_hand"):
        t.state.body[hand].fatigue = 0.50

    rng_reg = random.Random(123)
    rng_gs = random.Random(123)
    reg_fires = sum(1 for _ in range(2000) if _should_fire_stamina_desperation(
        t, rng=rng_reg, golden_score=False,
    ))
    gs_fires = sum(1 for _ in range(2000) if _should_fire_stamina_desperation(
        t, rng=rng_gs, golden_score=True,
    ))
    assert gs_fires > reg_fires
    # GS rate ~0.40, regulation rate ~0.20 — comfortable separation expected.
    assert gs_fires > reg_fires * 1.5


# ===========================================================================
# AC#5 — Shido farming damped in GS
# ===========================================================================
def test_shido_farming_damped_in_gs() -> None:
    """All hard gates pass; only the per-tick probability differs.
    GS damper should produce noticeably fewer fires."""
    t, _, _ = _match()
    # Style-DNA must clear the tendency floor.
    t.identity.style_dna["shido_farming_tendency"] = 0.6

    perceived = {}  # empty -> "no scoring opportunity" branch
    rng_reg = random.Random(7)
    rng_gs = random.Random(7)
    reg_fires = sum(
        1 for _ in range(5000)
        if _should_fire_shido_farming(
            t, opponent_kumi_kata_clock=SHIDO_FARMING_OPP_CLOCK + 5,
            perceived_by_throw=perceived, rng=rng_reg, golden_score=False,
        )
    )
    gs_fires = sum(
        1 for _ in range(5000)
        if _should_fire_shido_farming(
            t, opponent_kumi_kata_clock=SHIDO_FARMING_OPP_CLOCK + 5,
            perceived_by_throw=perceived, rng=rng_gs, golden_score=True,
        )
    )
    assert reg_fires > 0
    # GS rate should sit near reg_rate * damper, with stochastic slack.
    expected_gs = reg_fires * GS_SHIDO_FARMING_DAMPER
    assert gs_fires < reg_fires * 0.5
    assert abs(gs_fires - expected_gs) < reg_fires * 0.5  # loose


# ===========================================================================
# AC#6 — Shido counts persist across the regulation -> GS boundary
# ===========================================================================
def test_shidos_persist_across_regulation_boundary() -> None:
    """A fighter who arrived at regulation with two shidos still has two
    shidos in golden score. _check_regulation_end must not reset them."""
    t, s, m = _match(regulation_ticks=240, max_ticks=600)
    t.state.shidos = 2
    s.state.shidos = 1
    events: list = []
    m._check_regulation_end(tick=240, events=events)
    assert m.golden_score is True
    assert t.state.shidos == 2
    assert s.state.shidos == 1


# ===========================================================================
# AC#7 — Cardio drain is unchanged outside golden score
# ===========================================================================
def test_cardio_drain_unchanged_in_regulation() -> None:
    """Regression guard: in regulation, drain equals the legacy constant
    (modulo posture, which doesn't trigger from the bench fixture)."""
    t, _, m = _match()
    t.state.cardio_current = 0.8
    assert m.golden_score is False
    m._accumulate_base_fatigue(t)
    assert abs((0.8 - t.state.cardio_current) - CARDIO_DRAIN_PER_TICK) < 1e-9
