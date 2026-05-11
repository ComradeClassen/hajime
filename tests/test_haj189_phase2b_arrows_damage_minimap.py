# tests/test_haj189_phase2b_arrows_damage_minimap.py
# HAJ-189 — Phase 2b: intent/actual arrows, body damage tinting,
# mini-map. Capture-layer tests only — no pygame window opens.

from __future__ import annotations

import io
import os
import random
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from actions import Action, ActionKind
from body_state import place_judoka
from enums import GripDepth, GripMode, GripTarget, GripTypeV2, BodyPart
from grip_graph import GripEdge
from match import Match
from referee import build_suzuki
import main as main_module

from phase1_viewer import (
    ARROW_KIND_ACTUAL,
    ARROW_KIND_INTENT,
    DAMAGE_COMPROMISED,
    DAMAGE_CRITICAL,
    DAMAGE_HEALTHY,
    DAMAGE_WORKED,
    DAMAGE_BAND_RED_MIX,
    Identity,
    MINI_MAP_TAIL_LENGTH,
    Phase1RecordingRenderer,
    capture_phase1_view,
    damage_band,
    tint_toward_red,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _fresh_match(*, max_ticks=10, seed=1, renderer=None):
    random.seed(seed)
    t, s = _pair()
    return Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=max_ticks, seed=seed, renderer=renderer,
    )


# ---------------------------------------------------------------------------
# Acceptance #1 / #2 — intent fires only on active attempts; actual
# encodes delivered force.
# ---------------------------------------------------------------------------
def test_no_arrows_with_zero_force_state() -> None:
    """Fresh match, no actions issued — Match's intent/actual stay
    zero, capture should emit no arrows."""
    m = _fresh_match()
    snap = capture_phase1_view(m, tick=0, events=[])
    assert snap.arrows == ()


def test_intent_arrow_fires_when_intent_force_present() -> None:
    """Synthesise the intent vector that _compute_net_force_on would
    record. The arrow capture should emit a single INTENT arrow for
    that fighter, and no ACTUAL arrow because actual is zero."""
    m = _fresh_match()
    name = m.fighter_a.identity.name
    m._intent_force[name] = (3.0, 4.0)   # mag = 5
    snap = capture_phase1_view(m, tick=1, events=[])
    intents = [a for a in snap.arrows if a.kind == ARROW_KIND_INTENT]
    actuals = [a for a in snap.arrows if a.kind == ARROW_KIND_ACTUAL]
    assert len(intents) == 1
    assert len(actuals) == 0
    arrow = intents[0]
    assert arrow.judoka_name == name
    assert arrow.judoka_identity == Identity.BLUE
    assert abs(arrow.magnitude - 5.0) < 1e-9


def test_actual_arrow_fires_with_nonzero_actual_force() -> None:
    m = _fresh_match()
    name = m.fighter_b.identity.name
    m._actual_force[name] = (-6.0, 8.0)   # mag = 10
    snap = capture_phase1_view(m, tick=1, events=[])
    actuals = [a for a in snap.arrows if a.kind == ARROW_KIND_ACTUAL]
    assert len(actuals) == 1
    assert actuals[0].judoka_identity == Identity.WHITE
    assert abs(actuals[0].magnitude - 10.0) < 1e-9


def test_up_to_four_arrows_when_both_fighters_active() -> None:
    """Acceptance #4 — up to 4 arrows visible at once."""
    m = _fresh_match()
    a, b = m.fighter_a.identity.name, m.fighter_b.identity.name
    m._intent_force[a] = (5.0, 0.0)
    m._actual_force[a] = (3.0, 0.0)
    m._intent_force[b] = (-5.0, 0.0)
    m._actual_force[b] = (-3.0, 0.0)
    snap = capture_phase1_view(m, tick=1, events=[])
    assert len(snap.arrows) == 4
    kinds = {(a.judoka_identity, a.kind) for a in snap.arrows}
    assert (Identity.BLUE, ARROW_KIND_INTENT)  in kinds
    assert (Identity.BLUE, ARROW_KIND_ACTUAL)  in kinds
    assert (Identity.WHITE, ARROW_KIND_INTENT) in kinds
    assert (Identity.WHITE, ARROW_KIND_ACTUAL) in kinds


def test_intent_zero_no_arrow_even_with_actual() -> None:
    """If intent vector is zero (e.g. force resulted from Newton-3
    backreaction without an explicit driving action), only the actual
    arrow draws. The intent ghost is suppressed entirely per Section
    2.4: 'fade entirely when no active intent state.'"""
    m = _fresh_match()
    name = m.fighter_a.identity.name
    m._actual_force[name] = (4.0, 0.0)
    # _intent_force[name] stays (0.0, 0.0) — set by __init__.
    snap = capture_phase1_view(m, tick=1, events=[])
    intents = [a for a in snap.arrows if a.kind == ARROW_KIND_INTENT]
    actuals = [a for a in snap.arrows if a.kind == ARROW_KIND_ACTUAL]
    assert intents == []
    assert len(actuals) == 1


# ---------------------------------------------------------------------------
# Engine wiring — _compute_net_force_on populates intent + actual.
# ---------------------------------------------------------------------------
def test_engine_records_intent_and_actual_on_pull_action() -> None:
    """The engine's _compute_net_force_on accumulates intent (sum of
    requested action vectors) and actual (sum of delivered vectors).
    A PULL with a STANDARD lapel grip should land both nonzero."""
    m = _fresh_match()
    # Reset per-tick state the way _tick() does at the top.
    for name in m._intent_force:
        m._intent_force[name] = (0.0, 0.0)
        m._actual_force[name] = (0.0, 0.0)
    # Seat a STANDARD lapel grip so the action has somewhere to land.
    e = GripEdge(
        grasper_id=m.fighter_a.identity.name,
        grasper_part=BodyPart.RIGHT_HAND,
        target_id=m.fighter_b.identity.name,
        target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH,
        depth_level=GripDepth.STANDARD,
        strength=1.0, established_tick=0,
        mode=GripMode.CONNECTIVE,
    )
    m.grip_graph.add_edge(e)
    pull = Action(
        kind=ActionKind.PULL,
        hand="right_hand",
        direction=(1.0, 0.0),
        magnitude=200.0,
    )
    m._compute_net_force_on(
        victim=m.fighter_b, attacker=m.fighter_a,
        attacker_actions=[pull], tick=1,
    )
    ix, iy = m._intent_force[m.fighter_a.identity.name]
    ax, ay = m._actual_force[m.fighter_a.identity.name]
    assert ix > 0, "intent x should be positive after right-pull"
    # Actual should be nonzero AND <= intent (envelope/depth/etc clamp).
    assert ax > 0
    assert ax <= ix


def test_engine_force_resets_each_tick() -> None:
    """The per-tick reset at the top of _tick() must zero both maps so
    a tick with no driving action yields no arrows."""
    m = _fresh_match()
    name = m.fighter_a.identity.name
    m._intent_force[name] = (10.0, 0.0)
    m._actual_force[name] = (5.0, 0.0)
    # One real engine tick — should reset before any actions land.
    m.begin()
    snap_before_step = capture_phase1_view(m, tick=0, events=[])
    # Even though we set values manually, the begin() path doesn't run
    # _tick(), so they may persist. After one full step() the reset
    # must have run.
    m.step()
    # After the step, capture should reflect post-tick state.
    # Force values are whatever the engine computed this tick (may or
    # may not be zero), but the reset itself must happen — verify by
    # injecting a sentinel then running a step that reaches the reset.
    m._intent_force[name] = (999.0, 999.0)
    m._actual_force[name] = (888.0, 888.0)
    m.step()
    # After step, sentinels should be gone — replaced by fresh
    # accumulation (whatever it is) starting from 0.
    after = m._intent_force[name]
    assert after != (999.0, 999.0)


# ---------------------------------------------------------------------------
# Acceptance #5 — damage tinting bands + identity-preserving tint.
# ---------------------------------------------------------------------------
def test_damage_band_thresholds() -> None:
    assert damage_band(0.00) == DAMAGE_HEALTHY
    assert damage_band(0.10) == DAMAGE_HEALTHY
    assert damage_band(0.249) == DAMAGE_HEALTHY
    assert damage_band(0.25) == DAMAGE_WORKED
    assert damage_band(0.40) == DAMAGE_WORKED
    assert damage_band(0.499) == DAMAGE_WORKED
    assert damage_band(0.50) == DAMAGE_COMPROMISED
    assert damage_band(0.65) == DAMAGE_COMPROMISED
    assert damage_band(0.749) == DAMAGE_COMPROMISED
    assert damage_band(0.75) == DAMAGE_CRITICAL
    assert damage_band(1.00) == DAMAGE_CRITICAL


def test_damage_red_mix_monotonic() -> None:
    """Each band's red mix must strictly exceed the prior band's so
    the tint visibly progresses healthy → critical."""
    assert (DAMAGE_BAND_RED_MIX[DAMAGE_HEALTHY]
            < DAMAGE_BAND_RED_MIX[DAMAGE_WORKED]
            < DAMAGE_BAND_RED_MIX[DAMAGE_COMPROMISED]
            < DAMAGE_BAND_RED_MIX[DAMAGE_CRITICAL])


def test_tint_white_walks_through_pink_to_red() -> None:
    """White (235, 235, 240) at increasing red-mix progresses through
    pink to red. Pink = elevated R relative to G/B."""
    base_white = (235, 235, 240)
    healthy = tint_toward_red(base_white, 0.00)
    worked  = tint_toward_red(base_white, 0.25)
    crit    = tint_toward_red(base_white, 0.85)
    assert healthy == base_white
    # Pink: R unchanged-ish but G/B drop.
    assert worked[0] >= worked[1]
    assert worked[1] > crit[1], "G should fall as damage rises"
    assert crit[0] > crit[1] and crit[0] > crit[2], \
        "Red dominates at critical mix"


def test_tint_blue_walks_through_purple_to_dark_red() -> None:
    """Blue base — at mid mix the result should sit in the purple
    band (R rising, B still significant). At critical mix R should
    dominate while staying darker than white-base critical."""
    base_blue = (90, 140, 230)
    healthy = tint_toward_red(base_blue, 0.00)
    worked  = tint_toward_red(base_blue, 0.25)
    compro  = tint_toward_red(base_blue, 0.50)
    crit    = tint_toward_red(base_blue, 0.85)
    assert healthy == base_blue
    # Purple zone: R has risen, B is still > 0, neither pure red nor
    # pure blue.
    assert compro[0] > healthy[0]   # R climbing
    assert compro[2] < healthy[2]   # B falling
    assert compro[2] > 60           # Still some blue left
    # Critical: R clearly dominant.
    assert crit[0] > crit[1] and crit[0] > crit[2]


def test_tint_clamps_to_byte_range() -> None:
    """No matter the mix, channels stay in [0, 255]."""
    for mix in (-1.0, 0.0, 0.5, 1.0, 2.0):
        rgb = tint_toward_red((10, 20, 30), mix)
        for c in rgb:
            assert 0 <= c <= 255


def test_capture_carries_region_damage_for_renderer() -> None:
    """The Phase 1 capture already populated body.region_damage; the
    Phase 2b renderer reads it for tinting. Verify it's still present
    and exhaustive over the 20 anatomical regions."""
    m = _fresh_match()
    # Synthesise some damage.
    m.fighter_a.state.body["right_forearm"].fatigue = 0.6
    m.fighter_a.state.body["right_hand"].fatigue = 0.3
    snap = capture_phase1_view(m, tick=1, events=[])
    region_map = dict(snap.body_a.region_damage)
    assert region_map["right_forearm"] >= 0.6
    assert region_map["right_hand"] >= 0.3
    # Healthy regions still report 0.
    assert region_map["head"] == 0.0
    # All 20 regions present.
    assert len(snap.body_a.region_damage) == 20


# ---------------------------------------------------------------------------
# Acceptance #6 / #7 — mini-map renders mat geometry and edge pulse.
# ---------------------------------------------------------------------------
def test_mini_map_geometry_from_engine() -> None:
    """Mini-map carries mat geometry derived from match.MAT_HALF_WIDTH
    plus the IJF safety border. Default contest=4m, safety=7m."""
    m = _fresh_match()
    snap = capture_phase1_view(m, tick=0, events=[])
    mm = snap.mini_map
    assert mm is not None
    assert mm.contest_half_m == 4.0
    assert mm.safety_half_m == 7.0


def test_mini_map_carries_identity_and_positions() -> None:
    m = _fresh_match()
    snap = capture_phase1_view(m, tick=0, events=[])
    mm = snap.mini_map
    assert mm.a_identity == Identity.BLUE
    assert mm.b_identity == Identity.WHITE
    # Default placement: blue at (-0.5, 0.0), white at (+0.5, 0.0).
    assert mm.a_position == (-0.5, 0.0)
    assert mm.b_position == (+0.5, 0.0)


def test_mini_map_near_edge_flag_fires_within_threshold() -> None:
    """Within 0.75m of the contest boundary (MAT_HALF_WIDTH=4.0) →
    near_edge True. Centre of mat → False."""
    m = _fresh_match()
    # Mid mat — far from edge.
    snap_mid = capture_phase1_view(m, tick=0, events=[])
    assert snap_mid.mini_map.a_near_edge is False
    # Push fighter A near the +x boundary.
    m.fighter_a.state.body_state.com_position = (3.5, 0.0)
    snap_edge = capture_phase1_view(m, tick=1, events=[])
    assert snap_edge.mini_map.a_near_edge is True


def test_mini_map_tail_grows_with_history_and_truncates() -> None:
    """The tail walks the prev_view chain via capture_phase1_view's
    prev parameter. After more than MINI_MAP_TAIL_LENGTH ticks of
    distinct positions, the tail must cap at that length."""
    m = _fresh_match()
    snap = None
    # Move the fighter incrementally and capture each tick so the tail
    # builds up. 20 ticks > MINI_MAP_TAIL_LENGTH (12).
    for tick in range(20):
        m.fighter_a.state.body_state.com_position = (
            -1.0 + tick * 0.05, 0.0,
        )
        snap = capture_phase1_view(
            m, tick=tick, events=[], prev_view=snap,
        )
    assert snap is not None
    assert len(snap.mini_map.a_tail) == MINI_MAP_TAIL_LENGTH


# ---------------------------------------------------------------------------
# Acceptance #8 — text burst captioning still mirrors prose log 1:1.
# (Cross-check the HAJ-187 invariant continues to hold once arrows
# and damage capture are in.)
# ---------------------------------------------------------------------------
def test_text_burst_invariant_holds_with_phase2b_fields() -> None:
    rec = Phase1RecordingRenderer()
    random.seed(404)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=30, seed=404, renderer=rec,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    burst_set = {(tick, text) for tick, _, text in rec.all_text_bursts()}
    for tick, _etype, desc in rec.event_log:
        assert (tick, desc) in burst_set, (
            f"event at tick {tick} missing burst: {desc!r}"
        )


# ---------------------------------------------------------------------------
# Pure observer — Phase 2b additions don't perturb the engine.
# ---------------------------------------------------------------------------
def test_phase2b_capture_does_not_perturb_match() -> None:
    """Same seed, same prose stream with vs without recording."""
    def _run(renderer):
        random.seed(505)
        t, s = _pair()
        mm = Match(
            fighter_a=t, fighter_b=s, referee=build_suzuki(),
            max_ticks=25, seed=505, renderer=renderer,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            mm.run()
        return buf.getvalue()

    out_no  = _run(None)
    out_yes = _run(Phase1RecordingRenderer())
    assert out_no == out_yes


# ---------------------------------------------------------------------------
# Live smoke — a real match should populate at least some arrows and
# at least one mini-map snapshot with a non-trivial tail.
# ---------------------------------------------------------------------------
def test_live_match_populates_arrows() -> None:
    rec = Phase1RecordingRenderer()
    random.seed(606)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=40, seed=606, renderer=rec,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    total_arrows = sum(len(snap.arrows) for snap in rec.snapshots)
    assert total_arrows > 0, (
        "expected at least one arrow across 40 ticks of Tanaka vs Sato"
    )


def test_body_view_captures_facing() -> None:
    """The centre-pane top-down view needs facing to place hand
    dots. _capture_body must thread state.body_state.facing onto
    BodyView."""
    m = _fresh_match()
    snap = capture_phase1_view(m, tick=0, events=[])
    # Default placement: blue faces +x, white faces -x.
    assert snap.body_a.facing[0] == 1.0
    assert snap.body_b.facing[0] == -1.0


def test_topdown_hand_positions_forward_facing() -> None:
    """Forward facing (+x) puts left hand at body +y (above) and
    right hand at body -y (below) when the rotation convention is
    facing=+x → perp=+y. 30cm forward, 22cm lateral."""
    from phase1_viewer import _topdown_hand_positions_mat
    left, right = _topdown_hand_positions_mat((0.0, 0.0), (1.0, 0.0))
    assert left  == (0.30, 0.22)
    assert right == (0.30, -0.22)


def test_topdown_hand_positions_reverse_facing_mirrors() -> None:
    """Facing -x flips left/right hands across the y-axis."""
    from phase1_viewer import _topdown_hand_positions_mat
    left, right = _topdown_hand_positions_mat((0.0, 0.0), (-1.0, 0.0))
    assert left  == (-0.30, -0.22)
    assert right == (-0.30, 0.22)


def test_owned_hands_by_grasper_indexes_correctly() -> None:
    """Index returns {grasper_id: {hand_part, ...}} for active edges
    only — no entry when no edges, only the hand parts that own
    grips listed."""
    from phase1_viewer import owned_hands_by_grasper, GripEdgeView
    edges = [
        GripEdgeView(
            edge_id=1, grasper_id="X", grasper_identity=Identity.BLUE,
            grasper_part="right_hand", target_id="Y",
            target_identity=Identity.WHITE,
            target_node="left_lapel", target_raw="left_lapel",
            depth=0.7, state="stable",
        ),
        GripEdgeView(
            edge_id=2, grasper_id="X", grasper_identity=Identity.BLUE,
            grasper_part="left_hand", target_id="Y",
            target_identity=Identity.WHITE,
            target_node="right_sleeve", target_raw="right_sleeve",
            depth=0.4, state="stable",
        ),
        GripEdgeView(
            edge_id=3, grasper_id="Y", grasper_identity=Identity.WHITE,
            grasper_part="right_hand", target_id="X",
            target_identity=Identity.BLUE,
            target_node="belt", target_raw="belt",
            depth=1.0, state="stable",
        ),
    ]
    owned = owned_hands_by_grasper(edges)
    assert owned == {
        "X": {"right_hand", "left_hand"},
        "Y": {"right_hand"},
    }
    assert owned_hands_by_grasper([]) == {}


def test_live_match_mini_map_tail_grows() -> None:
    rec = Phase1RecordingRenderer()
    random.seed(707)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=20, seed=707, renderer=rec,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    # By the last snapshot, tail should have several positions.
    assert rec.snapshots
    last = rec.snapshots[-1]
    assert last.mini_map is not None
    assert len(last.mini_map.a_tail) >= 5
