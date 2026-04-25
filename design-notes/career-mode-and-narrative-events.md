# career-mode-and-narrative-events.md

## Purpose

This doc defines what Career Mode is in HAJIME and what narrative events are. They are coupled: Career Mode is the container, and narrative events are the content units that fill it. Both need committing-to in one place because the shape of the container determines what the events have to do.

This is internal design territory. It commits to several decisions and flags the open questions for later.

# Part 1 — Career Mode

## What Career Mode is

Career Mode is HAJIME's primary play surface at EA. The player runs a dojo from opening to a closing inheritance moment, across roughly one to a few generations of student lifecycles. Sandbox Mode (post-EA) generates similar structure procedurally; Career Mode is where authored content does most of the work.

Career Mode is *not* a campaign with multiple branching endings, *not* a single-character career arc, and *not* a scenario series. It is one continuous run of a dojo with anchored entry and anchored exit, emergent middle, and a continuity-not-game-over relationship to failure.

## Run scope

A single Career Mode run targets:

- **In-game duration:** 5–10 years.
- **Real-time playtime:** 15–25 hours.
- **Lifecycle generations played through:** ~2 — enough that the player sees a cohort arrive, mature, and either inherit or graduate while another cohort is still rising.

These numbers are calibration targets, not Phase 1 goals. Phase 1 (Personal Checkpoint, Jan 9 2027) compresses to a much shorter horizon while sketching the shape. Full calibration happens between Phase 1 and EA.

## Branching shape — anchored emergent

Career Mode has two Anchoring Scenes guaranteed to fire every run:

- **Opening — Twins Arrive.** Authored, fixed for the first run. The first dramatic moment of the game.
- **Closing — an inheritance scene.** Normally "Twins as Disciples" if the Twins reach the right lifecycle stage; transformed into a different inheritance scene if a succession event has shifted the cast (see "Succession" below).

Between the two, the calendar ticks and narrative events emerge from simulation state. There are no multi-branch story trees. The shape is fixed (opening → emergent middle → closing). The texture is emergent.

What makes a run *different* is what the player did to the lineage, the culture, and the roster by the time the closing fires. Same scene shape arriving with different inheritance, different cultural lean, different students.

Important matches happen frequently — the texture of "the coach sits to watch a match unfold" is something the engine produces often during the run. No specific match is a fixed plot beat.

## Succession — failure becomes continuity

When the dojo collapses past a threshold, the run does not game-over. A **succession event** fires:

- A time skip of several years passes.
- A new player-character takes over: most often a senior student who survived the collapse, sometimes an external buyer (a regional black belt looking to acquire a dojo), sometimes a fresh character who buys a different dojo and starts over with the lineage carried forward.
- The new character can either continue with the same dojo (rebuying or reopening it) or purchase a different one. The lineage from before transmits in either case.
- The run continues. The calendar resumes after the time skip. The closing eventually fires with whoever is running the dojo at that point.

Collapse thresholds — *placeholder, calibration territory:*

- Cash balance negative for N consecutive months.
- Active student count drops below a floor (e.g., 1) for N consecutive months.
- Cultural collapse: every student leaves over a short window for the same cultural reason.

A run can include multiple successions. A long run might play through two or three player-characters across a single Career Mode session. Each succession is a continuity event, not a reset — the lineage data, dojo history, and student records all persist forward.

This is unusual for the genre. Most simulation games have explicit loss conditions; HAJIME has *transformations of who's running the dojo.* The "either-choice-okay" thesis principle extends here to "either-outcome-okay" — collapse is a flavor of continuation, not a stop sign.

## Cross-run persistence

Cross-run persistence is the *between-run* version of what succession does *within a run*. Career Mode run 1 ends; the next run inherits the lineage that run 1 left behind. The "father" of run 2 is the player-coach (or final successor character) of run 1.

Detail and mechanism is in `lineage-system.md`. The relevant Career Mode commitment: each run's *ending state* becomes a candidate starting state for the next run.

**Open question:** how many generations chain before the player is offered a clean reset? Probably 3–5 runs, with a soft option to fork off into a fresh authored lineage at any reset point. Defer.

## Difficulty curve

Career Mode does not target a rising-difficulty curve in the usual sense. Instead:

- **Player competence rises** with playtime, as expected.
- **Dojo complexity rises** with student count and lineage depth.
- **Net challenge stays roughly even** but the *kind* of decision shifts:
  - **Early run:** economic survival, three-class break-even, recruiting beyond the Twins, basic session composition, navigating the antagonist's first visit.
  - **Mid run:** lifecycle gates, promotion philosophy choices, cultural drift decisions, scaling beyond the basement.
  - **Late run:** legacy questions, inheritance choices, who carries what forward, the closing scene's setup.

The player should not feel they "got better" at the same task — they should feel they grew into different tasks.

# Part 2 — Narrative Events

## What a narrative event is

A narrative event is a discrete moment in the run that surfaces to the player through the scene presentation pattern (HAJ-120) or through the coach stream. Events range from full Anchoring Scenes that pause the calendar to ambient one-line observations that flow past without interrupting.

Every event is a unit of (1) *trigger conditions*, (2) *beats* (what plays out), and (3) *consequences* (what changes). Different event types weight these three differently — Anchoring Scenes are mostly beats, ambient events are mostly trigger-and-consequence with minimal beats.

## Event template

Every narrative event is described by:

- **Trigger conditions.** A predicate over current game state. Could be calendar-pinned (fires on day X), state-pinned (fires when culture vector crosses a threshold, or when a student reaches a lifecycle gate, or when the cash balance drops below a level), or composite.
- **Pre-conditions / guards.** Additional constraints that prevent firing (e.g., "do not fire if Anchoring Scene is currently playing", "do not fire if same event fired in the last N days").
- **Beats.** The structured presentation: narration beats, dialogue beats, choice beats, reflection beats. Reuses HAJ-120's scene presentation pattern. Some events have zero beats — they only emit a coach-stream line.
- **Consequences.** State changes the event produces: cultural lean shifts, lineage drift annotations, student state updates, scheduling of follow-up events, flag flips. Consequences fire whether or not the player notices the event.
- **Priority class.** Determines firing order when multiple events compete and whether auto-advance halts (see "Firing and priority resolution" below).

## Six event types

1. **Anchoring Scenes.** Fixed, scheduled by run state. Two per run (opening, closing). Hand-authored, full beat structure, calendar pauses, the player cannot skip. Core dramatic moments.
2. **Succession events.** Triggered by collapse-condition predicates. Time-skip + character handoff + run continuation. Hand-authored shells with parameter substitution for which character takes over. Fire mid-run, possibly multiple times.
3. **Antagonist visits.** Semi-scheduled, calibrated cadence. Templated content with substitution for which antagonist (in runs with multiple antagonists or antagonist drift). Pause the calendar; the player navigates a confrontation; consequences shape future events.
4. **Lifecycle gates.** Triggered by student state crossing thresholds (graduation, promotion review, leaving, mastery moment). Templated content with student-name substitution and parameterization for which gate. Pause the calendar briefly.
5. **Cultural moments.** Triggered by cultural feedback loop signals — when a student's cultural fit drifts past a threshold, when the dojo's culture shifts past a threshold, when a cultural input choice has compounded into a visible effect. Procedurally assembled from a fragment corpus. Surface in the coach stream without pausing.
6. **Ambient texture.** Frequent, low-stakes observation-style events. "Maria is staying late after class again." "The mat is starting to show wear in the corner where everyone drills uchi-mata." Procedurally assembled from a large fragment corpus. Surface in the coach stream without pausing. The texture of the dojo as a place.

## Three authoring tiers

The six event types group into three authoring tiers:

- **Hand-authored** (Anchoring Scenes, Succession event shells): ~10–15 unique scenes per run, each fully written. The Anchoring Scenes for the first authored run plus the few succession variants needed.
- **Templated** (Antagonist visits, Lifecycle gates): ~30–50 distinct templates with parameter substitution. Each template handles a class of moments (e.g., a "graduation conversation" template that varies by student personality and lineage drift).
- **Procedural** (Cultural moments, Ambient texture): hundreds of fragments combined into thousands of possible surface events. The fragment corpus is hand-written but the assembly is automatic.

This split is what makes the simulation feel lived-in without requiring infinite hand-writing. The hand-authored layer carries dramatic weight; the templated layer carries categorical recognition; the procedural layer carries texture.

## Firing and priority resolution

The calendar checks each tick (or each day, in low time-scale modes) for events whose triggers are satisfied. When multiple events qualify simultaneously, priority class resolves order:

1. Anchoring Scenes (highest)
2. Succession events
3. Antagonist visits
4. Lifecycle gates
5. Cultural moments
6. Ambient texture (lowest)

Auto-advance behavior by class:

- **Halts auto-advance:** Anchoring Scenes, Succession events, Antagonist visits, Lifecycle gates. The first four classes interrupt the player's fast-forward and demand attention.
- **Flows past:** Cultural moments, Ambient texture. These surface in the coach stream as one-line observations without pausing the calendar.

This implements the "attention scarcity" thesis principle: the player feels the texture of dojo life passing without being interrupted by every detail. Important moments interrupt; texture does not.

Calibration note: which classes halt is calibration territory. The split above is a starting position. A few hours of play will reveal whether (e.g.) low-stakes lifecycle gates should flow past instead of halting.

# Part 3 — Open questions and handoffs

**This doc commits to:**

- Run scope (5–10 in-game years, 15–25 hrs real-time, ~2 lifecycle generations)
- Two Anchoring Scenes per run (opening + closing); emergent middle
- The closing is condition-fixed (an inheritance scene), not character-fixed
- Failure becomes succession, not game-over; runs can chain successions
- Cross-run persistence carries lineage between runs
- Difficulty curve: flat-with-shifting-kind, not rising
- Six event categories
- Event template: trigger + beats + consequences
- Three authoring tiers (hand / templated / procedural)
- Auto-advance halt rules

**This doc does not commit to:**

- Specific collapse thresholds for succession triggers — calibration territory.
- Generation chain horizon before reset — defer (will surface during cross-run testing).
- Exact fragment corpus for procedural events — content work, post-design.
- Templating language / data format for events — implementation territory, Ring 3.
- Content for the closing scene's collapse-path variants — authoring work, after Phase 1.

**Sibling design notes that touch this:**

- `lineage-system.md` — lineage's cross-run persistence operates inside this doc's run shape. Succession-on-collapse and cross-run persistence are two scales of the same continuity story.
- `cultural-layer.md` — cultural moments and ambient texture trigger off the culture vector defined there.
- `dojo-as-institution.md` — the dojo's institutional state is what collapse conditions read against.
- `physics-substrate.md` — the match engine produces the matches that observations reference, including the "coach sits to watch a match unfold" texture.

**Linear references:**

- HAJ-112 — Design question: Career Mode (this doc resolves the High-priority Design & Triage ticket).
- HAJ-111 — Design question: Inheritance Event (closing scene mechanism).
- HAJ-113 — Design question: lineage system (now drafted, see `lineage-system.md`).
- HAJ-106 — Design question: antagonist (cadence calibration territory).
- HAJ-104 — Design question: lifecycle (lifecycle gates as event category).
- HAJ-109 — Design question: culture & psychology (cultural moments / ambient feeds).
- Ring 3 — Narrative Event Framework project — implements this doc's event template.
- HAJ-120 — Opening Anchoring Scene event (scene presentation pattern, reused for all halt-class events).
