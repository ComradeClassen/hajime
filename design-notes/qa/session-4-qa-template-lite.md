# Session 4 QA — Lite Template

*Twenty matches. Four lenses per match. No checklists longer than your patience.*

Session 4 scope: HAJ-24 through HAJ-29 — worked throw templates, four-dimension signature match, worked throw instances, failed-throw compromised states, skill-compression, counter-windows as state regions.

**How to run:** `python src/main.py`. Default is Tanaka (BLACK_1, Seoi-nage specialist) vs Sato (Uchi-mata specialist). Reseed in `src/main.py`.

The goal is not to tick boxes. The goal is to answer: *do these matches look like judo now?* Write a couple of sentences per lens. If a lens has nothing to say for a given match, skip it — empty sections are a signal in themselves.

---

## Per-match entry (copy 20 times)

### Match #__ — seed `___`

**Outcome:** `[winner]` by `[ippon / 2× waza-ari / decision / draw / hansoku-make]` at tick `___`.

**Bug.** Anything that actually broke, misfired, or contradicted the spec. Log lines that shouldn't exist, crashes, impossible states, numbers that don't add up. One line per bug is fine. No bugs = say so.

**Feel.** How did the match *read*? Did it feel like four minutes of judo or forty-five seconds of dice rolls? Where did tension build, where did it sag? Was the winning throw earned or did it just roll in? Two or three sentences of prose, not a rubric.

**Prose.** What did the log itself sound like? Was there dead air during grip battles? Did compromised-state transitions narrate cleanly, or did they read as event spam? Any specific lines that landed well, or any that felt like placeholder?

**Architecture.** Anything this match surfaced about the structure — not a calibration knob, but a design seam. "The sub-event markers don't carry any force weight and you can feel it here." "Counter windows and compromised states overlap in a way that suggests they're the same concept viewed from two sides." Skip if nothing structural showed up.

---

## After the twenty

A page of prose, not a scorecard. Answer whichever of these actually matter after watching the twenty:

**What's working.** The one or two things that Session 4 clearly bought us. Be specific — not "throws feel better" but "Seoi-nage now reads as a grip-dependent ambush, not a dice roll."

**What's off.** The thing you'll have trouble not thinking about on the train home. The bit that made you wince more than once.

**Suspected calibration vs. suspected design.** For each "off" item — is this a knob (commit threshold, counter base rate, recovery ticks) or is this a shape problem (sub-events don't do what their name implies; compromised states overlap with counter windows; etc.)? Calibration is for this session; design is a ticket.

**Tickets to open.** One line each. Only the things you actually want to come back to.

**Verdict.** `ship as-is` / `calibrate and re-run` / `design pass needed before re-running`.

---

*If you want the exhaustive version — every compromised state ticked, every throw template counted, every knob cross-referenced to a source line — it lives in `session-4-qa-template.md`. Pull from it when a specific pattern here demands a full audit.*
