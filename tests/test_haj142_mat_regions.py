# tests/test_haj142_mat_regions.py
# HAJ-142 — graded mat regions and boundary-aware behaviors.
#
# HAJ-127 added binary OOB detection; this ticket layers a graded
# region system (CENTER / WORKING / WARNING / OUT_OF_BOUNDS) on top so
# the engine can model boundary-as-tactic in addition to boundary-as-
# event. AC coverage:
#
#   AC#1 — region_of helper exists, returns one of the four enums,
#          pure function of CoM.
#   AC#2 — Region exposed in MatchState (fighter_a_region /
#          fighter_b_region).
#   AC#3 — Edge-pressure STEP_IN bias active when opponent in WARNING
#          and actor fight_iq above threshold.
#   AC#4 — CRAWL_TOWARD_BOUNDARY ne-waza CoM drift + eventual OOB.
#   AC#5 — STEP_OUT_VOLUNTARY produces shido without throw resolution.
#   AC#6 — Matte resumes at center mark.
#   AC#7 — Three regression tests (covered: region transitions,
#          crawl-to-OOB, voluntary step-out).
#   AC#8 — No prose regressions (covered by full-suite green).

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from enums import (
    BodyArchetype, MatRegion, Position, SubLoopState,
)
from body_state import place_judoka
from match import (
    MAT_HALF_WIDTH, MAT_REGION_CENTER_FRAC, MAT_REGION_WARNING_FRAC,
    Match, region_of, is_out_of_bounds,
)
from referee import build_suzuki
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


def _new_match(seed: int = 1):
    random.seed(seed)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=40, seed=seed, stream="prose",
    )
    m._print_header = lambda: None
    return t, s, m


def _set_com(j, x: float, y: float = 0.0):
    j.state.body_state.com_position = (x, y)


# ===========================================================================
# AC#1 — region_of helper
# ===========================================================================
def test_region_of_at_origin_is_center() -> None:
    t, _ = _pair()
    _set_com(t, 0.0, 0.0)
    assert region_of(t) is MatRegion.CENTER


def test_region_of_at_center_band_edge_stays_center() -> None:
    t, _ = _pair()
    _set_com(t, MAT_HALF_WIDTH * MAT_REGION_CENTER_FRAC, 0.0)
    assert region_of(t) is MatRegion.CENTER


def test_region_of_in_working_band() -> None:
    t, _ = _pair()
    mid = MAT_HALF_WIDTH * (
        MAT_REGION_CENTER_FRAC + MAT_REGION_WARNING_FRAC
    ) / 2.0
    _set_com(t, mid, 0.0)
    assert region_of(t) is MatRegion.WORKING


def test_region_of_in_warning_band() -> None:
    t, _ = _pair()
    _set_com(t, MAT_HALF_WIDTH * 0.85, 0.0)
    assert region_of(t) is MatRegion.WARNING


def test_region_of_out_of_bounds() -> None:
    t, _ = _pair()
    _set_com(t, MAT_HALF_WIDTH + 0.5, 0.0)
    assert region_of(t) is MatRegion.OUT_OF_BOUNDS
    # OOB and OUT_OF_BOUNDS region agree.
    assert is_out_of_bounds(t)


def test_region_of_uses_chebyshev_distance() -> None:
    """Square-mat geometry: a point at (3.5, 3.5) is in WARNING because
    the nearest edge is min(MAT_HALF_WIDTH-3.5)=0.5 m, putting Chebyshev
    distance at 3.5 — well into WARNING."""
    t, _ = _pair()
    _set_com(t, 3.5, 3.5)
    assert region_of(t) is MatRegion.WARNING


# ===========================================================================
# AC#2 — Region exposed on MatchState
# ===========================================================================
def test_match_state_exposes_per_fighter_region() -> None:
    t, s, m = _new_match()
    _set_com(t, 0.1, 0.0)
    _set_com(s, MAT_HALF_WIDTH * 0.85, 0.0)
    state = m._build_match_state(tick=5)
    assert state.fighter_a_region == "CENTER"
    assert state.fighter_b_region == "WARNING"


# ===========================================================================
# AC#3 — Edge-pressure STEP_IN bias
# ===========================================================================
def test_edge_pressure_inactive_when_opponent_in_center() -> None:
    from action_selection import _edge_pressure_active
    t, s = _pair()
    t.capability.fight_iq = 9
    _set_com(s, 0.0, 0.0)  # opponent in center
    assert not _edge_pressure_active(t, s)


def test_edge_pressure_inactive_for_low_iq_actor() -> None:
    from action_selection import _edge_pressure_active
    t, s = _pair()
    t.capability.fight_iq = 2  # below threshold
    _set_com(s, MAT_HALF_WIDTH * 0.85, 0.0)
    assert not _edge_pressure_active(t, s)


def test_edge_pressure_active_when_opponent_in_warning_and_iq_high() -> None:
    from action_selection import _edge_pressure_active
    t, s = _pair()
    t.capability.fight_iq = 9
    _set_com(s, MAT_HALF_WIDTH * 0.85, 0.0)
    assert _edge_pressure_active(t, s)


def test_closing_step_biases_toward_boundary_when_edge_pressure_active() -> None:
    """STEP_IN against a WARNING-region opponent skews the direction off
    the dyad axis toward the opponent's nearest boundary, instead of
    aiming straight at their CoM. Place the opponent off the actor's
    axis so the bias has a measurable effect (1D dyad axes coincide
    with the edge direction by construction)."""
    from action_selection import _closing_step_action
    t, s = _pair()
    t.capability.fight_iq = 9
    _set_com(t, -2.0, 0.0)
    _set_com(s, MAT_HALF_WIDTH * 0.90, MAT_HALF_WIDTH * 0.50)
    # Plain (no edge pressure): aims at opponent CoM.
    t.capability.fight_iq = 0
    plain = _closing_step_action(t, s)
    # Biased: aims toward the corner the opponent is in.
    t.capability.fight_iq = 9
    biased = _closing_step_action(t, s)
    assert plain is not None and biased is not None
    plain_unit = _unit(plain.direction)
    biased_unit = _unit(biased.direction)
    assert plain_unit != biased_unit, (
        f"edge-pressure bias produced no measurable direction shift: "
        f"plain={plain_unit} biased={biased_unit}"
    )
    # The biased step has a stronger y-component (toward the corner)
    # than the plain dyad-axis step.
    assert abs(biased_unit[1]) >= abs(plain_unit[1])


def _unit(v):
    x, y = v
    n = (x * x + y * y) ** 0.5 or 1.0
    return (round(x / n, 4), round(y / n, 4))


# ===========================================================================
# AC#4 — CRAWL_TOWARD_BOUNDARY ne-waza CoM drift
# ===========================================================================
def test_crawl_toward_boundary_moves_bottom_com_when_under_threat() -> None:
    """Set up a ne-waza scenario with the bottom in WARNING under an
    active pin; run the crawl helper a few times and verify CoM moves
    toward the nearest boundary."""
    t, s, m = _new_match(seed=3)
    m.sub_loop_state = SubLoopState.NE_WAZA
    m.position = Position.SIDE_CONTROL
    m.ne_waza_top_id = t.identity.name
    # Bottom (sato) in WARNING band.
    _set_com(s, MAT_HALF_WIDTH * 0.85, 0.0)
    _set_com(t, MAT_HALF_WIDTH * 0.85, 0.0)
    m.osaekomi.start(t.identity.name, Position.SIDE_CONTROL)
    s.capability.ne_waza_skill = 9  # high crawl probability
    starting_x = s.state.body_state.com_position[0]
    # Run several ticks of the helper; with skill=9 + WARNING, ~30% per
    # tick — over 30 ticks we expect at least one crawl to fire and CoM
    # to advance toward the boundary.
    fired = False
    for tick in range(1, 30):
        evs = m._maybe_crawl_toward_boundary(tick)
        if evs:
            fired = True
            assert evs[0].event_type == "CRAWL_TOWARD_BOUNDARY"
            break
    assert fired
    # CoM x increased (advanced toward +x boundary).
    assert s.state.body_state.com_position[0] > starting_x


def test_crawl_skips_when_not_under_threat() -> None:
    t, s, m = _new_match(seed=4)
    m.sub_loop_state = SubLoopState.NE_WAZA
    m.position = Position.GUARD_TOP
    m.ne_waza_top_id = t.identity.name
    _set_com(s, MAT_HALF_WIDTH * 0.85, 0.0)
    # No active pin / technique — should not fire.
    for tick in range(1, 30):
        evs = m._maybe_crawl_toward_boundary(tick)
        assert evs == []


def test_crawl_skips_when_bottom_in_center() -> None:
    t, s, m = _new_match(seed=5)
    m.sub_loop_state = SubLoopState.NE_WAZA
    m.position = Position.SIDE_CONTROL
    m.ne_waza_top_id = t.identity.name
    m.osaekomi.start(t.identity.name, Position.SIDE_CONTROL)
    _set_com(s, 0.0, 0.0)  # CENTER
    for tick in range(1, 30):
        evs = m._maybe_crawl_toward_boundary(tick)
        assert evs == []


# ===========================================================================
# AC#5 — STEP_OUT_VOLUNTARY shido-eat
# ===========================================================================
def test_step_out_voluntary_fires_under_warning_and_desperation() -> None:
    """When the perceiver is in WARNING + defensive desperation +
    high-enough IQ, an opposing throw_commit intent triggers a
    voluntary OOB step. The staged commit is cancelled."""
    from intent_signal import IntentSignal, SETUP_THROW_COMMIT
    t, s, m = _new_match(seed=11)
    # Sato (perceiver) is the would-be victim; place near boundary.
    _set_com(s, MAT_HALF_WIDTH * 0.85, 0.0)
    s.capability.fight_iq = 9
    s.state.composure_current = 0.5  # low composure
    m._defensive_desperation_active[s.identity.name] = True
    # Stage a commit-from-tanaka consequence so the cancellation has
    # something to cancel.
    from match import _Consequence
    m._consequence_queue.append(_Consequence(
        due_tick=11, kind="FIRE_COMMIT_FROM_INTENT",
        payload={"attacker_name": t.identity.name},
    ))
    sig = IntentSignal(
        tick=10, fighter=t.identity.name,
        setup_class=SETUP_THROW_COMMIT,
        throw_id=None,
    )
    events: list = []
    fired = False
    # Run several seeds — voluntary step-out is probabilistic.
    for n in range(20):
        m._consequence_queue.append(_Consequence(
            due_tick=11, kind="FIRE_COMMIT_FROM_INTENT",
            payload={"attacker_name": t.identity.name},
        ))
        events.clear()
        # Reset CoM for each trial.
        _set_com(s, MAT_HALF_WIDTH * 0.85, 0.0)
        if m._maybe_step_out_voluntary(s, t, sig, 10 + n, events):
            fired = True
            break
    assert fired, "expected voluntary step-out to fire under desperation"
    # The step-out event was emitted.
    voluntary = [e for e in events if e.event_type == "STEP_OUT_VOLUNTARY"]
    assert voluntary
    # The perceiver landed OOB.
    assert is_out_of_bounds(s)
    # The staged commit consequence was cancelled.
    pending = [
        c for c in m._consequence_queue
        if c.kind == "FIRE_COMMIT_FROM_INTENT"
        and c.payload.get("attacker_name") == t.identity.name
    ]
    assert pending == []


def test_step_out_voluntary_skips_in_center_or_low_iq() -> None:
    """Gate combinations that should NOT fire: actor in CENTER, or
    actor with low fight_iq — both leave the engine alone."""
    from intent_signal import IntentSignal, SETUP_THROW_COMMIT
    t, s, m = _new_match(seed=12)
    # Centered, high IQ + desperation: still no fire (gate is region).
    _set_com(s, 0.0, 0.0)
    s.capability.fight_iq = 9
    m._defensive_desperation_active[s.identity.name] = True
    sig = IntentSignal(
        tick=5, fighter=t.identity.name,
        setup_class=SETUP_THROW_COMMIT, throw_id=None,
    )
    for n in range(10):
        events: list = []
        assert not m._maybe_step_out_voluntary(s, t, sig, 5 + n, events)

    # WARNING, low IQ: also no fire.
    _set_com(s, MAT_HALF_WIDTH * 0.85, 0.0)
    s.capability.fight_iq = 2
    for n in range(10):
        events: list = []
        assert not m._maybe_step_out_voluntary(s, t, sig, 5 + n, events)


# ===========================================================================
# AC#6 — Matte resumes at center
# ===========================================================================
def test_matte_resume_places_fighters_centered_on_origin() -> None:
    """After a matte / post-score reset, both fighters are seated
    symmetrically across the mat origin — center attractor at reset.
    Per AC#6 the placement is `(0, 0)` modulo HAJ-141's STANDING_DISTANT
    separation; each fighter lands at ±half-separation on the x-axis."""
    from match import STANDING_DISTANT_SEPARATION_M
    t, s, m = _new_match()
    _set_com(t, 3.0, 1.5)  # somewhere off-center
    _set_com(s, -2.5, -1.0)
    m._reset_dyad_to_distant(tick=20)
    tx, ty = t.state.body_state.com_position
    sx, sy = s.state.body_state.com_position
    # Symmetric across origin.
    assert abs(tx + sx) < 1e-6
    assert abs(ty + sy) < 1e-6
    # Each at half the standing-distant separation from origin.
    half = STANDING_DISTANT_SEPARATION_M / 2.0
    assert abs(abs(tx) - half) < 1e-6
    # Both fighters land in CENTER or WORKING (not WARNING) — they
    # have moved off the previous off-center positions.
    assert region_of(t) in (MatRegion.CENTER, MatRegion.WORKING)
    assert region_of(s) in (MatRegion.CENTER, MatRegion.WORKING)


# ===========================================================================
# AC#7 — Region transitions surface in narration
# ===========================================================================
def test_region_transition_prose_fires_on_warning_entry() -> None:
    from narration.altitudes.mat_side import MatSideNarrator
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    # First tick — establishes baseline.
    _set_com(t, 0.0, 0.0)
    narrator._last_phase = "grip_war"
    m.position = Position.GRIPPING
    narrator.consume_tick(0, [], [], m)
    # Move into WARNING and consume next tick.
    _set_com(t, MAT_HALF_WIDTH * 0.85, 0.0)
    entries = narrator.consume_tick(1, [], [], m)
    region = [e for e in entries if e.source == "region"]
    assert region, "expected region transition prose on WARNING entry"
    assert "warning" in region[0].prose.lower() or "edge" in region[0].prose.lower()


def test_region_transition_prose_silent_on_oob() -> None:
    """OOB transitions are owned by the existing HAJ-127 / Matte prose
    path; the new region narrator must not double-author."""
    from narration.altitudes.mat_side import MatSideNarrator
    t, s, m = _new_match()
    narrator = MatSideNarrator()
    _set_com(t, MAT_HALF_WIDTH * 0.85, 0.0)
    narrator._last_phase = "grip_war"
    m.position = Position.GRIPPING
    narrator.consume_tick(0, [], [], m)
    _set_com(t, MAT_HALF_WIDTH + 0.5, 0.0)
    entries = narrator.consume_tick(1, [], [], m)
    region = [e for e in entries if e.source == "region"]
    assert region == []


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    import traceback
    passed = 0
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                passed += 1
                print(f"PASS  {name}")
            except Exception:
                failed += 1
                print(f"FAIL  {name}")
                traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
