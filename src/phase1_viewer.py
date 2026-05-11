# phase1_viewer.py
# HAJ-187 — Viewer Phase 1: anatomical bodies, clock, score panel,
# text-burst captioning, sync architecture.
#
# This is the foundation of the viewer-fidelity rebuild specified in
# `design-notes/triage/viewer-visual-language.md`. Phase 1 commits to
# Section 3's data architecture (single source of truth, parallel
# consumer, synchronization invariant) but renders only the minimum
# vocabulary: two anatomical-diagram bodies (blue + outlined-white),
# match clock, score / shido panel, text burst captioning at the
# bottom, plus the basic referee/score event flashes (matte freeze,
# hajime resume, ippon sweep, score flash, shido card, hansoku-make).
#
# What ships here vs Phase 2/3:
#   * IN: 19-region body silhouettes (base coloring, no damage tinting),
#     position state via body posture, match clock, score panel, shido
#     stack, text bursts, score/referee event cues, playback-rate
#     scaling for animation timing.
#   * OUT: grip nodes/edges, intent/actual arrows, body damage tinting,
#     throw commit arc-sweeps, mini-map, ne-waza substate badges,
#     osaekomi clock, signature glow, tactical shift cues. Those land
#     in HAJ-188/189/190/191/192/193.
#
# Two parts to the module:
#   1. Capture layer (pure data, no pygame). Reads the same per-tick
#      engine state windows the prose-log narration consumes — proves
#      the 1:1 invariant in code by construction. Snapshots are
#      immutable so review-mode scrubbing always renders the engine
#      state at tick T, never something inferred independently.
#   2. Render layer (pygame). Throwaway-OK in the same sense as the
#      existing match_viewer.py — visual language is permanent, the
#      pygame code is interim until the Godot port. Kept simple: solid
#      polygons per anatomical region, no shaders, no per-region damage
#      tinting yet.
#
# Tests live in tests/test_haj187_phase1_viewer.py and exercise the
# capture layer + the 1:1 prose-log/text-burst commitment without
# opening a window.

from __future__ import annotations

import time
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
# global, rendered as a stamina bar, not a region. The viewer collapses
# left/right wrist into the forearm region for display purposes (the
# engine still tracks them separately) and surfaces every other limb
# pair as its own tintable region. Each tuple is
# (region_name, [engine_body_part, ...]) so Phase 2 damage tinting can
# read the worst — or averaged — engine value per region without
# re-mapping.
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
    ("chest",           ("core",)),       # chest renders top half of core
    ("core",            ("core",)),       # abdomen renders bottom half
    ("lower_back",      ("lower_back",)),
    ("hips",            ("left_hip", "right_hip")),
    ("left_thigh",      ("left_thigh", "left_knee")),
    ("right_thigh",     ("right_thigh", "right_knee")),
    ("left_shin",       ("left_leg",)),
    ("right_shin",      ("right_leg",)),
    ("left_foot",       ("left_foot",)),
    ("right_foot",      ("right_foot",)),
)
# Section 2.1 prose says "19 named regions per body"; the explicit list
# in that section enumerates 20 (head, neck, shoulders L/R, biceps L/R,
# forearms L/R, hands L/R, chest, core, lower_back, hips, thighs L/R,
# shins L/R, feet L/R). We follow the explicit list — and Section 2.1
# also notes "the implementation may collapse some regions to match the
# engine 1:1 if that reads better", so the count is intentionally
# flexible. Tests assert >= 19 to honour both readings.


# ---------------------------------------------------------------------------
# IDENTITY + POSITION STATE
# ---------------------------------------------------------------------------
class Identity:
    """Two-judoka identity tags. Mirrors actual judo competition — blue
    gi vs white gi. The white silhouette gets a visible outline so it
    doesn't disappear against a light background (Section 2.1)."""
    BLUE  = "BLUE"
    WHITE = "WHITE"


# Position-state buckets the viewer renders. The match itself uses a
# finer Position enum (STANDING_DISTANT, GRIPPING, ENGAGED, SCRAMBLE,
# THROW_COMMITTED, plus six ne-waza positions). Phase 1 collapses to
# three buckets — Section 2.8 carves up ne-waza substates in Phase 3.
TACHIWAZA    = "TACHIWAZA"
TRANSITIONAL = "TRANSITIONAL"
NE_WAZA      = "NE_WAZA"

_TRANSITIONAL_POSITIONS = frozenset({
    Position.SCRAMBLE,
    Position.THROW_COMMITTED,
    Position.DOWN,
})


def position_bucket(position: Position, sub_loop: SubLoopState) -> str:
    """Map (Position, SubLoopState) → one of the three Phase 1 buckets.

    Pure function so tests can pin behaviour without spinning a Match.
    NE_WAZA wins (it's a sub-loop state, not a position) because the
    six ground positions all imply we're past the transition. The
    transitional bucket carries SCRAMBLE / THROW_COMMITTED / DOWN —
    the in-air or just-landed beats where the body silhouettes should
    visibly mid-move rather than stand upright.
    """
    if sub_loop == SubLoopState.NE_WAZA:
        return NE_WAZA
    if position in _TRANSITIONAL_POSITIONS:
        return TRANSITIONAL
    return TACHIWAZA


# ---------------------------------------------------------------------------
# BODY VIEW — per-judoka per-tick anatomical state.
#
# Phase 1 captures `region_damage` (0.0–1.0 per region) so review-mode
# scrubbing carries it forward, but does NOT render it. Phase 2
# (HAJ-189) wires the tint pass against this exact field — no schema
# change required.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BodyView:
    name:           str
    identity:       str            # Identity.BLUE / Identity.WHITE
    posture_pose:   str            # 'standing' / 'transitional' / 'ne_waza'
    region_damage:  tuple[tuple[str, float], ...]
    cardio:         float          # 0.0–1.0 stamina bar
    com_position:   tuple[float, float]
    # Forward unit vector in mat coords. Captured so the top-down
    # renderer can place hand dots offset from the CoM along facing
    # — without it, hand positions can't be derived from snapshot
    # alone (the engine recomputes facing per tick from grip /
    # locomotion state). Defaulted to +x so older snapshots /
    # synthetic test fixtures keep working.
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
# TEXT BURST — Section 2.13
#
# Each text burst is the prose log line for an event firing this tick.
# Multiple bursts in the same tick queue and display sequentially per
# Section 2.13 ("each burst gets at least 800ms of visibility (at 1×
# playback) before the next replaces it").
#
# `event_type` is preserved so the renderer can pick burst styling
# (e.g. score burst gets brighter colour than a movement burst). The
# 1:1 invariant is structural: every Engine event with a description
# becomes one TextBurst at the same tick.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TextBurst:
    tick:       int
    text:       str
    event_type: str
    base_hold_seconds: float = 1.4   # at 1× playback


# ---------------------------------------------------------------------------
# REFEREE / SCORE FLASH KINDS — Section 2.7 visual cues.
#
# These ride alongside the text burst (which carries the prose) and
# drive the visual flash. Distinct objects from TextBurst because the
# renderer paints them in different planes (full-viewer ippon sweep vs
# bottom-of-viewer text vs score panel update).
# ---------------------------------------------------------------------------
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
    detail: Optional[str] = None    # e.g. shido reason


# ---------------------------------------------------------------------------
# PHASE 1 VIEW STATE — frozen per-tick snapshot.
#
# Section 3.4: the viewer's rendered state at tick T is a pure function
# of engine state at T plus events fired between T-1 and T. This struct
# IS that pure function's output. It carries everything Phase 1 renders
# AND the data Phase 2/3 will read (region damage, mat coords, era
# stamp) so the schema can grow additively without bumping every
# consumer.
#
# Per Section 3.2, the snapshot also surfaces:
#   * mat coordinates (mini-map prep — Phase 2)
#   * era stamp + ruleset (Phase 2 era-aware vocabulary). Engine doesn't
#     yet expose era; we capture None and let Phase 2 wire it.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Phase1ViewState:
    tick:              int
    position_state:    str            # TACHIWAZA / TRANSITIONAL / NE_WAZA
    body_a:            BodyView
    body_b:            BodyView
    score_a:           ScorePanelView
    score_b:           ScorePanelView
    clock:             MatchClockView
    text_bursts:       tuple[TextBurst, ...]      # bursts firing this tick
    referee_flashes:   tuple[RefereeFlash, ...]   # flashes firing this tick
    # Section 3.2 forward-compat fields. Phase 1 captures, Phase 2 renders.
    era:               Optional[str] = None
    ruleset:           Optional[str] = None
    mat_coords_a:      tuple[float, float] = (0.0, 0.0)
    mat_coords_b:      tuple[float, float] = (0.0, 0.0)
    # HAJ-188 — Phase 2a grip data. Defaulted to empty so existing
    # Phase 1 callers continue to work; callers building snapshots
    # directly in tests can skip these.
    grip_edges:        tuple["GripEdgeView", ...] = ()
    grip_node_flashes: tuple["GripNodeFlash", ...] = ()
    # HAJ-189 — Phase 2b: arrows + damage tinting + mini-map prep.
    # Body damage tinting reads body_a.region_damage; the band
    # classification lives on the BodyView itself via damage_bands so
    # the renderer doesn't re-classify per region per frame.
    arrows:            tuple["ArrowView", ...] = ()
    mini_map:          Optional["MiniMapView"] = None


# ---------------------------------------------------------------------------
# HAJ-188 — GRIP NODES + EDGES + STATE-CHANGE FLASHES (Sections 2.3, 2.6)
#
# Phase 2a brings the grip graph into the viewer so the grip war reads
# at a glance. The visual contract:
#
#   * Grip nodes — invisible by default, light up when an active grip
#     touches them. 10 named nodes per body covering every gripable
#     anatomical location (lapels, sleeves, collar, belt, thighs, head).
#   * Grip edges — line from the grasper's hand-node on judoka A to the
#     target node on judoka B (or vice versa). Owner color, depth-scaled
#     thickness, and a per-state animation token (stable / contested /
#     deepening / stripping / compromised).
#   * State-change flashes — when an edge changes state, a brief flash
#     fires on the affected grip node. Red ring on strip, green pulse
#     on deepen, yellow ring on compromise, swap animation on owner flip.
# ---------------------------------------------------------------------------

# 10 named grip-target nodes per body. Mirrors the engine's GripTarget
# enum for the standing/ne-waza target locations the simulation actually
# uses. Nodes that exist for ne-waza (head_neck, thighs) are present but
# only become visible when a grip lands on them — Phase 2a doesn't
# special-case ne-waza targeting; later phases pin osaekomi/submission
# state to the same nodes.
GRIP_NODE_IDS: tuple[str, ...] = (
    "left_lapel",   "right_lapel",
    "left_sleeve",  "right_sleeve",
    "back_collar",  "side_collar",
    "belt",
    "left_thigh",   "right_thigh",
    "head_neck",
)


# Grip-target string (lowercase, matches engine GripTarget.value or our
# normalised form) → display node id. Engine uses some legacy / ne-waza
# spellings (e.g. "neck" vs "head_neck"); collapse them onto the
# 10-node display vocabulary so the viewer doesn't grow a node per
# variant.
_TARGET_TO_NODE_ID: dict[str, str] = {
    "left_lapel":    "left_lapel",
    "right_lapel":   "right_lapel",
    "left_sleeve":   "left_sleeve",
    "right_sleeve":  "right_sleeve",
    "back_collar":   "back_collar",
    "side_collar":   "side_collar",
    "belt":          "belt",
    "waist":         "belt",            # ne-waza waist grip → belt node
    "left_thigh":    "left_thigh",
    "right_thigh":   "right_thigh",
    "left_knee":     "left_thigh",      # roll knee onto thigh node
    "right_knee":    "right_thigh",
    "head":          "head_neck",
    "neck":          "head_neck",
    "left_back_gi":  "back_collar",     # rear gi grips read as back-collar
    "right_back_gi": "back_collar",
}


def target_to_node_id(target_value: str) -> Optional[str]:
    """Map an engine GripTarget value (lowercase string) to one of the
    10 display node ids. Returns None for ne-waza-only targets that
    Phase 2a doesn't render (wrists / ankles / elbows / shoulders).
    Pure function — testable without a Match."""
    return _TARGET_TO_NODE_ID.get(target_value.lower())


# Edge-state vocabulary — Section 2.3. Strings rather than an Enum so
# capture-layer outputs serialise cleanly (e.g. for the future HAJ-194
# regression that diffs viewer output against a recorded fixture).
EDGE_STATE_STABLE      = "stable"
EDGE_STATE_CONTESTED   = "contested"
EDGE_STATE_DEEPENING   = "deepening"
EDGE_STATE_STRIPPING   = "stripping"
EDGE_STATE_COMPROMISED = "compromised"


@dataclass(frozen=True)
class GripEdgeView:
    """One active grip edge as the viewer needs to draw it. Per-tick.

    `edge_id` is the engine edge's `id()` so the renderer can correlate
    across consecutive snapshots (state-change flashes need the previous
    snapshot's edge for the same id). The id is stable for the
    lifetime of the edge — when the engine drops an edge and creates a
    new one, the id changes, which is exactly the signal the renderer
    uses for "switched ownership" detection.

    `depth` is the continuous 0.0–1.0 modifier from GripDepth (Section
    2.3 thickness mapping is linear: 1px at 0.0 → 6px at 1.0).
    """
    edge_id:         int
    grasper_id:      str
    grasper_identity: str          # Identity.BLUE / Identity.WHITE
    grasper_part:    str           # 'left_hand' / 'right_hand'
    target_id:       str
    target_identity: str
    target_node:     str           # one of GRIP_NODE_IDS
    target_raw:      str           # engine GripTarget.value (for debug / detail)
    depth:           float         # 0.0–1.0
    state:           str           # one of EDGE_STATE_*


# Grip-node flash kinds — Section 2.6.
NODE_FLASH_STRIPPED    = "STRIPPED"     # red ring, ~400ms at 1×
NODE_FLASH_DEEPENED    = "DEEPENED"     # green pulse, brief
NODE_FLASH_COMPROMISED = "COMPROMISED"  # yellow ring, ~600ms at 1×
NODE_FLASH_SWITCHED    = "SWITCHED"     # owner-flip swap, ~300ms at 1×


@dataclass(frozen=True)
class GripNodeFlash:
    """A grip-node flash firing this tick. The renderer decays it over
    the appropriate wall-clock window scaled by playback rate.

    `target_id` identifies which body owns the node (the body being
    gripped — flashes paint on the *target* node, not the grasper hand).
    `node_id` is one of GRIP_NODE_IDS. `prev_owner_identity` /
    `new_owner_identity` are populated for SWITCHED flashes."""
    tick:                 int
    kind:                 str
    target_id:            str
    target_identity:      str
    node_id:              str
    prev_owner_identity:  Optional[str] = None
    new_owner_identity:   Optional[str] = None


# Animation timing for grip cues, at 1× playback. Matches Section 2.6.
NODE_FLASH_STRIPPED_S:    float = 0.4
NODE_FLASH_DEEPENED_S:    float = 0.4
NODE_FLASH_COMPROMISED_S: float = 0.6
NODE_FLASH_SWITCHED_S:    float = 0.3


def _node_flash_base_duration(kind: str) -> float:
    return {
        NODE_FLASH_STRIPPED:    NODE_FLASH_STRIPPED_S,
        NODE_FLASH_DEEPENED:    NODE_FLASH_DEEPENED_S,
        NODE_FLASH_COMPROMISED: NODE_FLASH_COMPROMISED_S,
        NODE_FLASH_SWITCHED:    NODE_FLASH_SWITCHED_S,
    }.get(kind, 0.4)


# ---------------------------------------------------------------------------
# HAJ-189 — INTENT/ACTUAL ARROWS + DAMAGE TINTING + MINI-MAP (Sections
# 2.2, 2.4, 2.11)
# ---------------------------------------------------------------------------

# Arrow kinds — gray ghost intent vs solid identity-tinted actual.
ARROW_KIND_INTENT = "INTENT"
ARROW_KIND_ACTUAL = "ACTUAL"


@dataclass(frozen=True)
class ArrowView:
    """One per (judoka, kind). Vector is in mat-coordinate units (the
    same units the engine uses for force × direction). Renderer
    scales to pixels via `arrow_pixel_length`. The arrow originates
    near the judoka's CoM and points along (vec_x, vec_y).

    `magnitude` is the |vector| precomputed so tests + renderer don't
    need to recompute. Length encodes attempted (intent) or delivered
    (actual) force magnitude per Section 2.4."""
    judoka_name:     str
    judoka_identity: str
    kind:            str          # ARROW_KIND_INTENT / ARROW_KIND_ACTUAL
    vec_x:           float
    vec_y:           float
    magnitude:       float


# Damage tinting bands — Section 2.2. Boundaries are wear thresholds
# (0.0 = fresh, 1.0 = cooked). Discrete bands; render layer maps each
# band to a red mix amount.
DAMAGE_HEALTHY     = "healthy"
DAMAGE_WORKED      = "worked"
DAMAGE_COMPROMISED = "compromised"
DAMAGE_CRITICAL    = "critical"

# Thresholds — anything < WORKED_MIN is healthy, etc. Tunable in one
# place; calibration sweeps in HAJ-195 may shift them.
DAMAGE_BAND_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (0.25, DAMAGE_WORKED),
    (0.50, DAMAGE_COMPROMISED),
    (0.75, DAMAGE_CRITICAL),
)
# Red-mix per band, used by both the test layer (asserting band
# classification) and the render layer (computing tint). Healthy = 0.
DAMAGE_BAND_RED_MIX: dict[str, float] = {
    DAMAGE_HEALTHY:     0.00,
    DAMAGE_WORKED:      0.25,
    DAMAGE_COMPROMISED: 0.50,
    DAMAGE_CRITICAL:    0.85,    # 75-100% range; pulse in renderer
}


def damage_band(value: float) -> str:
    """Classify a 0.0-1.0 wear value into one of the four bands. Pure
    function; tested directly so calibration changes can pin the
    exact band boundaries.

    Bands (Section 2.2): healthy < 0.25, worked [0.25, 0.5),
    compromised [0.5, 0.75), critical >= 0.75."""
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
    """Section 2.2 — saturation/luminance shift toward red, not a
    pure hue replacement. Identity color is preserved.

    Implementation: linear interpolation between the base RGB and a
    deep red anchor. White (235, 235, 240) walks through pink to red.
    Blue (90, 140, 230) walks through purple to dark red. Pure
    function so tests can pin exact values per band."""
    if red_mix <= 0.0:
        return base_rgb
    mix = max(0.0, min(1.0, red_mix))
    # Anchor: a saturated red that isn't pure (255, 0, 0) so the blend
    # doesn't go neon. Slight orange-red so heavily-damaged regions
    # read as 'badly hurt' rather than 'video-game red'.
    anchor = (220, 60, 50)
    r = int(round(base_rgb[0] * (1 - mix) + anchor[0] * mix))
    g = int(round(base_rgb[1] * (1 - mix) + anchor[1] * mix))
    b = int(round(base_rgb[2] * (1 - mix) + anchor[2] * mix))
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


@dataclass(frozen=True)
class MiniMapView:
    """Section 2.11 — top-down mat schematic. Captures the geometry
    + per-fighter positions and recent-movement tail so the renderer
    can paint the corner widget without recomputing geometry per
    frame. Tail length is bounded to keep snapshots compact."""
    contest_half_m:   float           # half-side of contest area in meters
    safety_half_m:    float           # half-side of safety boundary
    a_position:       tuple[float, float]
    b_position:       tuple[float, float]
    a_identity:       str
    b_identity:       str
    a_tail:           tuple[tuple[float, float], ...]    # recent positions
    b_tail:           tuple[tuple[float, float], ...]
    a_near_edge:      bool             # for boundary-approach pulse
    b_near_edge:      bool


# Mini-map geometry — pulled from match.MAT_HALF_WIDTH (4.0) plus the
# usual safety border; if the engine doesn't expose them, fall back to
# IJF-reference values. The viewer is forgiving here because mat geom
# changes are rare and a default lets tests + headless runs work.
MINI_MAP_CONTEST_HALF_M_DEFAULT: float = 4.0
MINI_MAP_SAFETY_HALF_M_DEFAULT:  float = 7.0   # contest + 3m safety per IJF
MINI_MAP_TAIL_LENGTH:            int   = 12
MINI_MAP_EDGE_THRESHOLD_M:       float = 0.75  # within this many m of edge → pulse


# ---------------------------------------------------------------------------
# CAPTURE — pure read of Match state per tick.
# ---------------------------------------------------------------------------
def _capture_body(judoka, identity_tag: str, sub_loop: SubLoopState,
                  position: Position) -> BodyView:
    state = judoka.state
    body  = state.body
    # Per-region damage = max(fatigue, injury_severity) across the
    # mapped engine parts. Phase 1 doesn't render this; the field is
    # captured so the snapshot is forward-compat with Phase 2 tinting.
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


# Engine events that warrant a referee/score flash. Ordering matters
# only for stable per-tick output; the renderer paints all of them on
# the firing tick.
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
    """Detect a hansoku-make resolution this tick. The engine routes it
    through MATCH_ENDED with method='hansoku-make' rather than a
    dedicated event_type, so we synthesise a flash from the end event
    when present. Without this synthesis the red card from Section 2.7
    wouldn't fire visibly."""
    for ev in events:
        if ev.event_type != "MATCH_ENDED":
            continue
        data = ev.data or {}
        if data.get("method") != "hansoku-make":
            continue
        winner = data.get("winner")
        # The loser is the one who just got hansoku-make'd. We don't
        # have a direct field for them on MATCH_ENDED; the renderer
        # can still paint a centered card without a target name.
        return RefereeFlash(
            tick=ev.tick, kind=FLASH_HANSOKU, target=None,
            detail=f"loser_of:{winner}" if winner else None,
        )
    return None


def _capture_grip_edges(
    match, events, identity_for: dict[str, str],
) -> tuple[tuple["GripEdgeView", ...], frozenset[int], frozenset[int]]:
    """Extract a frozen GripEdgeView per active engine edge plus the
    sets of edge ids that deepened / stripped this tick (used for
    state derivation and flash synthesis). Returns
    (edges, deepened_ids, stripped_or_degraded_ids).

    `identity_for` maps fighter name → Identity tag (BLUE / WHITE) so
    edges carry the visual identity directly without re-deriving.

    Pure read of `match.grip_graph` and the per-tick events list; no
    mutation, no engine-side calls."""
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
            # Ne-waza-only target Phase 2a doesn't render. Skip; the
            # edge still exists in the engine but has no display node.
            continue
        # State derivation. Compromised wins over deepening / stripping
        # because a SLIPPING grip is structurally broken regardless of
        # what's happening to it this tick (Section 2.3).
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
        # Only RIGHT_HAND / LEFT_HAND grasping makes display sense in
        # Phase 2a (the spec's hand-node → body-node grammar). Other
        # graspers (e.g. ne-waza wrist-grip) collapse onto the same
        # left/right hand of the grasper for visual purposes.
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
    cur_edges: tuple["GripEdgeView", ...],
    deepened_ids: frozenset[int],
    degraded_ids: frozenset[int],
    prev_view: Optional["Phase1ViewState"],
) -> tuple["GripNodeFlash", ...]:
    """Derive per-tick node flashes from (this tick's events + diff
    against prev snapshot). Pure function — testable without pygame.

    Flash kinds (Section 2.6):
      * DEEPENED  — fires when a GRIP_DEEPEN event names an edge.
      * STRIPPING / fully-stripped — STRIPPED flash fires when a
        GRIP_STRIPPED or GRIP_BREAK event fires (edge gone from graph),
        OR when an edge's depth degraded to SLIPPING this tick (which
        the spec calls 'compromised' visually but the user-visible cue
        is still red — the grip is on its way out).
      * COMPROMISED — fires when an edge *enters* SLIPPING (was alive
        with depth > SLIPPING last tick, is SLIPPING now). Requires
        prev_view; without it we can't distinguish 'just compromised'
        from 'still compromised', so we skip rather than spam.
      * SWITCHED — fires when the same display target_node is now
        owned by the opposite identity vs the previous tick. Requires
        prev_view.
    """
    flashes: list[GripNodeFlash] = []
    cur_by_id = {e.edge_id: e for e in cur_edges}

    # Deepened: directly from this tick's deepen events.
    for e in cur_edges:
        if e.edge_id in deepened_ids:
            flashes.append(GripNodeFlash(
                tick=tick, kind=NODE_FLASH_DEEPENED,
                target_id=e.target_id,
                target_identity=e.target_identity,
                node_id=e.target_node,
            ))

    # Stripped: GRIP_STRIPPED / GRIP_BREAK events (edge no longer in
    # graph this tick). Pull target node from prev snapshot since the
    # edge is already gone from cur_edges.
    prev_by_id: dict[int, GripEdgeView] = {}
    if prev_view is not None:
        prev_by_id = {e.edge_id: e for e in prev_view.grip_edges}
    for ev in events:
        if ev.event_type not in ("GRIP_STRIPPED", "GRIP_BREAK"):
            continue
        # The engine doesn't currently embed edge_id on GRIP_STRIPPED /
        # GRIP_BREAK events, so we fall back to "any edge that vanished
        # between prev and current". That's lossy but correct in the
        # common case of one strip per tick.
        for eid, prev_e in prev_by_id.items():
            if eid in cur_by_id:
                continue
            flashes.append(GripNodeFlash(
                tick=tick, kind=NODE_FLASH_STRIPPED,
                target_id=prev_e.target_id,
                target_identity=prev_e.target_identity,
                node_id=prev_e.target_node,
            ))
        # Avoid double-firing: only one stripped event in the loop is
        # enough to cover all vanished edges this tick.
        break

    # Compromised: edge entered SLIPPING this tick. Need prev to detect.
    if prev_view is not None:
        for e in cur_edges:
            if e.state != EDGE_STATE_COMPROMISED:
                continue
            prev_e = prev_by_id.get(e.edge_id)
            if prev_e is None or prev_e.state == EDGE_STATE_COMPROMISED:
                # New grip that started SLIPPING (rare), or already
                # compromised last tick — no fresh flash.
                continue
            flashes.append(GripNodeFlash(
                tick=tick, kind=NODE_FLASH_COMPROMISED,
                target_id=e.target_id,
                target_identity=e.target_identity,
                node_id=e.target_node,
            ))

    # Switched ownership: same (target_id, target_node) is now held by
    # the opposite identity. Detect by indexing prev edges by
    # (target_id, target_node).
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


def capture_phase1_view(
    match, tick: int, events,
    prev_view: Optional["Phase1ViewState"] = None,
) -> Phase1ViewState:
    """Build a frozen Phase1ViewState from live Match state. Pure read;
    never mutates anything. Called once per tick from Phase1Renderer.update.

    Section 3.1 commitment: this function reads from the same per-tick
    state windows the narration module reads. It does not infer or
    invent any state. Anything visible in the Phase 1 viewer is
    derivable from (match @ tick T, events fired in T-1..T).

    `prev_view` is the previous tick's snapshot (or None for the first
    tick). It enables HAJ-188 grip-state diff cues — COMPROMISED and
    SWITCHED-ownership flashes need to compare against prev. Without
    it we still capture per-event cues (DEEPENED, STRIPPED) cleanly."""
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

    # Text bursts: every event with a description becomes a burst at
    # this tick. This is the structural form of the 1:1 invariant —
    # the prose log layer reads the same description fields, so by
    # construction no engine event with a prose line is missed by the
    # viewer. Bursts queue in event order; the renderer pops them one
    # at a time and animates fade-in/hold/fade-out per Section 2.13.
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

    # Mat coordinates + era. Engine carries CoM directly; no era field
    # yet, so capture None and let Phase 2 (HAJ-189 prep) populate.
    mat_a = tuple(match.fighter_a.state.body_state.com_position)
    mat_b = tuple(match.fighter_b.state.body_state.com_position)
    era = getattr(match, "era_stamp", None)
    ruleset = getattr(match, "ruleset_version", None)

    # HAJ-188 — grip edges + state-change flashes.
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

    # HAJ-189 — intent + actual arrows (Section 2.4).
    arrows = _capture_arrows(match, identity_for)

    # HAJ-189 — mini-map (Section 2.11).
    mini_map = _capture_mini_map(
        match, body_a, body_b, identity_for, prev_view,
    )

    return Phase1ViewState(
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


def _capture_arrows(
    match, identity_for: dict[str, str],
) -> tuple[ArrowView, ...]:
    """Pull per-fighter intent + actual force vectors from Match's
    HAJ-189 storage and convert to ArrowViews. A zero-magnitude
    vector emits no arrow — the spec's 'fade entirely when no active
    intent' is structural: no view, no draw, no flash.

    Match exposes `_intent_force` and `_actual_force` dicts keyed by
    fighter name; both reset to zero at the top of each tick and
    accumulate via _compute_net_force_on. Tolerant of older Match
    versions that lack these attrs (returns empty tuple)."""
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
    prev_view: Optional[Phase1ViewState],
) -> MiniMapView:
    """Pull mat geometry + per-fighter positions and recent-movement
    tail. Tail walks the prev_view chain backwards to MINI_MAP_TAIL_LENGTH
    snapshots so the mini-map renders the same trail across review-mode
    scrubbing as it did live."""
    contest_half = float(getattr(
        match, "MAT_HALF_WIDTH", MINI_MAP_CONTEST_HALF_M_DEFAULT,
    ) or MINI_MAP_CONTEST_HALF_M_DEFAULT)
    safety_half = contest_half + 3.0   # IJF safety border is 3m beyond contest
    a_pos = body_a.com_position
    b_pos = body_b.com_position
    # Tail = previous N positions, oldest-first. Built by appending the
    # prev tick's position onto the prev tick's tail and truncating.
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
    """Within MINI_MAP_EDGE_THRESHOLD_M of any contest-area boundary?
    Used by the mini-map's boundary-approach pulse cue."""
    x, y = pos
    margin = contest_half - max(abs(x), abs(y))
    return margin <= MINI_MAP_EDGE_THRESHOLD_M


# ---------------------------------------------------------------------------
# ANIMATION TIMING — Section 3.5
#
# All durations Phase 1 declares are at 1× playback. The renderer
# scales them by playback rate so a 0.5× scrub stretches them 2× and a
# 2× scrub halves them. Pure function, easily unit-tested.
# ---------------------------------------------------------------------------
def scaled_duration(base_seconds: float, playback_rate: float) -> float:
    """Section 3.5 — scale a 1×-playback animation duration to the
    current playback rate. Defensive against zero / negative rates
    (clamps to a tiny positive so cues still resolve eventually)."""
    rate = max(1e-3, float(playback_rate))
    return float(base_seconds) / rate


# Visual cue base durations at 1× playback. Section 2.6 / 2.7 / 2.13
# guidance. Adjustable in one place so future calibration can tune
# without touching the renderer.
TEXT_BURST_FADE_IN_S:    float = 0.4
TEXT_BURST_HOLD_S:       float = 1.4
TEXT_BURST_FADE_OUT_S:   float = 0.4
TEXT_BURST_MIN_VISIBLE_S: float = 0.8   # Section 2.13 minimum

MATTE_BANNER_S:   float = 1.6
HAJIME_BANNER_S:  float = 0.9
IPPON_SWEEP_S:    float = 1.2
SCORE_FLASH_S:    float = 0.7
SHIDO_FLASH_S:    float = 0.6
HANSOKU_FLASH_S:  float = 1.4


# ---------------------------------------------------------------------------
# RENDERER — pygame implementation.
#
# Phase 1 keeps the visual to the bare minimum that Section 2 commits
# to: anatomical bodies (boxed-region diagrams), match clock + score
# panel at the top, text burst at the bottom, screen flash on
# referee/score events. No grips, no arrows, no damage tinting yet.
#
# The renderer is a Push-style Renderer (Match owns the loop). Driver
# style (HAJ-126 pattern, owns wall-clock loop for pause/step/scrub)
# can come later if needed; Phase 1 demonstrates the data contract
# first, polish later (Section 4 — pygame is throwaway-OK).
# ---------------------------------------------------------------------------
WINDOW_W: int = 1280
WINDOW_H: int = 800
PANEL_TOP_H: int = 90       # match clock + score panel
PANEL_BOTTOM_H: int = 84    # text burst caption strip
FOOTER_H: int = 24          # speed + keybinding hint

# HAJ-189 follow-up — layout reversal per session feedback.
# Centre pane = top-down mat view (the diagnostic centerpiece). Two
# corner anatomical panels frame it, one per fighter, showing grip
# nodes + damage tinting + stamina at a glance. The original
# anatomical-centerpiece layout (HAJ-187/188/189 first cut) lost the
# 'sense of the match' — spatial information reads it; anatomy is
# detail-on-demand.
ANATOMY_PANEL_W: int = 280
ANATOMY_PANEL_TOP_Y: int = PANEL_TOP_H
ANATOMY_PANEL_H: int = WINDOW_H - PANEL_TOP_H - PANEL_BOTTOM_H - FOOTER_H

CENTRE_PANE_X: int = ANATOMY_PANEL_W
CENTRE_PANE_Y: int = PANEL_TOP_H
CENTRE_PANE_W: int = WINDOW_W - 2 * ANATOMY_PANEL_W
CENTRE_PANE_H: int = ANATOMY_PANEL_H

BODY_AREA_H: int = ANATOMY_PANEL_H   # legacy alias for older helpers

# Top-down mat constants — central pane geometry. The mat fills the
# pane minus a margin. px_per_m derived from MAT_HALF_WIDTH at draw
# time so both contest area and safety border fit.
TOPDOWN_PAD: int = 20
SAFETY_HALF_M_DEFAULT: float = 7.0    # contest 4m + 3m IJF safety border
COL_MAT_SAFETY = (148, 110,  74)
COL_MAT_CONTEST = (188, 154, 100)
COL_MAT_GRID    = ( 60,  64,  74)
COL_KUZUSHI     = (255,  95,  60)

# Hand offsets in body frame (meters). Mirrors the old top-down
# match_viewer.py constants — hands extend 30cm forward of CoM and
# 22cm to either side. Used by the centre pane to place hand dots
# and to anchor grip lines on the grasper hand.
HAND_FORWARD_M: float = 0.30
HAND_LATERAL_M: float = 0.22


def _topdown_hand_positions_mat(
    com: tuple[float, float], facing: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return (left_hand, right_hand) positions in mat coords given
    a CoM and a facing unit vector. Body-frame +x = facing; body
    +y (left side) = facing rotated 90° CCW. Same convention as the
    legacy top-down match_viewer.py — keep them aligned so anyone
    cross-referencing the two viewers reads consistent geometry."""
    cx, cy = com
    fx, fy = facing
    perp_x, perp_y = -fy, fx   # 90° CCW
    forward = (fx * HAND_FORWARD_M, fy * HAND_FORWARD_M)
    lateral = (perp_x * HAND_LATERAL_M, perp_y * HAND_LATERAL_M)
    left  = (cx + forward[0] + lateral[0], cy + forward[1] + lateral[1])
    right = (cx + forward[0] - lateral[0], cy + forward[1] - lateral[1])
    return left, right


# Which display nodes anchor at the *opponent's hand* (sleeve grips
# travel hand-to-hand) vs at the opponent's torso/CoM (lapel/collar
# /belt sit on the gi over the body). Determines where the centre
# pane's grip line terminates so the visual reads like real grip
# geometry, not abstract "fighter A is gripping fighter B."
_TARGET_NODE_ANCHOR_HAND: dict[str, str] = {
    "left_sleeve":  "left_hand",
    "right_sleeve": "right_hand",
}


def owned_hands_by_grasper(grip_edges) -> dict[str, set[str]]:
    """Index grip edges by grasper_id → set of grasper hand parts
    that own at least one active edge. Used by the centre-pane
    renderer to brighten gripping hands and by tests that assert
    which hand reads as gripping at a given tick. Pure function."""
    out: dict[str, set[str]] = {}
    for e in grip_edges:
        out.setdefault(e.grasper_id, set()).add(e.grasper_part)
    return out

# Identity colours. Blue judoka is straight blue; white judoka is
# off-white with a dark outline so it reads against the background.
COL_BG          = ( 18,  20,  26)
COL_PANEL       = ( 30,  34,  44)
COL_PANEL_LINE  = ( 70,  78,  96)
COL_TEXT        = (235, 235, 240)
COL_TEXT_DIM    = (160, 165, 180)
COL_BLUE        = ( 90, 140, 230)
COL_WHITE       = (235, 235, 240)
COL_WHITE_LINE  = ( 60,  64,  76)
COL_FLASH_IPPON   = (255, 220, 110)
COL_FLASH_SCORE   = (255, 230, 140)
COL_FLASH_SHIDO   = (240, 200,  60)
COL_FLASH_HANSOKU = (220,  60,  60)
COL_FLASH_MATTE   = (180,  60,  60)
COL_FLASH_HAJIME  = ( 80, 180, 100)

# Body region polygon layout. Each region is rendered as a simple
# rectangle anchored to a central body axis. Keeping it diagrammatic
# (not figurative) is intentional per Section 2.1 — anatomical chart,
# not figure drawing.
@dataclass(frozen=True)
class _RegionRect:
    name:    str
    dx:      float       # offset from body centre, in body-units
    dy:      float       # vertical offset (0 = top of head)
    w:       float
    h:       float


# 19+1 boxed regions per body. Body-units are scaled to pixels at
# render time so the same layout fits any window size. Ordering is
# top-down so the renderer can z-sort painters' algorithm naturally.
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


def _identity_color(identity_tag: str) -> tuple[int, int, int]:
    return COL_BLUE if identity_tag == Identity.BLUE else COL_WHITE


def _identity_outline(identity_tag: str) -> Optional[tuple[int, int, int]]:
    return COL_WHITE_LINE if identity_tag == Identity.WHITE else None


# Body silhouette positioning per position state. Tachiwaza: bodies
# face each other, upright, modest separation. Transitional: leaned in,
# closer (mid-throw beat). Ne-waza: bodies stack vertically (top
# fighter atop the bottom fighter), rotated to read as ground work.
# Section 2.1 — repositioning is informational, not spatially accurate.
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
        # Ne-waza: rotate the body 90° (lying on side). Swap x/y of the
        # offset and the dimensions.
        cx = self.centre_xy[0] + int(r.dy * u)
        cy = self.centre_xy[1] + int(r.dx * u)
        w = max(2, int(r.h * u))
        h = max(2, int(r.w * u))
        return (cx - w // 2, cy - h // 2, w, h)


# HAJ-188 — grip-node positions in body-units (dx, dy), measured from
# the top of the head outwards. Mirrors the chest / forearm / thigh
# anatomy used in _BODY_LAYOUT so nodes land on the rendered region
# they correspond to. Hand-nodes (left_hand, right_hand) are reused
# for grasper-side rendering — same position as the hand region.
_GRIP_NODE_POS_BODY_UNITS: dict[str, tuple[float, float]] = {
    # Standing-grip targets — placed on chest / forearm / belt regions.
    "left_lapel":   (-0.25, 0.95),
    "right_lapel":  (+0.25, 0.95),
    "left_sleeve":  (-0.70, 1.32),
    "right_sleeve": (+0.70, 1.32),
    "back_collar":  ( 0.00, 0.55),    # behind / above the neck
    "side_collar":  (+0.30, 0.65),    # near right shoulder line
    "belt":         ( 0.00, 1.82),
    # Ne-waza targets — exist but only light up when gripped.
    "left_thigh":   (-0.28, 2.15),
    "right_thigh": (+0.28, 2.15),
    "head_neck":    ( 0.00, 0.10),
    # Hand-nodes (grasper side) — same as the hand region centres.
    "left_hand":    (-0.72, 1.75),
    "right_hand":   (+0.72, 1.75),
}


def grip_node_screen_xy(
    node_id: str, pose: "_BodyPose",
) -> Optional[tuple[int, int]]:
    """Resolve a grip-node id to screen coordinates given a body pose.
    Returns None for unknown ids. Pure function so tests can verify
    layout without pygame."""
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


def _layout_bodies(position_state: str) -> tuple[_BodyPose, _BodyPose]:
    """Choose pose centres + body-unit scale per Phase 1 position
    bucket. Pure function — testable without pygame."""
    body_unit = 60
    centre_y = PANEL_TOP_H + BODY_AREA_H // 2 - 90
    if position_state == NE_WAZA:
        # Stacked: blue on top, white on bottom; both rotated.
        body_unit = 50
        cx = WINDOW_W // 2
        return (
            _BodyPose((cx - 90, centre_y), body_unit, rotated_90=True),
            _BodyPose((cx + 90, centre_y), body_unit, rotated_90=True),
        )
    if position_state == TRANSITIONAL:
        # Closer + slightly off-vertical to read as mid-throw.
        body_unit = 60
        return (
            _BodyPose((WINDOW_W // 2 - 95, centre_y), body_unit, rotated_90=False),
            _BodyPose((WINDOW_W // 2 + 95, centre_y), body_unit, rotated_90=False),
        )
    # Tachiwaza default — facing each other, ~3.5 body-units apart.
    return (
        _BodyPose((WINDOW_W // 2 - 180, centre_y), body_unit, rotated_90=False),
        _BodyPose((WINDOW_W // 2 + 180, centre_y), body_unit, rotated_90=False),
    )


# ---------------------------------------------------------------------------
# TEXT BURST QUEUE — drives the bottom-of-viewer caption.
#
# Every captured TextBurst gets pushed onto the queue at update() time;
# the active burst displays for `scaled_duration(hold + fades, rate)`
# before the next pops. Section 2.13 minimum-visibility floor is honored
# (the queue won't pop a burst that hasn't been visible for at least
# TEXT_BURST_MIN_VISIBLE_S at 1× playback, scaled).
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
        """Advance the queue using the supplied wall-clock timestamp.
        Separated from `tick()` so tests can drive it deterministically."""
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
            # No follower — let the active burst keep displaying until
            # its full lifetime expires, then clear.
            if elapsed >= self._full_lifetime():
                self._active = None
            return
        # Successor is waiting — pop after hold completes (full lifetime
        # minus fade-out so the successor's fade-in overlaps the
        # outgoing burst's fade-out).
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
# DEFAULT PLAYBACK RATE
#
# 0.5 tps = each engine tick takes ~2 seconds of wall clock. Slow
# enough that someone learning the visual vocabulary can actually read
# what changed (grip state, score events, position transitions) before
# the next tick lands. Per session feedback May 2026: faster defaults
# are unreadable; advanced users speed up with `+`. Mirrors the
# existing match_viewer.py default so the two viewers feel consistent.
# ---------------------------------------------------------------------------
DEFAULT_PLAYBACK_RATE: float = 1.25
MIN_PLAYBACK_RATE:     float = 0.05    # 1 tick per 20s — slow study mode
MAX_PLAYBACK_RATE:     float = 8.0     # 8 ticks/s — too fast to read on purpose
PLAYBACK_STEP_FACTOR:  float = 1.5


# ---------------------------------------------------------------------------
# PYGAME RENDERER
#
# Throwaway-OK; the visual language is permanent, the pygame code is
# interim per Section 4. Keep the impl small.
#
# Driver-style: the renderer owns the wall-clock loop so it can pace
# the engine, accept keyboard input for speed scrub / pause / quit, and
# render multiple frames per tick so flashes and burst fades read as
# continuous animation. Match.run() detects this via drives_loop() and
# hands control to run_interactive(self).
# ---------------------------------------------------------------------------
class Phase1AnatomicalRenderer:
    """Phase 1 viewer — anatomical bodies, clock, score panel, text
    burst captioning, basic referee/score event flashes. Driver-style
    Renderer; owns the wall-clock loop for pacing + speed controls."""

    def __init__(self, playback_rate: float = DEFAULT_PLAYBACK_RATE) -> None:
        import pygame  # noqa: F401  (validate dep at construction)
        self._playback_rate = max(
            MIN_PLAYBACK_RATE, min(MAX_PLAYBACK_RATE, float(playback_rate)),
        )
        self._initial_rate = self._playback_rate
        self._screen = None
        self._clock = None
        self._font_small = None
        self._font_med   = None
        self._font_big   = None
        self._open = True
        self._paused = False
        self._step_request = False
        self._snapshots: list[Phase1ViewState] = []
        self._burst_queue = TextBurstQueue(self._playback_rate)
        # Active flashes: (RefereeFlash, started_wall_seconds, base_duration)
        self._active_flashes: list[tuple[RefereeFlash, float, float]] = []
        # HAJ-188 — node flashes ride alongside but decay per kind.
        self._active_node_flashes: list[
            tuple[GripNodeFlash, float, float]
        ] = []
        self._latest_snap: Optional[Phase1ViewState] = None

    # --- Renderer protocol --------------------------------------------------
    def start(self) -> None:
        import pygame
        pygame.init()
        pygame.display.set_caption("Hajime — Phase 1 viewer (HAJ-187)")
        self._screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self._clock = pygame.time.Clock()
        self._font_small = pygame.font.SysFont("Consolas", 14)
        self._font_med   = pygame.font.SysFont("Consolas", 18, bold=True)
        self._font_big   = pygame.font.SysFont("Consolas", 32, bold=True)

    def update(self, tick: int, match: "Match", events) -> None:
        """Capture-only push hook. Called from inside Match.step() (which
        run_interactive drives). The wall-clock pacing + rendering loop
        runs in run_interactive between step calls."""
        snap = capture_phase1_view(
            match, tick, events, prev_view=self._latest_snap,
        )
        self._snapshots.append(snap)
        self._latest_snap = snap
        self._burst_queue.push_many(snap.text_bursts)
        now_wall = time.monotonic()
        for f in snap.referee_flashes:
            base = _flash_base_duration(f.kind)
            self._active_flashes.append((f, now_wall, base))
        # HAJ-188 — node flashes ride alongside referee flashes; the
        # render layer reads them out of _active_node_flashes during
        # _render_frame and decays them over their per-kind lifetime.
        for nf in snap.grip_node_flashes:
            base = _node_flash_base_duration(nf.kind)
            self._active_node_flashes.append((nf, now_wall, base))

    def stop(self) -> None:
        import pygame
        if pygame.get_init():
            pygame.quit()
        self._open = False

    def is_open(self) -> bool:
        return self._open

    # --- Driver-style hooks (HAJ-126 pattern) -------------------------------
    def drives_loop(self) -> bool:
        return True

    def run_interactive(self, match: "Match") -> None:
        """Own the wall-clock loop. Sleep between engine ticks so the
        viewer feels readable, render multiple frames per tick so cues
        animate smoothly, accept keyboard input for pause / step /
        speed scrub. Mirrors the structure of match_viewer.py's
        PygameMatchRenderer.run_interactive but trimmed to Phase 1's
        smaller surface.

        After the engine reports done, calls match.end() (so the prose
        summary fires once) then enters a linger loop that holds the
        final frame on screen until the user explicitly quits. Without
        the linger, the window auto-closes the moment the match ends
        and the user never gets to read the closing beats."""
        match.begin()
        last_step = time.monotonic()
        match_resolved = False
        try:
            while self._open and not match.is_done():
                self._pump_input()
                if not self._open:
                    break
                now = time.monotonic()
                period = self._tick_period_seconds()
                # Decide whether to advance the engine this frame.
                if self._step_request:
                    self._step_request = False
                    match.step()
                    last_step = now
                elif not self._paused and (now - last_step) >= period:
                    match.step()
                    last_step = now
                # Render every frame (60 FPS cap), independent of tick
                # advancement, so flashes / burst fades animate.
                cur = time.monotonic()
                self._burst_queue.set_playback_rate(self._playback_rate)
                self._burst_queue.tick_wall(cur)
                self._cull_flashes(cur)
                if self._latest_snap is not None:
                    self._render_frame(self._latest_snap)
                self._clock.tick(60)
            # Engine done — fire end() once so the post-match prose
            # summary lands, then drop into the linger loop.
            if not match_resolved:
                match.end()
                match_resolved = True
            self._linger_after_match()
        finally:
            # If the user closed the window before match.end() ran in
            # the try-block, ensure end() still fires for the prose
            # summary. Idempotency guarded by match_resolved + the
            # _resolve_match call inside Match.end is itself idempotent
            # via match_over.
            if not match_resolved and not getattr(
                match, "match_over", False,
            ):
                try:
                    match.end()
                except Exception:
                    raise

    def _linger_after_match(self) -> None:
        """Hold the final tick on screen after the match ends. The
        user can read the closing prose burst, the score panel, the
        last grip configuration — and only quits when they press
        q / Esc / close the window. Speed controls (+/-/0) and pause
        are inert here (no engine to advance), but kept active so
        keystrokes don't feel dead. Renders at 60 FPS so any
        still-fading flashes finish their animation cleanly."""
        # Mark paused so the footer hint reads PAUSED — communicates
        # to the user that the engine isn't advancing.
        self._paused = True
        while self._open:
            self._pump_input()
            if not self._open:
                break
            cur = time.monotonic()
            self._burst_queue.set_playback_rate(self._playback_rate)
            self._burst_queue.tick_wall(cur)
            self._cull_flashes(cur)
            self._cull_node_flashes(cur)
            if self._latest_snap is not None:
                self._render_frame(self._latest_snap)
            self._clock.tick(60)

    # --- Test introspection -------------------------------------------------
    def snapshots(self) -> list[Phase1ViewState]:
        return list(self._snapshots)

    def playback_rate(self) -> float:
        return self._playback_rate

    # --- Internals ----------------------------------------------------------
    def _tick_period_seconds(self) -> float:
        """Wall-clock seconds per engine tick, derived from the current
        playback rate. 1× rate = 1 second/tick (sim is 1 tick/sec), so
        period = 1.0 / rate. Mirrors scaled_duration semantics."""
        return 1.0 / max(MIN_PLAYBACK_RATE, self._playback_rate)

    def _pump_input(self) -> None:
        import pygame
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._open = False
            elif ev.type == pygame.KEYDOWN:
                self._handle_keydown(ev)

    def _handle_keydown(self, ev) -> None:
        import pygame
        k = ev.key
        if k in (pygame.K_q, pygame.K_ESCAPE):
            self._open = False
        elif k == pygame.K_SPACE:
            self._paused = not self._paused
        elif k in (pygame.K_RIGHT, pygame.K_PERIOD):
            # Step one tick. Useful while paused.
            self._step_request = True
        elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self._playback_rate = min(
                MAX_PLAYBACK_RATE,
                self._playback_rate * PLAYBACK_STEP_FACTOR,
            )
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._playback_rate = max(
                MIN_PLAYBACK_RATE,
                self._playback_rate / PLAYBACK_STEP_FACTOR,
            )
        elif k == pygame.K_0:
            self._playback_rate = self._initial_rate

    def _cull_flashes(self, now_wall: float) -> None:
        kept: list[tuple[RefereeFlash, float, float]] = []
        for entry in self._active_flashes:
            _, started, base = entry
            if now_wall - started < scaled_duration(base, self._playback_rate):
                kept.append(entry)
        self._active_flashes = kept

    def _render_frame(self, snap: Phase1ViewState) -> None:
        """Layout (post-feedback rebuild):

            +-------------------------------------------------+
            | TOP: clock / score / shido / position state     |
            +---------+---------------------------+-----------+
            | ANATOMY |                           | ANATOMY   |
            | A       |    TOP-DOWN MAT VIEW      | B         |
            | (corner)|    (diagnostic centre)    | (corner)  |
            |         |                           |           |
            +---------+---------------------------+-----------+
            | BOTTOM: text-burst captioning                   |
            +-------------------------------------------------+
            | FOOTER: speed + keybinds                        |
            +-------------------------------------------------+

        Top-down mat view is the centerpiece because spatial info is
        what reads 'the sense of the match' — who's pressing whom,
        edge tactics, mat-zone dynamics. Anatomical panels are
        glanceable supporting detail (grip nodes lit + damage tint
        + stamina). Mini-map is dropped — the centre pane already
        renders mat geometry at higher fidelity."""
        import pygame
        screen = self._screen
        screen.fill(COL_BG)
        self._draw_top_panel(screen, snap)
        # Centre pane: top-down mat with fighter dots, grip lines
        # between them, and intent/actual force arrows projected
        # onto the mat plane.
        self._draw_topdown_pane(screen, snap)
        # Two corner anatomy panels framing the centre pane.
        self._draw_anatomy_panel(
            screen, snap.body_a, snap, x=0, side="left",
        )
        self._draw_anatomy_panel(
            screen, snap.body_b, snap,
            x=WINDOW_W - ANATOMY_PANEL_W, side="right",
        )
        self._draw_caption_strip(screen, snap)
        self._draw_active_flashes(screen, snap)
        self._draw_footer_hint(screen)
        pygame.display.flip()

    def _draw_footer_hint(self, screen) -> None:
        """Bottom-edge keybinding hint + current playback rate. Helps
        the user discover speed controls without reading the source."""
        rate = self._playback_rate
        period = 1.0 / max(MIN_PLAYBACK_RATE, rate)
        if self._paused:
            tag = "PAUSED"
        else:
            tag = f"{rate:.2f}x  ({period:.1f}s/tick)"
        hint = (
            f"{tag}    space: pause/play    →: step    +/-: speed    "
            f"0: reset    q: quit"
        )
        surf = self._font_small.render(hint, True, COL_TEXT_DIM)
        screen.blit(surf, (12, WINDOW_H - 18))

    def _draw_top_panel(self, screen, snap: Phase1ViewState) -> None:
        import pygame
        pygame.draw.rect(screen, COL_PANEL, (0, 0, WINDOW_W, PANEL_TOP_H))
        pygame.draw.line(
            screen, COL_PANEL_LINE,
            (0, PANEL_TOP_H), (WINDOW_W, PANEL_TOP_H), 1,
        )
        # Match clock — centered.
        clk = snap.clock.display
        if snap.clock.golden_score:
            clk = "GS  " + clk
        clock_surf = self._font_big.render(clk, True, COL_TEXT)
        screen.blit(clock_surf,
                    (WINDOW_W // 2 - clock_surf.get_width() // 2, 12))
        # Position-state mini-label under the clock.
        ps_surf = self._font_small.render(
            snap.position_state, True, COL_TEXT_DIM,
        )
        screen.blit(
            ps_surf,
            (WINDOW_W // 2 - ps_surf.get_width() // 2, 56),
        )
        # Score panels — left for blue, right for white.
        self._draw_score_panel(screen, snap.score_a, x=20, align_left=True)
        self._draw_score_panel(
            screen, snap.score_b, x=WINDOW_W - 20, align_left=False,
        )

    def _draw_score_panel(self, screen, score: ScorePanelView,
                          x: int, align_left: bool) -> None:
        import pygame
        col = _identity_color(score.identity)
        outline = _identity_outline(score.identity)
        name_surf = self._font_med.render(score.name, True, col)
        score_text = f"W {score.waza_ari}" + ("  IPPON" if score.ippon else "")
        score_surf = self._font_med.render(score_text, True, COL_TEXT)
        # Shido cards as stacked yellow rectangles next to the name.
        if align_left:
            screen.blit(name_surf, (x, 12))
            screen.blit(score_surf, (x, 38))
        else:
            screen.blit(name_surf, (x - name_surf.get_width(), 12))
            screen.blit(score_surf, (x - score_surf.get_width(), 38))
        if outline is not None:
            pygame.draw.line(
                screen, outline,
                (x if align_left else x - name_surf.get_width(), 30),
                (x + name_surf.get_width() if align_left else x, 30),
                1,
            )
        # Shido cards.
        card_w, card_h = 12, 16
        for i in range(min(3, score.shidos)):
            cx = (x + name_surf.get_width() + 8 + i * (card_w + 4)
                  if align_left
                  else x - name_surf.get_width() - 8 - (i + 1) * (card_w + 4))
            colour = (
                COL_FLASH_HANSOKU if score.hansoku_make
                else COL_FLASH_SHIDO
            )
            pygame.draw.rect(screen, colour, (cx, 14, card_w, card_h))

    # ------------------------------------------------------------------
    # Layout-rebuild renderers — top-down centre + corner anatomy panels.
    # ------------------------------------------------------------------
    def _topdown_transform(self, snap: Phase1ViewState):
        """Return a closure (mat_to_px, px_per_m, contest_half_m,
        safety_half_m) for the centre pane. Pulled from
        snap.mini_map.* if present (they share geometry), else
        defaults. Pure layout math; no pygame."""
        if snap.mini_map is not None:
            contest_half = snap.mini_map.contest_half_m
            safety_half  = snap.mini_map.safety_half_m
        else:
            contest_half = MINI_MAP_CONTEST_HALF_M_DEFAULT
            safety_half  = SAFETY_HALF_M_DEFAULT
        usable_w = CENTRE_PANE_W - 2 * TOPDOWN_PAD
        usable_h = CENTRE_PANE_H - 2 * TOPDOWN_PAD
        px_per_m = min(usable_w, usable_h) / (2.0 * safety_half)
        cx = CENTRE_PANE_X + CENTRE_PANE_W // 2
        cy = CENTRE_PANE_Y + CENTRE_PANE_H // 2

        def mat_to_px(mp):
            mx, my = mp
            return (cx + int(round(mx * px_per_m)),
                    cy - int(round(my * px_per_m)))

        return mat_to_px, px_per_m, contest_half, safety_half

    def _draw_topdown_pane(self, screen, snap: Phase1ViewState) -> None:
        """Centre pane — the diagnostic centerpiece. Renders mat
        geometry, fighter dots with facing, top-down grip lines
        between dots (owner-tinted, depth-thickness), kuzushi halos
        on off-balance fighters, and intent/actual force arrows
        projected onto the mat plane originating from each dot."""
        import pygame
        # Background panel.
        pygame.draw.rect(
            screen, COL_PANEL,
            (CENTRE_PANE_X, CENTRE_PANE_Y, CENTRE_PANE_W, CENTRE_PANE_H),
        )
        mat_to_px, px_per_m, contest_half, safety_half = (
            self._topdown_transform(snap)
        )
        # Safety boundary (outer dashed).
        s_min = mat_to_px((-safety_half, +safety_half))
        s_max = mat_to_px((+safety_half, -safety_half))
        pygame.draw.rect(
            screen, COL_MAT_SAFETY,
            (s_min[0], s_min[1],
             s_max[0] - s_min[0], s_max[1] - s_min[1]),
        )
        # Contest area (inner solid).
        c_min = mat_to_px((-contest_half, +contest_half))
        c_max = mat_to_px((+contest_half, -contest_half))
        pygame.draw.rect(
            screen, COL_MAT_CONTEST,
            (c_min[0], c_min[1],
             c_max[0] - c_min[0], c_max[1] - c_min[1]),
        )
        # Centre cross — quick visual reference for mat origin.
        ox, oy = mat_to_px((0.0, 0.0))
        pygame.draw.line(
            screen, COL_MAT_GRID, (ox - 8, oy), (ox + 8, oy), 1,
        )
        pygame.draw.line(
            screen, COL_MAT_GRID, (ox, oy - 8), (ox, oy + 8), 1,
        )
        # Recent-movement tails for both fighters (read off mini_map
        # capture, which already truncates to MINI_MAP_TAIL_LENGTH).
        if snap.mini_map is not None:
            self._draw_topdown_tail(
                screen, snap.mini_map.a_tail,
                _identity_color(snap.body_a.identity), mat_to_px,
            )
            self._draw_topdown_tail(
                screen, snap.mini_map.b_tail,
                _identity_color(snap.body_b.identity), mat_to_px,
            )
        # Fighter positions + facing. body.com_position is in mat
        # coords; capture stored facing on… no, capture only kept
        # com_position in BodyView. Use mat_coords_*; facing isn't
        # currently captured. The dot itself is enough at this scale.
        a_xy = mat_to_px(snap.mat_coords_a)
        b_xy = mat_to_px(snap.mat_coords_b)
        # Hand positions in mat coords for both fighters.
        a_hand_l_mat, a_hand_r_mat = _topdown_hand_positions_mat(
            snap.body_a.com_position, snap.body_a.facing,
        )
        b_hand_l_mat, b_hand_r_mat = _topdown_hand_positions_mat(
            snap.body_b.com_position, snap.body_b.facing,
        )
        hands_for: dict[str, dict[str, tuple[int, int]]] = {
            snap.body_a.name: {
                "left_hand":  mat_to_px(a_hand_l_mat),
                "right_hand": mat_to_px(a_hand_r_mat),
            },
            snap.body_b.name: {
                "left_hand":  mat_to_px(b_hand_l_mat),
                "right_hand": mat_to_px(b_hand_r_mat),
            },
        }
        com_for: dict[str, tuple[int, int]] = {
            snap.body_a.name: a_xy, snap.body_b.name: b_xy,
        }
        # Top-down grip lines: from grasper's hand → target's
        # hand-or-CoM. Sleeve grips travel hand-to-hand (the gripping
        # hand catches the sleeve cuff over the opponent's hand);
        # lapel / collar / belt / leg grips terminate at opponent CoM
        # (the rough centroid of where those targets sit on the body).
        # Owner-tinted, depth-scaled thickness. The corner anatomy
        # panels carry the full grip-state animation detail.
        for e in snap.grip_edges:
            grasper_hand_xy = hands_for.get(e.grasper_id, {}).get(
                e.grasper_part,
            )
            if grasper_hand_xy is None:
                continue
            target_anchor_hand = _TARGET_NODE_ANCHOR_HAND.get(e.target_node)
            if target_anchor_hand is not None:
                target_xy = hands_for.get(e.target_id, {}).get(
                    target_anchor_hand,
                )
            else:
                target_xy = com_for.get(e.target_id)
            if target_xy is None:
                continue
            color = _identity_color(e.grasper_identity)
            outline = _identity_outline(e.grasper_identity)
            thickness = max(1, min(6, int(round(1 + 5 * e.depth))))
            pygame.draw.line(
                screen, color, grasper_hand_xy, target_xy, thickness,
            )
            if outline is not None:
                # White-identity outline for visibility.
                pygame.draw.line(
                    screen, outline, grasper_hand_xy, target_xy, 1,
                )

        # Hand dots — drawn after grip lines so the hand sits on top
        # of its grip line endpoint. Brighter when this hand owns at
        # least one active edge; dimmer when free.
        owned_for = owned_hands_by_grasper(snap.grip_edges)
        for body in (snap.body_a, snap.body_b):
            owned = owned_for.get(body.name, set())
            for which in ("left_hand", "right_hand"):
                hand_xy = hands_for[body.name][which]
                self._draw_topdown_hand(
                    screen, hand_xy, body.identity, which in owned,
                )

        # Fighter dots — drawn after grip lines + hands so the body
        # circle sits on top of everything else.
        self._draw_topdown_fighter(
            screen, a_xy, snap.body_a.identity,
            near_edge=(snap.mini_map.a_near_edge
                       if snap.mini_map is not None else False),
        )
        self._draw_topdown_fighter(
            screen, b_xy, snap.body_b.identity,
            near_edge=(snap.mini_map.b_near_edge
                       if snap.mini_map is not None else False),
        )
        # Reuse the COM positions for arrow anchoring.
        pos_for: dict[str, tuple[int, int]] = com_for
        # Intent + actual arrows projected onto the mat plane,
        # originating from each fighter's dot.
        self._draw_topdown_arrows(screen, snap, pos_for)
        # Pane outline.
        pygame.draw.rect(
            screen, COL_PANEL_LINE,
            (CENTRE_PANE_X, CENTRE_PANE_Y, CENTRE_PANE_W, CENTRE_PANE_H),
            1,
        )

    def _draw_topdown_tail(self, screen, tail, color, mat_to_px) -> None:
        import pygame
        n = len(tail)
        if n < 2:
            return
        for i in range(1, n):
            alpha = int(40 + 180 * (i / n))
            surf = pygame.Surface((4, 4), pygame.SRCALPHA)
            surf.fill((*color, alpha))
            px = mat_to_px(tail[i])
            screen.blit(surf, (px[0] - 2, px[1] - 2))

    def _draw_topdown_hand(
        self, screen, xy: tuple[int, int],
        identity_tag: str, gripping: bool,
    ) -> None:
        """Hand dot offset from CoM along the facing direction. Bright
        when this hand owns at least one active grip edge; dimmer
        when free. Mirrors the legacy match_viewer.py vocabulary so
        anyone cross-referencing reads consistent symbols."""
        import pygame
        col = _identity_color(identity_tag)
        if not gripping:
            # Dim the colour for free hands so the eye lands on
            # active gripping hands first.
            col = tuple(c // 2 + 30 for c in col)
        pygame.draw.circle(screen, col, xy, 4)
        outline = _identity_outline(identity_tag)
        if outline is not None:
            pygame.draw.circle(screen, outline, xy, 4, 1)

    def _draw_topdown_fighter(
        self, screen, xy: tuple[int, int],
        identity_tag: str, near_edge: bool,
    ) -> None:
        import pygame
        col = _identity_color(identity_tag)
        outline = _identity_outline(identity_tag)
        pygame.draw.circle(screen, col, xy, 12)
        if outline is not None:
            pygame.draw.circle(screen, outline, xy, 12, 1)
        if near_edge:
            import math
            r = 16 + int(4 * (0.5 + 0.5 * math.sin(time.monotonic() * 5.0)))
            surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(
                surf, (*col, 160), (r + 1, r + 1), r, 2,
            )
            screen.blit(surf, (xy[0] - r - 1, xy[1] - r - 1))

    def _draw_topdown_arrows(
        self, screen, snap: Phase1ViewState,
        pos_for: dict[str, tuple[int, int]],
    ) -> None:
        """Per-fighter intent + actual arrows in the centre pane.
        Anchor at the fighter dot, with the +x screen direction
        pointing along the mat-+x axis (so a (1, 0) force vector
        points right on screen, matching mat coords)."""
        import pygame
        if not snap.arrows:
            return
        # Slight offset so up to 4 arrows don't overlap from the same
        # dot — Tori-side arrows up/right of the dot, Uke-side
        # down/left.
        offset_for: dict[str, tuple[int, int]] = {
            snap.body_a.name: (0, -4),
            snap.body_b.name: (0, +4),
        }
        for arrow in snap.arrows:
            anchor = pos_for.get(arrow.judoka_name)
            if anchor is None:
                continue
            offs = offset_for.get(arrow.judoka_name, (0, 0))
            anchor = (anchor[0] + offs[0], anchor[1] + offs[1])
            length_px = self._arrow_pixel_length(arrow.magnitude)
            self._draw_one_arrow(screen, anchor, arrow, length_px)

    # ------------------------------------------------------------------
    # Corner anatomy panels — one per fighter, glanceable.
    # ------------------------------------------------------------------
    def _draw_anatomy_panel(
        self, screen, body: BodyView, snap: Phase1ViewState,
        x: int, side: str,
    ) -> None:
        """Anatomical body silhouette inside a corner panel. Renders
        damage tinting per region, lit grip nodes (only those touched
        by an active edge), and the active node-flash overlay scaled
        down for the panel. Stamina bar at the bottom of the panel.
        Identity tint for the panel border picks left/right side."""
        import pygame
        y = ANATOMY_PANEL_TOP_Y
        # Panel background.
        pygame.draw.rect(
            screen, COL_PANEL, (x, y, ANATOMY_PANEL_W, ANATOMY_PANEL_H),
        )
        # Identity stripe down the inner edge so the panel reads as
        # 'this side is fighter X'.
        accent = _identity_color(body.identity)
        if side == "left":
            stripe_x = x + ANATOMY_PANEL_W - 4
        else:
            stripe_x = x
        pygame.draw.rect(
            screen, accent, (stripe_x, y, 4, ANATOMY_PANEL_H),
        )
        # Centre body inside the panel. body_unit_px sized to fit the
        # panel comfortably with room for the stamina bar.
        body_unit = 48
        centre_xy = (x + ANATOMY_PANEL_W // 2,
                     y + ANATOMY_PANEL_H // 2 - 60)
        pose = _BodyPose(centre_xy, body_unit, rotated_90=False)
        self._draw_body(screen, body, pose)
        # Lit grip nodes for this body.
        self._draw_anatomy_panel_grip_nodes(screen, body, snap, pose)
        # Node flashes scaled to the panel.
        now_wall = time.monotonic()
        self._draw_anatomy_panel_node_flashes(screen, body, pose, now_wall)
        # Panel border + label.
        pygame.draw.rect(
            screen, COL_PANEL_LINE,
            (x, y, ANATOMY_PANEL_W, ANATOMY_PANEL_H), 1,
        )
        label = self._font_med.render(body.name, True, accent)
        screen.blit(label, (x + 12, y + 8))

    def _draw_anatomy_panel_grip_nodes(
        self, screen, body: BodyView, snap: Phase1ViewState,
        pose: "_BodyPose",
    ) -> None:
        """Light up only the nodes that have an active edge touching
        this body. Target-side nodes get the gripper's color; this
        body's hand-nodes (when it owns a grip on the opponent) get
        its own identity colour."""
        import pygame
        for e in snap.grip_edges:
            # A node on THIS body lights up if it's the target body
            # of an edge, OR if the edge's grasper is this body and
            # the grasper hand is on this body.
            node_id = None
            tint = None
            if e.target_id == body.name:
                node_id = e.target_node
                tint = _identity_color(e.grasper_identity)
            elif e.grasper_id == body.name:
                node_id = e.grasper_part   # 'left_hand' / 'right_hand'
                tint = _identity_color(body.identity)
            if node_id is None:
                continue
            xy = grip_node_screen_xy(node_id, pose)
            if xy is None:
                continue
            pygame.draw.circle(screen, tint, xy, 5)
            pygame.draw.circle(screen, COL_PANEL_LINE, xy, 5, 1)

    def _draw_anatomy_panel_node_flashes(
        self, screen, body: BodyView, pose: "_BodyPose", now_wall: float,
    ) -> None:
        """Overlay any active node flashes for this body's nodes.
        Walks the same _active_node_flashes list as the original
        draw, filtered to flashes that fired against this judoka."""
        import pygame
        for entry in self._active_node_flashes:
            nf, started, base = entry
            if nf.target_id != body.name:
                continue
            life = scaled_duration(base, self._playback_rate)
            if life <= 0:
                continue
            t = max(0.0, min(1.0, (now_wall - started) / life))
            alpha = int(255 * (1.0 - t))
            xy = grip_node_screen_xy(nf.node_id, pose)
            if xy is None:
                continue
            color = _node_flash_color(nf.kind)
            if nf.kind == NODE_FLASH_DEEPENED:
                radius = 6 + int(8 * t)
            else:
                radius = 6 + int(14 * t)
            surf = pygame.Surface(
                (radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA,
            )
            ring = 1 if nf.kind == NODE_FLASH_DEEPENED else 2
            pygame.draw.circle(
                surf, (*color, max(0, alpha)),
                (radius + 2, radius + 2), radius, ring,
            )
            screen.blit(surf, (xy[0] - radius - 2, xy[1] - radius - 2))

    def _draw_body(self, screen, body: BodyView, pose: _BodyPose) -> None:
        """HAJ-187 anatomy + HAJ-189 damage tinting. Each region's
        engine fatigue (captured into body.region_damage) classifies
        into a band; the band's red-mix shifts the region's identity
        colour toward red without losing the underlying tint. Critical
        regions slowly pulse via a wall-clock multiplier so the eye
        catches them even on a still frame."""
        import pygame
        base_col = _identity_color(body.identity)
        outline  = _identity_outline(body.identity)
        # Per-region damage map for fast lookup.
        damage_by_region = dict(body.region_damage)
        # Critical-band pulse multiplier — 0.85 baseline ± 0.15 over
        # ~1.5s. Phase from wall clock so it ticks even when paused.
        import math
        pulse = 0.85 + 0.15 * math.sin(time.monotonic() * 4.2)
        for region in _BODY_LAYOUT:
            rect = pose.region_rect(region)
            wear = float(damage_by_region.get(region.name, 0.0) or 0.0)
            band = damage_band(wear)
            mix = DAMAGE_BAND_RED_MIX[band]
            if band == DAMAGE_CRITICAL:
                mix = mix * pulse
            tinted = tint_toward_red(base_col, mix)
            pygame.draw.rect(screen, tinted, rect)
            if outline is not None:
                pygame.draw.rect(screen, outline, rect, 1)
            else:
                # Faint divider so adjacent regions read as separate
                # bands even on the blue body. Section 2.1 — boundaries
                # between regions need to be visible at viewer-zoom.
                pygame.draw.rect(screen, COL_PANEL_LINE, rect, 1)
        # Stamina bar under each body.
        bar_x = pose.centre_xy[0] - 50
        bar_y = pose.centre_xy[1] + int(3.4 * pose.body_unit_px)
        pygame.draw.rect(screen, COL_PANEL_LINE, (bar_x, bar_y, 100, 6))
        cardio_w = max(0, min(100, int(100 * body.cardio)))
        pygame.draw.rect(screen, base_col, (bar_x, bar_y, cardio_w, 6))

    def _draw_caption_strip(self, screen, snap: Phase1ViewState) -> None:
        import pygame
        y0 = WINDOW_H - PANEL_BOTTOM_H
        pygame.draw.rect(screen, COL_PANEL, (0, y0, WINDOW_W, PANEL_BOTTOM_H))
        pygame.draw.line(
            screen, COL_PANEL_LINE, (0, y0), (WINDOW_W, y0), 1,
        )
        active = self._burst_queue.active()
        if active is None:
            return
        text = active.text
        # Truncate at the panel width.
        max_chars = max(20, (WINDOW_W - 40) // 9)
        if len(text) > max_chars:
            text = text[:max_chars - 1] + "…"
        surf = self._font_med.render(text, True, COL_TEXT)
        screen.blit(
            surf,
            (WINDOW_W // 2 - surf.get_width() // 2, y0 + PANEL_BOTTOM_H // 2 - 12),
        )
        if self._burst_queue.pending() > 0:
            badge = self._font_small.render(
                f"+{self._burst_queue.pending()}", True, COL_TEXT_DIM,
            )
            screen.blit(badge, (WINDOW_W - 40, y0 + 6))

    def _draw_active_flashes(self, screen, snap: Phase1ViewState) -> None:
        import pygame
        for entry in self._active_flashes:
            f, started, base = entry
            elapsed = time.monotonic() - started
            life = scaled_duration(base, self._playback_rate)
            if life <= 0:
                continue
            t = max(0.0, min(1.0, elapsed / life))
            alpha = int(255 * (1.0 - t))
            if f.kind == FLASH_IPPON:
                self._sweep_flash(
                    screen, COL_FLASH_IPPON, alpha, height=WINDOW_H,
                )
            elif f.kind == FLASH_HANSOKU:
                self._sweep_flash(
                    screen, COL_FLASH_HANSOKU, alpha, height=WINDOW_H,
                )
            elif f.kind == FLASH_MATTE:
                self._edge_pulse(screen, COL_FLASH_MATTE, alpha)
            elif f.kind == FLASH_HAJIME:
                self._edge_pulse(screen, COL_FLASH_HAJIME, alpha)
            elif f.kind == FLASH_WAZA_ARI:
                self._score_panel_flash(
                    screen, f.target, COL_FLASH_SCORE, alpha, snap,
                )
            elif f.kind == FLASH_SHIDO:
                self._score_panel_flash(
                    screen, f.target, COL_FLASH_SHIDO, alpha, snap,
                )

    def _sweep_flash(self, screen, color, alpha: int, height: int) -> None:
        import pygame
        if alpha <= 0:
            return
        surf = pygame.Surface((WINDOW_W, height), pygame.SRCALPHA)
        surf.fill((*color, max(0, min(180, alpha // 2))))
        screen.blit(surf, (0, 0))

    def _edge_pulse(self, screen, color, alpha: int) -> None:
        import pygame
        if alpha <= 0:
            return
        thickness = 8
        surf = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        a = max(0, min(220, alpha))
        pygame.draw.rect(
            surf, (*color, a), (0, 0, WINDOW_W, WINDOW_H), thickness,
        )
        screen.blit(surf, (0, 0))

    def _score_panel_flash(self, screen, target_name, color, alpha: int,
                           snap: Phase1ViewState) -> None:
        import pygame
        if alpha <= 0 or target_name is None:
            return
        # Highlight the appropriate side's score panel area.
        if target_name == snap.score_a.name:
            rect = (4, 4, WINDOW_W // 2 - 8, PANEL_TOP_H - 8)
        elif target_name == snap.score_b.name:
            rect = (WINDOW_W // 2 + 4, 4, WINDOW_W // 2 - 8, PANEL_TOP_H - 8)
        else:
            return
        surf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        a = max(0, min(220, alpha))
        pygame.draw.rect(surf, (*color, a), surf.get_rect(), 4)
        screen.blit(surf, (rect[0], rect[1]))

    # ------------------------------------------------------------------
    # HAJ-188 — grip layer rendering
    # ------------------------------------------------------------------
    def _draw_grip_layer(self, screen, snap: Phase1ViewState) -> None:
        """Top-of-bodies layer: grip edges → grip nodes → node flashes.
        Drawn in that order so flashes ride above edges and nodes."""
        pose_a, pose_b = _layout_bodies(snap.position_state)
        pose_for: dict[str, "_BodyPose"] = {
            snap.body_a.name: pose_a,
            snap.body_b.name: pose_b,
        }
        # Edges first (so node dots sit on top of line endpoints).
        self._draw_grip_edges(screen, snap, pose_for)
        # Active nodes — every node touched by a current edge.
        self._draw_active_grip_nodes(screen, snap, pose_for)
        # State-change flashes ride on top.
        now_wall = time.monotonic()
        self._cull_node_flashes(now_wall)
        self._draw_node_flashes(screen, snap, pose_for, now_wall)

    def _draw_grip_edges(
        self, screen, snap: Phase1ViewState,
        pose_for: dict[str, "_BodyPose"],
    ) -> None:
        import pygame
        for e in snap.grip_edges:
            grasper_pose = pose_for.get(e.grasper_id)
            target_pose  = pose_for.get(e.target_id)
            if grasper_pose is None or target_pose is None:
                continue
            hand_xy = grip_node_screen_xy(e.grasper_part, grasper_pose)
            tgt_xy  = grip_node_screen_xy(e.target_node, target_pose)
            if hand_xy is None or tgt_xy is None:
                continue
            color = _identity_color(e.grasper_identity)
            outline = _identity_outline(e.grasper_identity)
            # Section 2.3 — thickness scales linearly 1px (depth 0) →
            # 6px (depth 1.0). Round to nearest pixel; clamp to 1.
            thickness = max(1, min(6, int(round(1 + 5 * e.depth))))
            # Per-state stylisation. Stable: solid line. Contested:
            # shimmer (dashed segments offset over time). Deepening:
            # short forward dashes. Stripping: short reverse dashes.
            # Compromised: long dashes + reduced alpha.
            self._draw_edge_with_state(
                screen, hand_xy, tgt_xy, color, outline,
                thickness, e.state,
            )

    def _draw_edge_with_state(
        self, screen, p0, p1, color, outline, thickness: int, state: str,
    ) -> None:
        """Draw a single grip edge, with the state animation token
        controlling dash pattern + shimmer. Phase 2a uses pygame
        primitives — no shaders. Throwaway-OK."""
        import pygame
        if state == EDGE_STATE_STABLE:
            pygame.draw.line(screen, color, p0, p1, thickness)
            return
        if state == EDGE_STATE_COMPROMISED:
            # Long dashes — visibly broken. Lower alpha so it reads as
            # 'on its way out'.
            self._draw_dashed_line(
                screen, color, p0, p1, thickness,
                dash=10, gap=8, alpha=140,
            )
            return
        if state == EDGE_STATE_DEEPENING:
            # Forward-flow short dashes. Phase animation uses wall
            # clock so it shifts each frame (continuous motion).
            self._draw_dashed_line(
                screen, color, p0, p1, thickness,
                dash=6, gap=4, alpha=255,
                phase_dir=+1,
            )
            return
        if state == EDGE_STATE_STRIPPING:
            # Reverse-flow dashes — same dash size, opposite direction.
            self._draw_dashed_line(
                screen, color, p0, p1, thickness,
                dash=6, gap=4, alpha=255,
                phase_dir=-1,
            )
            return
        if state == EDGE_STATE_CONTESTED:
            # Shimmer — fast back-and-forth dash phase. Visual cue:
            # the line oscillates rather than pulses.
            self._draw_dashed_line(
                screen, color, p0, p1, thickness,
                dash=4, gap=3, alpha=210,
                phase_dir=0, shimmer=True,
            )
            return
        # Fallback: solid.
        pygame.draw.line(screen, color, p0, p1, thickness)

    def _draw_dashed_line(
        self, screen, color, p0, p1, thickness: int,
        dash: int, gap: int, alpha: int = 255,
        phase_dir: int = 0, shimmer: bool = False,
    ) -> None:
        """Pygame doesn't ship a dashed-line primitive, so we segment
        the line manually. `phase_dir` shifts the dash pattern over
        wall-clock time so the dashes appear to flow forward (+1),
        backward (-1), or oscillate (shimmer=True)."""
        import pygame
        x0, y0 = p0
        x1, y1 = p1
        dx, dy = x1 - x0, y1 - y0
        length = max(1.0, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / length, dy / length
        period = dash + gap
        # Wall-clock phase: 60 px/sec scroll feels lively without
        # being distracting at the default playback rate.
        t = time.monotonic()
        if shimmer:
            phase = (60.0 * abs((t * 2.0) % 2.0 - 1.0))
        else:
            phase = (60.0 * t * phase_dir) % period
        # Walk segments along the line.
        cur = -phase
        while cur < length:
            seg_start = max(0.0, cur)
            seg_end   = min(length, cur + dash)
            if seg_end > seg_start:
                sx = int(round(x0 + ux * seg_start))
                sy = int(round(y0 + uy * seg_start))
                ex = int(round(x0 + ux * seg_end))
                ey = int(round(y0 + uy * seg_end))
                if alpha >= 255:
                    pygame.draw.line(
                        screen, color, (sx, sy), (ex, ey), thickness,
                    )
                else:
                    surf = pygame.Surface(
                        (WINDOW_W, WINDOW_H), pygame.SRCALPHA,
                    )
                    pygame.draw.line(
                        surf, (*color, max(0, min(255, alpha))),
                        (sx, sy), (ex, ey), thickness,
                    )
                    screen.blit(surf, (0, 0))
            cur += period

    def _draw_active_grip_nodes(
        self, screen, snap: Phase1ViewState,
        pose_for: dict[str, "_BodyPose"],
    ) -> None:
        """Per Section 2.3, grip nodes are normally invisible. They
        become visible when an active grip is on or near them. Phase 2a
        uses 'an active grip references this node' as the visibility
        signal — both grasper hand-nodes and target body-nodes light
        up when an edge involves them."""
        import pygame
        # Collect (judoka_name, node_id) pairs that have any active edge.
        active: set[tuple[str, str]] = set()
        edge_owner_identity: dict[tuple[str, str], str] = {}
        for e in snap.grip_edges:
            active.add((e.target_id,  e.target_node))
            edge_owner_identity[(e.target_id, e.target_node)] = (
                e.grasper_identity
            )
            active.add((e.grasper_id, e.grasper_part))
        for (judoka_name, node_id) in active:
            pose = pose_for.get(judoka_name)
            if pose is None:
                continue
            xy = grip_node_screen_xy(node_id, pose)
            if xy is None:
                continue
            # Target node tinted with the gripper's identity (so you
            # see at a glance who owns this contact); hand-node tinted
            # with the body's own identity.
            owner = edge_owner_identity.get((judoka_name, node_id))
            if owner is not None:
                col = _identity_color(owner)
            else:
                # It's a grasper hand-node — colour by its body.
                body_identity = (
                    snap.body_a.identity if judoka_name == snap.body_a.name
                    else snap.body_b.identity
                )
                col = _identity_color(body_identity)
            pygame.draw.circle(screen, col, xy, 6)
            pygame.draw.circle(screen, COL_PANEL_LINE, xy, 6, 1)

    def _cull_node_flashes(self, now_wall: float) -> None:
        kept: list[tuple[GripNodeFlash, float, float]] = []
        for entry in self._active_node_flashes:
            _, started, base = entry
            if now_wall - started < scaled_duration(
                base, self._playback_rate,
            ):
                kept.append(entry)
        self._active_node_flashes = kept

    def _draw_node_flashes(
        self, screen, snap: Phase1ViewState,
        pose_for: dict[str, "_BodyPose"], now_wall: float,
    ) -> None:
        import pygame
        for entry in self._active_node_flashes:
            nf, started, base = entry
            life = scaled_duration(base, self._playback_rate)
            if life <= 0:
                continue
            elapsed = now_wall - started
            t = max(0.0, min(1.0, elapsed / life))
            alpha = int(255 * (1.0 - t))
            pose = pose_for.get(nf.target_id)
            if pose is None:
                continue
            xy = grip_node_screen_xy(nf.node_id, pose)
            if xy is None:
                continue
            color = _node_flash_color(nf.kind)
            # Stripped / Compromised: expanding ring. Deepened: filled
            # pulse. Switched: small ring that swaps colours over its
            # short lifetime.
            if nf.kind == NODE_FLASH_DEEPENED:
                radius = 8 + int(12 * t)
                surf = pygame.Surface(
                    (radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA,
                )
                pygame.draw.circle(
                    surf, (*color, max(0, alpha)),
                    (radius + 2, radius + 2), radius,
                )
                screen.blit(
                    surf, (xy[0] - radius - 2, xy[1] - radius - 2),
                )
            elif nf.kind == NODE_FLASH_SWITCHED:
                # Two-colour swap: midway through, swap from prev to
                # new owner colour.
                if t < 0.5 and nf.prev_owner_identity is not None:
                    swap_col = _identity_color(nf.prev_owner_identity)
                else:
                    swap_col = _identity_color(
                        nf.new_owner_identity or nf.target_identity,
                    )
                radius = 10
                surf = pygame.Surface(
                    (radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA,
                )
                pygame.draw.circle(
                    surf, (*swap_col, max(0, alpha)),
                    (radius + 2, radius + 2), radius, 3,
                )
                screen.blit(
                    surf, (xy[0] - radius - 2, xy[1] - radius - 2),
                )
            else:
                # STRIPPED / COMPROMISED — expanding ring.
                radius = 8 + int(20 * t)
                surf = pygame.Surface(
                    (radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA,
                )
                pygame.draw.circle(
                    surf, (*color, max(0, alpha)),
                    (radius + 2, radius + 2), radius, 3,
                )
                screen.blit(
                    surf, (xy[0] - radius - 2, xy[1] - radius - 2),
                )

    # ------------------------------------------------------------------
    # HAJ-189 — arrow rendering (intent ghost + actual solid)
    # ------------------------------------------------------------------
    def _draw_arrows(self, screen, snap: Phase1ViewState) -> None:
        """Render up to 4 arrows total — intent + actual per fighter.
        Anchored near each fighter's body centre, offset to opposite
        sides per fighter so up to 4 arrows don't collide visually
        (Section 2.4)."""
        import pygame
        if not snap.arrows:
            return
        pose_a, pose_b = _layout_bodies(snap.position_state)
        pose_for: dict[str, "_BodyPose"] = {
            snap.body_a.name: pose_a,
            snap.body_b.name: pose_b,
        }
        # Tori (a) arrows offset slightly above body centre; Uke (b)
        # arrows offset slightly below — keeps the four arrows from
        # crossing each other when both fighters are active.
        offset_for: dict[str, tuple[int, int]] = {
            snap.body_a.name: (0, -10),
            snap.body_b.name: (0, +10),
        }
        for arrow in snap.arrows:
            pose = pose_for.get(arrow.judoka_name)
            if pose is None:
                continue
            # Body-centre anchor point. Roughly in the chest region.
            anchor = (
                pose.centre_xy[0] + offset_for.get(arrow.judoka_name, (0, 0))[0],
                pose.centre_xy[1] + int(1.0 * pose.body_unit_px)
                + offset_for.get(arrow.judoka_name, (0, 0))[1],
            )
            length_px = self._arrow_pixel_length(arrow.magnitude)
            self._draw_one_arrow(screen, anchor, arrow, length_px)

    def _arrow_pixel_length(self, magnitude: float) -> int:
        """Map a force magnitude to an arrow length in pixels. The
        engine's force units are ~Newton-scale; an empirical span
        from 0–500N maps to 0–80px works well at the default body
        scale (60 body-units = ~one body height of 240px). Saturating
        beyond that prevents a single high-magnitude tick from
        drawing an arrow off-screen."""
        clamped = max(0.0, min(500.0, magnitude))
        return int(round(clamped / 500.0 * 80.0)) + 8

    def _draw_one_arrow(
        self, screen, anchor: tuple[int, int],
        arrow: ArrowView, length_px: int,
    ) -> None:
        """One arrow body + arrowhead. Intent: gray ghost, thinner.
        Actual: identity-tinted, thicker, fully saturated. White
        identity arrows always get a dark outline so they read on the
        background (Section 2.4)."""
        import pygame
        if arrow.magnitude <= 0:
            return
        ux = arrow.vec_x / arrow.magnitude
        uy = arrow.vec_y / arrow.magnitude
        end = (
            anchor[0] + int(ux * length_px),
            anchor[1] + int(uy * length_px),
        )
        if arrow.kind == ARROW_KIND_INTENT:
            color = _intent_arrow_color(arrow.judoka_identity)
            thickness = 2
            outline = None
            head_size = 8
        else:
            color = _identity_color(arrow.judoka_identity)
            thickness = 5
            outline = _identity_outline(arrow.judoka_identity)
            head_size = 12
        # Shaft.
        pygame.draw.line(screen, color, anchor, end, thickness)
        if outline is not None:
            pygame.draw.line(screen, outline, anchor, end, 1)
        # Arrowhead — small triangle at the tip.
        # Perpendicular vector for the head's base.
        perp = (-uy, ux)
        base = (
            end[0] - int(ux * head_size),
            end[1] - int(uy * head_size),
        )
        left = (
            base[0] + int(perp[0] * head_size * 0.6),
            base[1] + int(perp[1] * head_size * 0.6),
        )
        right = (
            base[0] - int(perp[0] * head_size * 0.6),
            base[1] - int(perp[1] * head_size * 0.6),
        )
        pygame.draw.polygon(screen, color, (end, left, right))
        if outline is not None:
            pygame.draw.polygon(screen, outline, (end, left, right), 1)

    # ------------------------------------------------------------------
    # HAJ-189 — mini-map (corner widget, top-down mat schematic)
    # ------------------------------------------------------------------
    def _draw_mini_map(self, screen, snap: Phase1ViewState) -> None:
        import pygame
        mm = snap.mini_map
        if mm is None:
            return
        # Layout: ~140×140 in top-right, just under the score panel.
        widget_size = 140
        margin = 12
        x0 = WINDOW_W - widget_size - margin
        y0 = PANEL_TOP_H + margin
        # Background panel for legibility.
        pygame.draw.rect(
            screen, COL_PANEL, (x0, y0, widget_size, widget_size),
        )
        pygame.draw.rect(
            screen, COL_PANEL_LINE, (x0, y0, widget_size, widget_size), 1,
        )

        # Mat-coord → widget-pixel scale. The full safety boundary
        # spans (-safety_half, +safety_half); fit it in the widget
        # with a small inner pad.
        pad = 6
        usable = widget_size - 2 * pad
        scale = usable / (2.0 * mm.safety_half_m)
        cx = x0 + widget_size // 2
        cy = y0 + widget_size // 2

        def mat_to_px(mp):
            mx, my = mp
            return (cx + int(mx * scale), cy - int(my * scale))

        # Outer dashed safety boundary.
        safety_corner_min = mat_to_px((-mm.safety_half_m, +mm.safety_half_m))
        safety_corner_max = mat_to_px((+mm.safety_half_m, -mm.safety_half_m))
        self._draw_dashed_rect(
            screen, COL_PANEL_LINE, safety_corner_min, safety_corner_max,
        )
        # Inner solid contest area.
        contest_corner_min = mat_to_px((-mm.contest_half_m, +mm.contest_half_m))
        contest_corner_max = mat_to_px((+mm.contest_half_m, -mm.contest_half_m))
        pygame.draw.rect(
            screen, COL_PANEL_LINE,
            (contest_corner_min[0], contest_corner_min[1],
             contest_corner_max[0] - contest_corner_min[0],
             contest_corner_max[1] - contest_corner_min[1]),
            1,
        )

        # Tails — fading line behind each fighter's circle.
        self._draw_mini_map_tail(
            screen, mm.a_tail, _identity_color(mm.a_identity), mat_to_px,
        )
        self._draw_mini_map_tail(
            screen, mm.b_tail, _identity_color(mm.b_identity), mat_to_px,
        )

        # Fighter circles.
        a_xy = mat_to_px(mm.a_position)
        b_xy = mat_to_px(mm.b_position)
        self._draw_mini_map_fighter(
            screen, a_xy, mm.a_identity, mm.a_near_edge,
        )
        self._draw_mini_map_fighter(
            screen, b_xy, mm.b_identity, mm.b_near_edge,
        )

    def _draw_dashed_rect(self, screen, color, p_min, p_max) -> None:
        """Outer safety boundary as a dashed rectangle. Cheap manual
        segmentation — no pygame primitive for this."""
        import pygame
        x0, y0 = p_min
        x1, y1 = p_max
        dash, gap = 4, 3
        # Top.
        x = x0
        while x < x1:
            pygame.draw.line(
                screen, color, (x, y0), (min(x + dash, x1), y0), 1,
            )
            x += dash + gap
        # Bottom.
        x = x0
        while x < x1:
            pygame.draw.line(
                screen, color, (x, y1), (min(x + dash, x1), y1), 1,
            )
            x += dash + gap
        # Left.
        y = y0
        while y < y1:
            pygame.draw.line(
                screen, color, (x0, y), (x0, min(y + dash, y1)), 1,
            )
            y += dash + gap
        # Right.
        y = y0
        while y < y1:
            pygame.draw.line(
                screen, color, (x1, y), (x1, min(y + dash, y1)), 1,
            )
            y += dash + gap

    def _draw_mini_map_tail(self, screen, tail, color, mat_to_px) -> None:
        import pygame
        n = len(tail)
        if n < 2:
            return
        for i in range(1, n):
            alpha = int(40 + 180 * (i / n))
            surf = pygame.Surface((3, 3), pygame.SRCALPHA)
            surf.fill((*color, alpha))
            px = mat_to_px(tail[i])
            screen.blit(surf, (px[0] - 1, px[1] - 1))

    def _draw_mini_map_fighter(
        self, screen, xy, identity_tag: str, near_edge: bool,
    ) -> None:
        """Filled circle, identity-tinted; pulses outward when within
        the boundary-approach band (Section 2.11)."""
        import pygame
        col = _identity_color(identity_tag)
        outline = _identity_outline(identity_tag)
        pygame.draw.circle(screen, col, xy, 5)
        if outline is not None:
            pygame.draw.circle(screen, outline, xy, 5, 1)
        if near_edge:
            import math
            pulse_r = 7 + int(3 * (0.5 + 0.5 * math.sin(time.monotonic() * 5.0)))
            surf = pygame.Surface(
                (pulse_r * 2 + 2, pulse_r * 2 + 2), pygame.SRCALPHA,
            )
            pygame.draw.circle(
                surf, (*col, 160),
                (pulse_r + 1, pulse_r + 1), pulse_r, 1,
            )
            screen.blit(surf, (xy[0] - pulse_r - 1, xy[1] - pulse_r - 1))


def _intent_arrow_color(identity_tag: str) -> tuple[int, int, int]:
    """Section 2.4 — gray ghost intent arrow, identity-aware so the
    white judoka's intent reads against the white actual arrow.
    Blue identity → mid-gray; white identity → darker gray."""
    if identity_tag == Identity.WHITE:
        return (110, 110, 120)
    return (160, 160, 165)


def _node_flash_color(kind: str) -> tuple[int, int, int]:
    return {
        NODE_FLASH_STRIPPED:    (240,  80,  80),
        NODE_FLASH_DEEPENED:    ( 90, 220, 110),
        NODE_FLASH_COMPROMISED: (240, 210,  60),
        NODE_FLASH_SWITCHED:    (255, 255, 255),
    }.get(kind, (255, 255, 255))


def _flash_base_duration(kind: str) -> float:
    return {
        FLASH_IPPON:    IPPON_SWEEP_S,
        FLASH_WAZA_ARI: SCORE_FLASH_S,
        FLASH_SHIDO:    SHIDO_FLASH_S,
        FLASH_HANSOKU:  HANSOKU_FLASH_S,
        FLASH_MATTE:    MATTE_BANNER_S,
        FLASH_HAJIME:   HAJIME_BANNER_S,
    }.get(kind, 0.6)


# ---------------------------------------------------------------------------
# RECORDING / TEST RENDERER
#
# Push-only fake — used by tests to verify capture logic, the 1:1
# burst/event invariant, and Match wiring without opening a window.
# ---------------------------------------------------------------------------
class Phase1RecordingRenderer:
    """Captures every Phase1ViewState the engine produces. Pure data;
    no pygame. Used by tests + a forthcoming synchronization regression."""

    def __init__(self) -> None:
        self.start_calls: int = 0
        self.update_calls: int = 0
        self.stop_calls:   int = 0
        self.snapshots:    list[Phase1ViewState] = []
        self.event_log:    list[tuple[int, str, str]] = []
        self._open: bool = True

    def start(self) -> None:
        self.start_calls += 1

    def update(self, tick: int, match: "Match", events) -> None:
        self.update_calls += 1
        prev = self.snapshots[-1] if self.snapshots else None
        snap = capture_phase1_view(match, tick, events, prev_view=prev)
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
        """Test helper — simulate the user closing the window."""
        self._open = False

    # --- Convenience views for the synchronization test -------------------
    def all_text_bursts(self) -> list[tuple[int, str, str]]:
        """Flatten every captured TextBurst to (tick, event_type, text)."""
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
        """Flatten every captured grip edge to (tick, view) — used by
        tests asserting per-tick state derivation."""
        out: list[tuple[int, GripEdgeView]] = []
        for snap in self.snapshots:
            for e in snap.grip_edges:
                out.append((snap.tick, e))
        return out
