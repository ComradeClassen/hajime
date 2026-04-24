# Claude Code Instructions — Update physics-substrate.md Part 1.5

## Task

Replace Part 1.5 of `physics-substrate.md` with the revised version below. The revision reframes kuzushi from "CoM outside recoverable envelope (geometric)" to "weight commitment to one leg that cannot step (biomechanical), with the geometric predicate as the mathematical equivalent." This is a doctrinal change. The engine still computes the geometric form; the spec's canonical language becomes the biomechanical form.

## Context for this change

- Session 5 design decision, April 2026.
- Driven by the Cranford instructional video synthesis (`cranford-five-video-synthesis.md`): Sensei consistently frames kuzushi as weight commitment to a loaded leg, not as CoM displacement.
- Comrade's original spec used CoM framing because of a biomechanics reading path, not because it was the practitioner's mental model. The biomechanical framing is the truer model.
- This note unblocks HAJ-54 (weight-fraction hard-constraint on defensive action availability). Under the revised framing, HAJ-54 is no longer a new mechanic — it is a specification of what the kuzushi predicate already means.

## Steps

1. Open `physics-substrate.md`.
2. Locate Section 1.5 — currently titled "Recoverable region."
3. Replace the entire section (heading through the final sentence, up to but not including the Section 1.6 heading) with the content in the "Replacement content" block below.
4. Do NOT modify Sections 1.1–1.4 or 1.6+ in this edit.
5. Do NOT modify any other part of the document in this edit.
6. Commit with message: `Updates physics-substrate.md Part 1.5 — kuzushi as weight commitment (Session 5 design note)`

## Replacement content

Copy everything between the `--- BEGIN ---` and `--- END ---` markers into the document, replacing the existing Section 1.5. Do not include the markers themselves.

--- BEGIN ---

### 1.5 Kuzushi as weight commitment

Kuzushi is the moment uke's weight commits fully to one leg and that leg can no longer step. This is the canonical framing. It is what a judoka feels, what a coach teaches, and what a referee perceives when watching a throw open up. The pulls, pushes, and reactive forces that fill the kuzushi-tsukuri-kake sequence do not cause kuzushi directly — they *redistribute uke's weight* onto one leg. Once that leg is loaded past its capacity to step out from under the load, the throw window has opened. The pull is the cause of the weight commitment; the weight commitment is the kuzushi.

The geometric formulation that follows is the mathematical equivalent of this event. The engine computes it; the prose layer and any coach-voice output should describe the mechanism.

**The recoverable envelope.**

The recoverable envelope is the region around the BoS that a judoka can step back into if displaced. It is *not stored — computed*. As one leg's `weight_fraction` rises toward 1.0, that leg becomes the sole contributor to the envelope, and the envelope collapses asymmetrically: it can no longer extend past the stepping range of the loaded leg, because the loaded leg cannot lift to step.

```
recoverable_envelope(weight_fraction_left, weight_fraction_right,
                    com_velocity, leg_strength, fatigue, composure)
```

Inputs that shape the envelope:
- `weight_fraction` on each foot — the primary input. A leg at 1.0 cannot contribute to envelope expansion in any direction. A leg at 0.5 contributes its full stepping range.
- `com_velocity` — narrows the envelope opposite the direction of motion (committed momentum cannot easily reverse).
- `leg_strength` — per-judoka attribute; larger envelope overall for stronger legs.
- `fatigue` — shrinks the envelope as the match progresses.
- `composure` — shrinks the envelope under pressure.

**The kuzushi predicate.**

```
is_kuzushi(judoka) := com_projection(t) outside recoverable_envelope(t)
```

This is mathematically equivalent to: *one leg's weight_fraction has approached 1.0, and that leg cannot step to extend the envelope past where the CoM is now traveling*. The two predicates witness the same event. Where this spec or future tickets describe the mechanism, weight commitment is the canonical language. Where the engine computes the test, the geometric predicate is the computational form.

**Why this matters for the rest of the substrate.** Forces applied through grips (Part 2) do not directly produce kuzushi. They produce CoM displacement and trunk lean, which together cause uke's weight to redistribute toward one leg. When that redistribution reaches the locked-leg condition, kuzushi has occurred. Future tickets that introduce defensive lockouts (uke cannot pivot or step from a fully-loaded leg — see HAJ-54) are therefore not new mechanics; they are the spec stating in code what was always true in mechanism.

--- END ---

## Verification

After the edit, verify:
- Section heading reads "### 1.5 Kuzushi as weight commitment" (not "Recoverable region").
- The opening sentence begins "Kuzushi is the moment uke's weight commits fully to one leg..."
- Section 1.6 ("Per body part state") follows immediately with no content gap.
- No other sections were modified.
- The commit touches only `physics-substrate.md`.

Do not modify any Python code in this edit. Code-side implementation follows in a separate ticket (HAJ-54 revised).
