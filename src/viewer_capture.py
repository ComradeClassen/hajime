# viewer_capture.py
# Reusable capture / data layer for the dev match viewer.
#
# Originally extracted from `phase1_viewer.py` (HAJ-187/188/189). The
# Phase 1 anatomical-centerpiece viewer that lived alongside this code
# was retired after a session of playtesting against the existing
# top-down `match_viewer.py` — that one read more clearly. The
# *capture* work, however, stayed valuable: it knows how to read
# Match per-tick state into immutable snapshots that any renderer can
# consume.
#
# What this module provides:
#   * Pure-data view structs — MatchViewState, BodyView, ScorePanelView,
#     MatchClockView, GripEdgeView, GripNodeFlash, ArrowView,
#     MiniMapView, TextBurst, RefereeFlash. All frozen dataclasses.
#   * `capture_view(match, tick, events, prev_view=None)` — single
#     entry point that reads a live Match and returns a
#     MatchViewState. Pure read; never mutates anything. Reads from
#     the same per-tick state windows the narration module reads, so
#     the 1:1 prose-log/viewer-event invariant is structural.
#   * Anatomical layout helpers (`_BodyPose`, `_BODY_LAYOUT`,
#     `grip_node_screen_xy`, `_layout_bodies`) for any future renderer
#     that wants to draw the side anatomical body silhouettes.
#   * Damage-band / tinting helpers (`damage_band`, `tint_toward_red`,
#     `DAMAGE_BAND_RED_MIX`).
#   * `RecordingViewCapture` — push-style Renderer fake used by tests
#     and any future cross-check regression.
#   * `TextBurstQueue` — display-timing helper for the text-burst
#     captioning grammar (driver-style renderers can consume it).
#
# What this module does NOT provide:
#   * No pygame imports. All renderers belong elsewhere.
#   * No window dimensions / colour palettes. Those are renderer-side.
#
# Tests live in tests/test_haj187_phase1_viewer.py,
# tests/test_haj188_phase2a_grip_layer.py, and
# tests/test_haj189_phase2b_arrows_damage_minimap.py — all originally
# written against phase1_viewer; they import from here now.

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from enums import Position, SubLoopState

if TYPE_CHECKING:
    from match import Match
    from grip_graph import Event


# ---------------------------------------------------------------------------
# 19 ANATOMICAL REGIONS — Section 2.1 of the visual language doc.
#
# The engine carries 24 body parts (see judoka.BODY_PARTS); cardio is
# global. The viewer collapses left/right wrist into the forearm
# region and surfaces every other limb pair as its own tintable
# region.
# ---------------------------------------------------------------------------
ANATOMICAL_REGIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("head",            ("head",)),
    ("neck",            ("neck",)),
    ("left_shoulder",   ("left_shoulder",)),
    ("right_shoulder",  ("right_shoulder",)),
    ("left_bicep",      ("left_bicep",)),
    ("right_bicep",     ("right_bicep",)),
    ("left_forearm",    ("left_forearm", "left_wrist")),
    ("right_forearm",   ("right_forearm", "right_wrist")),
    ("left_hand",       ("left_hand",)),
    ("right_hand",      ("right_hand",)),
    ("chest",           ("core",)),
    ("core",            ("core",)),
    ("lower_back",      ("lower_back",)),
    ("hips",            ("left_hip", "right_hip")),
    ("left_thigh",      ("left_thigh", "left_knee")),
    ("right_thigh",     ("right_thigh", "right_knee")),
    ("left_shin",       ("left_leg",)),
    ("right_shin",      ("right_leg",)),
    ("left_foot",       ("left_foot",)),
    ("right_foot",      ("right_foot",)),
)


# ---------------------------------------------------------------------------
# IDENTITY + POSITION STATE
# ---------------------------------------------------------------------------
class Identity:
    """Two-judoka identity tags. Mirrors actual judo competition —
    blue gi vs white gi. Renderers translate these to actual RGB."""
    BLUE  = "BLUE"
    WHITE = "WHITE"


# Position-state buckets the viewer renders.
TACHIWAZA    = "TACHIWAZA"
TRANSITIONAL = "TRANSITIONAL"
NE_WAZA      = "NE_WAZA"

_TRANSITIONAL_POSITIONS = frozenset({
    Position.SCRAMBLE,
    Position.THROW_COMMITTED,
    Position.DOWN,
})


def position_bucket(position: Position, sub_loop: SubLoopState) -> str:
    """Map (Position, SubLoopState) → one of the three buckets.
    NE_WAZA wins (it's a sub-loop state). Transitional carries
    SCRAMBLE / THROW_COMMITTED / DOWN."""
    if sub_loop == SubLoopState.NE_WAZA:
        return NE_WAZA
    if position in _TRANSITIONAL_POSITIONS:
        return TRANSITIONAL
    return TACHIWAZA


# ---------------------------------------------------------------------------
# BODY VIEW — per-judoka per-tick anatomical state.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BodyView:
    name:           str
    identity:       str            # Identity.BLUE / Identity.WHITE
    posture_pose:   str            # 'standing' / 'transitional' / 'ne_waza'
    region_damage:  tuple[tuple[str, float], ...]
    cardio:         float          # 0.0–1.0 stamina bar
    com_position:   tuple[float, float]
    facing:         tuple[float, float] = (1.0, 0.0)


# ---------------------------------------------------------------------------
# SCORE PANEL — per-judoka.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ScorePanelView:
    name:        str
    identity:    str
    waza_ari:    int
    ippon:       bool
    shidos:      int
    hansoku_make: bool


# ---------------------------------------------------------------------------
# MATCH CLOCK
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MatchClockView:
    tick:               int
    max_ticks:          int
    regulation_ticks:   int
    golden_score:       bool

    @property
    def ticks_remaining(self) -> int:
        return max(0, self.max_ticks - self.tick)

    @property
    def display(self) -> str:
        rem = self.max_ticks - self.tick
        if rem < 0:
            m, s = divmod(-rem, 60)
            return f"+{m}:{s:02d}"
        m, s = divmod(rem, 60)
        return f"{m}:{s:02d}"


# ---------------------------------------------------------------------------
# TEXT BURST + REFEREE FLASH — per-tick event surfaces.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TextBurst:
    tick:       int
    text:       str
    event_type: str
    base_hold_seconds: float = 1.4   # at 1× playback


FLASH_IPPON       = "IPPON_SWEEP"
FLASH_WAZA_ARI    = "WAZA_ARI_FLASH"
FLASH_SHIDO       = "SHIDO_CARD"
FLASH_HANSOKU     = "HANSOKU_CARD"
FLASH_MATTE       = "MATTE_FREEZE"
FLASH_HAJIME      = "HAJIME_RESUME"


@dataclass(frozen=True)
class RefereeFlash:
    tick:   int
    kind:   str
    target: Optional[str] = None    # judoka name, or None for full-viewer
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# GRIP NODE / EDGE / FLASH — capture surface for the grip graph.
# ---------------------------------------------------------------------------
GRIP_NODE_IDS: tuple[str, ...] = (
    "left_lapel",   "right_lapel",
    "left_sleeve",  "right_sleeve",
    "back_collar",  "side_collar",
    "belt",
    "left_thigh",   "right_thigh",
    "head_neck",
)


_TARGET_TO_NODE_ID: dict[str, str] = {
    "left_lapel":    "left_lapel",
    "right_lapel":   "right_lapel",
    "left_sleeve":   "left_sleeve",
    "right_sleeve":  "right_sleeve",
    "back_collar":   "back_collar",
    "side_collar":   "side_collar",
    "belt":          "belt",
    "waist":         "belt",
    "left_thigh":    "left_thigh",
    "right_thigh":   "right_thigh",
    "left_knee":     "left_thigh",
    "right_knee":    "right_thigh",
    "head":          "head_neck",
    "neck":          "head_neck",
    "left_back_gi":  "back_collar",
    "right_back_gi": "back_collar",
}


def target_to_node_id(target_value: str) -> Optional[str]:
    """Map an engine GripTarget value (lowercase string) to one of
    the 10 display node ids. Returns None for ne-waza-only targets
    (wrists / ankles / elbows / shoulders)."""
    return _TARGET_TO_NODE_ID.get(target_value.lower())


EDGE_STATE_STABLE      = "stable"
EDGE_STATE_CONTESTED   = "contested"
EDGE_STATE_DEEPENING   = "deepening"
EDGE_STATE_STRIPPING   = "stripping"
EDGE_STATE_COMPROMISED = "compromised"


@dataclass(frozen=True)
class GripEdgeView:
    """One active grip edge as the viewer needs to draw it.

    `edge_id` is the engine edge's `id()` so the renderer can
    correlate across consecutive snapshots. `depth` is the
    continuous 0.0–1.0 modifier from GripDepth."""
    edge_id:         int
    grasper_id:      str
    grasper_identity: str          # Identity.BLUE / Identity.WHITE
    grasper_part:    str           # 'left_hand' / 'right_hand'
    target_id:       str
    target_identity: str
    target_node:     str           # one of GRIP_NODE_IDS
    target_raw:      str           # engine GripTarget.value
    depth:           float         # 0.0–1.0
    state:           str           # one of EDGE_STATE_*


NODE_FLASH_STRIPPED    = "STRIPPED"
NODE_FLASH_DEEPENED    = "DEEPENED"
NODE_FLASH_COMPROMISED = "COMPROMISED"
NODE_FLASH_SWITCHED    = "SWITCHED"


@dataclass(frozen=True)
class GripNodeFlash:
    """A grip-node flash firing this tick. Renderer decays it over
    the appropriate wall-clock window."""
    tick:                 int
    kind:                 str
    target_id:            str
    target_identity:      str
    node_id:              str
    prev_owner_identity:  Optional[str] = None
    new_owner_identity:   Optional[str] = None


# Animation timing for grip cues, at 1× playback.
NODE_FLASH_STRIPPED_S:    float = 0.4
NODE_FLASH_DEEPENED_S:    float = 0.4
NODE_FLASH_COMPROMISED_S: float = 0.6
NODE_FLASH_SWITCHED_S:    float = 0.3


def node_flash_base_duration(kind: str) -> float:
    return {
        NODE_FLASH_STRIPPED:    NODE_FLASH_STRIPPED_S,
        NODE_FLASH_DEEPENED:    NODE_FLASH_DEEPENED_S,
        NODE_FLASH_COMPROMISED: NODE_FLASH_COMPROMISED_S,
        NODE_FLASH_SWITCHED:    NODE_FLASH_SWITCHED_S,
    }.get(kind, 0.4)


# ---------------------------------------------------------------------------
# ARROWS — intent vs actual force vectors.
# ---------------------------------------------------------------------------
ARROW_KIND_INTENT = "INTENT"
ARROW_KIND_ACTUAL = "ACTUAL"


@dataclass(frozen=True)
class ArrowView:
    """One per (judoka, kind). Vector is in mat-coordinate units
    (the same units the engine uses for force × direction). Length
    encodes attempted (intent) or delivered (actual) magnitude."""
    judoka_name:     str
    judoka_identity: str
    kind:            str          # ARROW_KIND_INTENT / ARROW_KIND_ACTUAL
    vec_x:           float
    vec_y:           float
    magnitude:       float


# ---------------------------------------------------------------------------
# DAMAGE TINTING — per-region wear classification + RGB shift toward red.
# ---------------------------------------------------------------------------
DAMAGE_HEALTHY     = "healthy"
DAMAGE_WORKED      = "worked"
DAMAGE_COMPROMISED = "compromised"
DAMAGE_CRITICAL    = "critical"

DAMAGE_BAND_RED_MIX: dict[str, float] = {
    DAMAGE_HEALTHY:     0.00,
    DAMAGE_WORKED:      0.25,
    DAMAGE_COMPROMISED: 0.50,
    DAMAGE_CRITICAL:    0.85,
}


def damage_band(value: float) -> str:
    """Classify a 0.0-1.0 wear value into one of the four bands.
    Bands: healthy < 0.25, worked [0.25, 0.5), compromised
    [0.5, 0.75), critical >= 0.75."""
    if value < 0.25:
        return DAMAGE_HEALTHY
    if value < 0.50:
        return DAMAGE_WORKED
    if value < 0.75:
        return DAMAGE_COMPROMISED
    return DAMAGE_CRITICAL


def tint_toward_red(
    base_rgb: tuple[int, int, int], red_mix: float,
) -> tuple[int, int, int]:
    """Saturation/luminance shift toward red, not a hue replacement.
    Identity colour is preserved: white walks white→pink→red, blue
    walks blue→purple→dark red."""
    if red_mix <= 0.0:
        return base_rgb
    mix = max(0.0, min(1.0, red_mix))
    anchor = (220, 60, 50)
    r = int(round(base_rgb[0] * (1 - mix) + anchor[0] * mix))
    g = int(round(base_rgb[1] * (1 - mix) + anchor[1] * mix))
    b = int(round(base_rgb[2] * (1 - mix) + anchor[2] * mix))
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


# ---------------------------------------------------------------------------
# MINI-MAP — top-down mat schematic capture.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MiniMapView:
    contest_half_m:   float
    safety_half_m:    float
    a_position:       tuple[float, float]
    b_position:       tuple[float, float]
    a_identity:       str
    b_identity:       str
    a_tail:           tuple[tuple[float, float], ...]
    b_tail:           tuple[tuple[float, float], ...]
    a_near_edge:      bool
    b_near_edge:      bool


MINI_MAP_CONTEST_HALF_M_DEFAULT: float = 4.0
MINI_MAP_SAFETY_HALF_M_DEFAULT:  float = 7.0
MINI_MAP_TAIL_LENGTH:            int   = 12
MINI_MAP_EDGE_THRESHOLD_M:       float = 0.75


# ---------------------------------------------------------------------------
# MATCH VIEW STATE — frozen per-tick snapshot.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MatchViewState:
    tick:              int
    position_state:    str            # TACHIWAZA / TRANSITIONAL / NE_WAZA
    body_a:            BodyView
    body_b:            BodyView
    score_a:           ScorePanelView
    score_b:           ScorePanelView
    clock:             MatchClockView
    text_bursts:       tuple[TextBurst, ...]
    referee_flashes:   tuple[RefereeFlash, ...]
    era:               Optional[str] = None
    ruleset:           Optional[str] = None
    mat_coords_a:      tuple[float, float] = (0.0, 0.0)
    mat_coords_b:      tuple[float, float] = (0.0, 0.0)
    grip_edges:        tuple[GripEdgeView, ...] = ()
    grip_node_flashes: tuple[GripNodeFlash, ...] = ()
    arrows:            tuple[ArrowView, ...] = ()
    mini_map:          Optional[MiniMapView] = None


# Backward-compat alias — some imports may still use the old name.
Phase1ViewState = MatchViewState


# ---------------------------------------------------------------------------
# CAPTURE — pure read of Match state per tick.
# ---------------------------------------------------------------------------
def _capture_body(judoka, identity_tag: str, sub_loop: SubLoopState,
                  position: Position) -> BodyView:
    state = judoka.state
    body  = state.body
    region_damage: list[tuple[str, float]] = []
    for region_name, engine_parts in ANATOMICAL_REGIONS:
        worst = 0.0
        for p in engine_parts:
            ps = body.get(p)
            if ps is None:
                continue
            worst = max(worst, float(getattr(ps, "fatigue", 0.0) or 0.0))
        region_damage.append((region_name, worst))
    if sub_loop == SubLoopState.NE_WAZA:
        pose = "ne_waza"
    elif position in _TRANSITIONAL_POSITIONS:
        pose = "transitional"
    else:
        pose = "standing"
    return BodyView(
        name=judoka.identity.name,
        identity=identity_tag,
        posture_pose=pose,
        region_damage=tuple(region_damage),
        cardio=float(state.cardio_current),
        com_position=tuple(state.body_state.com_position),
        facing=tuple(state.body_state.facing),
    )


def _capture_score(judoka, identity_tag: str) -> ScorePanelView:
    s = judoka.state.score
    return ScorePanelView(
        name=judoka.identity.name,
        identity=identity_tag,
        waza_ari=int(s.get("waza_ari", 0)),
        ippon=bool(s.get("ippon", False)),
        shidos=int(judoka.state.shidos),
        hansoku_make=bool(judoka.state.shidos >= 3),
    )


_EVENT_TO_FLASH: dict[str, str] = {
    "IPPON_AWARDED":      FLASH_IPPON,
    "WAZA_ARI_AWARDED":   FLASH_WAZA_ARI,
    "SHIDO_AWARDED":      FLASH_SHIDO,
    "MATTE_CALLED":       FLASH_MATTE,
    "HAJIME_CALLED":      FLASH_HAJIME,
}


def _flash_for_event(ev) -> Optional[RefereeFlash]:
    kind = _EVENT_TO_FLASH.get(ev.event_type)
    if kind is None:
        return None
    data = ev.data or {}
    target = (
        data.get("scorer")
        or data.get("scorer_id")
        or data.get("fighter")
    )
    detail = data.get("reason") or data.get("technique")
    return RefereeFlash(
        tick=ev.tick, kind=kind, target=target, detail=detail,
    )


def _hansoku_flash(events) -> Optional[RefereeFlash]:
    """Detect a hansoku-make resolution this tick. The engine routes
    it through MATCH_ENDED with method='hansoku-make'; synthesise a
    flash so the red card from Section 2.7 still fires visibly."""
    for ev in events:
        if ev.event_type != "MATCH_ENDED":
            continue
        data = ev.data or {}
        if data.get("method") != "hansoku-make":
            continue
        winner = data.get("winner")
        return RefereeFlash(
            tick=ev.tick, kind=FLASH_HANSOKU, target=None,
            detail=f"loser_of:{winner}" if winner else None,
        )
    return None


def _capture_grip_edges(
    match, events, identity_for: dict[str, str],
) -> tuple[tuple[GripEdgeView, ...], frozenset[int], frozenset[int]]:
    """Extract a frozen GripEdgeView per active engine edge plus the
    sets of edge ids that deepened / stripped this tick."""
    deepened_ids: set[int] = set()
    degraded_ids: set[int] = set()
    for ev in events:
        et = ev.event_type
        if et == "GRIP_DEEPEN":
            eid = (ev.data or {}).get("edge_id")
            if eid is not None:
                deepened_ids.add(int(eid))
        elif et == "GRIP_DEGRADE":
            eid = (ev.data or {}).get("edge_id")
            if eid is not None:
                degraded_ids.add(int(eid))

    edges_out: list[GripEdgeView] = []
    grip_graph = getattr(match, "grip_graph", None)
    if grip_graph is None:
        return tuple(), frozenset(), frozenset()
    for e in grip_graph.edges:
        eid = id(e)
        depth = float(e.depth_level.modifier())
        target_raw = e.target_location.value
        node = target_to_node_id(target_raw)
        if node is None:
            continue
        if e.depth_level.name == "SLIPPING":
            state = EDGE_STATE_COMPROMISED
        elif eid in deepened_ids:
            state = EDGE_STATE_DEEPENING
        elif eid in degraded_ids:
            state = EDGE_STATE_STRIPPING
        elif getattr(e, "contested", False):
            state = EDGE_STATE_CONTESTED
        else:
            state = EDGE_STATE_STABLE
        grasper_part_name = e.grasper_part.value
        if grasper_part_name not in ("right_hand", "left_hand"):
            grasper_part_name = (
                "right_hand"
                if "right" in grasper_part_name
                else "left_hand"
            )
        edges_out.append(GripEdgeView(
            edge_id=eid,
            grasper_id=e.grasper_id,
            grasper_identity=identity_for.get(e.grasper_id, Identity.BLUE),
            grasper_part=grasper_part_name,
            target_id=e.target_id,
            target_identity=identity_for.get(e.target_id, Identity.WHITE),
            target_node=node,
            target_raw=target_raw,
            depth=depth,
            state=state,
        ))
    return tuple(edges_out), frozenset(deepened_ids), frozenset(degraded_ids)


def _derive_grip_node_flashes(
    tick: int,
    events,
    cur_edges: tuple[GripEdgeView, ...],
    deepened_ids: frozenset[int],
    degraded_ids: frozenset[int],
    prev_view: Optional[MatchViewState],
) -> tuple[GripNodeFlash, ...]:
    """Derive per-tick node flashes from this tick's events + diff
    against prev snapshot. Pure function."""
    flashes: list[GripNodeFlash] = []
    cur_by_id = {e.edge_id: e for e in cur_edges}

    # Deepened.
    for e in cur_edges:
        if e.edge_id in deepened_ids:
            flashes.append(GripNodeFlash(
                tick=tick, kind=NODE_FLASH_DEEPENED,
                target_id=e.target_id,
                target_identity=e.target_identity,
                node_id=e.target_node,
            ))

    # Stripped.
    prev_by_id: dict[int, GripEdgeView] = {}
    if prev_view is not None:
        prev_by_id = {e.edge_id: e for e in prev_view.grip_edges}
    for ev in events:
        if ev.event_type not in ("GRIP_STRIPPED", "GRIP_BREAK"):
            continue
        for eid, prev_e in prev_by_id.items():
            if eid in cur_by_id:
                continue
            flashes.append(GripNodeFlash(
                tick=tick, kind=NODE_FLASH_STRIPPED,
                target_id=prev_e.target_id,
                target_identity=prev_e.target_identity,
                node_id=prev_e.target_node,
            ))
        break

    # Compromised: edge entered SLIPPING this tick.
    if prev_view is not None:
        for e in cur_edges:
            if e.state != EDGE_STATE_COMPROMISED:
                continue
            prev_e = prev_by_id.get(e.edge_id)
            if prev_e is None or prev_e.state == EDGE_STATE_COMPROMISED:
                continue
            flashes.append(GripNodeFlash(
                tick=tick, kind=NODE_FLASH_COMPROMISED,
                target_id=e.target_id,
                target_identity=e.target_identity,
                node_id=e.target_node,
            ))

    # Switched ownership.
    if prev_view is not None:
        prev_owners: dict[tuple[str, str], str] = {}
        for pe in prev_view.grip_edges:
            prev_owners.setdefault(
                (pe.target_id, pe.target_node), pe.grasper_identity,
            )
        seen: set[tuple[str, str]] = set()
        for e in cur_edges:
            key = (e.target_id, e.target_node)
            if key in seen:
                continue
            seen.add(key)
            prev_owner = prev_owners.get(key)
            if prev_owner is None or prev_owner == e.grasper_identity:
                continue
            flashes.append(GripNodeFlash(
                tick=tick, kind=NODE_FLASH_SWITCHED,
                target_id=e.target_id,
                target_identity=e.target_identity,
                node_id=e.target_node,
                prev_owner_identity=prev_owner,
                new_owner_identity=e.grasper_identity,
            ))

    return tuple(flashes)


def _capture_arrows(
    match, identity_for: dict[str, str],
) -> tuple[ArrowView, ...]:
    """Pull per-fighter intent + actual force vectors. Match exposes
    `_intent_force` and `_actual_force` dicts keyed by fighter name;
    both reset to zero at the top of each tick and accumulate via
    _compute_net_force_on. Tolerant of older Match versions that
    lack these attrs (returns empty tuple)."""
    intent_map: dict[str, tuple[float, float]] = getattr(
        match, "_intent_force", {},
    )
    actual_map: dict[str, tuple[float, float]] = getattr(
        match, "_actual_force", {},
    )
    out: list[ArrowView] = []
    for name, identity in identity_for.items():
        ix, iy = intent_map.get(name, (0.0, 0.0))
        ax, ay = actual_map.get(name, (0.0, 0.0))
        i_mag = (ix * ix + iy * iy) ** 0.5
        a_mag = (ax * ax + ay * ay) ** 0.5
        if i_mag > 1e-6:
            out.append(ArrowView(
                judoka_name=name, judoka_identity=identity,
                kind=ARROW_KIND_INTENT,
                vec_x=float(ix), vec_y=float(iy),
                magnitude=float(i_mag),
            ))
        if a_mag > 1e-6:
            out.append(ArrowView(
                judoka_name=name, judoka_identity=identity,
                kind=ARROW_KIND_ACTUAL,
                vec_x=float(ax), vec_y=float(ay),
                magnitude=float(a_mag),
            ))
    return tuple(out)


def _capture_mini_map(
    match, body_a: BodyView, body_b: BodyView,
    identity_for: dict[str, str],
    prev_view: Optional[MatchViewState],
) -> MiniMapView:
    """Pull mat geometry + per-fighter positions and recent-movement
    tail. Tail walks the prev_view chain via successive captures."""
    contest_half = float(getattr(
        match, "MAT_HALF_WIDTH", MINI_MAP_CONTEST_HALF_M_DEFAULT,
    ) or MINI_MAP_CONTEST_HALF_M_DEFAULT)
    safety_half = contest_half + 3.0
    a_pos = body_a.com_position
    b_pos = body_b.com_position
    a_tail: list[tuple[float, float]] = []
    b_tail: list[tuple[float, float]] = []
    if prev_view is not None and prev_view.mini_map is not None:
        a_tail = list(prev_view.mini_map.a_tail)
        a_tail.append(prev_view.body_a.com_position)
        b_tail = list(prev_view.mini_map.b_tail)
        b_tail.append(prev_view.body_b.com_position)
        a_tail = a_tail[-MINI_MAP_TAIL_LENGTH:]
        b_tail = b_tail[-MINI_MAP_TAIL_LENGTH:]
    a_edge = _near_edge(a_pos, contest_half)
    b_edge = _near_edge(b_pos, contest_half)
    return MiniMapView(
        contest_half_m=contest_half,
        safety_half_m=safety_half,
        a_position=a_pos, b_position=b_pos,
        a_identity=body_a.identity, b_identity=body_b.identity,
        a_tail=tuple(a_tail),
        b_tail=tuple(b_tail),
        a_near_edge=a_edge, b_near_edge=b_edge,
    )


def _near_edge(pos: tuple[float, float], contest_half: float) -> bool:
    """Within MINI_MAP_EDGE_THRESHOLD_M of any contest-area
    boundary?"""
    x, y = pos
    margin = contest_half - max(abs(x), abs(y))
    return margin <= MINI_MAP_EDGE_THRESHOLD_M


def capture_view(
    match, tick: int, events,
    prev_view: Optional[MatchViewState] = None,
) -> MatchViewState:
    """Build a frozen MatchViewState from live Match state. Pure
    read; never mutates anything. Reads from the same per-tick state
    windows the narration module reads, so the 1:1 prose-log /
    viewer-event invariant is structural by construction."""
    body_a = _capture_body(match.fighter_a, Identity.BLUE,
                           match.sub_loop_state, match.position)
    body_b = _capture_body(match.fighter_b, Identity.WHITE,
                           match.sub_loop_state, match.position)
    score_a = _capture_score(match.fighter_a, Identity.BLUE)
    score_b = _capture_score(match.fighter_b, Identity.WHITE)

    clock = MatchClockView(
        tick=tick,
        max_ticks=int(getattr(match, "max_ticks", 0)),
        regulation_ticks=int(getattr(
            match, "regulation_ticks", getattr(match, "max_ticks", 0),
        )),
        golden_score=bool(getattr(match, "golden_score", False)),
    )

    bursts: list[TextBurst] = []
    flashes: list[RefereeFlash] = []
    for ev in events:
        desc = getattr(ev, "description", None)
        if desc:
            bursts.append(TextBurst(
                tick=tick, text=desc,
                event_type=ev.event_type or "",
            ))
        f = _flash_for_event(ev)
        if f is not None:
            flashes.append(f)
    hk = _hansoku_flash(events)
    if hk is not None:
        flashes.append(hk)

    mat_a = tuple(match.fighter_a.state.body_state.com_position)
    mat_b = tuple(match.fighter_b.state.body_state.com_position)
    era = getattr(match, "era_stamp", None)
    ruleset = getattr(match, "ruleset_version", None)

    identity_for = {
        match.fighter_a.identity.name: Identity.BLUE,
        match.fighter_b.identity.name: Identity.WHITE,
    }
    grip_edges, deepened_ids, degraded_ids = _capture_grip_edges(
        match, events, identity_for,
    )
    node_flashes = _derive_grip_node_flashes(
        tick, events, grip_edges, deepened_ids, degraded_ids, prev_view,
    )

    arrows = _capture_arrows(match, identity_for)
    mini_map = _capture_mini_map(
        match, body_a, body_b, identity_for, prev_view,
    )

    return MatchViewState(
        tick=tick,
        position_state=position_bucket(match.position, match.sub_loop_state),
        body_a=body_a, body_b=body_b,
        score_a=score_a, score_b=score_b,
        clock=clock,
        text_bursts=tuple(bursts),
        referee_flashes=tuple(flashes),
        era=era, ruleset=ruleset,
        mat_coords_a=mat_a, mat_coords_b=mat_b,
        grip_edges=grip_edges,
        grip_node_flashes=node_flashes,
        arrows=arrows,
        mini_map=mini_map,
    )


# Back-compat alias for the older capture function name.
capture_phase1_view = capture_view


# ---------------------------------------------------------------------------
# ANIMATION TIMING — Section 3.5
# ---------------------------------------------------------------------------
def scaled_duration(base_seconds: float, playback_rate: float) -> float:
    """Scale a 1×-playback animation duration to the current
    playback rate. Defensive against zero / negative rates."""
    rate = max(1e-3, float(playback_rate))
    return float(base_seconds) / rate


# Visual cue base durations at 1× playback.
TEXT_BURST_FADE_IN_S:    float = 0.4
TEXT_BURST_HOLD_S:       float = 1.4
TEXT_BURST_FADE_OUT_S:   float = 0.4
TEXT_BURST_MIN_VISIBLE_S: float = 0.8

MATTE_BANNER_S:   float = 1.6
HAJIME_BANNER_S:  float = 0.9
IPPON_SWEEP_S:    float = 1.2
SCORE_FLASH_S:    float = 0.7
SHIDO_FLASH_S:    float = 0.6
HANSOKU_FLASH_S:  float = 1.4


def referee_flash_base_duration(kind: str) -> float:
    return {
        FLASH_IPPON:    IPPON_SWEEP_S,
        FLASH_WAZA_ARI: SCORE_FLASH_S,
        FLASH_SHIDO:    SHIDO_FLASH_S,
        FLASH_HANSOKU:  HANSOKU_FLASH_S,
        FLASH_MATTE:    MATTE_BANNER_S,
        FLASH_HAJIME:   HAJIME_BANNER_S,
    }.get(kind, 0.6)


# ---------------------------------------------------------------------------
# ANATOMICAL LAYOUT HELPERS — pure math (no pygame).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _RegionRect:
    name:    str
    dx:      float
    dy:      float
    w:       float
    h:       float


# 20 boxed regions per body in body-units.
_BODY_LAYOUT: tuple[_RegionRect, ...] = (
    _RegionRect("head",            0.0,  0.00, 0.55, 0.50),
    _RegionRect("neck",            0.0,  0.50, 0.30, 0.18),
    _RegionRect("left_shoulder",  -0.55, 0.65, 0.40, 0.22),
    _RegionRect("right_shoulder", +0.55, 0.65, 0.40, 0.22),
    _RegionRect("left_bicep",     -0.65, 0.85, 0.30, 0.45),
    _RegionRect("right_bicep",    +0.65, 0.85, 0.30, 0.45),
    _RegionRect("left_forearm",   -0.70, 1.28, 0.28, 0.50),
    _RegionRect("right_forearm",  +0.70, 1.28, 0.28, 0.50),
    _RegionRect("left_hand",      -0.72, 1.75, 0.25, 0.22),
    _RegionRect("right_hand",     +0.72, 1.75, 0.25, 0.22),
    _RegionRect("chest",            0.0, 0.85, 0.95, 0.45),
    _RegionRect("core",             0.0, 1.28, 0.85, 0.40),
    _RegionRect("lower_back",       0.0, 1.66, 0.85, 0.18),
    _RegionRect("hips",             0.0, 1.82, 0.95, 0.25),
    _RegionRect("left_thigh",     -0.28, 2.06, 0.42, 0.55),
    _RegionRect("right_thigh",    +0.28, 2.06, 0.42, 0.55),
    _RegionRect("left_shin",      -0.28, 2.60, 0.34, 0.55),
    _RegionRect("right_shin",     +0.28, 2.60, 0.34, 0.55),
    _RegionRect("left_foot",      -0.28, 3.13, 0.36, 0.18),
    _RegionRect("right_foot",     +0.28, 3.13, 0.36, 0.18),
)


@dataclass(frozen=True)
class _BodyPose:
    centre_xy:   tuple[int, int]
    body_unit_px: int
    rotated_90:  bool

    def region_rect(self, r: _RegionRect) -> tuple[int, int, int, int]:
        u = self.body_unit_px
        if not self.rotated_90:
            cx = self.centre_xy[0] + int(r.dx * u)
            cy = self.centre_xy[1] + int(r.dy * u)
            w = max(2, int(r.w * u))
            h = max(2, int(r.h * u))
            return (cx - w // 2, cy - h // 2, w, h)
        cx = self.centre_xy[0] + int(r.dy * u)
        cy = self.centre_xy[1] + int(r.dx * u)
        w = max(2, int(r.h * u))
        h = max(2, int(r.w * u))
        return (cx - w // 2, cy - h // 2, w, h)


# Grip-node positions in body-units. Used to overlay nodes on top
# of the anatomical body silhouette.
_GRIP_NODE_POS_BODY_UNITS: dict[str, tuple[float, float]] = {
    "left_lapel":   (-0.25, 0.95),
    "right_lapel":  (+0.25, 0.95),
    "left_sleeve":  (-0.70, 1.32),
    "right_sleeve": (+0.70, 1.32),
    "back_collar":  ( 0.00, 0.55),
    "side_collar":  (+0.30, 0.65),
    "belt":         ( 0.00, 1.82),
    "left_thigh":   (-0.28, 2.15),
    "right_thigh": (+0.28, 2.15),
    "head_neck":    ( 0.00, 0.10),
    "left_hand":    (-0.72, 1.75),
    "right_hand":   (+0.72, 1.75),
}


def grip_node_screen_xy(
    node_id: str, pose: _BodyPose,
) -> Optional[tuple[int, int]]:
    """Resolve a grip-node id to screen coordinates given a body
    pose. Returns None for unknown ids. Pure function so tests can
    verify layout without pygame."""
    pos = _GRIP_NODE_POS_BODY_UNITS.get(node_id)
    if pos is None:
        return None
    u = pose.body_unit_px
    dx, dy = pos
    if not pose.rotated_90:
        cx = pose.centre_xy[0] + int(dx * u)
        cy = pose.centre_xy[1] + int(dy * u)
    else:
        cx = pose.centre_xy[0] + int(dy * u)
        cy = pose.centre_xy[1] + int(dx * u)
    return (cx, cy)


def _layout_bodies(
    position_state: str = TACHIWAZA,
) -> tuple[_BodyPose, _BodyPose]:
    """Default body pose pair for tests + simple renderers. Returns
    a fixed-coordinate pair sized to the original Phase 1 layout
    constants. Renderers with custom panel sizes should call
    `layout_anatomical_pair` directly."""
    return layout_anatomical_pair(
        panel_w=1280, panel_h=602, panel_top_y=90,
        body_unit_px=(50 if position_state == NE_WAZA else 60),
        position_state=position_state,
        centre_x_left=460,
        centre_x_right=820,
    )


def layout_anatomical_pair(
    panel_w: int, panel_h: int,
    panel_top_y: int = 0,
    body_unit_px: int = 60,
    *,
    position_state: str = TACHIWAZA,
    centre_x_left: Optional[int] = None,
    centre_x_right: Optional[int] = None,
) -> tuple[_BodyPose, _BodyPose]:
    """Return (left_pose, right_pose) for a pair of side-by-side
    body silhouettes in a panel of given dimensions. Used by any
    renderer that wants two anatomical bodies (e.g. damage side
    panels in match_viewer.py).

    `position_state` controls rotation: NE_WAZA rotates both bodies
    90° to read as ground work. Tachiwaza/transitional both render
    upright."""
    centre_y = panel_top_y + panel_h // 2 - 90
    rot = (position_state == NE_WAZA)
    if centre_x_left is None:
        centre_x_left = panel_w // 4
    if centre_x_right is None:
        centre_x_right = panel_w * 3 // 4
    return (
        _BodyPose((centre_x_left,  centre_y), body_unit_px, rotated_90=rot),
        _BodyPose((centre_x_right, centre_y), body_unit_px, rotated_90=rot),
    )


# ---------------------------------------------------------------------------
# HAND POSITIONS — top-down rendering helper.
# ---------------------------------------------------------------------------
HAND_FORWARD_M: float = 0.30
HAND_LATERAL_M: float = 0.22


def topdown_hand_positions_mat(
    com: tuple[float, float], facing: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return (left_hand, right_hand) positions in mat coords given
    a CoM and a facing unit vector. Body-frame +x = facing; body
    +y (left side) = facing rotated 90° CCW. Same convention as the
    legacy top-down match_viewer.py."""
    cx, cy = com
    fx, fy = facing
    perp_x, perp_y = -fy, fx
    forward = (fx * HAND_FORWARD_M, fy * HAND_FORWARD_M)
    lateral = (perp_x * HAND_LATERAL_M, perp_y * HAND_LATERAL_M)
    left  = (cx + forward[0] + lateral[0], cy + forward[1] + lateral[1])
    right = (cx + forward[0] - lateral[0], cy + forward[1] - lateral[1])
    return left, right


# Sleeve grips travel hand-to-hand; everything else terminates at
# opponent CoM. Used by top-down renderers that draw grip lines.
TARGET_NODE_ANCHOR_HAND: dict[str, str] = {
    "left_sleeve":  "left_hand",
    "right_sleeve": "right_hand",
}


def owned_hands_by_grasper(grip_edges) -> dict[str, set[str]]:
    """Index grip edges by grasper_id → set of grasper hand parts
    that own at least one active edge."""
    out: dict[str, set[str]] = {}
    for e in grip_edges:
        out.setdefault(e.grasper_id, set()).add(e.grasper_part)
    return out


# ---------------------------------------------------------------------------
# TEXT BURST QUEUE — display-timing helper.
# ---------------------------------------------------------------------------
class TextBurstQueue:
    def __init__(self, playback_rate: float = 1.0) -> None:
        self._queue: deque[TextBurst] = deque()
        self._playback_rate = max(1e-3, float(playback_rate))
        self._active: Optional[TextBurst] = None
        self._active_started_wall: float = 0.0

    def set_playback_rate(self, rate: float) -> None:
        self._playback_rate = max(1e-3, float(rate))

    def push_many(self, bursts) -> None:
        for b in bursts:
            self._queue.append(b)

    def _full_lifetime(self) -> float:
        return scaled_duration(
            TEXT_BURST_FADE_IN_S + TEXT_BURST_HOLD_S + TEXT_BURST_FADE_OUT_S,
            self._playback_rate,
        )

    def _min_visible(self) -> float:
        return scaled_duration(TEXT_BURST_MIN_VISIBLE_S, self._playback_rate)

    def tick_wall(self, now_wall: float) -> None:
        if self._active is None and self._queue:
            self._active = self._queue.popleft()
            self._active_started_wall = now_wall
            return
        if self._active is None:
            return
        elapsed = now_wall - self._active_started_wall
        if elapsed < self._min_visible():
            return
        if not self._queue:
            if elapsed >= self._full_lifetime():
                self._active = None
            return
        if elapsed >= self._full_lifetime() - scaled_duration(
            TEXT_BURST_FADE_OUT_S, self._playback_rate,
        ):
            self._active = self._queue.popleft()
            self._active_started_wall = now_wall

    def active(self) -> Optional[TextBurst]:
        return self._active

    def pending(self) -> int:
        return len(self._queue)


# ---------------------------------------------------------------------------
# RECORDING / TEST RENDERER — push-only fake. No pygame.
# ---------------------------------------------------------------------------
class RecordingViewCapture:
    """Captures every MatchViewState the engine produces. Pure data;
    no pygame. Used by tests + a forthcoming synchronization
    regression."""

    def __init__(self) -> None:
        self.start_calls: int = 0
        self.update_calls: int = 0
        self.stop_calls:   int = 0
        self.snapshots:    list[MatchViewState] = []
        self.event_log:    list[tuple[int, str, str]] = []
        self._open: bool = True

    def start(self) -> None:
        self.start_calls += 1

    def update(self, tick: int, match: "Match", events) -> None:
        self.update_calls += 1
        prev = self.snapshots[-1] if self.snapshots else None
        snap = capture_view(match, tick, events, prev_view=prev)
        self.snapshots.append(snap)
        for ev in events:
            desc = getattr(ev, "description", None)
            if desc:
                self.event_log.append((tick, ev.event_type or "", desc))

    def stop(self) -> None:
        self.stop_calls += 1

    def is_open(self) -> bool:
        return self._open

    def close(self) -> None:
        self._open = False

    # Convenience views.
    def all_text_bursts(self) -> list[tuple[int, str, str]]:
        out: list[tuple[int, str, str]] = []
        for snap in self.snapshots:
            for b in snap.text_bursts:
                out.append((b.tick, b.event_type, b.text))
        return out

    def all_flashes(self) -> list[RefereeFlash]:
        return [f for snap in self.snapshots for f in snap.referee_flashes]

    def all_grip_node_flashes(self) -> list[GripNodeFlash]:
        return [
            nf for snap in self.snapshots for nf in snap.grip_node_flashes
        ]

    def all_grip_edges(self) -> list[tuple[int, GripEdgeView]]:
        out: list[tuple[int, GripEdgeView]] = []
        for snap in self.snapshots:
            for e in snap.grip_edges:
                out.append((snap.tick, e))
        return out


# Back-compat alias for callers still using the old name.
Phase1RecordingRenderer = RecordingViewCapture
