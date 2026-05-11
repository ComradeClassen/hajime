# match_viewer.py
# HAJ-125 — top-down match viewer v1 (render layer).
# HAJ-126 — viewer v2: pause / step / speed scrub / click-to-inspect /
#           docked event ticker.
#
# Dev tool only. Not shipped with the game; UE5 is the player-facing
# renderer. The success metric: can a developer freeze a moment, slow
# down a transition, and interrogate a fighter's state mid-action?
#
# Read-only with respect to match state. v2 owns the wall-clock loop —
# Match.run() hands off via drives_loop() / run_interactive(match).
#
# Surfaces:
#   - Mat outlines: 8 m contest area + 3 m safety border (concentric rects)
#   - Fighter dots at com_position with facing arrows
#   - Foot dots at foot_state_left/right.position
#   - Kuzushi halo: alpha scales with |trunk_sagittal| + |trunk_frontal|;
#     bright flash on KUZUSHI_INDUCED for ~5 ticks
#   - Grip lines color-coded by GripMode
#   - Position trails (last 30 ticks of CoM, fading)
#   - Sidebar: state summary OR fighter inspector when one is clicked
#   - Docked event ticker (bottom of sidebar) — newest events highlighted
#   - Footer hint line listing keybindings

from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from enums import GripMode
from significance import (
    THRESHOLD_MAT_SIDE, THRESHOLD_STANDS,
    THRESHOLD_REVIEW, THRESHOLD_BROADCAST,
)

if TYPE_CHECKING:
    from match import Match
    from grip_graph import Event
    from judoka import Judoka


# ---------------------------------------------------------------------------
# TICKER ALTITUDE — narration filter for the on-screen event ticker.
# Each value maps to a `significance` floor. Per session feedback, the
# default went from "show everything" (mat-side, threshold 1) to
# "show narrative beats" (stands, threshold 4) so the in-viewer log
# reads more like what a player would see than what a developer would
# debug. CLI: --ticker-altitude {mat_side|stands|review|broadcast}.
# ---------------------------------------------------------------------------
TICKER_ALTITUDES: dict[str, int] = {
    "mat_side":  THRESHOLD_MAT_SIDE,    # 1 — every event with prose (legacy)
    "stands":    THRESHOLD_STANDS,      # 4 — narrative beats only (new default)
    "review":    THRESHOLD_REVIEW,      # 7 — only meaningful turning points
    "broadcast": THRESHOLD_BROADCAST,   # 9 — only score-defining moments
}


# ---------------------------------------------------------------------------
# VIEW STATE (per-tick snapshot)
# Everything the renderer needs to draw a single tick. Captured during
# the live match run so the post-match review mode can scrub back to any
# earlier tick without re-running the simulation.
#
# These are pure-data structs (no references to live Judoka objects) so
# the snapshot list is independent of subsequent state mutation. Cost
# per tick is small (~1 KB), so a 240-tick match holds <250 KB.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GripEdgeView:
    grasper_id:        str
    grasper_part_name: str
    target_id:         str
    target_loc_name:   str
    grip_type_name:    str
    depth_name:        str
    mode_value:        int   # GripMode.value — kept as int to detach


@dataclass(frozen=True)
class FighterView:
    name:              str
    color_tag:         str   # "a" or "b"
    com_position:      tuple[float, float]
    facing:            tuple[float, float]
    foot_l_pos:        tuple[float, float]
    foot_r_pos:        tuple[float, float]
    trunk_sagittal:    float
    trunk_frontal:     float
    score_waza_ari:    int
    score_ippon:       bool
    shidos:            int
    composure_current: float
    composure_ceiling: float
    cardio_current:    float
    stun_ticks:        int
    stance_name:       str
    belt_name:         str
    archetype_name:    str
    age:               int
    dominant_side:     str
    kumi_kata_clock:   int
    last_attack_tick:  int
    off_desperation:   bool
    def_desperation:   bool
    body_parts:        tuple[tuple[str, float, float], ...] = ()
    # Tuple of (part_name, effective, fatigue).
    # HAJ-128 — hand positions (derived from CoM + facing-rotated body
    # offsets) and per-hand grip flags. The viewer renders these instead
    # of feet because in judo the hands ARE the throw — knowing where the
    # gripping hands are matters far more than where the feet are.
    hand_l_pos:        tuple[float, float] = (0.0, 0.0)
    hand_r_pos:        tuple[float, float] = (0.0, 0.0)
    hand_l_gripping:   bool = False
    hand_r_gripping:   bool = False
    # HAJ-153 — per-fighter state pill. Compact label rendered near the
    # CoM dot summarising what the fighter is currently *doing* on this
    # tick (mid-throw, stunned, in desperation, follow-up chasing, etc.).
    # The pill string is computed in capture_view_state from the live
    # match state so review-mode scrubbing renders the same string the
    # tick produced. None means no pill.
    state_pill:        Optional[str] = None
    # HAJ-153 — owned grip count, surfaced separately from the pill so
    # the renderer can show "GRIPS 2" without re-deriving from grip_edges.
    own_edge_count:    int = 0


@dataclass(frozen=True)
class ViewState:
    tick:               int
    max_ticks:           int
    position_name:      str
    sub_loop_name:      str
    matchup_name:       str
    edge_count:         int
    fighter_a:          FighterView
    fighter_b:          FighterView
    grip_edges:         tuple[GripEdgeView, ...]
    event_descriptions: tuple[str, ...]
    kuzushi_victims:    tuple[str, ...]   # names whose halo should flash this tick
    # HAJ-153 — viewer-wire-up event-driven cues. These are derived from
    # the engine event list at capture time so review-mode rendering
    # produces the same visual cue the live tick did.
    matte_reason:       Optional[str] = None    # MATTE_CALLED reason this tick
    # HAJ-160 — hajime banner symmetric with the matte banner. Set when
    # the tick's events include a HAJIME_CALLED (match start at t000 +
    # every restart after a matte). Pure cue field; the renderer reads
    # it to fire the centered HAJIME banner just like matte.
    hajime_called:      bool = False
    stuff_victims:      tuple[str, ...] = ()    # STUFFED victims this tick
    score_awarded:      Optional[str] = None    # "WAZA_ARI" / "IPPON" awarded this tick
    score_scorer:       Optional[str] = None    # name of the scoring fighter
    counter_attacker:   Optional[str] = None    # COUNTER_COMMIT defender name
    counter_target:     Optional[str] = None    # COUNTER_COMMIT attacker name
    grip_seat_count:    int = 0                  # GRIP_ESTABLISH events on this tick
    # HAJ-152 follow-up window state — None when no follow-up is active.
    # Pill renders above the scorer's dot for the duration of the window.
    follow_up_scorer:   Optional[str] = None
    follow_up_decision: Optional[str] = None     # CHASE / STAND / DEFENSIVE_CHASE
    follow_up_stage:    Optional[str] = None     # PENDING_DECISION / NE_WAZA_LIVE / STANDING
    # HAJ-153 ne-waza schematic — top fighter name when the dyad is on
    # the ground. Bottom is the other fighter.
    ne_waza_top_name:   Optional[str] = None


_INSPECTOR_BODY_PARTS = (
    "right_hand", "left_hand", "right_leg", "left_leg",
    "core", "lower_back",
)

# HAJ-128 — hand position offsets in body frame (in meters). Hands
# extend forward and to either side of the CoM; the renderer uses these
# offsets rotated by `facing` to place hand dots on the mat.
HAND_FORWARD_M:  float = 0.30
HAND_LATERAL_M:  float = 0.22


def _hand_positions(
    com: tuple[float, float], facing: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Compute world-frame (left_hand, right_hand) positions from CoM
    and facing. Right hand sits to the +x side in body frame; rotate
    into mat frame using facing as the body's +x axis."""
    cx, cy = com
    fx, fy = facing
    # Body frame: facing = +x; perp (body +y) = (-fy, fx) — 90° CCW.
    perp_x, perp_y = -fy, fx
    forward = (fx * HAND_FORWARD_M, fy * HAND_FORWARD_M)
    lateral = (perp_x * HAND_LATERAL_M, perp_y * HAND_LATERAL_M)
    left  = (cx + forward[0] + lateral[0], cy + forward[1] + lateral[1])
    right = (cx + forward[0] - lateral[0], cy + forward[1] - lateral[1])
    return left, right


def _capture_fighter(judoka, color_tag: str, match) -> FighterView:
    ident = judoka.identity
    cap   = judoka.capability
    st    = judoka.state
    bs    = st.body_state
    parts = []
    for key in _INSPECTOR_BODY_PARTS:
        if key in st.body:
            parts.append((
                key,
                judoka.effective_body_part(key),
                st.body[key].fatigue,
            ))
    # HAJ-128 — hand positions + per-hand grip flags. A hand "grips" if
    # any owned grip edge has it as the grasper part.
    left_hand, right_hand = _hand_positions(
        tuple(bs.com_position), tuple(bs.facing),
    )
    own_edges = match.grip_graph.edges_owned_by(ident.name)
    grip_parts = {e.grasper_part.name for e in own_edges}
    # HAJ-153 — compact state pill for the fighter dot. Priority order
    # (higher == more important to surface): mid-throw → stunned →
    # offensive desperation → defensive desperation → grip count tag.
    pill: Optional[str] = None
    in_progress = match._throws_in_progress.get(ident.name)
    if in_progress is not None:
        pill = "THROW"
    elif st.stun_ticks > 0:
        pill = f"STUN {st.stun_ticks}"
    elif match._offensive_desperation_active.get(ident.name, False):
        pill = "OFF-DESP"
    elif match._defensive_desperation_active.get(ident.name, False):
        pill = "DEF-DESP"
    elif own_edges:
        pill = f"GRIPS {len(own_edges)}"
    return FighterView(
        name=ident.name,
        color_tag=color_tag,
        com_position=tuple(bs.com_position),
        facing=tuple(bs.facing),
        foot_l_pos=tuple(bs.foot_state_left.position),
        foot_r_pos=tuple(bs.foot_state_right.position),
        hand_l_pos=left_hand,
        hand_r_pos=right_hand,
        hand_l_gripping=("LEFT_HAND" in grip_parts),
        hand_r_gripping=("RIGHT_HAND" in grip_parts),
        trunk_sagittal=bs.trunk_sagittal,
        trunk_frontal=bs.trunk_frontal,
        score_waza_ari=st.score["waza_ari"],
        score_ippon=st.score["ippon"],
        shidos=st.shidos,
        composure_current=st.composure_current,
        composure_ceiling=float(cap.composure_ceiling),
        cardio_current=st.cardio_current,
        stun_ticks=st.stun_ticks,
        stance_name=st.current_stance.name.lower(),
        belt_name=ident.belt_rank.name,
        archetype_name=ident.body_archetype.name,
        age=ident.age,
        dominant_side=ident.dominant_side.name.lower(),
        kumi_kata_clock=match.kumi_kata_clock.get(ident.name, 0),
        last_attack_tick=match._last_attack_tick.get(ident.name, 0),
        off_desperation=match._offensive_desperation_active.get(ident.name, False),
        def_desperation=match._defensive_desperation_active.get(ident.name, False),
        body_parts=tuple(parts),
        state_pill=pill,
        own_edge_count=len(own_edges),
    )


def capture_view_state(
    match, tick: int, events, kuzushi_victims: tuple[str, ...] = (),
) -> ViewState:
    """Build a frozen ViewState from live Match state. Pure read; never
    mutates anything. Called once per tick during a live run."""
    edges = []
    for e in match.grip_graph.edges:
        edges.append(GripEdgeView(
            grasper_id=e.grasper_id,
            grasper_part_name=e.grasper_part.name,
            target_id=e.target_id,
            target_loc_name=e.target_location.name,
            grip_type_name=e.grip_type_v2.name,
            depth_name=e.depth_level.name,
            mode_value=e.mode.value,
        ))
    descs = tuple(
        e.description for e in events if getattr(e, "description", None)
    )

    # HAJ-153 — extract event-driven visual cues from this tick's events.
    matte_reason: Optional[str] = None
    # HAJ-160 — hajime banner cue. Any HAJIME_CALLED on this tick flips
    # the flag; renderer paints the banner exactly like matte.
    hajime_called: bool = False
    stuff_victims: list[str] = []
    score_awarded: Optional[str] = None
    score_scorer:  Optional[str] = None
    counter_attacker: Optional[str] = None
    counter_target:   Optional[str] = None
    grip_seat_count: int = 0
    for ev in events:
        et = ev.event_type
        data = ev.data or {}
        if et == "MATTE_CALLED":
            matte_reason = data.get("reason") or "matte"
        elif et == "HAJIME_CALLED":
            hajime_called = True
        elif et == "STUFFED":
            # The STUFFED event lives on the ATTACKER (whose throw was
            # stuffed). The attacker dot should flash, not the defender's.
            # Description format: "[throw] X stuffed on Y — Z defends.";
            # data may not carry the attacker name, so fall back to a
            # description scan.
            attacker = data.get("attacker")
            if not attacker:
                desc = ev.description or ""
                for f in (match.fighter_a, match.fighter_b):
                    if f.identity.name in desc.split(" stuffed")[0]:
                        attacker = f.identity.name
                        break
            if attacker:
                stuff_victims.append(attacker)
        elif et in ("WAZA_ARI_AWARDED", "IPPON_AWARDED"):
            score_awarded = "IPPON" if et == "IPPON_AWARDED" else "WAZA_ARI"
            score_scorer  = data.get("scorer") or data.get("scorer_id")
        elif et == "COUNTER_COMMIT":
            counter_attacker = data.get("defender")  # the counter-fire fighter
            counter_target   = data.get("attacker")  # the original attacker
        elif et == "GRIP_ESTABLISH":
            grip_seat_count += 1

    # HAJ-152 follow-up window state.
    follow_up_scorer: Optional[str] = None
    follow_up_decision: Optional[str] = None
    follow_up_stage:  Optional[str] = None
    fu = getattr(match, "_post_score_follow_up", None)
    if fu is not None:
        follow_up_scorer   = fu.get("tori_name")
        follow_up_decision = fu.get("decision")
        follow_up_stage    = fu.get("stage")

    # HAJ-153 ne-waza top fighter — the position machine already tracks
    # `ne_waza_top_id` while the dyad is on the ground.
    ne_waza_top_name: Optional[str] = None
    if match.sub_loop_state.name == "NE_WAZA":
        ne_waza_top_name = getattr(match, "ne_waza_top_id", None)

    return ViewState(
        tick=tick,
        max_ticks=match.max_ticks,
        position_name=match.position.name,
        sub_loop_name=match.sub_loop_state.name,
        matchup_name=match._compute_stance_matchup().name,
        edge_count=match.grip_graph.edge_count(),
        fighter_a=_capture_fighter(match.fighter_a, "a", match),
        fighter_b=_capture_fighter(match.fighter_b, "b", match),
        grip_edges=tuple(edges),
        event_descriptions=descs,
        kuzushi_victims=kuzushi_victims,
        matte_reason=matte_reason,
        hajime_called=hajime_called,
        stuff_victims=tuple(stuff_victims),
        score_awarded=score_awarded,
        score_scorer=score_scorer,
        counter_attacker=counter_attacker,
        counter_target=counter_target,
        grip_seat_count=grip_seat_count,
        follow_up_scorer=follow_up_scorer,
        follow_up_decision=follow_up_decision,
        follow_up_stage=follow_up_stage,
        ne_waza_top_name=ne_waza_top_name,
    )


# ---------------------------------------------------------------------------
# WINDOW / WORLD-FRAME LAYOUT
# Mat geometry is the IJF reference (HAJ-124 declares meters as the unit):
#   - Contest area: 8 × 8 m
#   - Safety border: 3 m on every side → total 14 × 14 m
# ---------------------------------------------------------------------------
WINDOW_W:        int = 1500
WINDOW_H:        int = 820
SIDEBAR_W:       int = 560
MAT_PANEL_W:     int = WINDOW_W - SIDEBAR_W
MAT_PIXEL_PAD:   int = 30
FOOTER_H:        int = 24       # bottom hint strip

VISIBLE_MAT_M:   float = 14.0
CONTEST_M:       float = 8.0

TRAIL_LENGTH:    int = 30

# Frame pacing — ticks/second of wall clock (a tick is 1 sim second).
# 0.5 tps ≈ 2s per tick — slow enough that a viewer learning the visual
# vocabulary can actually read what changed between ticks (grip flips,
# kuzushi flashes, score events). 1.25 tps was confusing; even 1.0 tps
# (real-time) hides too much. Per-session feedback May 2026: default
# slow, let the user speed up with +/- as they get fluent. A 4-minute
# (240-tick) match plays in ~8 minutes of wall clock at the default;
# tap '+' twice to roughly halve that.
DEFAULT_TICKS_PER_SECOND: float = 1.25
MIN_TPS: float = 0.1
MAX_TPS: float = 30.0   # 10× of real-time is the ticket spec; 30 leaves headroom
TPS_STEP_FACTOR: float = 1.5

# Event ticker geometry (inside the sidebar). Width is SIDEBAR_W minus
# left/right padding (~24px); the wrap helper computes char budget at
# render time from the actual font metrics so the ticker shows full
# event text instead of truncating mid-sentence.
TICKER_H:           int = 420
TICKER_LINE_H:      int = 18
TICKER_PAD_X:       int = 12
TICKER_MAX_LINES:   int = TICKER_H // TICKER_LINE_H
EVENT_BUFFER_LEN:   int = 200       # how much history we retain
NEW_EVENT_HIGHLIGHT_FRAMES: int = 18   # ~1 second at 18 FPS

# Colors (RGB).
COL_BG          = ( 22,  24,  30)
COL_SAFETY      = (148, 110,  74)
COL_CONTEST     = (188, 154, 100)
COL_GRID        = ( 60,  64,  74)
COL_FIGHTER_A   = ( 96, 144, 232)
COL_FIGHTER_B   = (220,  92,  92)
COL_FOOT_A      = (170, 200, 240)
COL_FOOT_B      = (240, 170, 170)
# HAJ-128 — hand dots replace foot dots in the viewer. Bright color when
# the hand owns a grip edge; dim when free.
COL_HAND_A_GRIP = (160, 220, 255)
COL_HAND_A_FREE = ( 90, 120, 160)
COL_HAND_B_GRIP = (255, 160, 160)
COL_HAND_B_FREE = (160,  90,  90)
COL_FACING      = (240, 240, 240)
COL_KUZUSHI     = (255,  95,  60)
COL_TRAIL_A     = ( 96, 144, 232)
COL_TRAIL_B     = (220,  92,  92)
COL_GRIP_CONN   = (140, 140, 140)
COL_GRIP_DRIVE  = (255, 220,  90)
COL_TEXT        = (235, 235, 240)
COL_TEXT_DIM    = (160, 160, 170)
COL_TEXT_NEW    = (255, 235, 120)
COL_PANEL       = ( 32,  34,  42)
COL_PANEL_ALT   = ( 28,  30,  36)
COL_PAUSE_BAR   = (240, 200,  80)
COL_INSPECT     = (255, 255, 255)
# HAJ-153 — viewer wire-up palette.
COL_MATTE_BG    = (180,  40,  40)   # MATTE banner background
COL_MATTE_TEXT  = (255, 240, 200)   # MATTE banner text
# HAJ-160 — HAJIME banner colors. Symmetric with MATTE but green so
# stop / restart are distinguishable at a glance.
COL_HAJIME_BG   = ( 40, 140,  60)   # HAJIME banner background
COL_HAJIME_TEXT = (240, 255, 220)   # HAJIME banner text
COL_STUFF_FLASH = (255, 100, 100)   # stuff impact flash
COL_SCORE_FLASH = (255, 230, 110)   # score award flash on scorer
COL_COUNTER     = (255, 230, 110)   # counter chevron between fighters
COL_FOLLOW_UP   = (130, 220, 255)   # follow-up window pill
COL_GRIP_FLASH  = (255, 230, 110)   # bright flash on multi-grip-seat tick
COL_NE_TOP      = (240, 240, 255)   # ne-waza schematic top fighter
COL_NE_BOT      = (160, 170, 195)   # ne-waza schematic bottom fighter
COL_PILL_BG     = ( 40,  44,  56)   # state-pill background
COL_PILL_BORDER = ( 90,  98, 118)

# HAJ-153 — visual-cue lifetime (in viewer frames). Cues fade over this
# many frames after the firing tick. With a default 60 FPS render and
# 6 tps simulation, each tick spans ~10 frames; a 18-frame lifetime
# carries the cue across roughly 1.8 ticks of wall-clock time.
CUE_LIFETIME_FRAMES: int = 18
MATTE_BANNER_FRAMES: int = 30   # ~1.7s at 18 FPS or ~0.5s at 60 FPS
# HAJ-160 — HAJIME banner persists for the same wall-clock window as
# the MATTE banner, so the matte → hajime cycle reads as a balanced
# pair of stop / restart beats.
HAJIME_BANNER_FRAMES: int = 30
# Triage 2026-05-02 (Priority 2) — number of ticks the banner stays on
# screen after firing. The matte banner needs to cover the full
# MATTE_TO_HAJIME_PAUSE_TICKS gap (match.py = 3 ticks) so the stop beat
# doesn't blink off before the hajime banner takes over. The hajime
# banner gets a 2-tick visible flash so the restart reads cleanly.
MATTE_BANNER_TICKS:  int = 3
HAJIME_BANNER_TICKS: int = 2
GRIP_SEAT_THRESHOLD: int = 3    # GRIP_ESTABLISH count that triggers F5 flash


def _grip_mode_color(mode: GripMode):
    if mode == GripMode.DRIVING:
        return COL_GRIP_DRIVE
    return COL_GRIP_CONN


# ---------------------------------------------------------------------------
# WORLD-TO-SCREEN TRANSFORM
# Pure math; testable without pygame.
# ---------------------------------------------------------------------------
class MatTransform:
    def __init__(
        self,
        window_w: int = WINDOW_W,
        window_h: int = WINDOW_H,
        sidebar_w: int = SIDEBAR_W,
        pad: int = MAT_PIXEL_PAD,
        visible_mat_m: float = VISIBLE_MAT_M,
        footer_h: int = FOOTER_H,
    ) -> None:
        self.panel_w = window_w - sidebar_w
        self.panel_h = window_h - footer_h
        self.pad = pad
        usable_w = self.panel_w - 2 * pad
        usable_h = self.panel_h - 2 * pad
        self.px_per_m = min(usable_w, usable_h) / visible_mat_m
        self.origin_x = pad + (self.panel_w - 2 * pad) / 2
        self.origin_y = pad + (self.panel_h - 2 * pad) / 2

    def world_to_screen(self, mx: float, my: float) -> tuple[int, int]:
        sx = self.origin_x + mx * self.px_per_m
        sy = self.origin_y - my * self.px_per_m
        return (int(round(sx)), int(round(sy)))

    def meters_to_pixels(self, m: float) -> int:
        return int(round(m * self.px_per_m))


# ---------------------------------------------------------------------------
# TRAIL BUFFER — pure data structure.
# ---------------------------------------------------------------------------
class TrailBuffer:
    def __init__(self, length: int = TRAIL_LENGTH) -> None:
        self._length = length
        self._a: deque[tuple[float, float]] = deque(maxlen=length)
        self._b: deque[tuple[float, float]] = deque(maxlen=length)

    def push(self, a_pos: tuple[float, float], b_pos: tuple[float, float]) -> None:
        self._a.append(a_pos)
        self._b.append(b_pos)

    def fighter_a(self) -> list[tuple[float, float]]:
        return list(self._a)

    def fighter_b(self) -> list[tuple[float, float]]:
        return list(self._b)


# ---------------------------------------------------------------------------
# PYGAME RENDERER
# ---------------------------------------------------------------------------
class PygameMatchRenderer:
    """v2 interactive viewer. Drives the match loop so it can pause,
    step, and scrub speed; surfaces a ticker and click-to-inspect."""

    def __init__(
        self,
        ticks_per_second: float = DEFAULT_TICKS_PER_SECOND,
        *,
        ticker_altitude_threshold: int = THRESHOLD_STANDS,
    ) -> None:
        import pygame  # noqa: F401  (validate dep at construction)
        self._tps = max(MIN_TPS, min(MAX_TPS, float(ticks_per_second)))
        self._initial_tps = self._tps
        self._transform = MatTransform()
        self._trails = TrailBuffer()
        self._screen = None
        self._clock = None
        self._font_small = None
        self._font_med   = None
        self._font_big   = None
        self._open = True

        # Driver state.
        self._paused = False
        self._step_request = False  # set by right-arrow under pause
        self._wall_t_last_step: float = 0.0

        # Inspector state — None or "a" / "b".
        self._inspect_target: Optional[str] = None

        # Event ticker buffer: list of (tick, description, frame_seen_at).
        # Filter: only events whose significance ≥ this threshold are
        # pushed to the on-screen ticker. The full mat-side stream
        # still goes to stdout / the prose log; this is just the
        # in-viewer surface. STANDS (4) is the default — drops per-tick
        # mechanics (move, SUB_TSUKURI, SUB_KAKE_COMMIT, baseline
        # grip churn) and surfaces narrative beats (kuzushi, grip
        # kills, throws, scores, referee). Override per-launch with
        # the --ticker-altitude CLI flag.
        self._ticker_altitude_threshold: int = ticker_altitude_threshold
        self._event_log: deque[tuple[int, str, int]] = deque(
            maxlen=EVENT_BUFFER_LEN,
        )
        self._frame_idx: int = 0

        # Kuzushi flash decay marker (per fighter).
        self._last_kuzushi_tick: dict[str, int] = {}

        # HAJ-153 — visual-cue decay markers. Each entry is the tick on
        # which the cue last fired; the renderer's draw helpers fade them
        # out over CUE_LIFETIME_FRAMES (banner: MATTE_BANNER_FRAMES). The
        # markers double as review-mode lookups: when scrubbing, the
        # snapshot at the displayed tick has the live event field set,
        # and the cue renders for one tick of real-time review per
        # the audit doc convention.
        self._last_matte_tick: int = -10**9
        self._last_matte_reason: Optional[str] = None
        # HAJ-160 — hajime banner decay marker. Mirrors _last_matte_tick.
        self._last_hajime_tick: int = -10**9
        self._last_stuff_tick: dict[str, int] = {}
        self._last_score_tick: dict[str, int] = {}
        self._last_counter_tick: int = -10**9
        self._last_counter_attacker: Optional[str] = None
        self._last_counter_target:   Optional[str] = None
        self._last_grip_seat_tick: int = -10**9

        # Per-tick visual snapshots, captured during the live run. After
        # match.end() the renderer enters review mode and renders these
        # so the user can scrub backward. The user can also enter review
        # mid-match by pressing LEFT — the match auto-pauses, the viewer
        # holds an older snapshot, and SPACE resumes live play.
        self._snapshots: list[ViewState] = []
        self._review_mode: bool = False
        self._review_idx: int = 0
        self._review_autoplay: bool = False
        self._review_autoplay_dir: int = +1   # +1 forward, -1 backward
        self._wall_t_last_review_step: float = 0.0
        # True while the live phase is running. Goes False after match.end().
        # Used by the review key handler to distinguish "resume live play"
        # (mid-match) from "toggle autoplay scrub" (post-match).
        self._match_live: bool = False

    # --- Renderer protocol (push) ----------------------------------------
    def start(self) -> None:
        import pygame
        pygame.init()
        pygame.display.set_caption("Hajime — match viewer (HAJ-126)")
        self._screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self._clock = pygame.time.Clock()
        self._font_small = pygame.font.SysFont("Consolas", 13)
        self._font_med   = pygame.font.SysFont("Consolas", 16, bold=True)
        self._font_big   = pygame.font.SysFont("Consolas", 22, bold=True)

    def stop(self) -> None:
        import pygame
        if pygame.get_init():
            pygame.quit()
        self._open = False

    def is_open(self) -> bool:
        return self._open

    def update(self, tick: int, match: "Match", events: "list[Event]") -> None:
        """Push hook called from inside Match.step(). Captures trails and
        events into the renderer's local buffers; the actual draw happens
        on the interactive loop's frame schedule, not here."""
        self._absorb_tick(tick, match, events)

    # --- Driver-style hooks (HAJ-126) -----------------------------------
    def drives_loop(self) -> bool:
        return True

    def run_interactive(self, match: "Match") -> None:
        """Own the wall-clock loop. Pump input every frame, advance the
        match according to pause / step / speed-scrub state, render.
        After match.end() is called, drop into review mode so the user
        can scrub backward through the captured snapshots."""
        import pygame
        match.begin()
        self._wall_t_last_step = time.monotonic()
        self._match_live = True

        match_resolved = False
        try:
            # Live phase — drive the match. Input dispatch flips to the
            # review handler when the user steps into mid-match review
            # (LEFT arrow); the loop keeps running until match.is_done(),
            # but the match doesn't advance while review is active.
            while self._open and not match.is_done():
                if self._review_mode:
                    self._handle_input_review()
                    self._advance_review_if_due()
                else:
                    self._handle_input(match)
                    self._advance_match_if_due(match)
                self._render_frame()
                self._frame_idx += 1
                self._clock.tick(60)   # 60 FPS render cap; sim pace is _tps

            # Match has ended (score, time-up, or window close). Resolve
            # for the narrative summary, then enter review mode if the
            # window is still open.
            try:
                match.end()
                match_resolved = True
            except Exception:
                raise

            self._match_live = False
            if not self._open:
                return

            # Auto-pause and start review at the final tick.
            self._enter_review_mode()

            # Review phase — user can scrub the captured history.
            while self._open:
                self._handle_input_review()
                self._advance_review_if_due()
                self._render_frame()
                self._frame_idx += 1
                self._clock.tick(60)
        finally:
            self._match_live = False
            if not match_resolved:
                # Window closed before resolution — still call end() so
                # the post-match summary fires for the log.
                try:
                    match.end()
                except Exception:
                    raise

    # --- Review mode helpers --------------------------------------------
    def _enter_review_mode(self) -> None:
        self._review_mode = True
        self._paused = True
        self._review_autoplay = False
        # Land on the most recent snapshot.
        self._review_idx = max(0, len(self._snapshots) - 1)

    def _handle_input_review(self) -> None:
        import pygame
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._open = False
                return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self._handle_click_review(ev.pos)
            if ev.type != pygame.KEYDOWN:
                continue
            k = ev.key
            if k == pygame.K_q or k == pygame.K_ESCAPE:
                # First Esc clears inspector if active; second quits.
                if self._inspect_target is not None and k == pygame.K_ESCAPE:
                    self._inspect_target = None
                else:
                    self._open = False
            elif k == pygame.K_LEFT:
                self._review_idx = max(0, self._review_idx - 1)
                self._review_autoplay = False
            elif k in (pygame.K_RIGHT, pygame.K_PERIOD):
                self._review_idx = min(
                    len(self._snapshots) - 1, self._review_idx + 1,
                )
                self._review_autoplay = False
            elif k == pygame.K_HOME:
                self._review_idx = 0
                self._review_autoplay = False
            elif k == pygame.K_END:
                self._review_idx = max(0, len(self._snapshots) - 1)
                self._review_autoplay = False
            elif k == pygame.K_SPACE:
                if self._match_live:
                    # Mid-match: SPACE exits review and resumes live play.
                    # The match was auto-paused on review entry; clearing
                    # both flags hands control back to the live phase.
                    self._review_mode = False
                    self._review_autoplay = False
                    self._paused = False
                    self._wall_t_last_step = time.monotonic()
                else:
                    # Post-match: toggle autoplay forward through history.
                    self._review_autoplay = not self._review_autoplay
                    self._review_autoplay_dir = +1
                    self._wall_t_last_review_step = time.monotonic()
            elif k == pygame.K_BACKSPACE:
                self._review_autoplay = not self._review_autoplay
                self._review_autoplay_dir = -1
                self._wall_t_last_review_step = time.monotonic()
            elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self._tps = min(MAX_TPS, self._tps * TPS_STEP_FACTOR)
            elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self._tps = max(MIN_TPS, self._tps / TPS_STEP_FACTOR)
            elif k == pygame.K_0:
                self._tps = self._initial_tps

    def _handle_click_review(self, pos: tuple[int, int]) -> None:
        # Hit-test against the snapshot's fighter positions.
        if not self._snapshots:
            return
        snap = self._snapshots[self._review_idx]
        T = self._transform
        click_x, click_y = pos
        hit: Optional[str] = None
        for fv in (snap.fighter_a, snap.fighter_b):
            cx, cy = T.world_to_screen(*fv.com_position)
            if (click_x - cx) ** 2 + (click_y - cy) ** 2 <= 16 ** 2:
                hit = fv.color_tag
                break
        if hit is None:
            if click_x < MAT_PANEL_W:
                self._inspect_target = None
        else:
            self._inspect_target = None if self._inspect_target == hit else hit

    def _advance_review_if_due(self) -> None:
        if not self._review_autoplay:
            return
        if not self._snapshots:
            return
        period = 1.0 / max(MIN_TPS, self._tps)
        now = time.monotonic()
        if now - self._wall_t_last_review_step < period:
            return
        self._wall_t_last_review_step = now
        new_idx = self._review_idx + self._review_autoplay_dir
        last = len(self._snapshots) - 1
        if new_idx < 0:
            new_idx = 0
            self._review_autoplay = False
        elif new_idx > last:
            new_idx = last
            self._review_autoplay = False
        self._review_idx = new_idx

    # --- Internal: input + advance ---------------------------------------
    def _handle_input(self, match: "Match") -> None:
        import pygame
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._open = False
                return
            if ev.type == pygame.KEYDOWN:
                self._handle_keydown(ev, match)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self._handle_click(ev.pos, match)

    def _handle_keydown(self, ev, match: "Match") -> None:
        import pygame
        if ev.key == pygame.K_SPACE:
            self._paused = not self._paused
        elif ev.key in (pygame.K_RIGHT, pygame.K_PERIOD):
            # Step one tick. Only meaningful when paused, but harmless
            # otherwise — _advance_match_if_due will also fire normally.
            self._step_request = True
        elif ev.key == pygame.K_LEFT:
            # Mid-match scrub-back: auto-pause and flip into review
            # showing the previous tick's snapshot. Keep pressing LEFT
            # to walk further backward; SPACE resumes live play.
            if self._snapshots:
                self._paused = True
                self._review_mode = True
                self._review_idx = max(0, len(self._snapshots) - 2)
                self._review_autoplay = False
        elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self._tps = min(MAX_TPS, self._tps * TPS_STEP_FACTOR)
        elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._tps = max(MIN_TPS, self._tps / TPS_STEP_FACTOR)
        elif ev.key == pygame.K_0:
            self._tps = self._initial_tps
        elif ev.key == pygame.K_ESCAPE:
            self._inspect_target = None
        elif ev.key == pygame.K_q:
            self._open = False

    def _handle_click(self, pos: tuple[int, int], match: "Match") -> None:
        T = self._transform
        names_in_order = (
            ("a", match.fighter_a, COL_FIGHTER_A),
            ("b", match.fighter_b, COL_FIGHTER_B),
        )
        # Hit-test against each fighter's screen position.
        click_x, click_y = pos
        hit: Optional[str] = None
        for tag, f, _ in names_in_order:
            cx, cy = T.world_to_screen(*f.state.body_state.com_position)
            if (click_x - cx) ** 2 + (click_y - cy) ** 2 <= 16 ** 2:
                hit = tag
                break
        if hit is None:
            # Click in mat panel but not on a fighter clears the inspector;
            # click in the sidebar leaves it alone.
            if click_x < MAT_PANEL_W:
                self._inspect_target = None
        else:
            # Toggle off if clicking the already-selected fighter.
            self._inspect_target = None if self._inspect_target == hit else hit

    def _advance_match_if_due(self, match: "Match") -> None:
        if match.is_done():
            return
        if self._paused and not self._step_request:
            return
        if self._step_request:
            self._step_request = False
            match.step()
            self._wall_t_last_step = time.monotonic()
            return
        # Free-running: step while we're behind on wall clock.
        period = 1.0 / self._tps
        now = time.monotonic()
        if now - self._wall_t_last_step >= period:
            match.step()
            self._wall_t_last_step = now

    # --- Internal: per-tick absorption (called from update()) ------------
    def _absorb_tick(self, tick: int, match: "Match", events: "list[Event]") -> None:
        # Watch for kuzushi events to flash halos. Track victims at this
        # tick so the snapshot can paint the same flash in review mode.
        kuzushi_victims: list[str] = []
        # HAJ-153 — count grip-seat events for the F5 multi-seat flash.
        grip_seat_this_tick: int = 0
        for e in events:
            if e.event_type == "KUZUSHI_INDUCED":
                victim = (e.data or {}).get("victim")
                if victim:
                    self._last_kuzushi_tick[victim] = tick
                    kuzushi_victims.append(victim)
                else:
                    for f in (match.fighter_a, match.fighter_b):
                        if f.identity.name in (e.description or ""):
                            self._last_kuzushi_tick[f.identity.name] = tick
                            kuzushi_victims.append(f.identity.name)
            elif e.event_type == "MATTE_CALLED":
                self._last_matte_tick = tick
                self._last_matte_reason = (e.data or {}).get("reason")
            elif e.event_type == "HAJIME_CALLED":
                # HAJ-160 — drive the hajime banner the same way as
                # matte: stamp the firing tick, let the draw helper
                # fade it out over HAJIME_BANNER_FRAMES.
                self._last_hajime_tick = tick
            elif e.event_type == "STUFFED":
                attacker = (e.data or {}).get("attacker")
                if not attacker:
                    desc = (e.description or "").split(" stuffed")[0]
                    for f in (match.fighter_a, match.fighter_b):
                        if f.identity.name in desc:
                            attacker = f.identity.name
                            break
                if attacker:
                    self._last_stuff_tick[attacker] = tick
            elif e.event_type in ("WAZA_ARI_AWARDED", "IPPON_AWARDED"):
                scorer = (e.data or {}).get("scorer") or (
                    e.data or {}).get("scorer_id"
                )
                if scorer:
                    self._last_score_tick[scorer] = tick
            elif e.event_type == "COUNTER_COMMIT":
                self._last_counter_tick = tick
                self._last_counter_attacker = (e.data or {}).get("defender")
                self._last_counter_target   = (e.data or {}).get("attacker")
            elif e.event_type == "GRIP_ESTABLISH":
                grip_seat_this_tick += 1
            # Stash narratively-significant events with a description
            # into the ticker. The threshold (default STANDS = 4)
            # drops per-tick mechanics — movement narration,
            # SUB_TSUKURI, SUB_KAKE_COMMIT, baseline grip churn — and
            # keeps narrative beats (kuzushi induction, grip kills,
            # throws, scores, referee). Significance is set on the
            # event at emit time by `significance_for(...)` in match.py
            # so by the time it reaches the renderer the floor is
            # already correct.
            if e.description and getattr(
                e, "significance", THRESHOLD_MAT_SIDE,
            ) >= self._ticker_altitude_threshold:
                self._event_log.append((tick, e.description, self._frame_idx))
        if grip_seat_this_tick >= GRIP_SEAT_THRESHOLD:
            self._last_grip_seat_tick = tick
        # Capture a frozen snapshot of everything the renderer needs to
        # draw THIS tick. Powers post-match scrubbing in review mode.
        self._snapshots.append(capture_view_state(
            match, tick, events, kuzushi_victims=tuple(kuzushi_victims),
        ))

    # --- Internal: rendering ---------------------------------------------
    def _current_view(self) -> Optional[ViewState]:
        """The ViewState that drives the current frame.

        - Live mode: most recent snapshot (or None pre-tick-0).
        - Review mode: snapshot at _review_idx.
        """
        if not self._snapshots:
            return None
        if self._review_mode:
            return self._snapshots[self._review_idx]
        return self._snapshots[-1]

    def _trail_positions(self, view: ViewState, tag: str) -> list[tuple[float, float]]:
        """Construct a trail tail by reading recent snapshots up to the
        currently-displayed view. Live mode shows the most recent
        TRAIL_LENGTH; review mode shows TRAIL_LENGTH preceding the
        review_idx so the trail is "what led up to this moment.\""""
        if self._review_mode:
            end = self._review_idx + 1
        else:
            end = len(self._snapshots)
        start = max(0, end - TRAIL_LENGTH)
        sl = self._snapshots[start:end]
        if tag == "a":
            return [s.fighter_a.com_position for s in sl]
        return [s.fighter_b.com_position for s in sl]

    def _ticks_since_kuzushi(self, view: ViewState, name: str) -> int:
        """How many ticks ago this fighter last had a KUZUSHI_INDUCED
        event. Live mode reads from the live decay marker; review mode
        scans the snapshot history backwards from the displayed tick."""
        if not self._review_mode:
            last = self._last_kuzushi_tick.get(name, -10**9)
            return view.tick - last
        # Review: scan back through snapshots up to and including the
        # currently-displayed one for any kuzushi flash on this fighter.
        for i in range(self._review_idx, -1, -1):
            snap = self._snapshots[i]
            if name in snap.kuzushi_victims:
                return view.tick - snap.tick
        return 10**9

    def _render_frame(self) -> None:
        import pygame
        view = self._current_view()
        screen = self._screen
        screen.fill(COL_BG)
        self._draw_mat(screen)
        if view is not None:
            self._draw_trails(screen, view)
            self._draw_grip_edges(screen, view)
            self._draw_kuzushi_halos(screen, view)
            self._draw_stuff_flashes(screen, view)
            self._draw_score_flashes(screen, view)
            self._draw_grip_seat_warning(screen, view)
            self._draw_fighters(screen, view)
            self._draw_hands(screen, view)
            self._draw_state_pills(screen, view)
            self._draw_follow_up_pill(screen, view)
            self._draw_counter_chevron(screen, view)
            self._draw_ne_waza_schematic(screen, view)
            self._draw_matte_banner(screen, view)
            self._draw_hajime_banner(screen, view)
        self._draw_pause_indicator(screen, view)
        self._draw_sidebar(screen, view)
        self._draw_footer_hint(screen)
        pygame.display.flip()

    # ------------------------------------------------------------------
    # HAJ-153 — interpolation, decay, and audit-driven render helpers
    # ------------------------------------------------------------------
    def _interp_alpha(self) -> float:
        """Tick-fraction in [0, 1] used to tween fighter positions
        between consecutive snapshots. 0 means we just absorbed the
        current snapshot; 1 means we're due to absorb the next one.

        Live mode: derive from wall-clock since the last sim step,
        scaled by tps. Review mode / paused: 1.0 so the discrete
        snapshot renders without drift."""
        if self._review_mode or self._paused:
            return 1.0
        if not self._snapshots:
            return 1.0
        period = 1.0 / max(self._tps, MIN_TPS)
        if period <= 0.0:
            return 1.0
        elapsed = time.monotonic() - self._wall_t_last_step
        return max(0.0, min(1.0, elapsed / period))

    def _interpolated_com(
        self, view: ViewState, tag: str,
    ) -> tuple[float, float]:
        """HAJ-153 — tween fighter CoM between previous and current
        snapshots so per-tick position changes don't render as
        teleports. Falls back to the snapshot value when there's no
        previous snapshot or in review mode."""
        if not self._snapshots:
            fv = view.fighter_a if tag == "a" else view.fighter_b
            return fv.com_position
        # Find the index of `view` in the snapshot list — usually the
        # last one (live), otherwise wherever review_idx points.
        if self._review_mode:
            idx = self._review_idx
        else:
            idx = len(self._snapshots) - 1
        if idx <= 0:
            fv = view.fighter_a if tag == "a" else view.fighter_b
            return fv.com_position
        prev = self._snapshots[idx - 1]
        cur  = self._snapshots[idx]
        prev_f = prev.fighter_a if tag == "a" else prev.fighter_b
        cur_f  = cur.fighter_a  if tag == "a" else cur.fighter_b
        a = self._interp_alpha()
        return (
            prev_f.com_position[0] + (cur_f.com_position[0] - prev_f.com_position[0]) * a,
            prev_f.com_position[1] + (cur_f.com_position[1] - prev_f.com_position[1]) * a,
        )

    def _interpolated_facing(
        self, view: ViewState, tag: str,
    ) -> tuple[float, float]:
        if not self._snapshots:
            fv = view.fighter_a if tag == "a" else view.fighter_b
            return fv.facing
        if self._review_mode:
            idx = self._review_idx
        else:
            idx = len(self._snapshots) - 1
        if idx <= 0:
            fv = view.fighter_a if tag == "a" else view.fighter_b
            return fv.facing
        prev = self._snapshots[idx - 1]
        cur  = self._snapshots[idx]
        prev_f = prev.fighter_a if tag == "a" else prev.fighter_b
        cur_f  = cur.fighter_a  if tag == "a" else cur.fighter_b
        a = self._interp_alpha()
        return (
            prev_f.facing[0] + (cur_f.facing[0] - prev_f.facing[0]) * a,
            prev_f.facing[1] + (cur_f.facing[1] - prev_f.facing[1]) * a,
        )

    def _interpolated_hand_positions(
        self, view: ViewState, tag: str,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Recompute hand positions from the interpolated CoM + facing
        so they track the tweened body, not the snapshot body."""
        com = self._interpolated_com(view, tag)
        facing = self._interpolated_facing(view, tag)
        return _hand_positions(com, facing)

    def _ticks_since_event(self, view: ViewState, last_tick: int) -> int:
        """How many ticks ago an event last fired, relative to the
        view's tick. Returns a sentinel large value when nothing has
        fired yet (so callers can compare against a lifetime threshold
        and skip cleanly)."""
        if last_tick < 0:
            return 10**9
        return view.tick - last_tick

    def _frames_into_cue(self, last_tick: int) -> int:
        """How many viewer frames into the cue we are. Uses the
        wall-clock fraction so the cue fades smoothly at 60 FPS over
        the configured lifetime."""
        if last_tick < 0:
            return 10**9
        if self._review_mode:
            # Review mode renders the cue for exactly one tick of
            # real-time at full intensity.
            return 0 if (
                self._snapshots and
                self._snapshots[self._review_idx].tick == last_tick
            ) else 10**9
        elapsed = time.monotonic() - self._wall_t_last_step
        period  = 1.0 / max(self._tps, MIN_TPS)
        ticks_since = max(0, self._frame_view_tick() - last_tick)
        # Approximate: ticks_since * frames-per-tick + intra-tick frames.
        frames_per_tick = max(1, int(round(60.0 * period)))
        intra = int(min(frames_per_tick, max(0, elapsed / period * frames_per_tick)))
        return ticks_since * frames_per_tick + intra

    def _frame_view_tick(self) -> int:
        """The tick the current frame's view is centered on."""
        v = self._current_view()
        return v.tick if v is not None else 0

    def _draw_mat(self, screen) -> None:
        import pygame
        T = self._transform
        sx_tl, sy_tl = T.world_to_screen(-VISIBLE_MAT_M / 2, +VISIBLE_MAT_M / 2)
        sx_br, sy_br = T.world_to_screen(+VISIBLE_MAT_M / 2, -VISIBLE_MAT_M / 2)
        outer = pygame.Rect(sx_tl, sy_tl, sx_br - sx_tl, sy_br - sy_tl)
        pygame.draw.rect(screen, COL_SAFETY, outer)
        cx_tl, cy_tl = T.world_to_screen(-CONTEST_M / 2, +CONTEST_M / 2)
        cx_br, cy_br = T.world_to_screen(+CONTEST_M / 2, -CONTEST_M / 2)
        contest = pygame.Rect(cx_tl, cy_tl, cx_br - cx_tl, cy_br - cy_tl)
        pygame.draw.rect(screen, COL_CONTEST, contest)
        ox, oy = T.world_to_screen(0, 0)
        pygame.draw.line(screen, COL_GRID, (ox - 6, oy), (ox + 6, oy), 1)
        pygame.draw.line(screen, COL_GRID, (ox, oy - 6), (ox, oy + 6), 1)

    def _draw_trails(self, screen, view: ViewState) -> None:
        import pygame
        T = self._transform
        for tag, color in (("a", COL_TRAIL_A), ("b", COL_TRAIL_B)):
            trail = self._trail_positions(view, tag)
            n = len(trail)
            if n < 2:
                continue
            for i in range(1, n):
                alpha = int(40 + 180 * (i / n))
                surf = pygame.Surface((2, 2), pygame.SRCALPHA)
                surf.fill((*color, alpha))
                px, py = T.world_to_screen(*trail[i])
                screen.blit(surf, (px - 1, py - 1))

    def _draw_grip_edges(self, screen, view: ViewState) -> None:
        """HAJ-128 — grip lines now run from the grasper's hand dot to
        the opponent's body (CoM), so the viewer shows which hand owns
        which grip rather than a generic body-to-body line.

        HAJ-153 — endpoints track the interpolated hand / CoM positions
        so the grip line tweens with the body during the wall-clock
        interval between sim ticks, instead of snapping each tick.
        """
        import pygame
        T = self._transform
        a, b = view.fighter_a, view.fighter_b
        a_left, a_right = self._interpolated_hand_positions(view, "a")
        b_left, b_right = self._interpolated_hand_positions(view, "b")
        a_com = self._interpolated_com(view, "a")
        b_com = self._interpolated_com(view, "b")
        ax, ay = T.world_to_screen(*a_com)
        bx, by = T.world_to_screen(*b_com)
        for edge in view.grip_edges:
            mode = GripMode(edge.mode_value)
            color = _grip_mode_color(mode)
            on_a = edge.grasper_id == a.name
            target_com = (bx, by) if on_a else (ax, ay)
            # Hand dot to use depends on which body part is gripping.
            if edge.grasper_part_name == "RIGHT_HAND":
                hand_pos = a_right if on_a else b_right
            elif edge.grasper_part_name == "LEFT_HAND":
                hand_pos = a_left if on_a else b_left
            else:
                hand_pos = a_com if on_a else b_com
            hp = T.world_to_screen(*hand_pos)
            # HAJ-153 F5 — bright the line if the multi-grip-seat warning
            # is currently active for this tick.
            if not self._review_mode:
                ts = self._ticks_since_event(view, self._last_grip_seat_tick)
                bright = ts == 0
            else:
                bright = view.grip_seat_count >= GRIP_SEAT_THRESHOLD
            line_col = COL_GRIP_FLASH if bright else color
            line_w = 3 if bright else 2
            pygame.draw.line(screen, line_col, hp, target_com, line_w)

    def _draw_kuzushi_halos(self, screen, view: ViewState) -> None:
        import pygame
        T = self._transform
        for fv in (view.fighter_a, view.fighter_b):
            mag = abs(fv.trunk_sagittal) + abs(fv.trunk_frontal)
            ticks_since = self._ticks_since_kuzushi(view, fv.name)
            flash = max(0.0, 1.0 - ticks_since / 5.0) if ticks_since >= 0 else 0.0
            base_alpha = int(min(255, mag * 200))
            flash_alpha = int(min(255, flash * 255))
            alpha = max(base_alpha, flash_alpha)
            if alpha <= 0:
                continue
            radius_px = T.meters_to_pixels(0.55) + (8 if flash > 0.5 else 0)
            cx, cy = T.world_to_screen(*fv.com_position)
            halo = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                halo, (*COL_KUZUSHI, alpha),
                (radius_px, radius_px), radius_px,
            )
            screen.blit(halo, (cx - radius_px, cy - radius_px))

    def _draw_fighters(self, screen, view: ViewState) -> None:
        import pygame
        T = self._transform
        for fv, color in (
            (view.fighter_a, COL_FIGHTER_A),
            (view.fighter_b, COL_FIGHTER_B),
        ):
            com = self._interpolated_com(view, fv.color_tag)
            cx, cy = T.world_to_screen(*com)
            pygame.draw.circle(screen, color, (cx, cy), 9)
            if self._inspect_target == fv.color_tag:
                pygame.draw.circle(screen, COL_INSPECT, (cx, cy), 13, 2)
            facing = self._interpolated_facing(view, fv.color_tag)
            tip_m = (
                com[0] + facing[0] * 0.45,
                com[1] + facing[1] * 0.45,
            )
            tx, ty = T.world_to_screen(*tip_m)
            pygame.draw.line(screen, COL_FACING, (cx, cy), (tx, ty), 2)

    def _draw_hands(self, screen, view: ViewState) -> None:
        """HAJ-128 — render hand dots in place of foot dots. In judo the
        hands ARE the throw — knowing which hand grips where reads more
        cleanly than ankle positions. A bright hand owns a grip edge;
        a dim hand is free.

        HAJ-153 — hands track the interpolated CoM/facing so they tween
        with the body during the wall-clock interval between sim ticks.
        """
        import pygame
        T = self._transform
        for fv, grip_col, free_col in (
            (view.fighter_a, COL_HAND_A_GRIP, COL_HAND_A_FREE),
            (view.fighter_b, COL_HAND_B_GRIP, COL_HAND_B_FREE),
        ):
            l_col = grip_col if fv.hand_l_gripping else free_col
            r_col = grip_col if fv.hand_r_gripping else free_col
            left, right = self._interpolated_hand_positions(view, fv.color_tag)
            for pos, col in ((left, l_col), (right, r_col)):
                hx, hy = T.world_to_screen(*pos)
                pygame.draw.circle(screen, col, (hx, hy), 4)

    # ------------------------------------------------------------------
    # HAJ-153 — visual cues for engine events
    # ------------------------------------------------------------------
    def _draw_state_pills(self, screen, view: ViewState) -> None:
        """Render a one-or-two-word state label above each fighter's
        CoM dot. Surfaces THROW / STUN N / OFF-DESP / DEF-DESP /
        GRIPS N / DISTANT so the reader can tell at a glance what each
        fighter is currently doing without piecing together log
        lines (HAJ-153 finding F1)."""
        import pygame
        T = self._transform
        for fv in (view.fighter_a, view.fighter_b):
            label = fv.state_pill
            # When no pill is active, show DISTANT for STANDING_DISTANT
            # so the empty state is still legible.
            if not label and view.position_name == "STANDING_DISTANT":
                label = "DISTANT"
            if not label:
                continue
            com = self._interpolated_com(view, fv.color_tag)
            cx, cy = T.world_to_screen(*com)
            text = self._font_small.render(label, True, COL_TEXT)
            tw, th = text.get_size()
            pad_x, pad_y = 4, 2
            rect = pygame.Rect(
                cx - tw // 2 - pad_x,
                cy - 26 - th - pad_y,
                tw + 2 * pad_x,
                th + 2 * pad_y,
            )
            pygame.draw.rect(screen, COL_PILL_BG, rect)
            pygame.draw.rect(screen, COL_PILL_BORDER, rect, 1)
            screen.blit(text, (rect.x + pad_x, rect.y + pad_y))

    def _draw_follow_up_pill(self, screen, view: ViewState) -> None:
        """HAJ-152 follow-up window indicator. Renders a coloured pill
        above the scoring fighter's pill while the post-score follow-up
        is open. Reads CHASING / STAND / DEFENSIVE based on the chase
        decision; while the decision is still pending shows FOLLOW-UP.
        """
        import pygame
        if not view.follow_up_scorer:
            return
        T = self._transform
        decision = view.follow_up_decision
        if decision == "CHASE":
            label = "CHASING"
        elif decision == "DEFENSIVE_CHASE":
            label = "DEFENSIVE"
        elif decision == "STAND":
            label = "STAND"
        else:
            label = "FOLLOW-UP"
        scorer = (
            view.fighter_a if view.follow_up_scorer == view.fighter_a.name
            else view.fighter_b
        )
        com = self._interpolated_com(view, scorer.color_tag)
        cx, cy = T.world_to_screen(*com)
        text = self._font_small.render(label, True, COL_BG)
        tw, th = text.get_size()
        pad_x, pad_y = 5, 2
        # Sit above the state pill (which is offset 26px above CoM).
        rect = pygame.Rect(
            cx - tw // 2 - pad_x,
            cy - 26 - th - pad_y - 22,
            tw + 2 * pad_x,
            th + 2 * pad_y,
        )
        pygame.draw.rect(screen, COL_FOLLOW_UP, rect)
        screen.blit(text, (rect.x + pad_x, rect.y + pad_y))

    def _draw_matte_banner(self, screen, view: ViewState) -> None:
        """Centered banner that fades out over MATTE_BANNER_FRAMES after
        any MATTE_CALLED event. Reason text appended in the smaller
        font so the reader can distinguish stalemate / post-score /
        stuffed-throw / OOB matte at a glance."""
        import pygame
        # Live mode reads the decay marker; review mode reads the
        # snapshot's matte_reason field directly.
        if self._review_mode:
            reason = view.matte_reason
            if not reason:
                return
            alpha = 1.0
        else:
            ticks_since = self._ticks_since_event(view, self._last_matte_tick)
            if ticks_since >= MATTE_BANNER_TICKS:
                return
            reason = self._last_matte_reason
            if not reason:
                return
            elapsed = time.monotonic() - self._wall_t_last_step
            period = 1.0 / max(self._tps, MIN_TPS)
            tick_phase = max(0.0, min(1.0, elapsed / period))
            # Hold full alpha for the early ticks of the pause, then fade
            # out across the final tick so hajime can overwrite cleanly.
            ticks_remaining = MATTE_BANNER_TICKS - 1 - ticks_since
            if ticks_remaining > 0:
                alpha = 1.0
            else:
                alpha = max(0.0, 1.0 - tick_phase)
            if alpha <= 0.0:
                return

        T = self._transform
        banner_w = T.panel_w - 240
        banner_h = 70
        banner_x = (T.panel_w - banner_w) // 2
        banner_y = T.panel_h // 2 - banner_h // 2
        banner = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        bg_alpha = int(220 * alpha)
        banner.fill((*COL_MATTE_BG, bg_alpha))
        title = self._font_big.render("MATTE", True, COL_MATTE_TEXT)
        sub = self._font_small.render(
            self._matte_reason_label(reason), True, COL_MATTE_TEXT,
        )
        banner.blit(
            title, (banner_w // 2 - title.get_width() // 2, 12),
        )
        banner.blit(
            sub, (banner_w // 2 - sub.get_width() // 2, 44),
        )
        # Fade text alpha by re-blitting onto a full-alpha rect.
        if alpha < 1.0:
            banner.set_alpha(int(255 * alpha))
        screen.blit(banner, (banner_x, banner_y))

    @staticmethod
    def _matte_reason_label(reason: Optional[str]) -> str:
        return {
            "STALEMATE":             "stalemate",
            "OUT_OF_BOUNDS":         "out of bounds",
            "STUFFED_THROW_TIMEOUT": "stuffed throw — reset",
            "INJURY":                "injury",
            "OSAEKOMI_DECISION":     "osaekomi decision",
            "POST_SCORE_FOLLOW_UP_END": "post-score reset",
        }.get(reason or "", reason or "")

    def _draw_hajime_banner(self, screen, view: ViewState) -> None:
        """HAJ-160 — centered HAJIME banner symmetric with the matte
        banner. Fires on the match-start hajime (t000) and on the
        restart-hajime that follows every matte. Fades out over
        HAJIME_BANNER_FRAMES, mirroring the matte banner's persistence
        so the matte → restart cycle reads as balanced beats.

        Color treatment is green to distinguish "go" from the matte
        banner's red "stop." Same render position, same font, same
        size — the eye reads stop / restart as a paired rhythm.
        """
        import pygame
        # Live mode reads the decay marker; review mode reads the
        # snapshot's hajime_called field directly so scrubbing back
        # through the post-tick captures shows the banner exactly when
        # the engine fired the hajime.
        if self._review_mode:
            if not view.hajime_called:
                return
            alpha = 1.0
        else:
            ticks_since = self._ticks_since_event(view, self._last_hajime_tick)
            if ticks_since >= HAJIME_BANNER_TICKS:
                return
            elapsed = time.monotonic() - self._wall_t_last_step
            period = 1.0 / max(self._tps, MIN_TPS)
            tick_phase = max(0.0, min(1.0, elapsed / period))
            ticks_remaining = HAJIME_BANNER_TICKS - 1 - ticks_since
            if ticks_remaining > 0:
                alpha = 1.0
            else:
                alpha = max(0.0, 1.0 - tick_phase)
            if alpha <= 0.0:
                return

        T = self._transform
        banner_w = T.panel_w - 240
        banner_h = 70
        banner_x = (T.panel_w - banner_w) // 2
        banner_y = T.panel_h // 2 - banner_h // 2
        banner = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        bg_alpha = int(220 * alpha)
        banner.fill((*COL_HAJIME_BG, bg_alpha))
        title = self._font_big.render("HAJIME", True, COL_HAJIME_TEXT)
        sub = self._font_small.render(
            "begin", True, COL_HAJIME_TEXT,
        )
        banner.blit(
            title, (banner_w // 2 - title.get_width() // 2, 12),
        )
        banner.blit(
            sub, (banner_w // 2 - sub.get_width() // 2, 44),
        )
        if alpha < 1.0:
            banner.set_alpha(int(255 * alpha))
        screen.blit(banner, (banner_x, banner_y))

    def _draw_stuff_flashes(self, screen, view: ViewState) -> None:
        """Render a brief impact flash on a stuffed fighter's CoM dot.
        Live mode reads the decay marker; review mode reads the
        snapshot's stuff_victims field."""
        import pygame
        T = self._transform
        for fv in (view.fighter_a, view.fighter_b):
            if self._review_mode:
                flash = 1.0 if fv.name in view.stuff_victims else 0.0
            else:
                last = self._last_stuff_tick.get(fv.name, -10**9)
                ticks_since = self._ticks_since_event(view, last)
                if ticks_since > 1:
                    flash = 0.0
                elif ticks_since == 0:
                    elapsed = time.monotonic() - self._wall_t_last_step
                    period  = 1.0 / max(self._tps, MIN_TPS)
                    flash = max(0.0, 1.0 - elapsed / period)
                else:
                    flash = 0.0
            if flash <= 0.0:
                continue
            com = self._interpolated_com(view, fv.color_tag)
            cx, cy = T.world_to_screen(*com)
            radius = T.meters_to_pixels(0.45) + 4
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            alpha = int(min(255, flash * 220))
            pygame.draw.circle(
                surf, (*COL_STUFF_FLASH, alpha),
                (radius, radius), radius, 3,
            )
            screen.blit(surf, (cx - radius, cy - radius))

    def _draw_score_flashes(self, screen, view: ViewState) -> None:
        """Score award flash on the scoring fighter."""
        import pygame
        T = self._transform
        for fv in (view.fighter_a, view.fighter_b):
            if self._review_mode:
                flash = 1.0 if fv.name == view.score_scorer else 0.0
            else:
                last = self._last_score_tick.get(fv.name, -10**9)
                ticks_since = self._ticks_since_event(view, last)
                if ticks_since > 1:
                    flash = 0.0
                elif ticks_since == 0:
                    elapsed = time.monotonic() - self._wall_t_last_step
                    period  = 1.0 / max(self._tps, MIN_TPS)
                    flash = max(0.0, 1.0 - elapsed / period)
                else:
                    flash = 0.0
            if flash <= 0.0:
                continue
            com = self._interpolated_com(view, fv.color_tag)
            cx, cy = T.world_to_screen(*com)
            radius = T.meters_to_pixels(0.55) + 6
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            alpha = int(min(255, flash * 220))
            pygame.draw.circle(
                surf, (*COL_SCORE_FLASH, alpha),
                (radius, radius), radius, 4,
            )
            screen.blit(surf, (cx - radius, cy - radius))

    def _draw_grip_seat_warning(self, screen, view: ViewState) -> None:
        """HAJ-144 t003 finding (F5) — when 3+ GRIP_ESTABLISH events
        seat on a single tick, mark the dyad with a warning ring on
        each fighter so the anomaly visually surfaces."""
        import pygame
        T = self._transform
        if self._review_mode:
            active = view.grip_seat_count >= GRIP_SEAT_THRESHOLD
            flash  = 1.0 if active else 0.0
        else:
            ticks_since = self._ticks_since_event(view, self._last_grip_seat_tick)
            if ticks_since > 1:
                flash = 0.0
            elif ticks_since == 0:
                elapsed = time.monotonic() - self._wall_t_last_step
                period  = 1.0 / max(self._tps, MIN_TPS)
                flash = max(0.0, 1.0 - elapsed / period)
            else:
                flash = 0.0
        if flash <= 0.0:
            return
        for fv in (view.fighter_a, view.fighter_b):
            com = self._interpolated_com(view, fv.color_tag)
            cx, cy = T.world_to_screen(*com)
            radius = T.meters_to_pixels(0.65) + 2
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            alpha = int(min(255, flash * 200))
            pygame.draw.circle(
                surf, (*COL_GRIP_FLASH, alpha),
                (radius, radius), radius, 2,
            )
            screen.blit(surf, (cx - radius, cy - radius))

    def _draw_counter_chevron(self, screen, view: ViewState) -> None:
        """Brief chevron between the counter-attacker and the original
        attacker so a counter throw is visually distinct from a
        regular commit."""
        import pygame
        T = self._transform
        if self._review_mode:
            attacker = view.counter_attacker
            target   = view.counter_target
            flash = 1.0 if attacker and target else 0.0
        else:
            ticks_since = self._ticks_since_event(view, self._last_counter_tick)
            if ticks_since > 1:
                return
            attacker = self._last_counter_attacker
            target   = self._last_counter_target
            if not attacker or not target:
                return
            elapsed = time.monotonic() - self._wall_t_last_step
            period  = 1.0 / max(self._tps, MIN_TPS)
            flash = max(0.0, 1.0 - elapsed / period) if ticks_since == 0 else 0.0
        if flash <= 0.0 or not attacker or not target:
            return
        # Resolve names to figs and draw a chevron from attacker to target.
        a = view.fighter_a
        b = view.fighter_b
        if attacker == a.name:
            from_fv, to_fv = a, b
        elif attacker == b.name:
            from_fv, to_fv = b, a
        else:
            return
        from_com = self._interpolated_com(view, from_fv.color_tag)
        to_com   = self._interpolated_com(view, to_fv.color_tag)
        sx, sy = T.world_to_screen(*from_com)
        tx, ty = T.world_to_screen(*to_com)
        # Solid chevron — alpha is implicit via flash gating above.
        pygame.draw.line(screen, COL_COUNTER, (sx, sy), (tx, ty), 3)
        # Arrowhead at the target end.
        import math
        ang = math.atan2(ty - sy, tx - sx)
        ah = 12
        for sgn in (-1, +1):
            ex = tx - ah * math.cos(ang - sgn * 0.45)
            ey = ty - ah * math.sin(ang - sgn * 0.45)
            pygame.draw.line(
                screen, COL_COUNTER, (tx, ty), (int(ex), int(ey)), 3,
            )

    def _draw_ne_waza_schematic(self, screen, view: ViewState) -> None:
        """When the dyad is on the ground, render a small schematic at
        the dyad midpoint indicating the position and which fighter is
        on top. Stylised — top fighter is a larger filled circle, bottom
        is a smaller offset circle, line between the two. The position
        name (GUARD_TOP / SIDE_CONTROL / MOUNT / BACK_CONTROL /
        TURTLE_*) renders below."""
        import pygame
        if view.sub_loop_name != "NE_WAZA":
            return
        T = self._transform
        # Compute dyad midpoint from the interpolated CoMs.
        a_com = self._interpolated_com(view, "a")
        b_com = self._interpolated_com(view, "b")
        mx = (a_com[0] + b_com[0]) / 2.0
        my = (a_com[1] + b_com[1]) / 2.0
        cx, cy = T.world_to_screen(mx, my)
        # Identify top + bottom by ne_waza_top_name.
        top_name = view.ne_waza_top_name
        if top_name == view.fighter_a.name:
            top_col, bot_col = COL_FIGHTER_A, COL_FIGHTER_B
        elif top_name == view.fighter_b.name:
            top_col, bot_col = COL_FIGHTER_B, COL_FIGHTER_A
        else:
            top_col = COL_NE_TOP
            bot_col = COL_NE_BOT
        # Offset the schematic slightly above the dyad midpoint so it
        # doesn't overlap the existing fighter dots.
        sch_x = cx
        sch_y = cy - 38
        # Bottom (larger ring, offset down).
        pygame.draw.circle(screen, bot_col, (sch_x, sch_y + 6), 9, 2)
        # Top (filled, slightly higher).
        pygame.draw.circle(screen, top_col, (sch_x, sch_y - 4), 7)
        # Connector line.
        pygame.draw.line(
            screen, COL_NE_TOP,
            (sch_x, sch_y - 4), (sch_x, sch_y + 6), 2,
        )
        # Position label.
        label = view.position_name
        text = self._font_small.render(label, True, COL_TEXT)
        screen.blit(
            text,
            (sch_x - text.get_width() // 2, sch_y + 18),
        )

    def _draw_pause_indicator(self, screen, view: Optional[ViewState]) -> None:
        import pygame
        if self._review_mode:
            last = max(0, len(self._snapshots) - 1)
            cur = view.tick if view else 0
            if self._match_live:
                label = self._font_med.render(
                    f"SCRUB-BACK  tick {cur}/{last}  "
                    f"(← →: scrub   space: resume live)",
                    True, COL_PAUSE_BAR,
                )
            else:
                label = self._font_med.render(
                    f"REVIEW  tick {cur}/{last}  "
                    f"(← →: scrub   space: autoplay   "
                    f"backspace: rewind   home/end: ends)",
                    True, COL_PAUSE_BAR,
                )
            screen.blit(label, (16, 12))
            return
        if not self._paused:
            return
        label = self._font_med.render(
            f"PAUSED  (tps {self._tps:.2f})", True, COL_PAUSE_BAR,
        )
        screen.blit(label, (16, 12))

    def _draw_sidebar(self, screen, view: Optional[ViewState]) -> None:
        import pygame
        x0 = WINDOW_W - SIDEBAR_W
        panel = pygame.Rect(x0, 0, SIDEBAR_W, WINDOW_H)
        pygame.draw.rect(screen, COL_PANEL, panel)

        if view is not None:
            if self._inspect_target is None:
                self._draw_summary(screen, view, x0)
            else:
                fv = (view.fighter_a if self._inspect_target == "a"
                      else view.fighter_b)
                self._draw_inspector(screen, view, fv, x0)

        self._draw_ticker(screen, x0)

    def _draw_summary(self, screen, view: ViewState, x0: int) -> None:
        a, b = view.fighter_a, view.fighter_b
        remaining = max(0, view.max_ticks - view.tick)
        clock = f"{remaining // 60}:{remaining % 60:02d}"
        if self._review_mode:
            speed_mark = "REVIEW MODE"
        else:
            speed_mark = (f"{self._tps:.2f}× ticks/sec"
                          f"{' [paused]' if self._paused else ''}")
        lines: list[tuple[str, tuple]] = [
            (f"tick {view.tick:03d}/{view.max_ticks}    {clock}", COL_TEXT),
            (speed_mark, COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"position:    {view.position_name}", COL_TEXT),
            (f"sub-loop:    {view.sub_loop_name}", COL_TEXT),
            ("", COL_TEXT),
            (f"  {a.name}", COL_FIGHTER_A),
            (f"   waza-ari {a.score_waza_ari}   shidos {a.shidos}", COL_TEXT_DIM),
            (f"   composure {a.composure_current:.2f}/"
             f"{a.composure_ceiling:.0f}", COL_TEXT_DIM),
            (f"   stance {a.stance_name}", COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"  {b.name}", COL_FIGHTER_B),
            (f"   waza-ari {b.score_waza_ari}   shidos {b.shidos}", COL_TEXT_DIM),
            (f"   composure {b.composure_current:.2f}/"
             f"{b.composure_ceiling:.0f}", COL_TEXT_DIM),
            (f"   stance {b.stance_name}", COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"matchup:     {view.matchup_name}", COL_TEXT),
            (f"edges:       {view.edge_count}", COL_TEXT_DIM),
        ]
        y = 14
        for text, color in lines:
            if text:
                surf = self._font_small.render(text, True, color)
                screen.blit(surf, (x0 + 12, y))
            y += 18

    def _draw_inspector(
        self, screen, view: ViewState, fv: FighterView, x0: int,
    ) -> None:
        import pygame
        pygame.draw.rect(screen, COL_PANEL_ALT,
                         pygame.Rect(x0, 0, SIDEBAR_W, WINDOW_H - TICKER_H - FOOTER_H))
        cf = COL_FIGHTER_A if fv.color_tag == "a" else COL_FIGHTER_B
        head = self._font_big.render(f"{fv.name}  [inspect]", True, cf)
        screen.blit(head, (x0 + 12, 10))

        own_edges = [e for e in view.grip_edges if e.grasper_id == fv.name]

        lines: list[tuple[str, tuple]] = [
            (f"belt {fv.belt_name}   {fv.archetype_name}   age {fv.age}",
             COL_TEXT_DIM),
            (f"stance {fv.stance_name}   dom {fv.dominant_side}",
             COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"score: waza-ari {fv.score_waza_ari}   "
             f"ippon {fv.score_ippon}   shidos {fv.shidos}", COL_TEXT),
            ("", COL_TEXT),
            ("composure / cardio / stun:", COL_TEXT),
            (f"  composure  {fv.composure_current:.2f} / "
             f"{fv.composure_ceiling:.0f}", COL_TEXT_DIM),
            (f"  cardio     {fv.cardio_current:.3f}", COL_TEXT_DIM),
            (f"  stun_ticks {fv.stun_ticks}", COL_TEXT_DIM),
            ("", COL_TEXT),
            ("body fatigue:", COL_TEXT),
        ]
        for part_key, eff, fat in fv.body_parts:
            lines.append((
                f"  {part_key:<11} eff {eff:.2f}  fat {fat:.3f}",
                COL_TEXT_DIM,
            ))
        lines.extend([
            ("", COL_TEXT),
            ("body state:", COL_TEXT),
            (f"  com_pos    ({fv.com_position[0]:+.2f}, "
             f"{fv.com_position[1]:+.2f}) m", COL_TEXT_DIM),
            (f"  trunk_sag  {fv.trunk_sagittal:+.3f} rad", COL_TEXT_DIM),
            (f"  trunk_frt  {fv.trunk_frontal:+.3f} rad", COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"clocks: kumi-kata {fv.kumi_kata_clock}", COL_TEXT),
            (f"        last_attack {fv.last_attack_tick}", COL_TEXT_DIM),
            ("", COL_TEXT),
            ("desperation:", COL_TEXT),
            (f"  offensive {fv.off_desperation}", COL_TEXT_DIM),
            (f"  defensive {fv.def_desperation}", COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"grips ({len(own_edges)}):", COL_TEXT),
        ])
        for e in own_edges:
            lines.append((
                f"  {e.grasper_part_name:<10} → {e.target_loc_name:<14} "
                f"{e.grip_type_name:<12} {e.depth_name:<10} "
                f"{GripMode(e.mode_value).name}",
                COL_TEXT_DIM,
            ))
        if not own_edges:
            lines.append(("  (none)", COL_TEXT_DIM))

        y = 42
        for text, color in lines:
            if text:
                surf = self._font_small.render(text, True, color)
                screen.blit(surf, (x0 + 12, y))
            y += 16
            if y > WINDOW_H - TICKER_H - FOOTER_H - 8:
                break

    def _draw_ticker(self, screen, x0: int) -> None:
        import pygame
        ticker_y0 = WINDOW_H - TICKER_H - FOOTER_H
        bg = pygame.Rect(x0, ticker_y0, SIDEBAR_W, TICKER_H)
        pygame.draw.rect(screen, COL_PANEL_ALT, bg)
        pygame.draw.line(screen, COL_GRID,
                         (x0, ticker_y0), (WINDOW_W, ticker_y0), 1)

        title_text = ("event ticker (review)" if self._review_mode
                      else "event ticker")
        title = self._font_med.render(title_text, True, COL_TEXT_DIM)
        screen.blit(title, (x0 + 12, ticker_y0 + 6))

        # In review mode, show only events at or before the current tick
        # so the ticker reflects what's visible on the mat.
        if self._review_mode and self._snapshots:
            cutoff = self._snapshots[self._review_idx].tick
            events = [(t, d, fs) for (t, d, fs) in self._event_log
                      if t <= cutoff]
        else:
            events = list(self._event_log)
        events.reverse()  # newest at top

        # Pixel budget for one rendered line of body text, after the
        # tick prefix. Sidebar minus left+right padding minus ~38px for
        # the "tNNN " tick stamp leaves the body wrap budget.
        wrap_px = SIDEBAR_W - 2 * TICKER_PAD_X - 38
        max_y = ticker_y0 + TICKER_H - TICKER_LINE_H
        y = ticker_y0 + 30
        for ev_tick, desc, frame_seen in events:
            if y > max_y:
                break
            if self._review_mode:
                color = COL_TEXT_DIM
            else:
                age = self._frame_idx - frame_seen
                color = (COL_TEXT_NEW
                         if age <= NEW_EVENT_HIGHLIGHT_FRAMES
                         else COL_TEXT_DIM)
            # Render the tick prefix on the first line; wrap the body
            # across as many lines as needed and indent the continuations
            # so wrapped events read as a single block.
            prefix = f"t{ev_tick:03d} "
            lines = self._wrap_text(desc, self._font_small, wrap_px)
            if not lines:
                continue
            first = self._font_small.render(prefix + lines[0], True, color)
            screen.blit(first, (x0 + TICKER_PAD_X, y))
            y += TICKER_LINE_H
            indent_x = x0 + TICKER_PAD_X + len(prefix) * 7
            for cont in lines[1:]:
                if y > max_y:
                    break
                surf = self._font_small.render(cont, True, color)
                screen.blit(surf, (indent_x, y))
                y += TICKER_LINE_H

    @staticmethod
    def _wrap_text(text: str, font, max_px: int) -> list[str]:
        """Word-wrap `text` so each rendered line fits within `max_px`.
        Falls back to character splits for words longer than the budget
        (e.g. URL-like strings without spaces).
        """
        if not text:
            return []
        words = text.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else current + " " + word
            if font.size(candidate)[0] <= max_px:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            # Word alone too wide — char-split.
            if font.size(word)[0] > max_px:
                buf = ""
                for ch in word:
                    if font.size(buf + ch)[0] > max_px:
                        if buf:
                            lines.append(buf)
                        buf = ch
                    else:
                        buf += ch
                current = buf
            else:
                current = word
        if current:
            lines.append(current)
        return lines

    def _draw_footer_hint(self, screen) -> None:
        import pygame
        rect = pygame.Rect(0, WINDOW_H - FOOTER_H, WINDOW_W, FOOTER_H)
        pygame.draw.rect(screen, COL_PANEL, rect)
        if self._review_mode and self._match_live:
            hint = ("SCRUB-BACK   ← →: scrub one tick   "
                    "home/end: jump   space: resume live   "
                    "click: inspect   q: quit")
        elif self._review_mode:
            hint = ("REVIEW   ← →: scrub one tick   "
                    "space: autoplay forward   backspace: autoplay back   "
                    "home/end: jump   click: inspect   q: quit")
        else:
            hint = ("space: pause/play   ←: scrub back   →: step   "
                    "+/-: speed   0: reset speed   click: inspect   q: quit")
        surf = self._font_small.render(hint, True, COL_TEXT_DIM)
        screen.blit(surf, (12, WINDOW_H - FOOTER_H + 4))


# ---------------------------------------------------------------------------
# RECORDING / TEST RENDERER
# Push-only fake — used by tests to verify Match wiring without a window.
# ---------------------------------------------------------------------------
class RecordingRenderer:
    """Counts protocol calls; records last (tick, match, events) tuple.
    Push-style; does not own the loop."""

    def __init__(self) -> None:
        self.start_calls: int = 0
        self.update_calls: int = 0
        self.stop_calls: int = 0
        self.last_tick: Optional[int] = None
        self.tick_history: list[int] = []
        self._open: bool = True

    def start(self) -> None:
        self.start_calls += 1

    def update(self, tick: int, match: "Match", events: "list[Event]") -> None:
        self.update_calls += 1
        self.last_tick = tick
        self.tick_history.append(tick)

    def stop(self) -> None:
        self.stop_calls += 1

    def is_open(self) -> bool:
        return self._open

    def close(self) -> None:
        """Test helper — simulate the user closing the window."""
        self._open = False


# ---------------------------------------------------------------------------
# DRIVER FAKE — used by tests to validate Match.run() handoff to a
# loop-driving renderer without involving pygame.
# ---------------------------------------------------------------------------
class ScriptedDriverRenderer(RecordingRenderer):
    """A test-only driver that owns the loop and follows a script of
    actions per frame: 'step', 'pause', 'play', 'close'. Used to
    validate pause/step/window-close semantics deterministically."""

    def __init__(self, script: list[str]) -> None:
        super().__init__()
        self._script = list(script)
        self._paused = False

    def drives_loop(self) -> bool:
        return True

    def run_interactive(self, match: "Match") -> None:
        match.begin()
        for cmd in self._script:
            if not self._open or match.is_done():
                break
            if cmd == "pause":
                self._paused = True
            elif cmd == "play":
                self._paused = False
            elif cmd == "step":
                match.step()
            elif cmd == "close":
                self._open = False
                break
            else:
                raise ValueError(f"unknown ScriptedDriverRenderer cmd: {cmd!r}")
        match.end()
