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


def capture_phase1_view(match, tick: int, events) -> Phase1ViewState:
    """Build a frozen Phase1ViewState from live Match state. Pure read;
    never mutates anything. Called once per tick from Phase1Renderer.update.

    Section 3.1 commitment: this function reads from the same per-tick
    state windows the narration module reads. It does not infer or
    invent any state. Anything visible in the Phase 1 viewer is
    derivable from (match @ tick T, events fired in T-1..T)."""
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
    )


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
WINDOW_W: int = 1100
WINDOW_H: int = 720
PANEL_TOP_H: int = 90      # match clock + score panel
PANEL_BOTTOM_H: int = 90   # text burst caption strip
BODY_AREA_H: int = WINDOW_H - PANEL_TOP_H - PANEL_BOTTOM_H

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
DEFAULT_PLAYBACK_RATE: float = 0.7
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
        snap = capture_phase1_view(match, tick, events)
        self._snapshots.append(snap)
        self._latest_snap = snap
        self._burst_queue.push_many(snap.text_bursts)
        now_wall = time.monotonic()
        for f in snap.referee_flashes:
            base = _flash_base_duration(f.kind)
            self._active_flashes.append((f, now_wall, base))

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
        smaller surface."""
        match.begin()
        last_step = time.monotonic()
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
            match.end()
        finally:
            # If the user closed the window before match.end() ran in the
            # try-block, ensure end() still fires for the prose summary.
            if not getattr(match, "match_over", False):
                try:
                    match.end()
                except Exception:
                    raise

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
        import pygame
        screen = self._screen
        screen.fill(COL_BG)
        self._draw_top_panel(screen, snap)
        self._draw_bodies(screen, snap)
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

    def _draw_bodies(self, screen, snap: Phase1ViewState) -> None:
        pose_a, pose_b = _layout_bodies(snap.position_state)
        self._draw_body(screen, snap.body_a, pose_a)
        self._draw_body(screen, snap.body_b, pose_b)

    def _draw_body(self, screen, body: BodyView, pose: _BodyPose) -> None:
        import pygame
        col = _identity_color(body.identity)
        outline = _identity_outline(body.identity)
        for region in _BODY_LAYOUT:
            rect = pose.region_rect(region)
            pygame.draw.rect(screen, col, rect)
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
        pygame.draw.rect(screen, col, (bar_x, bar_y, cardio_w, 6))

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
        snap = capture_phase1_view(match, tick, events)
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
