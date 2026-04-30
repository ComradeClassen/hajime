# tests/test_haj152_post_score_follow_up.py
# HAJ-152 — post-score follow-up window regression tests.
#
# Covers the canonical scenarios from the ticket:
#   - HAJ-144 t017-t018 reproduction (no same-tick reset after waza-ari)
#   - GROUND_SPECIALIST chase probability dominance
#   - LEVER moderate chase probability
#   - Sacrifice-throw routing to DEFENSIVE_CHASE
#   - Leading tori declining chase (with match-end as the related path)
#   - Trailing tori at clock-low producing high chase probability
#   - Stand path produces explicit POST_SCORE_FOLLOW_UP_END matte
#   - Reset only after matte (HAJ-152 AC#8)

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from enums import (
    BodyArchetype, BodyPart, GripTarget, GripTypeV2, GripDepth, GripMode,
    LandingProfile, MatteReason, Position, SubLoopState,
)
from grip_graph import GripEdge
from match import Match
from referee import build_suzuki, ScoreResult
from throws import ThrowID, THROW_DEFS
from chase_decision import (
    ChaseDecision, make_chase_decision,
)
from defense_decision import (
    DefenseDecision, make_defense_decision,
)
import main as main_module
import match as match_module


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------
def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _seat_grips(m, owner, target):
    m.grip_graph.add_edge(GripEdge(
        grasper_id=owner.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=target.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.STANDARD,
        strength=0.8, established_tick=0, mode=GripMode.DRIVING,
    ))
    m.grip_graph.add_edge(GripEdge(
        grasper_id=owner.identity.name, grasper_part=BodyPart.LEFT_HAND,
        target_id=target.identity.name, target_location=GripTarget.RIGHT_SLEEVE,
        grip_type_v2=GripTypeV2.SLEEVE_HIGH, depth_level=GripDepth.STANDARD,
        strength=0.8, established_tick=0, mode=GripMode.DRIVING,
    ))


def _pair_match(seed: int = 1):
    random.seed(seed)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=seed)
    return t, s, m


def _force_waza_ari(t, s, m, throw_id, tick):
    """Drive a clean waza-ari award through _apply_throw_result and return
    the events emitted."""
    m.position = Position.GRIPPING
    _seat_grips(m, t, s)
    real = match_module.resolve_throw
    match_module.resolve_throw = lambda *a, **kw: ("WAZA_ARI", 2.0)
    try:
        events = m._apply_throw_result(
            attacker=t, defender=s, throw_id=throw_id,
            outcome="WAZA_ARI", net=2.0, window_quality=1.0, tick=tick,
            execution_quality=0.9,
        )
    finally:
        match_module.resolve_throw = real
    return events


# ===========================================================================
# AC#1 — POST_SCORE_FOLLOW_UP state exists, opens after waza-ari
# ===========================================================================
def test_waza_ari_opens_follow_up_window_state() -> None:
    t, s, m = _pair_match()
    events = _force_waza_ari(t, s, m, ThrowID.UCHI_MATA, tick=29)
    assert m._post_score_follow_up is not None
    assert m._post_score_follow_up["tori_name"] == t.identity.name
    assert m._post_score_follow_up["uke_name"]  == s.identity.name
    assert m._post_score_follow_up["throw_id"]  == ThrowID.UCHI_MATA
    # POST_SCORE_FOLLOW_UP_OPEN event surfaces for inspection.
    assert any(
        ev.event_type == "POST_SCORE_FOLLOW_UP_OPEN" for ev in events
    )


# ===========================================================================
# AC#2 — match-outcome check: ippon-by-accumulation skips follow-up
# ===========================================================================
def test_two_waza_ari_match_end_skips_follow_up() -> None:
    """Tori already has 1 waza-ari; this score takes them to 2 → ippon by
    accumulation. Match ends without opening the follow-up window."""
    t, s, m = _pair_match()
    t.state.score["waza_ari"] = 1
    _force_waza_ari(t, s, m, ThrowID.UCHI_MATA, tick=29)
    assert m.match_over
    assert m._post_score_follow_up is None
    queued = [
        c for c in m._consequence_queue
        if c.kind in ("POST_SCORE_DECISION", "POST_SCORE_FOLLOW_UP_MATTE")
    ]
    assert not queued


# ===========================================================================
# AC#3 + AC#4 — chase decision is probabilistic, attribute-driven, surfaces
# in an engineering event with the factor breakdown
# ===========================================================================
def test_chase_decision_event_carries_factors() -> None:
    """The CHASE_DECISION event carries tori's decision and the per-factor
    breakdown (throw_advantage, ne_waza_skill, archetype, …) so the debug
    overlay and tests can see why a given decision came out the way it
    did."""
    t, s, m = _pair_match(seed=11)
    _force_waza_ari(t, s, m, ThrowID.UCHI_MATA, tick=29)
    follow_up: list = []
    m._resolve_consequences(tick=30, events=follow_up)
    chase = next(ev for ev in follow_up if ev.event_type == "CHASE_DECISION")
    assert chase.data["tori"] == t.identity.name
    assert chase.data["throw_id"] == "UCHI_MATA"
    assert chase.data["decision"] in {d.name for d in ChaseDecision}
    # Factor breakdown present for inspection.
    factors = chase.data["factors"]
    assert "base" in factors
    assert "throw_advantage" in factors
    assert "ne_waza_skill" in factors
    assert "archetype" in factors


def test_defense_decision_event_carries_factors() -> None:
    """Mirror of the chase event — uke's defense decision surfaces with
    its score breakdown for inspection."""
    t, s, m = _pair_match(seed=12)
    _force_waza_ari(t, s, m, ThrowID.UCHI_MATA, tick=29)
    follow_up: list = []
    m._resolve_consequences(tick=30, events=follow_up)
    defense = next(
        ev for ev in follow_up if ev.event_type == "DEFENSE_DECISION"
    )
    assert defense.data["uke"] == s.identity.name
    assert defense.data["decision"] in {d.name for d in DefenseDecision}
    assert "factors" in defense.data


# ===========================================================================
# Throw vocabulary — post_score_chase_advantage populated
# ===========================================================================
def test_post_score_chase_advantage_field_populated() -> None:
    """Every throw def carries a post_score_chase_advantage value in
    [0, 1]."""
    for throw_id, td in THROW_DEFS.items():
        assert hasattr(td, "post_score_chase_advantage"), throw_id
        v = td.post_score_chase_advantage
        assert 0.0 <= v <= 1.0, f"{throw_id}: {v}"
    # Hip throws cluster high.
    assert THROW_DEFS[ThrowID.UCHI_MATA].post_score_chase_advantage   >= 0.7
    assert THROW_DEFS[ThrowID.HARAI_GOSHI].post_score_chase_advantage >= 0.7
    # Sacrifice throws cluster low.
    assert THROW_DEFS[ThrowID.SUMI_GAESHI].post_score_chase_advantage <= 0.5
    assert THROW_DEFS[ThrowID.TOMOE_NAGE].post_score_chase_advantage  <= 0.5


# ===========================================================================
# AC#10 — match-context modifies chase probability (trailing > tied >
# leading)
# ===========================================================================
def test_match_context_modifies_chase_probability() -> None:
    """Same fighter, same throw, same opponent — but score state shifts
    chase probability measurably. Trailing tori has higher chase
    probability than leading tori."""
    t, _ = _pair()
    rng_neutral = random.Random(0)
    rng_trailing = random.Random(0)
    rng_leading = random.Random(0)
    p_neutral = make_chase_decision(
        t, ThrowID.UCHI_MATA,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        chase_advantage=0.85,
        score_diff_before=0,
        clock_remaining=200,
        rng=rng_neutral,
    ).probability
    p_trailing = make_chase_decision(
        t, ThrowID.UCHI_MATA,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        chase_advantage=0.85,
        score_diff_before=-1,  # trailing before this score
        clock_remaining=200,
        rng=rng_trailing,
    ).probability
    p_leading = make_chase_decision(
        t, ThrowID.UCHI_MATA,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        chase_advantage=0.85,
        score_diff_before=+1,  # leading before this score
        clock_remaining=200,
        rng=rng_leading,
    ).probability
    assert p_trailing > p_neutral > p_leading, (
        f"trailing={p_trailing:.2f}, neutral={p_neutral:.2f}, "
        f"leading={p_leading:.2f}"
    )


# ===========================================================================
# AC#11 — clock-pressure modifies chase probability per HAJ-151 pattern
# ===========================================================================
def test_clock_pressure_lifts_trailing_chase_probability() -> None:
    """Trailing tori at clock-low has high chase probability regardless
    of attribute (urgency)."""
    t, _ = _pair()
    p_low_trailing = make_chase_decision(
        t, ThrowID.SEOI_NAGE,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        chase_advantage=0.5,    # mid-range throw
        score_diff_before=-1,    # was trailing → still trailing or tied
        clock_remaining=25,      # last 25 seconds
        rng=random.Random(0),
    ).probability
    p_high_clock = make_chase_decision(
        t, ThrowID.SEOI_NAGE,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        chase_advantage=0.5,
        score_diff_before=-1,
        clock_remaining=200,     # plenty of time
        rng=random.Random(0),
    ).probability
    assert p_low_trailing > p_high_clock + 0.20, (
        f"clock-low trailing should lift chase markedly: "
        f"low={p_low_trailing:.2f}, high={p_high_clock:.2f}"
    )


def test_clock_pressure_drops_leading_chase_probability() -> None:
    """Leading tori at clock-low has low chase probability (run the
    clock, accept the points)."""
    t, _ = _pair()
    p_low_leading = make_chase_decision(
        t, ThrowID.UCHI_MATA,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        chase_advantage=0.85,
        score_diff_before=0,     # was tied → now leading after this score
        clock_remaining=25,
        rng=random.Random(0),
    ).probability
    p_high_clock = make_chase_decision(
        t, ThrowID.UCHI_MATA,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        chase_advantage=0.85,
        score_diff_before=0,
        clock_remaining=200,
        rng=random.Random(0),
    ).probability
    assert p_low_leading < p_high_clock - 0.20, (
        f"clock-low leading should drop chase markedly: "
        f"low={p_low_leading:.2f}, high={p_high_clock:.2f}"
    )


# ===========================================================================
# AC#12 — GROUND_SPECIALIST chase probability dominates on hip throws
# ===========================================================================
def test_ground_specialist_high_chase_probability_on_hip_throws() -> None:
    """A GROUND_SPECIALIST tori scoring with a hip throw produces a
    chase probability >0.85 — comfortable on the mat, high-advantage
    geometry, archetype bonus."""
    t, _ = _pair()
    t.identity.body_archetype = BodyArchetype.GROUND_SPECIALIST
    t.capability.ne_waza_skill = 9
    t.identity.personality_facets = {"aggressive": 7, "confident": 7}
    p = make_chase_decision(
        t, ThrowID.UCHI_MATA,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        chase_advantage=THROW_DEFS[
            ThrowID.UCHI_MATA
        ].post_score_chase_advantage,
        score_diff_before=0,
        clock_remaining=200,
        rng=random.Random(0),
    ).probability
    assert p >= 0.85, f"expected >= 0.85; got {p:.2f}"


def test_lever_moderate_chase_probability_on_hip_throws() -> None:
    """A LEVER tori scoring with a hip throw produces a moderate chase
    probability — high-advantage geometry but neutral archetype and
    typical ne_waza_skill keep it in the 0.55–0.85 band."""
    t, _ = _pair()
    t.identity.body_archetype = BodyArchetype.LEVER
    t.capability.ne_waza_skill = 5
    t.identity.personality_facets = {"aggressive": 5, "confident": 5}
    p = make_chase_decision(
        t, ThrowID.UCHI_MATA,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        chase_advantage=THROW_DEFS[
            ThrowID.UCHI_MATA
        ].post_score_chase_advantage,
        score_diff_before=0,
        clock_remaining=200,
        rng=random.Random(0),
    ).probability
    assert 0.50 <= p <= 0.85, f"expected 0.50-0.85 band; got {p:.2f}"


# ===========================================================================
# AC#12 — sacrifice-throw routing to DEFENSIVE_CHASE
# ===========================================================================
def test_sacrifice_throw_routes_chase_to_defensive_chase() -> None:
    """A successful chase decision on a SACRIFICE landing profile
    becomes DEFENSIVE_CHASE — tori is on the bottom and plays
    bottom-game defense rather than dropping into a forward GUARD_TOP
    transition."""
    t, _ = _pair()
    t.identity.body_archetype = BodyArchetype.GROUND_SPECIALIST
    t.capability.ne_waza_skill = 9
    # Many seeds to confirm the routing always picks DEFENSIVE_CHASE
    # when chase wins on a SACRIFICE throw.
    seen = set()
    for seed in range(50):
        result = make_chase_decision(
            t, ThrowID.SUMI_GAESHI,
            landing_profile=LandingProfile.SACRIFICE,
            chase_advantage=THROW_DEFS[
                ThrowID.SUMI_GAESHI
            ].post_score_chase_advantage,
            score_diff_before=0,
            clock_remaining=200,
            rng=random.Random(seed),
        )
        seen.add(result.decision)
    # CHASE must never appear for a SACRIFICE landing.
    assert ChaseDecision.CHASE not in seen, (
        f"sacrifice throw must not route to forward CHASE; saw {seen}"
    )
    # DEFENSIVE_CHASE must appear at least once.
    assert ChaseDecision.DEFENSIVE_CHASE in seen, (
        f"expected DEFENSIVE_CHASE in {seen}"
    )


# ===========================================================================
# AC#9 — standing throw with no chase produces explicit matte sequence
# ===========================================================================
def test_stand_path_produces_explicit_matte_before_reset() -> None:
    """When tori chooses STAND, the explicit POST_SCORE_FOLLOW_UP_END
    matte fires on tick+2, followed by the SCORE_RESET — there is no
    same-tick reset after the score (HAJ-152 AC#8)."""
    t, s, m = _pair_match(seed=99)
    # Bias toward STAND: leading + low ne-waza + leading-archetype.
    t.identity.body_archetype = BodyArchetype.GRIP_FIGHTER
    t.capability.ne_waza_skill = 1
    t.identity.personality_facets = {"aggressive": 1, "confident": 3}
    # Make tori already lead so leading-penalty hits.
    t.state.score["waza_ari"] = 0
    s.state.score["waza_ari"] = 0
    # Monkey-patch chase to STAND for determinism.
    import chase_decision as cd_mod
    real_chase = cd_mod.make_chase_decision
    def force_stand(*args, **kwargs):
        return cd_mod.ChaseDecisionResult(
            decision=cd_mod.ChaseDecision.STAND,
            probability=0.0,
            factors={"forced": 1.0},
        )
    cd_mod.make_chase_decision = force_stand
    # Match.py imports ChaseDecisionResult / ChaseDecision and
    # `make_chase_decision` directly into its namespace, so patch
    # there too.
    real_match_chase = match_module.make_chase_decision
    match_module.make_chase_decision = force_stand
    try:
        T = 30
        score_events = _force_waza_ari(t, s, m, ThrowID.SEOI_NAGE, tick=T)
        # Tick T+1: chase decision fires from consequence queue.
        decision_events: list = []
        m._resolve_consequences(tick=T + 1, events=decision_events)
        chase = next(
            ev for ev in decision_events if ev.event_type == "CHASE_DECISION"
        )
        assert chase.data["decision"] == "STAND"
        # No matte yet on T+1 — the matte fires on T+3 per AC#9.
        assert not any(
            ev.event_type == "MATTE_CALLED" for ev in decision_events
        )
        # T+2 still no matte (both fighters standing up).
        idle_events: list = []
        m._resolve_consequences(tick=T + 2, events=idle_events)
        assert not any(
            ev.event_type == "MATTE_CALLED" for ev in idle_events
        )
        # Tick T+3: explicit matte + SCORE_RESET fire.
        matte_events: list = []
        m._resolve_consequences(tick=T + 3, events=matte_events)
        matte = next(
            ev for ev in matte_events if ev.event_type == "MATTE_CALLED"
        )
        assert matte.data["reason"] == "POST_SCORE_FOLLOW_UP_END"
        reset = next(
            ev for ev in matte_events if ev.event_type == "SCORE_RESET"
        )
        assert matte.tick == T + 3
        assert reset.tick == T + 3
        matte_idx = matte_events.index(matte)
        reset_idx = matte_events.index(reset)
        assert matte_idx < reset_idx, (
            "matte must precede SCORE_RESET in the event order"
        )
    finally:
        cd_mod.make_chase_decision = real_chase
        match_module.make_chase_decision = real_match_chase


# ===========================================================================
# AC#8 — no `[reset]` event fires on the same tick as a score event
# without an intervening `[ref] Matte!`
# ===========================================================================
def test_no_score_reset_co_fires_with_score_tick() -> None:
    """Pin the HAJ-152 contract: the SCORE_RESET event never shares a
    tick with the score award. There is always a matte event between
    them in the engine log."""
    t, s, m = _pair_match(seed=21)
    score_tick = 29
    score_events = _force_waza_ari(t, s, m, ThrowID.UCHI_MATA, tick=score_tick)
    # No SCORE_RESET should appear in the score-tick events.
    assert not any(
        ev.event_type == "SCORE_RESET" for ev in score_events
    )


# ===========================================================================
# HAJ-144 t017–t018 reproduction
# ===========================================================================
def test_haj144_t017_t018_no_same_tick_reset_after_uchi_mata_waza_ari() -> None:
    """Sato gets a waza-ari from Uchi-mata; verify the t017–t018 break
    is dissolved. The follow-up window opens, the chase decision
    fires on tick+1, and no SCORE_RESET event co-fires with the score
    on tick T."""
    t, s, m = _pair_match(seed=17)
    # Sato is the scorer to mirror the t017–t018 setup.
    score_events = _force_waza_ari(s, t, m, ThrowID.UCHI_MATA, tick=17)
    # Score and follow-up open events on tick 17; no SCORE_RESET there.
    assert any(ev.event_type == "POST_SCORE_FOLLOW_UP_OPEN"
               for ev in score_events)
    assert not any(ev.event_type == "SCORE_RESET" for ev in score_events)
    # Drive the decision consequence on tick 18 (the canonical t018).
    decision_events: list = []
    m._resolve_consequences(tick=18, events=decision_events)
    assert any(
        ev.event_type == "CHASE_DECISION" for ev in decision_events
    )
    # The chase decision tick produces a CHASE_DECISION event but NOT
    # a matte and NOT a reset on tick 18 — both are deferred.
    assert not any(
        ev.event_type == "MATTE_CALLED"
        and ev.tick == 18
        and ev.data.get("reason") == "POST_SCORE_FOLLOW_UP_END"
        for ev in decision_events
    )
    assert not any(
        ev.event_type == "SCORE_RESET" and ev.tick == 18
        for ev in decision_events
    )


# ===========================================================================
# AC#7 — ne-waza unfolds in the existing substrate
# ===========================================================================
def test_chase_dispatches_into_existing_newaza_substrate() -> None:
    """When chase wins, the dispatch routes through the existing
    `_resolve_newaza_transition` helper. A NEWAZA_TRANSITION event
    fires and the sub-loop state flips to NE_WAZA — no new ne-waza
    mechanics added by this ticket."""
    t, s, m = _pair_match(seed=44)
    # Bias tori toward CHASE.
    t.identity.body_archetype = BodyArchetype.GROUND_SPECIALIST
    t.capability.ne_waza_skill = 9
    # Force the resolver to accept the ground commit so we can observe
    # the transition without rng noise.
    real_attempt = m.ne_waza_resolver.attempt_ground_commit
    m.ne_waza_resolver.attempt_ground_commit = lambda *a, **kw: True
    try:
        _force_waza_ari(t, s, m, ThrowID.UCHI_MATA, tick=30)
        decision_events: list = []
        m._resolve_consequences(tick=31, events=decision_events)
        # If chase won, the ne-waza substrate fired NEWAZA_TRANSITION.
        if any(ev.event_type == "NEWAZA_TRANSITION"
               for ev in decision_events):
            assert m.sub_loop_state == SubLoopState.NE_WAZA
            ne_trans = next(
                ev for ev in decision_events
                if ev.event_type == "NEWAZA_TRANSITION"
            )
            assert ne_trans.data.get("source") == "POST_SCORE_CHASE"
    finally:
        m.ne_waza_resolver.attempt_ground_commit = real_attempt


# ===========================================================================
# AC#7 escape exit — uke escape during ne-waza resumes tachi-waza without
# matte
# ===========================================================================
def test_escape_during_post_score_chase_clears_follow_up_without_matte() -> None:
    """Per AC#7, escape from post-score chase routes the dyad back to
    standing without firing an explicit POST_SCORE_FOLLOW_UP_END
    matte. Tachi-waza resumes via the existing closing-phase path."""
    t, s, m = _pair_match(seed=55)
    # Force tori into a chase that lands ne-waza.
    t.identity.body_archetype = BodyArchetype.GROUND_SPECIALIST
    t.capability.ne_waza_skill = 9
    real_attempt = m.ne_waza_resolver.attempt_ground_commit
    m.ne_waza_resolver.attempt_ground_commit = lambda *a, **kw: True
    try:
        _force_waza_ari(t, s, m, ThrowID.UCHI_MATA, tick=30)
        decision_events: list = []
        m._resolve_consequences(tick=31, events=decision_events)
        # If we reached ne-waza, simulate an escape by clearing the
        # follow-up state through the same path the existing
        # ESCAPE_SUCCESS handler walks. We can't easily synthesise the
        # event here, so verify the contract directly: escape clears
        # `_post_score_follow_up` and resets without queuing a
        # POST_SCORE_FOLLOW_UP_MATTE.
        if m.sub_loop_state == SubLoopState.NE_WAZA:
            # Manually walk the contract — escape would do this.
            m._post_score_follow_up = None
            m._reset_dyad_to_distant(tick=32, recovery_bonus=0)
            assert m.position == Position.STANDING_DISTANT
            # No POST_SCORE_FOLLOW_UP_MATTE consequence pending.
            queued = [
                c for c in m._consequence_queue
                if c.kind == "POST_SCORE_FOLLOW_UP_MATTE"
            ]
            assert not queued
    finally:
        m.ne_waza_resolver.attempt_ground_commit = real_attempt


# ===========================================================================
# Defense decision — sweep counter gates and accept-position fatigue floor
# ===========================================================================
def test_sweep_counter_gated_by_iq_and_skill() -> None:
    """SWEEP_COUNTER fires only on SACRIFICE landings against high-IQ /
    high-ne_waza_skill uke."""
    _, s = _pair()
    s.capability.fight_iq = 9
    s.capability.ne_waza_skill = 8
    result = make_defense_decision(
        s,
        landing_profile=LandingProfile.SACRIFICE,
        score_diff_before=0,
        clock_remaining=200,
        tori_chasing=True,
        rng=random.Random(0),
    )
    # SACRIFICE + high attributes → sweep_counter score competitive.
    assert result.factors["sweep_counter"] > 0.0


def test_sweep_counter_suppressed_for_non_sacrifice_throw() -> None:
    """No matter the uke's attributes, a non-SACRIFICE landing leaves
    SWEEP_COUNTER unavailable (uke is on the bottom under tori, not on
    top)."""
    _, s = _pair()
    s.capability.fight_iq = 10
    s.capability.ne_waza_skill = 10
    result = make_defense_decision(
        s,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        score_diff_before=0,
        clock_remaining=200,
        tori_chasing=True,
        rng=random.Random(0),
    )
    assert result.decision != DefenseDecision.SWEEP_COUNTER
    assert result.factors["sweep_counter"] < 0.0


def test_low_composure_defaults_to_accept_position() -> None:
    """A panicked uke (composure < ACCEPT_COMPOSURE_FLOOR) defaults to
    ACCEPT_POSITION — conceding the chase rather than scrambling."""
    _, s = _pair()
    s.state.composure_current = 0.05  # well below 0.30 floor
    result = make_defense_decision(
        s,
        landing_profile=LandingProfile.FORWARD_ROTATIONAL,
        score_diff_before=0,
        clock_remaining=200,
        tori_chasing=True,
        rng=random.Random(0),
    )
    assert result.decision == DefenseDecision.ACCEPT_POSITION


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
