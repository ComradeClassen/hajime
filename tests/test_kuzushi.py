# test_kuzushi.py — HAJ-130 acceptance tests for the KuzushiEvent module.
#
# Covers:
#   - Decay math: zero-age full magnitude, half-life accuracy, monotonic falloff.
#   - Vector composition: same-direction stacks, opposing cancels, partial cancel.
#   - Buffer capping: events past capacity drop from the front (FIFO).
#   - Judoka integration: fresh judoka has an empty buffer; record_kuzushi_event
#     appends; the buffer's maxlen is enforced.

import math
import sys
from pathlib import Path

# Match the existing test layout (sys.path injection — see other test files).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from kuzushi import (
    DECAY_HALF_LIFE_TICKS,
    KUZUSHI_BUFFER_CAPACITY,
    CompromisedState,
    KuzushiEvent,
    KuzushiSource,
    compromised_state,
    decay_factor,
    fresh_buffer,
    record_kuzushi_event,
)


# ---------------------------------------------------------------------------
# DECAY
# ---------------------------------------------------------------------------
class TestDecay:
    def test_zero_age_full_magnitude(self):
        assert decay_factor(0) == 1.0

    def test_negative_age_clamped_to_one(self):
        # Defensive: future-dated events shouldn't amplify.
        assert decay_factor(-3) == 1.0

    def test_half_life_value(self):
        # By construction, age == DECAY_HALF_LIFE_TICKS → 0.5.
        assert decay_factor(int(DECAY_HALF_LIFE_TICKS)) == pytest.approx(0.5)

    def test_decay_is_monotonic(self):
        prev = decay_factor(0)
        for age in range(1, 25):
            cur = decay_factor(age)
            assert cur < prev
            prev = cur

    def test_decay_at_two_ticks_mostly_live(self):
        # Spec §2: "a pull two ticks ago is mostly live".
        assert decay_factor(2) > 0.7

    def test_decay_at_ten_ticks_mostly_faded(self):
        # Spec §2: "one from ten ticks ago is mostly faded".
        # 5-tick half-life → age=10 = 0.25. "Mostly faded" but a tail remains
        # by design; calibration may steepen this in HAJ-A.7.
        assert decay_factor(10) <= 0.25 + 1e-9

    def test_event_n_ticks_ago_reduced_by_decay_formula(self):
        ev = KuzushiEvent(
            tick_emitted=0, vector=(1.0, 0.0),
            magnitude=10.0, source_kind=KuzushiSource.PULL,
        )
        for n in (1, 3, 7, 12):
            cs = compromised_state([ev], current_tick=n)
            expected_mag = 10.0 * decay_factor(n)
            assert cs.magnitude == pytest.approx(expected_mag)
            assert cs.total_decayed_magnitude == pytest.approx(expected_mag)


# ---------------------------------------------------------------------------
# COMPOSITION
# ---------------------------------------------------------------------------
class TestComposition:
    def test_empty_event_stream(self):
        cs = compromised_state([], current_tick=10)
        assert cs == CompromisedState.empty()
        assert cs.magnitude == 0.0
        assert cs.total_decayed_magnitude == 0.0

    def test_single_event_unit_vector(self):
        ev = KuzushiEvent(
            tick_emitted=5, vector=(1.0, 0.0),
            magnitude=4.0, source_kind=KuzushiSource.PULL,
        )
        cs = compromised_state([ev], current_tick=5)
        assert cs.vector == pytest.approx((4.0, 0.0))
        assert cs.magnitude == pytest.approx(4.0)
        assert cs.total_decayed_magnitude == pytest.approx(4.0)

    def test_same_direction_events_stack_additively(self):
        # Two simultaneous forward pulls of magnitude 3 → resultant 6.
        evs = [
            KuzushiEvent(tick_emitted=0, vector=(1.0, 0.0),
                         magnitude=3.0, source_kind=KuzushiSource.PULL),
            KuzushiEvent(tick_emitted=0, vector=(1.0, 0.0),
                         magnitude=3.0, source_kind=KuzushiSource.PULL),
        ]
        cs = compromised_state(evs, current_tick=0)
        assert cs.vector == pytest.approx((6.0, 0.0))
        assert cs.magnitude == pytest.approx(6.0)
        assert cs.total_decayed_magnitude == pytest.approx(6.0)

    def test_opposing_events_cancel_to_zero_resultant(self):
        # Two equal-and-opposite pulls at the same tick → net vector zero,
        # but total_decayed_magnitude reflects both events still being live.
        evs = [
            KuzushiEvent(tick_emitted=0, vector=(1.0, 0.0),
                         magnitude=5.0, source_kind=KuzushiSource.PULL),
            KuzushiEvent(tick_emitted=0, vector=(-1.0, 0.0),
                         magnitude=5.0, source_kind=KuzushiSource.PULL),
        ]
        cs = compromised_state(evs, current_tick=0)
        assert cs.vector == pytest.approx((0.0, 0.0))
        assert cs.magnitude == pytest.approx(0.0)
        assert cs.total_decayed_magnitude == pytest.approx(10.0)

    def test_partial_cancel(self):
        # Forward pull of 5, backward pull of 2 → net forward 3.
        evs = [
            KuzushiEvent(tick_emitted=0, vector=(1.0, 0.0),
                         magnitude=5.0, source_kind=KuzushiSource.PULL),
            KuzushiEvent(tick_emitted=0, vector=(-1.0, 0.0),
                         magnitude=2.0, source_kind=KuzushiSource.PULL),
        ]
        cs = compromised_state(evs, current_tick=0)
        assert cs.vector == pytest.approx((3.0, 0.0))
        assert cs.magnitude == pytest.approx(3.0)
        assert cs.total_decayed_magnitude == pytest.approx(7.0)

    def test_orthogonal_events_compose_pythagorean(self):
        # Forward 3 + lateral 4 → resultant magnitude 5 (3-4-5 triangle).
        evs = [
            KuzushiEvent(tick_emitted=0, vector=(1.0, 0.0),
                         magnitude=3.0, source_kind=KuzushiSource.PULL),
            KuzushiEvent(tick_emitted=0, vector=(0.0, 1.0),
                         magnitude=4.0, source_kind=KuzushiSource.PULL),
        ]
        cs = compromised_state(evs, current_tick=0)
        assert cs.vector == pytest.approx((3.0, 4.0))
        assert cs.magnitude == pytest.approx(5.0)
        assert cs.total_decayed_magnitude == pytest.approx(7.0)

    def test_decay_applied_per_event_before_composition(self):
        # Old forward pull (mostly faded) + fresh backward pull → backward wins.
        evs = [
            KuzushiEvent(tick_emitted=0, vector=(1.0, 0.0),
                         magnitude=10.0, source_kind=KuzushiSource.PULL),
            KuzushiEvent(tick_emitted=15, vector=(-1.0, 0.0),
                         magnitude=10.0, source_kind=KuzushiSource.PULL),
        ]
        cs = compromised_state(evs, current_tick=15)
        # Old event: 10 * decay(15) = 10 * 2^-3 = 1.25; fresh: 10.
        # Net = -10 + 1.25 = -8.75 (backward).
        assert cs.vector[0] == pytest.approx(-8.75)
        assert cs.vector[1] == pytest.approx(0.0)
        assert cs.magnitude == pytest.approx(8.75)


# ---------------------------------------------------------------------------
# BUFFER CAPPING
# ---------------------------------------------------------------------------
class TestBufferCapping:
    def test_fresh_buffer_is_empty_with_correct_maxlen(self):
        buf = fresh_buffer()
        assert len(buf) == 0
        assert buf.maxlen == KUZUSHI_BUFFER_CAPACITY

    def test_overflow_drops_oldest_event_from_front(self):
        buf = fresh_buffer()
        # Push capacity+5 events tagged with their tick number.
        for i in range(KUZUSHI_BUFFER_CAPACITY + 5):
            buf.append(KuzushiEvent(
                tick_emitted=i, vector=(1.0, 0.0),
                magnitude=1.0, source_kind=KuzushiSource.PULL,
            ))
        assert len(buf) == KUZUSHI_BUFFER_CAPACITY
        # Oldest 5 should be gone; first remaining event is tick=5.
        assert buf[0].tick_emitted == 5
        assert buf[-1].tick_emitted == KUZUSHI_BUFFER_CAPACITY + 4


# ---------------------------------------------------------------------------
# JUDOKA INTEGRATION
# ---------------------------------------------------------------------------
class TestJudokaIntegration:
    def _build_judoka(self):
        # Minimal Judoka — borrow the same builder pattern other tests use.
        from enums import BodyArchetype, BeltRank, DominantSide
        from judoka import BODY_PARTS, Capability, Identity, Judoka, State

        identity = Identity(
            name="Test", age=25, weight_class="-73kg", height_cm=175,
            body_archetype=BodyArchetype.GRIP_FIGHTER,
            belt_rank=BeltRank.BLACK_1, dominant_side=DominantSide.RIGHT,
        )
        cap_kwargs = {part: 7 for part in BODY_PARTS}
        cap = Capability(
            **cap_kwargs,
            cardio_capacity=7, cardio_efficiency=7,
            composure_ceiling=7, fight_iq=7, ne_waza_skill=7,
        )
        state = State.fresh(cap, identity)
        return Judoka(identity=identity, capability=cap, state=state)

    def test_fresh_judoka_has_empty_kuzushi_buffer(self):
        j = self._build_judoka()
        assert hasattr(j, "kuzushi_events")
        assert len(j.kuzushi_events) == 0
        assert j.kuzushi_events.maxlen == KUZUSHI_BUFFER_CAPACITY

    def test_record_kuzushi_event_appends_to_buffer(self):
        j = self._build_judoka()
        ev = KuzushiEvent(
            tick_emitted=3, vector=(0.0, 1.0),
            magnitude=2.5, source_kind=KuzushiSource.FOOT_ATTACK,
        )
        record_kuzushi_event(j, ev)
        assert len(j.kuzushi_events) == 1
        assert j.kuzushi_events[0] is ev

    def test_two_judoka_have_independent_buffers(self):
        # Guards against the classic mutable-default-argument bug; the
        # default_factory on Judoka.kuzushi_events should produce a fresh
        # deque per instance.
        a = self._build_judoka()
        b = self._build_judoka()
        record_kuzushi_event(a, KuzushiEvent(
            tick_emitted=0, vector=(1.0, 0.0),
            magnitude=1.0, source_kind=KuzushiSource.PULL,
        ))
        assert len(a.kuzushi_events) == 1
        assert len(b.kuzushi_events) == 0

    def test_buffer_overflow_via_record_helper(self):
        j = self._build_judoka()
        for i in range(KUZUSHI_BUFFER_CAPACITY + 3):
            record_kuzushi_event(j, KuzushiEvent(
                tick_emitted=i, vector=(1.0, 0.0),
                magnitude=1.0, source_kind=KuzushiSource.PULL,
            ))
        assert len(j.kuzushi_events) == KUZUSHI_BUFFER_CAPACITY
        assert j.kuzushi_events[0].tick_emitted == 3

    def test_compromised_state_reads_judoka_buffer_end_to_end(self):
        # Smoke: write events into the Judoka buffer, then have the module
        # function read them as the spec intends.
        j = self._build_judoka()
        record_kuzushi_event(j, KuzushiEvent(
            tick_emitted=10, vector=(1.0, 0.0),
            magnitude=8.0, source_kind=KuzushiSource.PULL,
        ))
        record_kuzushi_event(j, KuzushiEvent(
            tick_emitted=12, vector=(1.0, 0.0),
            magnitude=4.0, source_kind=KuzushiSource.PULL,
        ))
        cs = compromised_state(j.kuzushi_events, current_tick=12)
        # tick 10 event: age 2, magnitude 8 * decay(2)
        # tick 12 event: age 0, magnitude 4
        expected = 8.0 * decay_factor(2) + 4.0
        assert cs.vector[0] == pytest.approx(expected)
        assert cs.magnitude == pytest.approx(expected)
