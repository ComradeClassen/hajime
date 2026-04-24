# Claude Code Instructions — Add Part 4.2.1 to physics-substrate.md

## Task

Insert a new sub-section `4.2.1 Execution quality within signature` into `physics-substrate.md`, immediately after the existing Section 4.2 ("The four-dimension signature, formalized") and before Section 4.3 ("The Couple throw template").

This sub-section introduces `execution_quality` as a first-class concept in the physics substrate. It commits the engine to treating every fired throw as having a quality score in [0.0, 1.0] that flows through force transfer, landing severity, counter vulnerability, and prose register. No existing content is modified — this is purely an insertion.

## Context for this change

- Session 5 design decision, April 2026.
- Driven by the Cranford instructional video synthesis: Sensei repeatedly distinguishes correct-but-sloppy execution from correct-and-clean execution of the same throw. Tai-otoshi with hips forward, O-soto-gari with heel-to-calf — these are signature-valid throws executed at low quality, not signature failures.
- Commits Hajime to a depth-first simulation model. A fired throw is no longer a binary event; it has a quality score that every downstream system reads.
- This note unblocks HAJ-55 and HAJ-59 (both revised to become execution-quality modifiers instead of hard gates/new compromised states), and requires a new spine ticket — "Execution quality plumbing" — before HAJ-55 and HAJ-59 can be implemented.

## Steps

1. Open `physics-substrate.md`.
2. Locate Section 4.2 — titled "The four-dimension signature, formalized."
3. Find the end of Section 4.2 (the last line before the Section 4.3 heading, "### 4.3 The Couple throw template").
4. Insert the content in the "New sub-section content" block below between Section 4.2's end and Section 4.3's heading.
5. Do NOT modify Section 4.2 or Section 4.3 themselves.
6. Do NOT modify any other part of the document.
7. Commit with message: `Adds physics-substrate.md Part 4.2.1 — execution quality within signature (Session 5 design note)`

## New sub-section content

Insert everything between the `--- BEGIN ---` and `--- END ---` markers. Do not include the markers themselves. Ensure the inserted content is separated from Section 4.2 above by a blank line and from Section 4.3 below by a blank line.

--- BEGIN ---

### 4.2.1 Execution quality within signature

Signature match above the commit threshold is not uniform. The same throw fired at marginal-match and elite-match produces materially different outcomes — different force transfer, different landing severity, different counter vulnerability, different scores awarded. This sub-section makes execution quality a first-class concept in the signature model.

**The execution quality score.**

For any throw whose `actual_match` exceeds `commit_threshold` and therefore fires, the engine derives an `execution_quality` score in [0.0, 1.0]:

```
execution_quality = clamp(
    (actual_match - commit_threshold) / (1.0 - commit_threshold),
    0.0, 1.0
)
```

A throw that fires at exactly the commit threshold has `execution_quality = 0.0`. A throw that fires at full signature match (1.0) has `execution_quality = 1.0`. Most live throws will fall somewhere in between, with the distribution skewing higher as belt rank rises.

**What execution quality flows through.**

Execution quality is consumed by four downstream systems. The specific multiplier curves and threshold values within each system are calibration work, not committed by this spec — but the *coupling* is committed.

1. **Force transfer.** The kake sequence delivers force to uke's CoM and trunk in proportion to execution quality. A heel-to-calf O-soto-gari at `execution_quality = 0.2` transfers far less rotational momentum than the same throw at `execution_quality = 0.8` — uke ends up displaced but not airborne, or airborne but not landing flat.

2. **Landing severity.** Score award decisions consume execution quality alongside the existing landing-position checks. A clean Ippon requires high execution quality combined with a back-flat landing. A waza-ari-eligible landing with low execution quality may award yuko-equivalent or no score at all, depending on Ring 1 scoring rules.

3. **Counter vulnerability.** A throw that fires at low execution quality leaves tori in a more compromised post-throw position — the kake didn't complete the rotation, the connective grips remained engaged, tori is closer to uke and slower to recover. Counter-window perception (Part 3.5) is computed against tori's post-throw vulnerability, which scales inversely with execution quality.

4. **Prose register.** The narration layer reads execution quality directly. A throw at 1.0 narrates as a clean technical action. A throw at 0.3 narrates as an "almost-threw" — uke staggers but recovers, or lands but rolls out, or absorbs the force without scoring. This is the texture that distinguishes white-belt sloppy success from elite-level clean execution in the log.

**Why this is in the spec, not deferred.**

A simulation that only models clean throws and clean failures cannot represent the central pedagogical fact of judo: that a sloppy throw can still work. White, yellow, and green belts succeed with technically incorrect execution all the time — the throw lands, the score is awarded, the simulation must be able to narrate it. Without execution quality as a first-class concept, the simulation collapses into a binary that the source material does not have.

This also resolves a class of failure-mode tickets that would otherwise need bespoke compromised states. Hip-engagement on a non-hip throw (HAJ-59), heel-to-calf O-soto-gari (HAJ-55), Tai-otoshi with hips loaded in front — these are not signature failures. They are signature-valid throws executed at low quality. Hard gates and new compromised states would over-correct by removing them from the throw space entirely. Within-signature quality is the truer model: the throws fire, but they fire badly.

**Implementation note.**

The mechanism is committed by this sub-section. The specific calibration — what curve maps execution quality to force transfer, what threshold separates ippon from waza-ari, how counter vulnerability scales — is the work of subsequent tickets. The first such tickets are HAJ-55 and HAJ-59 in revised form: they no longer add hard gates or new compromised states. They become specifications of how their respective execution patterns reduce execution quality and what the resulting outcomes look like.

--- END ---

## Verification

After the edit, verify:
- Section 4.2 ends exactly as it did before the edit (no changes).
- Section 4.2.1 appears between Section 4.2 and Section 4.3, at the correct heading level (`###` — same level as 4.2 and 4.3).
- Section 4.2.1's heading reads "### 4.2.1 Execution quality within signature".
- Section 4.3's heading ("### 4.3 The Couple throw template") is unchanged.
- Blank lines separate the new section from both neighbors.
- No other sections were modified.
- The commit touches only `physics-substrate.md`.

Do not modify any Python code in this edit. Code-side implementation follows in a separate ticket (to be filed as "Execution quality plumbing" — the spine ticket that HAJ-55 and HAJ-59 will depend on).
