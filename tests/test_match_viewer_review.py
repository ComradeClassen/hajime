# tests/test_match_viewer_review.py
# HAJ-126 follow-up — post-match review mode + ViewState snapshot capture.
#
# After Match.end() the pygame viewer doesn't shut the window. It enters
# review mode: paused, holding the final tick, with arrow keys scrubbing
# back and forward through every captured tick. The pygame UI is not
# unit-tested (it's a key/mouse shell); these tests cover the data
# layer — the ViewState capture and the snapshot list growth — plus the
# pure-math review-pacing logic.

from __future__ import annotations
import io
import os
import random
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from match import Match
from match_viewer import (
    capture_view_state, ViewState, FighterView, GripEdgeView,
)
from referee import build_suzuki
import main as main_module


def _new_match(*, max_ticks=8, seed=1):
    random.seed(seed)
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=max_ticks, seed=seed,
    )


def _silent_run(m):
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    return buf


# ---------------------------------------------------------------------------
# capture_view_state — pure read of a Match
# ---------------------------------------------------------------------------
def test_capture_view_state_returns_frozen_view() -> None:
    m = _new_match()
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.begin()
    view = capture_view_state(m, tick=0, events=[])
    assert isinstance(view, ViewState)
    assert view.tick == 0
    assert view.max_ticks == m.max_ticks
    assert view.position_name == m.position.name
    assert view.fighter_a.name == m.fighter_a.identity.name
    assert view.fighter_b.name == m.fighter_b.identity.name
    assert view.fighter_a.color_tag == "a"
    assert view.fighter_b.color_tag == "b"


def test_view_state_is_decoupled_from_live_state() -> None:
    """A captured ViewState shouldn't drift if the match keeps running.
    com_position is a tuple copy at capture time."""
    m = _new_match()
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.begin()
    early = capture_view_state(m, tick=0, events=[])
    # Mutate live com_position (mimicking many ticks of physics).
    m.fighter_a.state.body_state.com_position = (5.0, 5.0)
    # Snapshot value did not change.
    assert early.fighter_a.com_position != (5.0, 5.0)


def test_view_state_grip_edges_capture_mode_as_int() -> None:
    """Mode is stored as int (GripMode.value) so the snapshot is fully
    pickleable / decoupled from the live GripMode enum identity."""
    from grip_graph import GripGraph, GripEdge
    from enums import BodyPart, GripTarget, GripTypeV2, GripDepth, GripMode
    m = _new_match()
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.begin()
    m.grip_graph.add_edge(GripEdge(
        grasper_id=m.fighter_a.identity.name, grasper_part=BodyPart.RIGHT_HAND,
        target_id=m.fighter_b.identity.name, target_location=GripTarget.LEFT_LAPEL,
        grip_type_v2=GripTypeV2.LAPEL_HIGH, depth_level=GripDepth.DEEP,
        strength=1.0, established_tick=0, mode=GripMode.DRIVING,
    ))
    view = capture_view_state(m, tick=0, events=[])
    assert len(view.grip_edges) == 1
    edge = view.grip_edges[0]
    assert isinstance(edge, GripEdgeView)
    assert edge.mode_value == GripMode.DRIVING.value


# ---------------------------------------------------------------------------
# Snapshot growth during a live run with the pygame renderer
# ---------------------------------------------------------------------------
def test_snapshot_count_equals_ticks_plus_one() -> None:
    """The interactive renderer captures one snapshot per Match.update()
    call. tick-0 paint + N stepped ticks = N+1 snapshots. We exercise
    this with the ScriptedDriverRenderer-shaped test driver from the
    main controls test, NOT pygame, so this stays headless."""

    from match_viewer import ScriptedDriverRenderer

    class Capturing(ScriptedDriverRenderer):
        """Mirrors the pygame renderer's snapshot list behavior — every
        update() pushes a ViewState into a local list."""
        def __init__(self, script):
            super().__init__(script)
            self.snapshots: list[ViewState] = []

        def update(self, tick, match, events):
            super().update(tick, match, events)
            self.snapshots.append(capture_view_state(match, tick, events))

    drv = Capturing(["step", "step", "step", "step"])
    m = _new_match(max_ticks=8, seed=2)
    m._renderer = drv
    _silent_run(m)
    assert len(drv.snapshots) == 5   # tick 0 + 4 stepped
    assert [s.tick for s in drv.snapshots] == [0, 1, 2, 3, 4]


def test_snapshot_history_independent_of_subsequent_match_state() -> None:
    """Once a tick is captured, advancing the match further must not
    perturb older snapshots. Frozen dataclasses + tuple copies guarantee
    this; verify via byte-equal field check."""
    from match_viewer import ScriptedDriverRenderer

    class Capturing(ScriptedDriverRenderer):
        def __init__(self, script):
            super().__init__(script)
            self.snapshots: list[ViewState] = []

        def update(self, tick, match, events):
            super().update(tick, match, events)
            self.snapshots.append(capture_view_state(match, tick, events))

    drv = Capturing(["step", "step", "step"])
    m = _new_match(max_ticks=8, seed=3)
    m._renderer = drv
    _silent_run(m)
    # Capture the early-tick CoM and then mutate live state.
    early_a_pos = drv.snapshots[1].fighter_a.com_position
    m.fighter_a.state.body_state.com_position = (10.0, 10.0)
    assert drv.snapshots[1].fighter_a.com_position == early_a_pos


# ---------------------------------------------------------------------------
# Review-mode logic via direct method calls (no pygame window).
# ---------------------------------------------------------------------------
def test_renderer_enters_review_after_match_ends() -> None:
    """We exercise PygameMatchRenderer at the API level under SDL dummy
    so no real window is required. Drive the match, then verify the
    renderer flipped to review mode and landed on the final snapshot."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    from match_viewer import PygameMatchRenderer

    class StopAfterReview(PygameMatchRenderer):
        """Closes itself after a few review frames so the test exits."""
        def __init__(self):
            super().__init__(ticks_per_second=30.0)
            self._review_frames = 0

        def _handle_input_review(self):
            super()._handle_input_review()
            self._review_frames += 1
            if self._review_frames > 5:
                self._open = False

    r = StopAfterReview()
    m = _new_match(max_ticks=4, seed=7)
    m._renderer = r
    _silent_run(m)
    # Snapshot list populated, review_mode entered, idx at the final tick.
    assert len(r._snapshots) >= 1
    assert r._review_mode is True
    assert r._review_idx == len(r._snapshots) - 1


def test_review_mode_holds_window_open_after_match_end() -> None:
    """The viewer must NOT exit when match.is_done() goes True; review
    mode keeps the window alive until the user explicitly closes it."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    from match_viewer import PygameMatchRenderer

    closed = {"flag": False}

    class TrackClose(PygameMatchRenderer):
        def __init__(self):
            super().__init__(ticks_per_second=30.0)
            self._review_frames = 0

        def _handle_input_review(self):
            super()._handle_input_review()
            self._review_frames += 1
            # First time we land in review, the window must still be open.
            if self._review_frames == 1:
                assert self._open is True
            if self._review_frames > 3:
                self._open = False
                closed["flag"] = True

    r = TrackClose()
    m = _new_match(max_ticks=3, seed=11)
    m._renderer = r
    _silent_run(m)
    assert closed["flag"] is True
    assert r._review_mode is True


def test_review_scrubbing_does_not_call_match_step() -> None:
    """Critical invariant: review never re-runs the simulation. Once
    in review mode, scrubbing left/right reads snapshots only — Match
    state and ticks_run remain pinned at end-of-match."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    from match_viewer import PygameMatchRenderer

    class ScrubAndQuit(PygameMatchRenderer):
        def __init__(self):
            super().__init__(ticks_per_second=30.0)
            self._frames = 0

        def _handle_input_review(self):
            super()._handle_input_review()
            self._frames += 1
            # Move idx around across several review frames.
            if self._frames == 1:
                self._review_idx = 0
            elif self._frames == 2:
                self._review_idx = 1
            elif self._frames == 3:
                self._review_idx = max(0, len(self._snapshots) - 2)
            elif self._frames > 4:
                self._open = False

    r = ScrubAndQuit()
    m = _new_match(max_ticks=5, seed=13)
    m._renderer = r
    _silent_run(m)
    # ticks_run stayed at the end-of-match value (or earlier if match
    # ended on score). Either way, scrubbing didn't drive it forward.
    final = m.ticks_run
    assert final >= 1
    # Snapshots include all the ticks the engine actually ran.
    assert len(r._snapshots) == final + 1   # tick 0 paint + final stepped


def test_left_arrow_enters_mid_match_scrub_back() -> None:
    """Pressing LEFT during the live phase auto-pauses the match and
    flips the renderer into review at (latest - 1)."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    from match_viewer import PygameMatchRenderer
    import pygame

    class PressLeftAtFrame3(PygameMatchRenderer):
        def __init__(self):
            super().__init__(ticks_per_second=30.0)
            self._review_frames = 0
            self._was_live_when_review_first_seen: Optional[bool] = None
            self._review_idx_at_entry: Optional[int] = None
            self._left_sent = False

        def _handle_input(self, match):
            # Drop a fake LEFT into the queue once we have snapshots.
            if not self._left_sent and len(self._snapshots) >= 3:
                self._left_sent = True
                pygame.event.post(pygame.event.Event(
                    pygame.KEYDOWN,
                    {"key": pygame.K_LEFT, "mod": 0, "unicode": "",
                     "scancode": 0},
                ))
            super()._handle_input(match)

        def _handle_input_review(self):
            if self._was_live_when_review_first_seen is None:
                self._was_live_when_review_first_seen = self._match_live
                self._review_idx_at_entry = self._review_idx
            super()._handle_input_review()
            self._review_frames += 1
            if self._review_frames > 3:
                self._open = False

    r = PressLeftAtFrame3()
    m = _new_match(max_ticks=20, seed=23)
    m._renderer = r
    _silent_run(m)
    assert r._review_mode is True
    assert r._was_live_when_review_first_seen is True, (
        "review entered mid-match (during the live phase)"
    )
    # Entry index landed at len-2 (one tick back from the latest).
    assert r._review_idx_at_entry == max(0, len(r._snapshots) - 2)
    assert r._paused is True


def test_space_in_mid_match_review_resumes_live_play() -> None:
    """SPACE while in mid-match review exits review and unpauses, so
    the live phase resumes advancing the match."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    from match_viewer import PygameMatchRenderer
    import pygame

    class LeftThenSpace(PygameMatchRenderer):
        def __init__(self):
            super().__init__(ticks_per_second=30.0)
            self._left_sent = False
            self._space_sent = False
            self._ticks_at_resume: Optional[int] = None
            self._post_resume_frames = 0

        def _handle_input(self, match):
            if not self._left_sent and len(self._snapshots) >= 3:
                self._left_sent = True
                pygame.event.post(pygame.event.Event(
                    pygame.KEYDOWN,
                    {"key": pygame.K_LEFT, "mod": 0, "unicode": "",
                     "scancode": 0},
                ))
            # If we're back in live mode after the LEFT/SPACE round-trip,
            # snapshot the tick count once and quit shortly after.
            if (self._left_sent and self._space_sent
                    and self._ticks_at_resume is None):
                self._ticks_at_resume = match.ticks_run
            if self._ticks_at_resume is not None:
                self._post_resume_frames += 1
                if self._post_resume_frames > 5:
                    self._open = False
            super()._handle_input(match)

        def _handle_input_review(self):
            if not self._space_sent:
                self._space_sent = True
                pygame.event.post(pygame.event.Event(
                    pygame.KEYDOWN,
                    {"key": pygame.K_SPACE, "mod": 0, "unicode": " ",
                     "scancode": 0},
                ))
            super()._handle_input_review()

    r = LeftThenSpace()
    m = _new_match(max_ticks=20, seed=29)
    m._renderer = r
    _silent_run(m)
    # The match continued running after SPACE was pressed in review.
    assert r._ticks_at_resume is not None
    # Match advanced past the resume point.
    assert m.ticks_run >= r._ticks_at_resume


def test_review_idx_clamped_to_snapshot_range() -> None:
    """Manually nudging _review_idx outside the snapshot range gets
    clamped on the next handle_input_review call (LEFT/RIGHT clamp at
    the boundaries)."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    from match_viewer import PygameMatchRenderer
    import pygame

    class ProbeBoundaries(PygameMatchRenderer):
        def __init__(self):
            super().__init__(ticks_per_second=30.0)
            self._stage = 0
            self._observed = []

        def _handle_input_review(self):
            # Fabricate a left-arrow event when at index 0.
            self._stage += 1
            if self._stage == 1:
                self._review_idx = 0
                # Press LEFT — must stay at 0.
                pygame.event.post(pygame.event.Event(
                    pygame.KEYDOWN, {"key": pygame.K_LEFT, "mod": 0,
                                     "unicode": "", "scancode": 0},
                ))
            elif self._stage == 2:
                self._observed.append(("after_left", self._review_idx))
                last = len(self._snapshots) - 1
                self._review_idx = last
                pygame.event.post(pygame.event.Event(
                    pygame.KEYDOWN, {"key": pygame.K_RIGHT, "mod": 0,
                                     "unicode": "", "scancode": 0},
                ))
            elif self._stage == 3:
                self._observed.append(("after_right", self._review_idx))
                self._open = False
            super()._handle_input_review()

    r = ProbeBoundaries()
    m = _new_match(max_ticks=3, seed=17)
    m._renderer = r
    _silent_run(m)
    last = len(r._snapshots) - 1
    after_left = dict(r._observed).get("after_left")
    after_right = dict(r._observed).get("after_right")
    assert after_left == 0, f"LEFT at idx 0 should clamp to 0, got {after_left}"
    assert after_right == last, (
        f"RIGHT at idx {last} should clamp to {last}, got {after_right}"
    )
