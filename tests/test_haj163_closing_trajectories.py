# tests/test_haj163_closing_trajectories.py
# HAJ-163 — Closing-phase trajectory variance.
#
# Acceptance criteria:
#   1. Three new closing actions exist — CIRCLE_CLOSING,
#      LATERAL_APPROACH, BAIT_RETREAT — and emit MOVE events with the
#      appropriate tactical_intent.
#   2. Selector picks variety. Across many seeds, the closing phase
#      exhibits multiple distinct trajectory shapes.
#   3. Style differentiation is visible. Aggressive / pressure fighters
#      lean STEP_IN; counter / defensive fighters lean BAIT_RETREAT.
#   4. Engagement transition works for non-head-on closes — a fighter
#      who lateral-only-approaches still eventually engages when the
#      reach-tick window completes.
#   5. (this file)

from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from match import Match
from action_selection import (
    select_actions, _select_closing_step_action,
    _circle_closing_step_action, _lateral_approach_step_action,
    _bait_retreat_step_action, ENGAGEMENT_DISTANCE_M,
    BAIT_RETREAT_MAGNITUDE_M, LATERAL_APPROACH_MAGNITUDE_M,
)
from actions import (
    ActionKind,
    TACTICAL_INTENT_CLOSING, TACTICAL_INTENT_CIRCLE_CLOSING,
    TACTICAL_INTENT_LATERAL_APPROACH, TACTICAL_INTENT_BAIT_RETREAT,
    TACTICAL_INTENTS,
)
from enums import Position, PositionalStyle
from grip_graph import GripGraph
from referee import build_suzuki
import main as main_module


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------
def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-1.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+1.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _build_match(seed: int = 1, max_ticks: int = 30):
    random.seed(seed)
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    m = Match(t, s, build_suzuki(), max_ticks=max_ticks, seed=seed)
    m._print_events = lambda evs: None
    m._print_header = lambda: None
    return t, s, m


def _collect_closing_intents(seeds: list[int], window: int = 6) -> list[str]:
    """Run a batch of matches, collect every closing-phase MOVE intent
    across the first `window` ticks. Returns a flat list of intent
    strings (not aggregated)."""
    intents: list[str] = []
    for seed in seeds:
        _, _, m = _build_match(seed=seed)
        captured: list = []
        m._print_events = lambda evs: captured.extend(evs)
        m.begin()
        for _ in range(window):
            if m.is_done():
                break
            m.step()
        for e in captured:
            if e.event_type == "MOVE":
                intent = (e.data or {}).get("tactical_intent")
                if intent in (
                    TACTICAL_INTENT_CLOSING,
                    TACTICAL_INTENT_CIRCLE_CLOSING,
                    TACTICAL_INTENT_LATERAL_APPROACH,
                    TACTICAL_INTENT_BAIT_RETREAT,
                ):
                    intents.append(intent)
    return intents


# ===========================================================================
# AC#1 — three new tactical intents exist and are wired into the
# canonical TACTICAL_INTENTS set
# ===========================================================================
def test_three_new_closing_intents_are_known() -> None:
    assert TACTICAL_INTENT_CIRCLE_CLOSING == "circle_closing"
    assert TACTICAL_INTENT_LATERAL_APPROACH == "lateral_approach"
    assert TACTICAL_INTENT_BAIT_RETREAT == "bait_retreat"
    assert TACTICAL_INTENT_CIRCLE_CLOSING in TACTICAL_INTENTS
    assert TACTICAL_INTENT_LATERAL_APPROACH in TACTICAL_INTENTS
    assert TACTICAL_INTENT_BAIT_RETREAT in TACTICAL_INTENTS


# ===========================================================================
# AC#1 — each new helper produces a STEP action with the right intent
# ===========================================================================
def test_circle_closing_step_carries_circle_intent() -> None:
    t, s = _pair()
    rng = random.Random(0)
    act = _circle_closing_step_action(t, s, rng)
    assert act is not None
    assert act.kind == ActionKind.STEP
    assert act.tactical_intent == TACTICAL_INTENT_CIRCLE_CLOSING


def test_lateral_approach_step_is_perpendicular_to_dyad_axis() -> None:
    """LATERAL_APPROACH has zero closing component — vector is
    perpendicular to the judoka → opponent direction."""
    t, s = _pair()
    rng = random.Random(0)
    act = _lateral_approach_step_action(t, s, rng)
    assert act is not None
    assert act.tactical_intent == TACTICAL_INTENT_LATERAL_APPROACH
    # Dyad axis is along x (Tanaka at -1.5, Sato at +1.5). A pure
    # lateral step has zero x-component.
    dx, dy = act.direction
    assert abs(dx) < 1e-6
    assert abs(dy) > 0


def test_bait_retreat_step_moves_away_from_opponent() -> None:
    """BAIT_RETREAT has a negative closing component — direction
    points away from the opponent."""
    t, s = _pair()
    act = _bait_retreat_step_action(t, s)
    assert act is not None
    assert act.tactical_intent == TACTICAL_INTENT_BAIT_RETREAT
    # Tanaka at -1.5, Sato at +1.5. "Toward opponent" is +x; bait
    # retreats in -x.
    dx, dy = act.direction
    assert dx < 0
    assert act.magnitude == BAIT_RETREAT_MAGNITUDE_M


def test_circle_closing_step_has_both_closing_and_lateral_components() -> None:
    """CIRCLE_CLOSING vector blends head-on and lateral so the fighter
    arcs into engagement."""
    t, s = _pair()
    rng = random.Random(0)
    act = _circle_closing_step_action(t, s, rng)
    assert act is not None
    dx, dy = act.direction
    # Closing component (toward Sato at +x) should be positive.
    assert dx > 0
    # Lateral component (y-axis) should be non-zero.
    assert abs(dy) > 0


# ===========================================================================
# AC#1 — bait-retreat declines when there's no room to retreat
# ===========================================================================
def test_bait_retreat_declines_inside_engagement_distance() -> None:
    t, s = _pair()
    place_judoka(t, com_position=(-0.4, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.4, 0.0), facing=(-1.0, 0.0))
    assert _bait_retreat_step_action(t, s) is None


# ===========================================================================
# AC#1 — closing-phase MOVE events surface the new intents in a
# real match run
# ===========================================================================
def test_closing_phase_emits_at_least_one_new_intent_across_seeds() -> None:
    """Across a batch of seeds, at least one MOVE event with each new
    tactical_intent should fire during a closing phase."""
    intents = _collect_closing_intents(list(range(20)))
    assert TACTICAL_INTENT_CIRCLE_CLOSING in intents
    assert TACTICAL_INTENT_LATERAL_APPROACH in intents
    assert TACTICAL_INTENT_BAIT_RETREAT in intents


# ===========================================================================
# AC#2 — selector picks variety (multiple distinct intents across seeds)
# ===========================================================================
def test_closing_intents_show_variety_across_seeds() -> None:
    intents = _collect_closing_intents(list(range(20)))
    distinct = set(intents)
    assert len(distinct) >= 3, (
        f"expected >= 3 distinct closing intents across 20 seeds, "
        f"got {distinct}"
    )


# ===========================================================================
# AC#3 — style differentiation. Pressure fighters lean STEP_IN;
# defensive fighters lean BAIT_RETREAT / LATERAL.
# ===========================================================================
def test_pressure_fighter_leans_head_on_step_in() -> None:
    """A PRESSURE-style fighter with high aggression should pick
    STEP_IN much more often than BAIT_RETREAT across many ticks."""
    t = main_module.build_tanaka()
    t.identity.positional_style = PositionalStyle.PRESSURE
    t.identity.personality_facets = {"aggressive": 9, "technical": 3}
    s = main_module.build_sato()
    place_judoka(t, com_position=(-1.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+1.5, 0.0), facing=(-1.0, 0.0))
    rng = random.Random(0)
    counts = {"closing": 0, "circle_closing": 0,
              "lateral_approach": 0, "bait_retreat": 0}
    for _ in range(200):
        act = _select_closing_step_action(t, s, rng)
        if act is not None and act.tactical_intent in counts:
            counts[act.tactical_intent] += 1
    assert counts["closing"] > counts["bait_retreat"], (
        f"PRESSURE fighter should pick STEP_IN more than BAIT_RETREAT; "
        f"got {counts}"
    )
    assert counts["closing"] > counts["lateral_approach"]


def test_defensive_edge_fighter_picks_bait_retreat_more_than_pressure() -> None:
    """A DEFENSIVE_EDGE-style fighter with high fight_iq should pick
    BAIT_RETREAT noticeably more often than a PRESSURE fighter."""
    rng = random.Random(0)
    counts_def = {"bait_retreat": 0, "closing": 0}
    counts_press = {"bait_retreat": 0, "closing": 0}

    def _count(judoka, opponent, counts):
        for _ in range(400):
            act = _select_closing_step_action(judoka, opponent, rng)
            if act is not None and act.tactical_intent in counts:
                counts[act.tactical_intent] += 1

    # Defensive fighter
    t = main_module.build_tanaka()
    t.identity.positional_style = PositionalStyle.DEFENSIVE_EDGE
    t.identity.personality_facets = {"aggressive": 3, "technical": 5}
    t.capability.fight_iq = 9
    s = main_module.build_sato()
    place_judoka(t, com_position=(-1.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+1.5, 0.0), facing=(-1.0, 0.0))
    _count(t, s, counts_def)

    # Pressure fighter
    t2 = main_module.build_tanaka()
    t2.identity.positional_style = PositionalStyle.PRESSURE
    t2.identity.personality_facets = {"aggressive": 9, "technical": 3}
    t2.capability.fight_iq = 5
    s2 = main_module.build_sato()
    place_judoka(t2, com_position=(-1.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s2, com_position=(+1.5, 0.0), facing=(-1.0, 0.0))
    _count(t2, s2, counts_press)

    assert counts_def["bait_retreat"] > counts_press["bait_retreat"], (
        f"DEFENSIVE_EDGE should bait-retreat more than PRESSURE; "
        f"def={counts_def}, press={counts_press}"
    )


# ===========================================================================
# AC#4 — engagement transition still works for non-head-on closes
# ===========================================================================
def test_lateral_only_fighter_eventually_engages() -> None:
    """A fighter forced to pick LATERAL_APPROACH every closing tick
    still engages once the reach-tick counter completes — the
    engagement gate is tick-based, not spatial."""
    t, s, m = _build_match(seed=3)
    # Monkey-patch the selector so this fighter only picks lateral.
    import action_selection
    real = action_selection._select_closing_step_action

    def lateral_only(judoka, opponent, rng):
        if judoka is t:
            return action_selection._lateral_approach_step_action(
                judoka, opponent, rng,
            )
        return real(judoka, opponent, rng)

    action_selection._select_closing_step_action = lateral_only
    try:
        m.begin()
        max_steps = 20
        steps = 0
        while m.position == Position.STANDING_DISTANT and steps < max_steps:
            if m.is_done():
                break
            m.step()
            steps += 1
        assert m.position != Position.STANDING_DISTANT, (
            f"engagement never fired after {steps} ticks; position={m.position}"
        )
    finally:
        action_selection._select_closing_step_action = real


# ===========================================================================
# Selector-level: select_actions returns REACH + a closing variant
# even when the selector picks a non-STEP_IN variant
# ===========================================================================
def test_select_actions_returns_reach_with_any_closing_variant() -> None:
    """REACH still fires every closing tick (so the engagement counter
    advances) regardless of which trajectory variant the selector picks."""
    t, s = _pair()
    g = GripGraph()
    seen_kinds = set()
    for seed in range(40):
        rng = random.Random(seed)
        acts = select_actions(
            t, s, g, kumi_kata_clock=0, rng=rng,
            position=Position.STANDING_DISTANT,
        )
        # REACH always present.
        assert any(a.kind == ActionKind.REACH for a in acts), (
            f"REACH missing from closing-phase actions at seed {seed}"
        )
        for a in acts:
            if a.kind == ActionKind.STEP and a.tactical_intent:
                seen_kinds.add(a.tactical_intent)
    # Across 40 seeds the selector should have picked at least 2
    # different STEP variants (variety).
    assert len(seen_kinds) >= 2, f"expected variety, got {seen_kinds}"
