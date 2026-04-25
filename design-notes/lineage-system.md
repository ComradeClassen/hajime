# lineage-system.md

## Purpose

This doc defines what a *lineage* is in HAJIME, how it's structured as data, how the player encounters it, and what carries between Career Mode runs. It exists because the master doc references a lineage system that doesn't yet have its own design note, and because the cultural-feedback-loop principle and the closing Anchoring Scene ("Twins as Disciples") both depend on something specific being meant by "lineage."

This is internal design territory. It commits to several decisions and flags the open questions for later.

## What a lineage is

A lineage is a *bundle of inheritance* transmitted through a graph of teachers and students. It is not a stat block, not a single ancestral line, and not a flag set on a coach. It carries four kinds of content:

- **Tradition** — a named identity (e.g., "Tanaka-line") that students and rivals recognize.
- **Signature techniques** — specific throws, ne-waza positions, or grip games that this lineage is known for.
- **Philosophy** — short stated principles ("Never quit a grip you've earned"; "Win or learn"; etc.) that surface in dialogue and shape student internal states.
- **Rituals** — how class begins and ends, how promotions are conferred, how visitors are received, how mistakes are addressed. The *texture* of the dojo as a place.

These four ride together. A lineage with techniques but no rituals is a curriculum, not a lineage. A lineage with rituals but no techniques is a culture without a craft.

## Sources of transmission

A lineage is not transmitted by a single teacher. Within a dojo, multiple senior figures contribute different pieces of the bundle:

- The **head coach** transmits the dominant share — usually the philosophy, the rituals, and a core of signature techniques.
- **Assistant coaches** (where they exist) often carry their own signature techniques alongside the head coach's, and transmit those to students directly.
- **Senior students** can become transmitters themselves once they cross the right lifecycle threshold — a brown belt teaching a white belt their signature uchi-mata is a real piece of the lineage moving sideways.

This means the unit of transmission is the *dojo*, not the coach. A student inherits from the room they trained in, weighted toward the head coach but not exclusively from them. This is judo-true and mechanically richer than a single-teacher model.

The implication for `dojo-as-institution.md`: the dojo is what carries the lineage forward across student generations within a single coach's career. The institution outlives the individual transmissions.

## Data model

A lineage is a directed graph.

- **Nodes** are coaches and other transmitters (assistants, senior students once they reach transmitter status).
- **Edges** are inheritance events — typed by what was transmitted (technique, philosophy fragment, ritual, full lineage handoff) and stamped with the calendar date the transmission occurred.

The graph supports two kinds of edges:

- **Cross-generation edges** — the father → the player-coach, the player-coach → a graduated senior student. These cross dojo boundaries and time.
- **Within-dojo edges** — head coach → assistant, assistant → senior student, senior student → junior student. These live inside a single dojo's lifespan and represent its internal transmission.

Storing this as a graph (rather than a parent-pointer list) is what makes the within-dojo edges expressible. A list collapses the dojo into a single transmitter; the graph keeps the assistants and senior students legible as their own nodes with their own outgoing edges.

Each node carries: name, the bundle pieces they transmit (techniques, fragments, rituals), and any student-side preferences (who they prefer to teach, what kinds of students they don't get along with).

## The starting lineage

In Career Mode, the player-coach starts with one inherited lineage — authored, fixed for the run. The lineage comes from the player-coach's *father*. The father is a fictional character; what the lineage carries (tradition name, signature techniques, philosophy, rituals) is authored content for the first Career Mode run.

Subsequent Career Mode runs inherit *what the previous run produced* — see "Cross-run persistence" below.

Sandbox Mode (post-EA) generates a procedural starting lineage. The shape of that procedure is out of scope for this doc.

## Lineage drift

Across a Career Mode run, the player's relationship to the inherited lineage takes one of three shapes — and any of the three is valid:

- **Preserve** — the player runs the dojo close to how they were taught. Inherited techniques, philosophy, rituals carry forward mostly intact.
- **Extend** — the player adds. New techniques (from observation, from competition, from a visiting figure), new principles, modified rituals. The lineage at run's end is recognizably the inherited one with new pieces added.
- **Refuse** — the player drops or reverses pieces. A technique the father swore by is removed. A ritual is replaced. A principle is contradicted publicly.

All three are valid endings. The "either-choice-okay" thesis principle applies hard here: refusing a piece of the inherited lineage is not failure, and preserving it is not safety. The closing Anchoring Scene ("Twins as Disciples") plays out across any of the three shapes.

Drift is not a core mechanic surfaced constantly to the player. It is *observable*, not *managed* — see the next section.

## Visibility and player surface

The player does not navigate the lineage graph as a primary interaction surface. There is no constant lineage tab the player is expected to tend. Lineage surfaces three ways:

- **Consequences in play** — certain techniques are available because they're in the lineage; certain students self-select to or away from the dojo because of cultural alignment with the lineage's philosophy and rituals.
- **Dialogue references** — senior students, the antagonist, occasional narrative beats, and Anchoring Scene reflection moments mention "what your father taught you," "the way the old dojo did it," etc. The lineage is heard more often than it is shown.
- **Post-hoc visualization** — a menu (probably accessed from a coach-info or dojo-info screen) shows the lineage graph as a tree with nodes and edges, the techniques and rituals attached, the drift annotations. The player can study it. They are not required to.

The visualization is a Ring 5 nicety in execution but the *data* it visualizes is real and load-bearing — the simulation reads the lineage graph constantly even when the player isn't looking at it.

## Cross-run persistence

This is the second-run hook for Career Mode.

Career Mode run 1: the player inherits an authored lineage (from the father), runs the dojo, drifts the lineage in some direction, ends the run with the lineage in some configuration.

Career Mode run 2: the player inherits *what they left behind*. The new player-coach is positioned downstream of the previous run's final lineage state. The "father" of run 2 is the player-coach of run 1.

This is the Wildermyth-Heroes parallel adapted for Hajime's frame. It turns Career Mode from a single coach's career into a story about generations. It also gives the player a concrete reason to care about *how* they leave the lineage at the end of a run — that ending becomes someone else's starting point.

**Open question:** how many generations chain before reset? Wildermyth allows arbitrarily long chains; Hajime probably wants a soft horizon (3–5 runs?) before offering a fresh start. Defer to `career-mode-and-narrative-events.md`.

## Relationship to the culture vector

Lineage *biases* the culture vector but does not constrain it.

A lineage with competition-heavy philosophy and tournament-frequent rituals tilts the dojo's starting culture toward competition orientation. A lineage with traditional / pedagogical philosophy tilts it toward formality and depth. The bias is real — students self-select against it, and shifting the culture against the lineage's bias takes ongoing player effort.

But the bias does not lock. A player who inherits a competition-heavy lineage can deliberately drift it toward tradition (refusing the competition rituals, adding pedagogical principles), and over time the culture vector follows. The drift mechanic is the channel through which the player overrides the bias.

See `cultural-layer.md` for the culture vector itself; this doc only specifies the bias relationship.

## Open questions and handoffs

**This doc commits to:** the bundle (tradition, techniques, philosophy, rituals); the graph data model; multi-source within-dojo transmission; authored starting lineage from the father; the three drift modes; post-hoc visualization rather than constant management; cross-run persistence; bias-not-constrain culture relationship.

**This doc does not commit to:**

- The specific schema for technique entries, philosophy fragments, and ritual descriptions in the data — defer to implementation when Ring 2 Phase 3 lands.
- The number of generations before cross-run persistence resets — defer to `career-mode-and-narrative-events.md`.
- The exact UI of the post-hoc lineage visualization — defer to Ring 5.
- How rituals interact with session composition — pointer to `dojo-as-institution.md`.

**Sibling design notes that touch this:**

- `career-mode-and-narrative-events.md` (drafting target) — the run shape that lineage's cross-run persistence operates inside.
- `cultural-layer.md` — the culture vector that lineage biases.
- `dojo-as-institution.md` — the dojo as the unit of transmission, where rituals live.

**Linear references:**

- HAJ-113 — Design question: lineage system (this doc resolves the High-priority Design & Triage ticket).
- HAJ-111 — Design question: Inheritance Event (the moment-of-handoff mechanic this doc's structure operates against).
- HAJ-112 — Design question: Career Mode (run shape, including cross-run persistence horizon).
- HAJ-109 — Design question: culture & psychology (the culture vector this doc biases).
