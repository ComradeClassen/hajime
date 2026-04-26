# match_viewer.py
# HAJ-125 — top-down match viewer v1 (pygame).
#
# Dev tool only. Not shipped with the game; UE5 is the player-facing
# renderer. The single success metric is: "can I watch a 30-second clip
# and form hypotheses about what fighters are doing?" Ugly is fine.
#
# Read-only by design. The renderer never mutates Match state — it
# consumes match.fighter_a, match.fighter_b, match.grip_graph, etc.,
# and draws.
#
# v1 surfaces (per ticket):
#   - Mat outlines: 8 m contest area + 3 m safety border (concentric rects).
#   - Fighter dots at com_position with facing arrows.
#   - Foot dots at foot_state_left/right.position.
#   - Kuzushi halo: alpha scales with |trunk_sagittal| + |trunk_frontal|.
#     Bright red flash when the kuzushi predicate fires this tick — this
#     is the single most important diagnostic on screen.
#   - Grip lines color-coded by GripMode (CONNECTIVE / DRIVING).
#   - Sidebar: Position enum, SubLoopState, score, tick clock.
#   - Position trail: last ~30 ticks of CoM, fading.

from __future__ import annotations
from collections import deque
from typing import TYPE_CHECKING, Optional

from enums import GripMode

if TYPE_CHECKING:
    from match import Match
    from grip_graph import Event


# ---------------------------------------------------------------------------
# WINDOW / WORLD-FRAME LAYOUT
# Mat geometry is the IJF reference (HAJ-124 declares meters as the unit):
#   - Contest area: 8 × 8 m
#   - Safety border: 3 m on every side → total 14 × 14 m
# We render the full 14 × 14 m so OOB region is visually obvious.
# ---------------------------------------------------------------------------
WINDOW_W:        int = 1100
WINDOW_H:        int = 760
SIDEBAR_W:       int = 380          # right panel width
MAT_PANEL_W:     int = WINDOW_W - SIDEBAR_W  # left panel for mat
MAT_PIXEL_PAD:   int = 30           # gap between window edge and mat outer rect

# Total visible world dimension (meters). Drives the px-per-meter scale.
VISIBLE_MAT_M:   float = 14.0       # 8 m contest + 3 m border each side
CONTEST_M:       float = 8.0        # IJF contest area

TRAIL_LENGTH:    int = 30           # ticks of CoM history per fighter

# Frame pacing — ticks/second of wall clock (a tick is 1 sim second).
# Real-time would be 1.0; ~6 makes a 4-minute match watchable in 40 seconds.
DEFAULT_TICKS_PER_SECOND: float = 6.0

# Colors (RGB).
COL_BG          = ( 22,  24,  30)
COL_SAFETY      = (148, 110,  74)   # tan
COL_CONTEST     = (188, 154, 100)   # lighter tan
COL_GRID        = ( 60,  64,  74)
COL_FIGHTER_A   = ( 96, 144, 232)   # blue
COL_FIGHTER_B   = (220,  92,  92)   # red
COL_FOOT_A      = (170, 200, 240)
COL_FOOT_B      = (240, 170, 170)
COL_FACING      = (240, 240, 240)
COL_KUZUSHI     = (255,  95,  60)   # warm red — flashes for kuzushi
COL_TRAIL_A     = ( 96, 144, 232)
COL_TRAIL_B     = (220,  92,  92)
COL_GRIP_CONN   = (140, 140, 140)
COL_GRIP_DRIVE  = (255, 220,  90)   # bright yellow
COL_TEXT        = (235, 235, 240)
COL_TEXT_DIM    = (160, 160, 170)
COL_PANEL       = ( 32,  34,  42)


def _grip_mode_color(mode: GripMode):
    if mode == GripMode.DRIVING:
        return COL_GRIP_DRIVE
    return COL_GRIP_CONN


# ---------------------------------------------------------------------------
# WORLD-TO-SCREEN TRANSFORM
# Pure math; testable without pygame. Kept module-level so test code can
# call it directly.
# ---------------------------------------------------------------------------
class MatTransform:
    """Maps mat-frame meters → screen-frame pixels for the v1 viewer.

    Centers the visible mat in the left panel (MAT_PANEL_W × WINDOW_H),
    leaves MAT_PIXEL_PAD of breathing room on every side.
    """

    def __init__(
        self,
        window_w: int = WINDOW_W,
        window_h: int = WINDOW_H,
        sidebar_w: int = SIDEBAR_W,
        pad: int = MAT_PIXEL_PAD,
        visible_mat_m: float = VISIBLE_MAT_M,
    ) -> None:
        self.panel_w = window_w - sidebar_w
        self.panel_h = window_h
        self.pad = pad
        # Choose px/m so the full visible mat fits with padding.
        usable_w = self.panel_w - 2 * pad
        usable_h = self.panel_h - 2 * pad
        self.px_per_m = min(usable_w, usable_h) / visible_mat_m
        # Origin of the mat (mat-frame 0,0) in screen pixels.
        self.origin_x = pad + (self.panel_w - 2 * pad) / 2
        self.origin_y = pad + (self.panel_h - 2 * pad) / 2

    def world_to_screen(self, mx: float, my: float) -> tuple[int, int]:
        """Mat (mx, my) in meters → screen (sx, sy) in pixels.
        Mat-frame +y is up on the mat; screen-frame +y is down. Flip y."""
        sx = self.origin_x + mx * self.px_per_m
        sy = self.origin_y - my * self.px_per_m
        return (int(round(sx)), int(round(sy)))

    def meters_to_pixels(self, m: float) -> int:
        return int(round(m * self.px_per_m))


# ---------------------------------------------------------------------------
# TRAIL BUFFER
# Per-fighter deque of recent CoM positions. Pure data structure;
# deliberately separated from the pygame draw step.
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
# Imports pygame lazily inside __init__ so the rest of the codebase can
# reference this module without a hard dependency.
# ---------------------------------------------------------------------------
class PygameMatchRenderer:
    """v1 top-down viewer. Conforms to the Match Renderer protocol."""

    def __init__(
        self,
        ticks_per_second: float = DEFAULT_TICKS_PER_SECOND,
    ) -> None:
        # Pygame deferred so unit tests / headless runs that import this
        # module never need the dep loaded.
        import pygame  # noqa: F401  (validates at construction time)
        self._ticks_per_second = ticks_per_second
        self._transform = MatTransform()
        self._trails = TrailBuffer()
        self._screen = None
        self._clock = None
        self._font_small = None
        self._font_med = None
        self._open = True
        # Tick of the most recent kuzushi event for each fighter — drives
        # the halo flash decay.
        self._last_kuzushi_tick: dict[str, int] = {}

    # --- Renderer protocol ------------------------------------------------
    def start(self) -> None:
        import pygame
        pygame.init()
        pygame.display.set_caption("Hajime — match viewer (HAJ-125)")
        self._screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self._clock = pygame.time.Clock()
        self._font_small = pygame.font.SysFont("Consolas", 14)
        self._font_med   = pygame.font.SysFont("Consolas", 18, bold=True)

    def stop(self) -> None:
        import pygame
        if pygame.get_init():
            pygame.quit()
        self._open = False

    def is_open(self) -> bool:
        return self._open

    def update(self, tick: int, match: "Match", events: "list[Event]") -> None:
        import pygame

        # Pump events; bail out cleanly on window close.
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._open = False
                return

        # Watch the event log for kuzushi so the halo flash maps to the
        # exact tick the predicate fired, not just current trunk angle.
        for e in events:
            if e.event_type == "KUZUSHI_INDUCED":
                # Event description format from match.py varies; data dict
                # may carry the victim. Fall back to checking both names.
                victim = e.data.get("victim") if e.data else None
                if victim:
                    self._last_kuzushi_tick[victim] = tick
                else:
                    # Conservative: paint flash on whichever fighter's
                    # name appears in the description.
                    for f in (match.fighter_a, match.fighter_b):
                        if f.identity.name in (e.description or ""):
                            self._last_kuzushi_tick[f.identity.name] = tick

        # Push trail samples once per frame.
        self._trails.push(
            match.fighter_a.state.body_state.com_position,
            match.fighter_b.state.body_state.com_position,
        )

        screen = self._screen
        screen.fill(COL_BG)
        self._draw_mat(screen)
        self._draw_trails(screen)
        self._draw_grip_edges(screen, match)
        self._draw_kuzushi_halos(screen, match, tick)
        self._draw_fighters(screen, match)
        self._draw_feet(screen, match)
        self._draw_sidebar(screen, match, tick)

        pygame.display.flip()
        self._clock.tick(self._ticks_per_second)

    # --- Draw helpers -----------------------------------------------------
    def _draw_mat(self, screen) -> None:
        import pygame
        T = self._transform
        # Safety border = the full visible 14×14 m.
        sx_tl, sy_tl = T.world_to_screen(-VISIBLE_MAT_M / 2, +VISIBLE_MAT_M / 2)
        sx_br, sy_br = T.world_to_screen(+VISIBLE_MAT_M / 2, -VISIBLE_MAT_M / 2)
        outer = pygame.Rect(sx_tl, sy_tl, sx_br - sx_tl, sy_br - sy_tl)
        pygame.draw.rect(screen, COL_SAFETY, outer)
        # Contest area = inner 8×8 m.
        cx_tl, cy_tl = T.world_to_screen(-CONTEST_M / 2, +CONTEST_M / 2)
        cx_br, cy_br = T.world_to_screen(+CONTEST_M / 2, -CONTEST_M / 2)
        contest = pygame.Rect(cx_tl, cy_tl, cx_br - cx_tl, cy_br - cy_tl)
        pygame.draw.rect(screen, COL_CONTEST, contest)
        # Center axis hairs to read drift orientation at a glance.
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
                # Older points fade toward background.
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
            # Direction: from grasper's COM toward target's COM.
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
            # Recent kuzushi predicate-fire flashes the halo for ~5 ticks.
            ticks_since = tick - self._last_kuzushi_tick.get(f.identity.name, -10**9)
            flash = max(0.0, 1.0 - ticks_since / 5.0) if ticks_since >= 0 else 0.0
            # Convert magnitude into an alpha; cap at full bright.
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
        for f, color in (
            (match.fighter_a, COL_FIGHTER_A),
            (match.fighter_b, COL_FIGHTER_B),
        ):
            bs = f.state.body_state
            cx, cy = T.world_to_screen(*bs.com_position)
            pygame.draw.circle(screen, color, (cx, cy), 9)
            # Facing arrow.
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

    def _draw_sidebar(self, screen, match: "Match", tick: int) -> None:
        import pygame
        x0 = WINDOW_W - SIDEBAR_W
        panel = pygame.Rect(x0, 0, SIDEBAR_W, WINDOW_H)
        pygame.draw.rect(screen, COL_PANEL, panel)

        a = match.fighter_a
        b = match.fighter_b
        remaining = max(0, match.max_ticks - tick)
        clock = f"{remaining // 60}:{remaining % 60:02d}"

        lines: list[tuple[str, tuple]] = [
            (f"tick {tick:03d} / {match.max_ticks}    clock {clock}", COL_TEXT),
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

        y = 16
        for text, color in lines:
            if text:
                surf = self._font_small.render(text, True, color)
                screen.blit(surf, (x0 + 14, y))
            y += 22

        # Legend at the bottom.
        legend_y = WINDOW_H - 110
        legend = [
            ("grip CONNECTIVE", COL_GRIP_CONN),
            ("grip DRIVING",    COL_GRIP_DRIVE),
            ("kuzushi flash",   COL_KUZUSHI),
        ]
        for text, color in legend:
            import pygame
            pygame.draw.rect(screen, color, (x0 + 14, legend_y, 14, 14))
            surf = self._font_small.render(text, True, COL_TEXT_DIM)
            screen.blit(surf, (x0 + 34, legend_y - 2))
            legend_y += 22


# ---------------------------------------------------------------------------
# RECORDING / TEST RENDERER
# A no-op renderer that records calls. Used by tests to verify the Match
# wiring without opening a pygame window.
# ---------------------------------------------------------------------------
class RecordingRenderer:
    """Counts protocol calls; records last (tick, match, events) tuple.
    Used by HAJ-125 tests to assert wiring without a window."""

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
