# Session 4 QA Template — Physics Substrate (Parts 4–6.3)

**Session 4 scope:** HAJ-24 through HAJ-29. Worked throw templates, four-dimension signature match, worked throw instances (×12), failed-throw compromised states, skill-compression of tsukuri-kuzushi-kake, counter-windows as state regions.

**QA goal:** run ≥ 20 matches and verify the new mechanics produce varied, believable match behavior — not just that tests pass.

**How to run:**
```
python src/main.py
```
Default match is Tanaka (right-dominant BLACK_1, Seoi-nage specialist) vs Sato (right-dominant, Uchi-mata specialist). Reseed by editing the `random.seed()` in `src/main.py`.

---

## Per-match template (copy 20 times)

### Match #__

**Seed / setup:**
- RNG seed: `___`
- Any fighter modifications: `___`
- Final result: `[winner]` by `[ippon / waza-ari×2 / decision / hansoku-make / draw]` at tick `___`

**Headline counts:**
| Metric | Count |
|--------|------:|
| `THROW_ENTRY` (commits attempted) | `___` |
| `THROW_LANDING` (scored) | `___` |
| `COUNTER_COMMIT` (counters fired) | `___` |
| `THROW_ABORTED` (mid-attempt interrupts) | `___` |
| `FAILED` w/ `desperation=True` | `___` |
| `MATTE` calls | `___` |
| Matches reached `NE_WAZA` | `Y / N` |

**Sub-event coverage (skill compression):**
- Did you see multi-tick throws unfold? `Y / N`
- Longest throw attempt observed (ticks from `THROW_ENTRY` to `KAKE_COMMIT`): `___`
- Shortest (should be 1 for signature throws of BLACK_1+): `___`

**Compromised states observed** (tick ✓ for each seen at least once):
- [ ] `TORI_COMPROMISED_FORWARD_LEAN`
- [ ] `TORI_COMPROMISED_SINGLE_SUPPORT`
- [ ] `TORI_STUCK_WITH_UKE_ON_BACK`
- [ ] `TORI_BENT_FORWARD_LOADED`
- [ ] `TORI_ON_KNEE_UKE_STANDING`
- [ ] `TORI_ON_BOTH_KNEES_UKE_STANDING`
- [ ] `TORI_SWEEP_BOUNCES_OFF`
- [ ] `STANCE_RESET` (non-compromised)
- [ ] `UCHI_MATA_SUKASHI` / other clean counter

**Counter-window regions seen** (tick ✓):
- [ ] `SEN_SEN_NO_SEN` (pre-commit)
- [ ] `SEN_NO_SEN` (reach / kuzushi-achieved)
- [ ] `GO_NO_SEN` (tsukuri / kake)
- [ ] Perception flip observed (low-IQ defender mis-reads region)

**Throw templates observed** (tick ✓ — includes both fired and aborted commits):
- [ ] Uchi-mata
- [ ] O-soto-gari
- [ ] Seoi-nage
- [ ] De-ashi-harai
- [ ] O-goshi
- [ ] Tai-otoshi
- [ ] Ko-uchi-gari
- [ ] O-uchi-gari
- [ ] Harai-goshi (competitive)
- [ ] Harai-goshi (classical)
- [ ] Tomoe-nage
- [ ] O-guruma

**Narrative feel (free-form):**
- What felt right: `___`
- What felt off: `___`
- One-sentence summary of the match: `___`

---

## Aggregate patterns across 20 matches

Fill in once the 20 matches are done.

### Throw diversity
| Throw | Times committed | Times landed |
|-------|----------------:|-------------:|
| Uchi-mata                | `__` | `__` |
| O-soto-gari              | `__` | `__` |
| Seoi-nage                | `__` | `__` |
| De-ashi-harai            | `__` | `__` |
| O-goshi                  | `__` | `__` |
| Tai-otoshi               | `__` | `__` |
| Ko-uchi-gari             | `__` | `__` |
| O-uchi-gari              | `__` | `__` |
| Harai-goshi (comp.)      | `__` | `__` |
| Harai-goshi (classical)  | `__` | `__` |
| Tomoe-nage               | `__` | `__` |
| O-guruma                 | `__` | `__` |
| Sumi-gaeshi (legacy)     | `__` | `__` |

**Red flag:** any throw with zero commits across 20 matches probably has commit thresholds or requirements mis-calibrated, or isn't in either fighter's vocabulary. Check `build_tanaka` / `build_sato` in [main.py](../src/main.py).

### Counter cadence
- Total `COUNTER_COMMIT` fires across 20 matches: `___`
- Of those, counters that **landed** a score: `___`
- Counter success rate: `___ %`
- Most common winning counter: `___`

**Calibration feel:**
- Too many counters (matches end quickly on counters): tune down `COUNTER_BASE_PROBABILITY` in [counter_windows.py:43](../src/counter_windows.py)
- Too few counters (attackers score uncontested): tune up same constant OR relax `COUNTER_COMPOSURE_GATE` / `COUNTER_FATIGUE_GATE`

### Compromised-state distribution
- Did every state get hit at least once across 20 matches? `Y / N`
- If no — which states never fired? `___`
- Do recovery windows feel appropriately painful (tori can't immediately re-attack)? `Y / N`

**Calibration feel:**
- If recovery feels too harsh or too lenient, adjust `RECOVERY_TICKS_BY_OUTCOME` in [failure_resolution.py:31](../src/failure_resolution.py)
- If counter bonuses against compromised tori don't feel impactful, adjust per-state `counter_bonuses` dict in [compromised_state.py:60](../src/compromised_state.py)

### Desperation spirals
- Matches where `desperation=True` fired at least once: `___ / 20`
- Did any match exhibit a spiral (attacker keeps failing while desperate)? `Y / N`

**Calibration feel:**
- Too frequent — lower `DESPERATION_COMPOSURE_FRAC` (tighter threshold) in [compromised_state.py:26](../src/compromised_state.py)
- Too rare — raise it
- Spirals too punishing — reduce `DESPERATION_RECOVERY_BONUS`

### Match flow
- Matches decided by ippon: `___ / 20`
- Matches decided by two waza-ari: `___ / 20`
- Matches reaching time limit (draw / decision): `___ / 20`
- Matches going to ne-waza at any point: `___ / 20`
- Matches ending on hansoku-make: `___ / 20`

**Red flag:** if > 50% time out as draws, matches have become too defensive — commit thresholds across templates may be too high, or `COMMIT_THRESHOLD` in [action_selection.py:30](../src/action_selection.py) is too strict.

---

## Calibration knobs cheat-sheet

| Behavior feels off | Knob | File |
|--------------------|------|------|
| Throws fire too easily / not enough | `commit_threshold` per template | [worked_throws.py](../src/worked_throws.py) |
| All throws feel the same speed | `N_BY_BELT` table | [skill_compression.py](../src/skill_compression.py) |
| Signature throws not faster than others | Tokui-waza override (N-1) | `compression_n_for` in [skill_compression.py](../src/skill_compression.py) |
| Counters fire too often / rarely | `COUNTER_BASE_PROBABILITY` | [counter_windows.py](../src/counter_windows.py) |
| Fatigued defenders still countering | `COUNTER_FATIGUE_GATE` | [counter_windows.py](../src/counter_windows.py) |
| Panicked defenders still countering | `COUNTER_COMPOSURE_GATE` | [counter_windows.py](../src/counter_windows.py) |
| Recovery windows too long / short | `RECOVERY_TICKS_BY_OUTCOME` | [failure_resolution.py](../src/failure_resolution.py) |
| Desperation never fires | `DESPERATION_COMPOSURE_FRAC` / `DESPERATION_CLOCK_TICKS` | [compromised_state.py](../src/compromised_state.py) |
| Compromised state doesn't feel distinct | Per-state `CompromisedStateConfig` | [compromised_state.py](../src/compromised_state.py) |

---

## Known limitations (not bugs)

- **Sumi-gaeshi** is still on the legacy signature-match path. Expected — Part 5.5 didn't parameterize it. If you see generic `failed (no commitment, net ...)` for Sumi-gaeshi, that's intentional.
- **Left-dominant fighters** aren't mirrored yet. All current worked templates assume right-dominant. Both fighters in `main.py` are right-dominant so this doesn't surface in default QA.
- **Chain counters** (tori counters uke's counter) are deferred. At most one counter fires per tick.
- **Per-sub-event compromised-state granularity** (white-belt who fails at TSUKURI specifically lands in a different state than failing at KAKE) is deferred — all failures currently select from the full `FailureSpec` regardless of which sub-event was in flight.
- **Sub-event actions** during the multi-tick attempt don't yet differ (no "tori is committing harder at tsukuri than at reach-kuzushi"). Sub-events are narrative / counter-window markers, not force modifiers.

---

## Sign-off

- [ ] All 20 matches logged above
- [ ] Aggregate patterns filled in
- [ ] Calibration suggestions (if any) noted:
  - `___`
  - `___`
  - `___`
- [ ] Screenshots / log files archived: `___`

**QA verdict:**  `[ ship as-is / calibrate and re-run / bugs to file ]`

**Follow-up tickets to open:**
- `___`
- `___`
