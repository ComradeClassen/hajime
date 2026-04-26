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
from typing import TYPE_CHECKING, Optional

from enums import GripMode

if TYPE_CHECKING:
    from match import Match
    from grip_graph import Event
    from judoka import Judoka


# ---------------------------------------------------------------------------
# WINDOW / WORLD-FRAME LAYOUT
# Mat geometry is the IJF reference (HAJ-124 declares meters as the unit):
#   - Contest area: 8 × 8 m
#   - Safety border: 3 m on every side → total 14 × 14 m
# ---------------------------------------------------------------------------
WINDOW_W:        int = 1100
WINDOW_H:        int = 760
SIDEBAR_W:       int = 380
MAT_PANEL_W:     int = WINDOW_W - SIDEBAR_W
MAT_PIXEL_PAD:   int = 30
FOOTER_H:        int = 24       # bottom hint strip

VISIBLE_MAT_M:   float = 14.0
CONTEST_M:       float = 8.0

TRAIL_LENGTH:    int = 30

# Frame pacing — ticks/second of wall clock (a tick is 1 sim second).
DEFAULT_TICKS_PER_SECOND: float = 6.0
MIN_TPS: float = 0.1
MAX_TPS: float = 30.0   # 10× of real-time is the ticket spec; 30 leaves headroom
TPS_STEP_FACTOR: float = 1.5

# Event ticker geometry (inside the sidebar).
TICKER_H:           int = 360
TICKER_LINE_H:      int = 18
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

    def __init__(self, ticks_per_second: float = DEFAULT_TICKS_PER_SECOND) -> None:
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
        self._event_log: deque[tuple[int, str, int]] = deque(
            maxlen=EVENT_BUFFER_LEN,
        )
        self._frame_idx: int = 0

        # Kuzushi flash decay marker (per fighter).
        self._last_kuzushi_tick: dict[str, int] = {}

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
        match according to pause / step / speed-scrub state, render."""
        import pygame
        match.begin()
        self._wall_t_last_step = time.monotonic()

        try:
            while self._open and not match.is_done():
                self._handle_input(match)
                self._advance_match_if_due(match)
                self._render_frame(match)
                self._frame_idx += 1
                self._clock.tick(60)   # 60 FPS render cap; sim pace is _tps

            # Drain remaining input + give the user one final paint that
            # shows the final state. Do NOT call begin/step here.
            if self._open:
                self._render_frame(match)
        finally:
            # Resolve match (decision/draw/summary) regardless of why we exited.
            try:
                match.end()
            except Exception:
                # Don't let viewer teardown swallow real engine errors.
                raise

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
        # Watch for kuzushi events to flash halos.
        for e in events:
            if e.event_type == "KUZUSHI_INDUCED":
                victim = (e.data or {}).get("victim")
                if victim:
                    self._last_kuzushi_tick[victim] = tick
                else:
                    for f in (match.fighter_a, match.fighter_b):
                        if f.identity.name in (e.description or ""):
                            self._last_kuzushi_tick[f.identity.name] = tick
            # Stash everything-with-a-description into the ticker.
            if e.description:
                self._event_log.append((tick, e.description, self._frame_idx))
        # Push trails once per tick (not once per frame).
        self._trails.push(
            match.fighter_a.state.body_state.com_position,
            match.fighter_b.state.body_state.com_position,
        )

    # --- Internal: rendering ---------------------------------------------
    def _render_frame(self, match: "Match") -> None:
        import pygame
        screen = self._screen
        screen.fill(COL_BG)
        self._draw_mat(screen)
        self._draw_trails(screen)
        self._draw_grip_edges(screen, match)
        self._draw_kuzushi_halos(screen, match, match.ticks_run)
        self._draw_fighters(screen, match)
        self._draw_feet(screen, match)
        self._draw_pause_indicator(screen)
        self._draw_sidebar(screen, match)
        self._draw_footer_hint(screen)
        pygame.display.flip()

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

    def _draw_trails(self, screen) -> None:
        import pygame
        T = self._transform
        for trail, color in (
            (self._trails.fighter_a(), COL_TRAIL_A),
            (self._trails.fighter_b(), COL_TRAIL_B),
        ):
            n = len(trail)
            if n < 2:
                continue
            for i in range(1, n):
                alpha = int(40 + 180 * (i / n))
                surf = pygame.Surface((2, 2), pygame.SRCALPHA)
                surf.fill((*color, alpha))
                px, py = T.world_to_screen(*trail[i])
                screen.blit(surf, (px - 1, py - 1))

    def _draw_grip_edges(self, screen, match: "Match") -> None:
        import pygame
        T = self._transform
        a = match.fighter_a
        b = match.fighter_b
        ax, ay = T.world_to_screen(*a.state.body_state.com_position)
        bx, by = T.world_to_screen(*b.state.body_state.com_position)
        for edge in match.grip_graph.edges:
            color = _grip_mode_color(edge.mode)
            if edge.grasper_id == a.identity.name:
                p0, p1 = (ax, ay), (bx, by)
            else:
                p0, p1 = (bx, by), (ax, ay)
            pygame.draw.line(screen, color, p0, p1, 2)

    def _draw_kuzushi_halos(self, screen, match: "Match", tick: int) -> None:
        import pygame
        T = self._transform
        for f in (match.fighter_a, match.fighter_b):
            bs = f.state.body_state
            mag = abs(bs.trunk_sagittal) + abs(bs.trunk_frontal)
            ticks_since = tick - self._last_kuzushi_tick.get(f.identity.name, -10**9)
            flash = max(0.0, 1.0 - ticks_since / 5.0) if ticks_since >= 0 else 0.0
            base_alpha = int(min(255, mag * 200))
            flash_alpha = int(min(255, flash * 255))
            alpha = max(base_alpha, flash_alpha)
            if alpha <= 0:
                continue
            radius_px = T.meters_to_pixels(0.55) + (8 if flash > 0.5 else 0)
            cx, cy = T.world_to_screen(*bs.com_position)
            halo = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                halo, (*COL_KUZUSHI, alpha),
                (radius_px, radius_px), radius_px,
            )
            screen.blit(halo, (cx - radius_px, cy - radius_px))

    def _draw_fighters(self, screen, match: "Match") -> None:
        import pygame
        T = self._transform
        for tag, f, color in (
            ("a", match.fighter_a, COL_FIGHTER_A),
            ("b", match.fighter_b, COL_FIGHTER_B),
        ):
            bs = f.state.body_state
            cx, cy = T.world_to_screen(*bs.com_position)
            pygame.draw.circle(screen, color, (cx, cy), 9)
            # Highlight the inspect target with a thin white ring.
            if self._inspect_target == tag:
                pygame.draw.circle(screen, COL_INSPECT, (cx, cy), 13, 2)
            fx, fy = bs.facing
            tip_m = (
                bs.com_position[0] + fx * 0.45,
                bs.com_position[1] + fy * 0.45,
            )
            tx, ty = T.world_to_screen(*tip_m)
            pygame.draw.line(screen, COL_FACING, (cx, cy), (tx, ty), 2)

    def _draw_feet(self, screen, match: "Match") -> None:
        import pygame
        T = self._transform
        for f, color in (
            (match.fighter_a, COL_FOOT_A),
            (match.fighter_b, COL_FOOT_B),
        ):
            bs = f.state.body_state
            for foot in (bs.foot_state_left, bs.foot_state_right):
                fx, fy = T.world_to_screen(*foot.position)
                pygame.draw.circle(screen, color, (fx, fy), 3)

    def _draw_pause_indicator(self, screen) -> None:
        import pygame
        if not self._paused:
            return
        # Simple "PAUSED" label top-left of the mat panel.
        label = self._font_med.render(
            f"PAUSED  (tps {self._tps:.2f})", True, COL_PAUSE_BAR,
        )
        screen.blit(label, (16, 12))

    def _draw_sidebar(self, screen, match: "Match") -> None:
        import pygame
        x0 = WINDOW_W - SIDEBAR_W
        panel = pygame.Rect(x0, 0, SIDEBAR_W, WINDOW_H)
        pygame.draw.rect(screen, COL_PANEL, panel)

        # Top half: state summary (or inspector when a fighter is selected).
        if self._inspect_target is None:
            self._draw_summary(screen, match, x0)
        else:
            target = (match.fighter_a if self._inspect_target == "a"
                      else match.fighter_b)
            self._draw_inspector(screen, match, target, x0)

        # Bottom half: docked event ticker.
        self._draw_ticker(screen, x0)

    def _draw_summary(self, screen, match: "Match", x0: int) -> None:
        a = match.fighter_a
        b = match.fighter_b
        remaining = max(0, match.max_ticks - match.ticks_run)
        clock = f"{remaining // 60}:{remaining % 60:02d}"
        speed_mark = (f"{self._tps:.2f}× ticks/sec"
                      f"{' [paused]' if self._paused else ''}")
        lines: list[tuple[str, tuple]] = [
            (f"tick {match.ticks_run:03d}/{match.max_ticks}    {clock}", COL_TEXT),
            (speed_mark, COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"position:    {match.position.name}", COL_TEXT),
            (f"sub-loop:    {match.sub_loop_state.name}", COL_TEXT),
            ("", COL_TEXT),
            (f"  {a.identity.name}", COL_FIGHTER_A),
            (f"   waza-ari {a.state.score['waza_ari']}   "
             f"shidos {a.state.shidos}", COL_TEXT_DIM),
            (f"   composure {a.state.composure_current:.2f}/"
             f"{a.capability.composure_ceiling}", COL_TEXT_DIM),
            (f"   stance {a.state.current_stance.name.lower()}", COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"  {b.identity.name}", COL_FIGHTER_B),
            (f"   waza-ari {b.state.score['waza_ari']}   "
             f"shidos {b.state.shidos}", COL_TEXT_DIM),
            (f"   composure {b.state.composure_current:.2f}/"
             f"{b.capability.composure_ceiling}", COL_TEXT_DIM),
            (f"   stance {b.state.current_stance.name.lower()}", COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"matchup:     {match._compute_stance_matchup().name}", COL_TEXT),
            (f"edges:       {match.grip_graph.edge_count()}", COL_TEXT_DIM),
        ]
        y = 14
        for text, color in lines:
            if text:
                surf = self._font_small.render(text, True, color)
                screen.blit(surf, (x0 + 12, y))
            y += 18

    def _draw_inspector(
        self, screen, match: "Match", judoka: "Judoka", x0: int,
    ) -> None:
        import pygame
        # Background tint to make inspect mode visually distinct.
        pygame.draw.rect(screen, COL_PANEL_ALT,
                         pygame.Rect(x0, 0, SIDEBAR_W, WINDOW_H - TICKER_H - FOOTER_H))
        ident = judoka.identity
        cap   = judoka.capability
        st    = judoka.state
        bs    = st.body_state
        cf    = COL_FIGHTER_A if judoka is match.fighter_a else COL_FIGHTER_B
        head  = self._font_big.render(
            f"{ident.name}  [inspect]", True, cf,
        )
        screen.blit(head, (x0 + 12, 10))

        # Active grip edges (this fighter as grasper).
        own_edges = [e for e in match.grip_graph.edges
                     if e.grasper_id == ident.name]

        body = st.body
        lines: list[tuple[str, tuple]] = [
            (f"belt {ident.belt_rank.name}   "
             f"{ident.body_archetype.name}   age {ident.age}", COL_TEXT_DIM),
            (f"stance {st.current_stance.name.lower()}   "
             f"dom {ident.dominant_side.name.lower()}", COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"score: waza-ari {st.score['waza_ari']}   "
             f"ippon {st.score['ippon']}   shidos {st.shidos}", COL_TEXT),
            ("", COL_TEXT),
            ("composure / cardio / stun:", COL_TEXT),
            (f"  composure  {st.composure_current:.2f} / "
             f"{cap.composure_ceiling}", COL_TEXT_DIM),
            (f"  cardio     {st.cardio_current:.3f}", COL_TEXT_DIM),
            (f"  stun_ticks {st.stun_ticks}", COL_TEXT_DIM),
            ("", COL_TEXT),
            ("body fatigue:", COL_TEXT),
        ]
        for part_key in ("right_hand", "left_hand", "right_leg", "left_leg",
                         "core", "lower_back"):
            if part_key in body:
                lines.append((
                    f"  {part_key:<11} eff {judoka.effective_body_part(part_key):.2f}  "
                    f"fat {body[part_key].fatigue:.3f}",
                    COL_TEXT_DIM,
                ))
        lines.extend([
            ("", COL_TEXT),
            ("body state:", COL_TEXT),
            (f"  com_pos    ({bs.com_position[0]:+.2f}, {bs.com_position[1]:+.2f}) m",
             COL_TEXT_DIM),
            (f"  trunk_sag  {bs.trunk_sagittal:+.3f} rad", COL_TEXT_DIM),
            (f"  trunk_frt  {bs.trunk_frontal:+.3f} rad", COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"clocks: kumi-kata {match.kumi_kata_clock.get(ident.name, 0)}",
             COL_TEXT),
            (f"        last_attack {match._last_attack_tick.get(ident.name, 0)}",
             COL_TEXT_DIM),
            ("", COL_TEXT),
            ("desperation:", COL_TEXT),
            (f"  offensive {match._offensive_desperation_active.get(ident.name, False)}",
             COL_TEXT_DIM),
            (f"  defensive {match._defensive_desperation_active.get(ident.name, False)}",
             COL_TEXT_DIM),
            ("", COL_TEXT),
            (f"grips ({len(own_edges)}):", COL_TEXT),
        ])
        for e in own_edges:
            lines.append((
                f"  {e.grasper_part.name:<10} → {e.target_location.name:<14} "
                f"{e.grip_type_v2.name:<12} {e.depth_level.name:<10} {e.mode.name}",
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

        title = self._font_med.render("event ticker", True, COL_TEXT_DIM)
        screen.blit(title, (x0 + 12, ticker_y0 + 6))

        # Newest at top.
        events = list(self._event_log)
        events.reverse()
        y = ticker_y0 + 30
        for ev_tick, desc, frame_seen in events[:TICKER_MAX_LINES]:
            age = self._frame_idx - frame_seen
            color = COL_TEXT_NEW if age <= NEW_EVENT_HIGHLIGHT_FRAMES else COL_TEXT_DIM
            text = f"t{ev_tick:03d} {desc}"
            # Truncate to fit.
            max_chars = 52
            if len(text) > max_chars:
                text = text[:max_chars - 1] + "…"
            surf = self._font_small.render(text, True, color)
            screen.blit(surf, (x0 + 12, y))
            y += TICKER_LINE_H

    def _draw_footer_hint(self, screen) -> None:
        import pygame
        rect = pygame.Rect(0, WINDOW_H - FOOTER_H, WINDOW_W, FOOTER_H)
        pygame.draw.rect(screen, COL_PANEL, rect)
        hint = ("space: pause/play   →: step   +/-: speed   "
                "0: reset speed   click: inspect   esc: clear   q: quit")
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
