# TACHIWAZA — Master Design & Development Document
### A Living Brainstorm / Build Roadmap / Reference

*This document is a working artifact. Update it after every session.*

---

## THE CORE LOOP

You coach a stable of judoka. You train them in the dojo. You enter them in matches. You watch the matches simulate tick-by-tick as a stream of grip exchanges, fatigue events, throw attempts, scrambles, and ground transitions. When the referee calls Mate, the simulation pauses. You see your fighter's current state. You issue up to two short instructions. The simulation resumes — and how well your instructions land depends on the fighter's composure, fight IQ, fatigue, and trust in you. After the match, you return to the dojo and use what you learned to shape the next training cycle.

That's the loop. Everything else exists to make that loop deeper.

---

## THE ANCHORING SCENE

This is the scene the whole game is built around. When in doubt, return here.

```
Round 1 · 0:00 — Tanaka (blue) vs. Sato (white)

0:03  Tanaka steps in. Right hand reaches for the lapel.
0:04  Sato's left hand intercepts — pistol grip on the sleeve.
0:06  Tanaka pulls — Sato's grip holds. Right grip strength -1.
0:09  Tanaka secures high collar. Deep grip.
0:11  Sato breaks posture forward, framing the bicep.
0:14  Grip battle. Both hands engaged. Tanaka's forearms fatiguing.
0:18  Tanaka attempts seoi-nage —
       → Sato sprawls. Hips back. Throw stuffed.
       → Slight scramble. Sato briefly exposes back.
       → ne-waza window: 11% — Tanaka does not commit.
       → Both stand. Grips reset.
0:22  Sato attacks o-uchi-gari — Tanaka's left leg absorbs.
0:24  Mate.
```

**[ Match paused — coach's chair ]**

```
TANAKA          status
─────────────────────────
Composure       7/10  ↓ (-1 from stuffed throw)
Right grip      5/10  ↓↓ (fatigued)
Left grip       8/10
Legs            8/10
Read speed      6/10
Trust in coach  9/10  ← high. He'll listen.

What you saw: He went for his strongest throw too early.
Sato read it. The grip fight is going against him on the right side.

→ Choose 2 instructions (max):

  A. Switch stance. Attack the left side.
  B. Break his grip first. Don't engage until you have yours.
  C. Stay patient. Let him come to you.
  D. Go to the ground if he opens up again.
  E. Tighten up. He's reading you.
  F. [Write your own — short phrase]
```

The player picks B and D. The simulation resumes and Tanaka begins executing the new plan, biased by composure, fatigue, and trust.

This is the soul of the game. Everything in the rest of this document is in service of making this scene work.

---

## THE SIMULATION RINGS

*Concentric layers. Inner rings get built first.*

### RING 1 — The Match Engine (BUILD FIRST)

Event-driven tick simulation. Two judoka in a relational state graph (grip configuration, posture, position, stance matchup). Throw attempts as high-commitment state changes. Stuffed throws can open ne-waza windows. Mate is called naturally on stalemate, OOB, defensive resolution, or penalties. Standard IJF scoring.

### RING 2 — The Coach Instruction System & Tournament Attention

The Mate window. Two instructions max. Reception based on composure × trust × read speed × (1 - fatigue). Free-text instructions mapped to known tags via a small Claude call or local heuristic.

**Tournament Attention Economy** also begins here — when you have multiple judoka in one tournament, you can only sit in one chair at a time. See `design-notes/dojo-as-institution.md`.

### RING 3 — The Dojo & Training System

The dojo as facility. Training items target specific attribute clusters. Weekly time advancement. Trust as the slowest variable in the game. Money & Prestige activate here — see `design-notes/dojo-as-institution.md`.

### RING 4 — The Roster, Long Arcs, & Lineage

Recruitment of young prospects. Career arcs spanning 10+ in-game years. Multigenerational lineage when a sensei retires and a former judoka inherits the dojo. Traits, prestige, and institutional memory carry forward.

### RING 5 — The 2D Visual Layer (POST-PROTOTYPE)

Pixel-art figures with stripe-based grip indicators. Kairosoft-style top-down dojo view. Always paired with the prose log, never replacing it. *Symbols that change state, not animation frames.*

### RING 6 — Sound (LATE)

Dojo ambient theme, match tension layers responsive to score and fatigue, signature motif when one of *your* judoka enters their finals. Built when the world is ready to hold it.

---

## THE INSTRUCTION TAXONOMY

*Initial set. Will grow with playtesting.*

**Grip-focused** — Break his grip first / Get the dominant grip before you commit / Switch stance — attack the other side / Stop reaching with your tired hand

**Tempo-focused** — Stay patient. Let him come to you / Push the pace. Tire him out / Slow it down. Reset / Attack on his next breath

**Tactical** — Go to the ground if he opens up / Stay standing — he's better on the mat / Attack his weak leg / Counter, don't initiate

**Composure** — Tighten up. He's reading you / Trust your training / Forget the last exchange / Breathe. You have time

**Risk** — Take the chance. Go for ippon / Play for shidos. He'll panic / Defensive grip. Run the clock

---

## TONE RULES (the writing guide)

**The voice of the match log is a knowledgeable sportswriter.** Specific. Calm. Loves the sport. Doesn't explain what kuzushi is — assumes the reader is paying attention or willing to learn.

**The voice of the coach window is intimate.** It's the player's view of their fighter. Quiet, focused, slightly worried.

**The voice of the dojo is warm.** This is home. This is where the work happens. The dojo prose has the texture of routine — sweat, repetition, small jokes, the smell of the mats.

**No hype. No announcer voice.** Tachiwaza is not the UFC. It is judo — a sport with deep roots, formal etiquette, and an understated culture. The writing should respect that.

**Every fighter is treated with dignity.** Including the opponents. Including the ones who lose. Especially the ones who lose.

---

## OPEN QUESTIONS

**Q1: How real-time is the match?** Live-scrolling log with player-controlled speed seems right, but worth playtesting.

**Q2: How many judoka in a stable?** 5 active fighters as a starting cap. Eventually unlock more — and competitive stables grow significantly across the multigenerational arc.

**Q3: How long is a "season"?** ~1 in-game month = 5 minutes of play. A full career arc fits in a play session of reasonable length.

**Q4: Single-discipline or multiple?** Pure judo for v1. BJJ, sambo, freestyle wrestling could be future expansions sharing the same engine.

**Q5: How does a non-judoka learn the sport through play?** Glossary tooltips on every term in the match log. Hover "ko-uchi-gari" → see a one-line description and a tiny diagram.

**Q6: AI prose generation for matches?** Same architectural question as Player Two. Build deterministic prose templates first as a fallback; layer Claude-in-Claude generation on top once the system works.

**Q7: Does the Mate window have a real-time pressure element?** A 10-second window to issue instructions before the fighter goes back out alone? Mirrors real coaching pressure. Possibly toggleable difficulty.

---

## WHAT TO BUILD FIRST (priority order)

**Phase 1 — The Match Engine Skeleton.** Three-layer Judoka class. 15 body parts declared. Throw and Combo registries. Two hand-built fighters. Match tick loop with placeholder events. Match ends with a placeholder winner. Goal: prove the architecture compiles.

**Phase 2 — Real Combat Logic.** Real grip state graph. Throw success rolls using body archetype, dominant side, fatigue. Ne-waza windows. Mate detection. Scoring. First prose templates.

**Phase 3 — The Mate Window.** Pause logic. Stat panel. Instruction menu. Reception calculation. Resumption.

**Phase 4 — A Single Training Cycle.** Dojo class. Training items. Weekly time. Attribute changes. Injury risk.

**Phase 5 — A Roster & Career.** Recruitment. Tournament schedule. Multiple judoka in parallel. First version of Tournament Attention Economy.

**Phase 6 — The 2D Layer.** Only after the loop is undeniably fun in pure text.

---

## RELATIONSHIP TO PLAYER TWO

Tachiwaza and Player Two are **parallel projects of equal priority.**

Both share architectural DNA:
- Tick-based simulation
- Prose layered over structured events
- Systems as the author
- Python and the same toolchain

Both compete for the same finite hours. Whichever project is generating real creative pull on a given day earns that day's session. The discipline is not which project ranks higher — it's that whichever one gets a session today gets a *clean* session: focused, committed at the end, with a clear next entry point recorded in the dashboard.

**Practical working model:**
- Each project has its own repo, its own folder, its own dashboard, its own orientation doc
- When a session is for one project, the other repo stays closed
- Once a week (Sunday or whenever feels natural), a 10-minute meta-check: which project am I excited to open this week? That answer is data — not a contract — and over 3–4 weeks a pattern emerges
- That pattern *is* the real roadmap. It comes from doing the work, not from deciding in advance

**Scope discipline still applies inside any single session.** Don't try to build Ring 4 features when you're supposed to be writing Phase 1 skeleton code. The dojo-as-institution doc holds the long ambition; Phase 1 stays Phase 1. Discipline about staying inside the chosen ring is different from ranking projects.

Player Two has a January 9, 2027 release target. That target was set when Player Two was the only project. If Tachiwaza turns out to be the alive project for an extended stretch, Player Two's date or scope adjusts. The release date serves the work. The work does not serve the release date.

---

## WHAT'S BEEN BUILT

*Nothing yet. April 13, 2026 — design phase.*

## WHAT'S NEXT

1. v0.2 of `data-model.md` integrating age curves, archetype definitions, and amplified dominant-side grips ✓
2. First Claude Code session: implement Phase 1 skeleton from the data model spec
3. Run `python src/main.py` and verify the architecture compiles and the placeholder match runs

---

*Document version: April 13, 2026. Update after every session.*
