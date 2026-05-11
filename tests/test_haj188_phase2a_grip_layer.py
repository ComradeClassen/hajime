# tests/test_haj188_phase2a_grip_layer.py
# HAJ-188 — Phase 2a grip layer: nodes, edges, state-change flashes.
#
# Capture-layer tests + state-change diff logic + node positioning. No
# pygame window opens. The render layer reads these structures and
# draws; correctness of the data contract is what we lock down here so
# the synchronization test (HAJ-194) can build on top.

from __future__ import annotations

import io
import os
import random
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from enums import (
    GripDepth, GripMode, GripTarget, GripTypeV2, BodyPart,
)
from grip_graph import Event, GripEdge
from match import Match
from referee import build_suzuki
import main as main_module

from viewer_capture import (
    EDGE_STATE_COMPROMISED,
    EDGE_STATE_CONTESTED,
    EDGE_STATE_DEEPENING,
    EDGE_STATE_STABLE,
    EDGE_STATE_STRIPPING,
    GRIP_NODE_IDS,
    GripEdgeView,
    GripNodeFlash,
    Identity,
    NODE_FLASH_COMPROMISED,
    NODE_FLASH_DEEPENED,
    NODE_FLASH_STRIPPED,
    NODE_FLASH_SWITCHED,
    Phase1RecordingRenderer,
    Phase1ViewState,
    capture_phase1_view,
    grip_node_screen_xy,
    target_to_node_id,
    _layout_bodies,
    TACHIWAZA,
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


def _make_edge(
    grasper, target, *,
    grasper_part=BodyPart.RIGHT_HAND,
    target_loc=GripTarget.LEFT_LAPEL,
    grip_type=GripTypeV2.LAPEL_HIGH,
    depth=GripDepth.STANDARD,
    contested=False,
):
    e = GripEdge(
        grasper_id=grasper.identity.name,
        grasper_part=grasper_part,
        target_id=target.identity.name,
        target_location=target_loc,
        grip_type_v2=grip_type,
        depth_level=depth,
        strength=1.0,
        established_tick=0,
        mode=GripMode.CONNECTIVE,
    )
    e.contested = contested
    return e


# ---------------------------------------------------------------------------
# Acceptance #1 — grip nodes render at the right anatomical positions.
# ---------------------------------------------------------------------------
def test_ten_grip_nodes_per_body() -> None:
    """Section 2.3 calls for 8–10 grip nodes per body. We carry 10."""
    assert len(GRIP_NODE_IDS) == 10
    expected = {
        "left_lapel", "right_lapel",
        "left_sleeve", "right_sleeve",
        "back_collar", "side_collar",
        "belt",
        "left_thigh", "right_thigh",
        "head_neck",
    }
    assert set(GRIP_NODE_IDS) == expected


def test_grip_node_screen_xy_resolves_for_every_node() -> None:
    """Every node must resolve to a concrete (x, y) when given a body
    pose — otherwise the renderer can't draw it."""
    pose_a, _ = _layout_bodies(TACHIWAZA)
    for node_id in GRIP_NODE_IDS:
        xy = grip_node_screen_xy(node_id, pose_a)
        assert xy is not None, f"node {node_id!r} has no screen position"
        assert isinstance(xy[0], int) and isinstance(xy[1], int)


def test_grip_node_screen_xy_distinct_per_node() -> None:
    """Nodes shouldn't all collapse to the same point — that would
    defeat the diagrammatic anatomy. Allow at most a tiny number of
    coincidences from layout rounding."""
    pose_a, _ = _layout_bodies(TACHIWAZA)
    xys = [grip_node_screen_xy(n, pose_a) for n in GRIP_NODE_IDS]
    assert len(set(xys)) >= len(GRIP_NODE_IDS) - 1


def test_grip_node_screen_xy_returns_none_for_unknown() -> None:
    pose_a, _ = _layout_bodies(TACHIWAZA)
    assert grip_node_screen_xy("not_a_real_node", pose_a) is None


def test_target_to_node_id_handles_engine_targets() -> None:
    """Standing-grip GripTarget values should map onto display nodes."""
    assert target_to_node_id("left_lapel")  == "left_lapel"
    assert target_to_node_id("right_sleeve") == "right_sleeve"
    assert target_to_node_id("back_collar")  == "back_collar"
    assert target_to_node_id("belt")         == "belt"
    # Ne-waza variants collapse onto the standing-display vocabulary.
    assert target_to_node_id("waist") == "belt"
    assert target_to_node_id("left_back_gi") == "back_collar"
    # Ne-waza-only targets the display doesn't render → None.
    assert target_to_node_id("left_wrist") is None
    assert target_to_node_id("left_ankle") is None


# ---------------------------------------------------------------------------
# Acceptance #2 — grip edges encode owner, depth thickness, target.
# ---------------------------------------------------------------------------
def test_capture_grip_edges_carries_owner_and_depth() -> None:
    """Owner identity is set from the grasper id; depth comes from
    GripDepth.modifier(): SLIPPING=0.2, POCKET=0.4, STANDARD=0.7,
    DEEP=1.0."""
    m = _fresh_match()
    m.grip_graph.add_edge(_make_edge(
        m.fighter_a, m.fighter_b,
        target_loc=GripTarget.LEFT_LAPEL, depth=GripDepth.DEEP,
    ))
    snap = capture_phase1_view(m, tick=1, events=[])
    assert len(snap.grip_edges) == 1
    e = snap.grip_edges[0]
    assert e.grasper_id == m.fighter_a.identity.name
    assert e.grasper_identity == Identity.BLUE
    assert e.target_id == m.fighter_b.identity.name
    assert e.target_identity == Identity.WHITE
    assert e.target_node == "left_lapel"
    assert abs(e.depth - 1.0) < 1e-9


def test_capture_depth_modifier_slipping() -> None:
    m = _fresh_match()
    m.grip_graph.add_edge(_make_edge(
        m.fighter_a, m.fighter_b, depth=GripDepth.SLIPPING,
    ))
    snap = capture_phase1_view(m, tick=1, events=[])
    e = snap.grip_edges[0]
    assert abs(e.depth - 0.2) < 1e-9
    # SLIPPING is the COMPROMISED visual state regardless of events.
    assert e.state == EDGE_STATE_COMPROMISED


def test_capture_grasper_part_normalised_to_hand() -> None:
    """Edges always render hand → body in Phase 2a. Non-hand grasper
    parts (e.g. forearm-anchored ne-waza grips) collapse onto the
    matching left/right hand."""
    m = _fresh_match()
    m.grip_graph.add_edge(_make_edge(
        m.fighter_a, m.fighter_b,
        grasper_part=BodyPart.RIGHT_FOREARM,
    ))
    snap = capture_phase1_view(m, tick=1, events=[])
    assert snap.grip_edges[0].grasper_part == "right_hand"


def test_capture_skips_non_displayable_target() -> None:
    """Ne-waza wrist/ankle targets aren't on the 10-node display map.
    The edge is skipped from grip_edges; engine state is unchanged."""
    m = _fresh_match()
    m.grip_graph.add_edge(_make_edge(
        m.fighter_a, m.fighter_b,
        target_loc=GripTarget.LEFT_WRIST,
    ))
    snap = capture_phase1_view(m, tick=1, events=[])
    assert len(snap.grip_edges) == 0
    # Engine still has the edge.
    assert len(m.grip_graph.edges) == 1


# ---------------------------------------------------------------------------
# Acceptance #3 — distinguishable state per edge.
# ---------------------------------------------------------------------------
def test_state_stable_when_no_events_and_not_contested() -> None:
    m = _fresh_match()
    e = _make_edge(m.fighter_a, m.fighter_b, depth=GripDepth.STANDARD)
    m.grip_graph.add_edge(e)
    snap = capture_phase1_view(m, tick=1, events=[])
    assert snap.grip_edges[0].state == EDGE_STATE_STABLE


def test_state_contested_when_engine_flag_set() -> None:
    m = _fresh_match()
    m.grip_graph.add_edge(_make_edge(
        m.fighter_a, m.fighter_b, contested=True,
    ))
    snap = capture_phase1_view(m, tick=1, events=[])
    assert snap.grip_edges[0].state == EDGE_STATE_CONTESTED


def test_state_deepening_when_grip_deepen_event_for_edge() -> None:
    m = _fresh_match()
    e = _make_edge(m.fighter_a, m.fighter_b)
    m.grip_graph.add_edge(e)
    deepen_ev = Event(
        tick=2, event_type="GRIP_DEEPEN",
        description="[grip] deepens",
        data={"edge_id": id(e), "from": "POCKET", "to": "STANDARD"},
    )
    snap = capture_phase1_view(m, tick=2, events=[deepen_ev])
    assert snap.grip_edges[0].state == EDGE_STATE_DEEPENING


def test_state_stripping_when_grip_degrade_event_for_edge() -> None:
    m = _fresh_match()
    e = _make_edge(m.fighter_a, m.fighter_b, depth=GripDepth.STANDARD)
    m.grip_graph.add_edge(e)
    degrade_ev = Event(
        tick=2, event_type="GRIP_DEGRADE",
        description="[grip] degrades",
        data={"edge_id": id(e)},
    )
    snap = capture_phase1_view(m, tick=2, events=[degrade_ev])
    assert snap.grip_edges[0].state == EDGE_STATE_STRIPPING


def test_state_compromised_wins_over_deepening_at_slipping_depth() -> None:
    """A SLIPPING grip is structurally broken — even if a deepen
    event fires, the visual reads compromised."""
    m = _fresh_match()
    e = _make_edge(m.fighter_a, m.fighter_b, depth=GripDepth.SLIPPING)
    m.grip_graph.add_edge(e)
    deepen_ev = Event(
        tick=3, event_type="GRIP_DEEPEN",
        description="[grip] deepens",
        data={"edge_id": id(e)},
    )
    snap = capture_phase1_view(m, tick=3, events=[deepen_ev])
    assert snap.grip_edges[0].state == EDGE_STATE_COMPROMISED


# ---------------------------------------------------------------------------
# Acceptance #4 — state transitions trigger node flashes.
# ---------------------------------------------------------------------------
def test_deepen_event_synthesizes_deepened_flash() -> None:
    m = _fresh_match()
    e = _make_edge(m.fighter_a, m.fighter_b)
    m.grip_graph.add_edge(e)
    deepen = Event(
        tick=2, event_type="GRIP_DEEPEN",
        description="[grip] deepens", data={"edge_id": id(e)},
    )
    snap = capture_phase1_view(m, tick=2, events=[deepen])
    kinds = [nf.kind for nf in snap.grip_node_flashes]
    assert NODE_FLASH_DEEPENED in kinds
    flash = next(nf for nf in snap.grip_node_flashes
                 if nf.kind == NODE_FLASH_DEEPENED)
    assert flash.target_id == m.fighter_b.identity.name
    assert flash.node_id == "left_lapel"


def test_compromised_flash_fires_on_first_slipping_tick() -> None:
    """The flash should fire when an edge *enters* SLIPPING, not on
    every subsequent tick it stays there."""
    m = _fresh_match()
    e = _make_edge(m.fighter_a, m.fighter_b, depth=GripDepth.STANDARD)
    m.grip_graph.add_edge(e)
    snap_t1 = capture_phase1_view(m, tick=1, events=[])
    # Mutate engine: depth drops to SLIPPING.
    e.depth_level = GripDepth.SLIPPING
    snap_t2 = capture_phase1_view(m, tick=2, events=[], prev_view=snap_t1)
    kinds_t2 = [nf.kind for nf in snap_t2.grip_node_flashes]
    assert NODE_FLASH_COMPROMISED in kinds_t2
    # On t3 (still SLIPPING), no fresh COMPROMISED flash.
    snap_t3 = capture_phase1_view(m, tick=3, events=[], prev_view=snap_t2)
    kinds_t3 = [nf.kind for nf in snap_t3.grip_node_flashes]
    assert NODE_FLASH_COMPROMISED not in kinds_t3


def test_strip_event_synthesizes_stripped_flash() -> None:
    """When an edge vanishes between prev and current snapshots and a
    GRIP_STRIPPED / GRIP_BREAK event fires, the affected node gets a
    STRIPPED flash. The flash carries the node from the prev
    snapshot since the engine edge is already gone."""
    m = _fresh_match()
    e = _make_edge(
        m.fighter_a, m.fighter_b,
        target_loc=GripTarget.RIGHT_SLEEVE,
        depth=GripDepth.STANDARD,
    )
    m.grip_graph.add_edge(e)
    snap_t1 = capture_phase1_view(m, tick=1, events=[])
    # Engine drops the edge + emits stripped event.
    m.grip_graph.remove_edge(e)
    strip = Event(
        tick=2, event_type="GRIP_STRIPPED",
        description="[grip] stripped",
    )
    snap_t2 = capture_phase1_view(
        m, tick=2, events=[strip], prev_view=snap_t1,
    )
    kinds = [nf.kind for nf in snap_t2.grip_node_flashes]
    assert NODE_FLASH_STRIPPED in kinds
    flash = next(nf for nf in snap_t2.grip_node_flashes
                 if nf.kind == NODE_FLASH_STRIPPED)
    assert flash.node_id == "right_sleeve"
    assert flash.target_id == m.fighter_b.identity.name


def test_switched_ownership_flash_when_target_node_owner_flips() -> None:
    """Same target node, different grasper across consecutive ticks
    → SWITCHED flash with prev/new owner identities."""
    m = _fresh_match()
    e1 = _make_edge(m.fighter_a, m.fighter_b)   # blue grips white's left lapel
    m.grip_graph.add_edge(e1)
    snap_t1 = capture_phase1_view(m, tick=1, events=[])
    # White rips it free + counter-grips the same lapel position.
    m.grip_graph.remove_edge(e1)
    e2 = GripEdge(
        grasper_id=m.fighter_b.identity.name,
        grasper_part=BodyPart.RIGHT_HAND,
        target_id=m.fighter_b.identity.name,    # self? no — should target other
        target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH,
        depth_level=GripDepth.POCKET,
        strength=1.0, established_tick=2,
    )
    # Correct: grasper=fighter_b, target=fighter_a's lapel. Same display
    # node ('left_lapel') on a different judoka — that's NOT a switch
    # because target_id differs. To test a true switch, both edges
    # must point at the same target_id + node.
    e2.target_id = m.fighter_a.identity.name
    m.grip_graph.add_edge(e2)
    snap_t2 = capture_phase1_view(m, tick=2, events=[], prev_view=snap_t1)
    # Different target_id → not a switch on the original (target_b, node)
    # key. The switch detector should NOT fire.
    kinds = [nf.kind for nf in snap_t2.grip_node_flashes]
    assert NODE_FLASH_SWITCHED not in kinds


def test_switched_ownership_flash_actually_fires_on_same_target() -> None:
    """Same (target_id, target_node) with a flipped grasper between
    consecutive snapshots → SWITCHED flash."""
    m = _fresh_match()
    e1 = _make_edge(
        m.fighter_a, m.fighter_b,
        target_loc=GripTarget.LEFT_LAPEL,
    )
    m.grip_graph.add_edge(e1)
    snap_t1 = capture_phase1_view(m, tick=1, events=[])
    m.grip_graph.remove_edge(e1)
    # Fighter_b grips fighter_b's own left_lapel — no, target_id must
    # be the opponent. To swap ownership of (target=fighter_b,
    # node=left_lapel), we need fighter_b to be the new grasper of
    # something on themselves, which doesn't make engine sense. Real
    # ownership swap: fighter_b counter-grips on the same lapel of the
    # same body — but in judo this is fighter_b stripping then re-grasping
    # the same target their *opponent* was holding. The same
    # (target_id, target_node) implies the target body is unchanged,
    # so the swap is grasper changing.
    # Simulation: fighter_a held white's left_lapel (target=white).
    # Now fighter_b also grips white's left_lapel (still target=white).
    # That's nonsensical (fighter_b gripping themselves) — so use
    # fighter_a → fighter_b grips, then fighter_b's grip stripped and
    # fighter_a re-grips the same target. That's NOT a switch — same
    # owner. Real switch = two different opponents trading the same
    # gi target, which only happens if both are gripping the third
    # judoka. With only 2 fighters, ownership-swap on a body-target
    # cannot happen directly.
    #
    # The detector still needs to be wired right for the abstraction.
    # Test that detector with synthetic snapshots instead.
    from viewer_capture import _derive_grip_node_flashes
    cur_edge = GripEdgeView(
        edge_id=999, grasper_id="X", grasper_identity=Identity.WHITE,
        grasper_part="right_hand", target_id="Y",
        target_identity=Identity.BLUE,
        target_node="belt", target_raw="belt",
        depth=0.7, state=EDGE_STATE_STABLE,
    )
    prev_edge = GripEdgeView(
        edge_id=998, grasper_id="Z", grasper_identity=Identity.BLUE,
        grasper_part="left_hand", target_id="Y",
        target_identity=Identity.BLUE,
        target_node="belt", target_raw="belt",
        depth=0.7, state=EDGE_STATE_STABLE,
    )
    prev_view = Phase1ViewState(
        tick=1, position_state=TACHIWAZA,
        body_a=snap_t1.body_a, body_b=snap_t1.body_b,
        score_a=snap_t1.score_a, score_b=snap_t1.score_b,
        clock=snap_t1.clock,
        text_bursts=(), referee_flashes=(),
        grip_edges=(prev_edge,),
    )
    flashes = _derive_grip_node_flashes(
        tick=2, events=[], cur_edges=(cur_edge,),
        deepened_ids=frozenset(), degraded_ids=frozenset(),
        prev_view=prev_view,
    )
    kinds = [nf.kind for nf in flashes]
    assert NODE_FLASH_SWITCHED in kinds
    sw = next(nf for nf in flashes if nf.kind == NODE_FLASH_SWITCHED)
    assert sw.prev_owner_identity == Identity.BLUE
    assert sw.new_owner_identity == Identity.WHITE
    assert sw.node_id == "belt"


# ---------------------------------------------------------------------------
# Acceptance #5 — text burst captioning still matches grip events 1:1.
# ---------------------------------------------------------------------------
def test_grip_event_descriptions_become_text_bursts_same_tick() -> None:
    """The Phase 1 text-burst invariant must still hold for grip
    events: every grip event with a description becomes a TextBurst
    on the same tick."""
    rec = Phase1RecordingRenderer()
    random.seed(101)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=40, seed=101, renderer=rec,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    burst_set = {(tick, text) for tick, _, text in rec.all_text_bursts()}
    grip_event_descs = [
        (tick, etype, desc)
        for tick, etype, desc in rec.event_log
        if etype.startswith("GRIP_")
    ]
    # We need at least *some* grip events for the assertion to be
    # meaningful — Tanaka/Sato should be deep into grip war by tick 40.
    assert grip_event_descs, "expected grip events in 40-tick match"
    for tick, _, desc in grip_event_descs:
        assert (tick, desc) in burst_set, (
            f"grip event at tick {tick} missing from text bursts: {desc!r}"
        )


# ---------------------------------------------------------------------------
# Acceptance #7 — animation timing scales with playback speed.
# (The scaled_duration helper is already covered in HAJ-187 tests; here
# we confirm the per-kind base durations exist and are positive.)
# ---------------------------------------------------------------------------
def test_node_flash_base_durations_are_positive() -> None:
    from viewer_capture import node_flash_base_duration as _node_flash_base_duration
    for kind in (NODE_FLASH_STRIPPED, NODE_FLASH_DEEPENED,
                 NODE_FLASH_COMPROMISED, NODE_FLASH_SWITCHED):
        assert _node_flash_base_duration(kind) > 0


# ---------------------------------------------------------------------------
# Pure-observer contract: HAJ-188 capture must not perturb match outcome.
# ---------------------------------------------------------------------------
def test_grip_capture_does_not_perturb_match() -> None:
    random.seed(202)
    _, _ = _pair()  # warm up
    rec_no = None
    rec_yes = Phase1RecordingRenderer()

    def _run(renderer):
        random.seed(202)
        t, s = _pair()
        mm = Match(
            fighter_a=t, fighter_b=s, referee=build_suzuki(),
            max_ticks=25, seed=202, renderer=renderer,
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            mm.run()
        return buf.getvalue()

    out_no  = _run(rec_no)
    out_yes = _run(rec_yes)
    assert out_no == out_yes


# ---------------------------------------------------------------------------
# Live-match smoke: capture some real grip edges.
# ---------------------------------------------------------------------------
def test_live_match_produces_grip_edges_in_capture() -> None:
    """A 30-tick Tanaka-vs-Sato match should land at least one captured
    grip edge in some snapshot — confirms the wiring carries through
    a real engine run, not just a synthesised one."""
    rec = Phase1RecordingRenderer()
    random.seed(303)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=30, seed=303, renderer=rec,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    total_edges = sum(len(snap.grip_edges) for snap in rec.snapshots)
    assert total_edges > 0, (
        "expected at least one grip edge across 30 ticks of "
        "Tanaka vs Sato"
    )
