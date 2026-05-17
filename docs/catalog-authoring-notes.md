This doc is for finding gaps within the techniques.yaml file, which is the source of truth for all techniques in the catalog.

## HAJ-213 schema gaps — resolved

The two gaps surfaced during initial deashi-harai authoring have been addressed in schema v1.2 (see `design-notes/triage/technique-vocabulary-system.md` Section 2):

### Multi-configuration grip variants — resolved by `canonical_grip_signatures` list

`canonical_grip_signature` (singular) became `canonical_grip_signatures` (list). Most entries still have a single-entry list. Multi-entry lists are reserved for *genuinely distinct grip variants* of the same technique (classic seoi-nage vs. one-handed seoi-nage), not for left/right mirrors.

**Lefty mirrors are NOT authored.** Each signature carries `mirror_eligible: bool` (default `true`). At Stage 1 filter time (HAJ-207), the engine auto-mirrors the signature against opposite-stance judoka based on the judoka's stance attribute (downstream substrate work, not catalog work). Authors record only the canonical right-stance configuration.

### Multi-direction kuzushi — resolved by admissible/primary split + `any` wildcard

`kuzushi_vector` became two fields:

- `admissible_kuzushi_vectors` (required) — directions in which the technique can fire. Gates Stage 2 selection. Accepts the literal scalar `any` as a wildcard for omnidirectional techniques like foot sweeps.
- `primary_kuzushi_vectors` (optional) — subset that scores cleanest, used by scoring quality and prose surfaces. If omitted, defaults to a copy of admissible.

For deashi-harai: `admissible_kuzushi_vectors: any`, `primary_kuzushi_vectors: [forward_right_diagonal, forward_left_diagonal]`.

## Difficulty calibration

Fixture difficulty values were "minimally plausible" in HAJ-204, not authored. The HAJ-213 migration pass adjusted them modestly (deashi 25 → 65 per the original note; osoto 35 → 40; seoi 55 → 60; tomoe 60 → 65; uchi-mata held at 70). These remain first-pass values — recalibrate against Kodokan Judo / Judo Unleashed during HAJ-205 authoring, then revisit again during the calibration tickets downstream of HAJ-201/HAJ-202.

## Open gaps not yet resolved

(Add new findings below as authoring continues against the v1.2 schema.)
