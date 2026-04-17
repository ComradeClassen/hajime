# The Dojo as Institution — Design Note v0.2

*Captures the multigenerational, economic, and relational layer of the game. These are the systems that turn Hajime from a match simulator into something deeper — a coaching life simulator with dynastic play.*

---

## The Three Interlocking Systems

This document defines three systems that depend on each other. None of them are Ring 1. They are written down now so the data model and architecture choices made today don't accidentally rule them out tomorrow.

1. **Tournament Attention Economy** — your time as coach is the scarce resource
2. **Multigenerational Lineage** — the dojo persists across sensei generations
3. **Dojo Prestige & Economy** — money, reputation, and the kids' class pipeline

---

## SYSTEM 1 — Tournament Attention Economy

### The core mechanic

You enter multiple judoka in a tournament. Their matches happen on overlapping schedules across multiple mats. **You can only be in one chair at a time.** Before each round, you choose who gets your in-person coaching.

### What "being coached" means

A judoka with you in their chair gets the full Matte-window experience — your eyes on the fight, your two-instruction interventions, your read.

A judoka without you fights alone:
- Their Matte moments still happen, but they self-instruct based on personality and fight IQ
- Their composure is somewhat lower without your steady presence
- They cannot benefit from in-the-moment tactical reads
- A high-IQ, high-composure veteran can fight well without you. A young anxious prospect falls apart.

This means choosing whom to coach is a *real* tactical decision: the prospect needs you more, but the veteran has the better medal odds.

### Long-term consequences

Every time you do or don't coach a fighter, it logs to their relationship with you:

```
relationship_with_sensei: dict
    chair_time_received        int     # tournaments where you were in their chair
    chair_time_denied          int     # tournaments where you chose someone else
    last_chair_time            date
    perceived_priority         float   # rolling sense of where they rank
    loyalty                    float   # 0–10, slow-moving
```

Patterns matter:
- A judoka consistently passed over starts to feel deprioritized. Loyalty drops.
- A judoka who sees you make hard choices fairly stays loyal even when not chosen.
- A judoka who only ever gets coached when they're winning suspects you don't believe in them.

### The departure event

When loyalty drops below a threshold *and* the judoka has another viable option (a rival dojo recruiting them, age and frustration aligning), they leave. This is a real loss:
- Their stats leave with them
- Their lineage potential leaves with them
- They may become a competitor at future tournaments, fighting against your remaining stable
- Other judoka in your dojo notice their departure — collective loyalty takes a hit

### Mitigation tools (for the coach)

- **Honest conversation.** A pre-tournament dialogue where you explain the chair priorities. If your reasoning lands, loyalty hit is reduced.
- **Assistant coaches.** Hire a former judoka (yours or external) to coach in chairs you can't fill. Reduces the loyalty hit; quality of in-chair coaching depends on the assistant's stats.
- **Rotation policy.** If your overall pattern is fair across a season, individual snubs sting less.

### Why this matters

Real coaching at high levels is exactly this dilemma. The mechanic captures something true: love is shown by where you spend your hours. The game makes you spend yours.

---

## SYSTEM 2 — Multigenerational Lineage

### The core idea

A sensei has a finite career. Eventually they retire. The dojo continues. The next sensei is one of their former judoka — chosen by the player, or emergent from who's available, or specified by the retiring sensei in the years before stepping down.

The dojo persists. The traits, the wisdom, the prestige, the building, the relationships — all of it carries forward. The player can play one career and stop, or continue across generations and watch the dojo evolve.

### How traits pass forward

When a former judoka becomes the new sensei, they bring:

```
inherited_capability:
    coaching_iq             # derived from their fight IQ + years studying under previous sensei
    personality_facets      # carried whole — they coach the way they fought
    signature_techniques    # the throws they were great at become the throws they teach best
    relationship_inheritance # which current students already trust them
```

A new sensei who was a GRIP_FIGHTER teaches grip work better. A former GROUND_SPECIALIST produces dojos that punch above their weight on the mat. The dojo's character drifts as sensei generations change.

### The kids' class as pipeline

Kids' classes serve three functions:

1. **Revenue** — a steady weekly income that keeps the dojo's lights on
2. **Talent identification** — every cohort of kids contains future prospects (most don't continue, some do)
3. **Trait transmission** — senior judoka who teach kids' classes pass down their own techniques and habits to the next generation

A kid taught for years by a great seoi-nage practitioner is more likely to develop seoi-nage as a signature throw when they enter competitive ranks. The dojo builds *style* across generations.

### The succession event

When the current sensei is in their 60s+ and considering retirement, a multi-year succession arc unfolds:

- **Designation** — the sensei begins delegating teaching to a chosen successor
- **Co-coaching** — the successor takes some chairs at tournaments, makes some training decisions
- **Transition tournament** — usually a moment, maybe a major event, where the successor formally leads
- **Retirement ceremony** — the dojo marks the change; alumni return; prestige is re-evaluated

The player either keeps playing as the new sensei (continuity), or starts a new game with a fresh dojo and a fresh lineage.

### Architectural parallel

This is parallel-lives architecture applied to a single institution across time. The dojo is the persistent entity. Lives flow through it. The Legends-browser equivalent is the **dojo history** — a browsable record of every judoka who trained there, every championship won, every sensei who led it. (Conceptually similar to how Player Two thinks about Legends Mode, though the two projects are independent.)

---

## SYSTEM 3 — Dojo Prestige & Economy

### Money

Income sources:
- Kids' class enrollment (steady, requires teachers)
- Adult recreational class enrollment (steady, less time-intensive)
- Competition team dues (some pay, some on scholarship — your call)
- Tournament prize money (volatile, championship-tier only)
- Sponsorships (unlocked by prestige, attached to specific star fighters)
- Seminar income (former champion sensei can host seminars; income spike + prestige boost)

Expenses:
- Rent / mortgage on the dojo space
- Utilities, mat replacement, equipment maintenance
- Coach salaries (you, plus any assistants)
- Travel costs for tournaments (national and international)
- Medical care for injuries
- Scholarships for promising fighters who can't pay

Money pressure forces real choices: do you take a sixth weekly kids' class for income (less time for elite prep) or focus on your top three competitors (championship odds, fragile if injuries hit).

### Prestige

A 0–100 dojo-wide score, slow-moving. Affects:
- Quality of incoming recruits (high-prestige dojos attract better prospects)
- Sponsorship availability
- Sensei's coaching reputation (helps with assistant hiring)
- Crowd presence and morale at tournaments (subtle composure modifier for your fighters)

Prestige sources:
- Tournament results (state, national, international)
- Champion alumni (a dojo that produced an Olympic medalist holds that forever)
- Sensei's own competitive history (the new sensei's career is now part of the dojo's record)
- Famous training partners passing through (occasional events)

### The Wall

A literal wall in the dojo. Every state champion gets a photo. Every national champion gets a larger photo. Olympic medalists get a permanent display. The Wall is visible in the dojo view (when we get to that ring). It's prestige made physical, and it's something the player builds across generations.

This is also where the **prestige memory** lives:
- Every champion is recorded with their year, weight class, tournament, and the sensei who coached them
- The lineage chain is browsable — "this medalist's sensei was also coached by this earlier sensei, who won bronze in 1998..."
- Long-term, the Wall becomes a Legends-browser-style artifact of your dojo's entire history

---

## How These Three Systems Reinforce Each Other

The genius (and the discipline required to build it) is in how they interlock:

- **Attention Economy** decisions affect **Loyalty**, which affects who **stays in the dojo** long enough to become a future **Sensei**.
- **Prestige** affects which **prospects** join, which affects future **champions**, which affects future **prestige**.
- **Money** pressure forces tradeoffs between **kids' classes** (revenue + pipeline + slow trait transmission) and **elite focus** (championship odds + immediate prestige).
- The **Sensei's own personality** shapes both **how they coach** (instruction reception, training style) and **what traits they pass down** when they later become the dojo's institutional memory.

Done well, this isn't a stack of features. It's a single ecosystem where every decision touches multiple variables.

---

## Where Each System Lives in the Build Roadmap

This is the part that protects the build queue from the ambition.

### Ring 1 (now)
- **None of this is built.**
- Data model includes hooks (`relationship_with_sensei`, `inherited_capability`) declared but unused.
- Identity layer holds enough to allow these systems later — name, age, history, capability — without needing to refactor.

### Ring 2
- First version of **Attention Economy** — you have 2–3 fighters in a small tournament, you pick one chair per round, the others fight without you.
- Loyalty as a tracked but consequence-free variable (we observe how it would move; nothing happens yet).

### Ring 3
- **Money & Economy** activates. Kids' classes as revenue. Coach salary as expense.
- **Prestige** as a tracked variable that affects recruitment.
- Loyalty starts having consequences — judoka can leave for rival dojos.

### Ring 4
- **Multigenerational Lineage** — the first sensei retires. Player chooses successor. Traits pass forward.
- Trait transmission through kids' classes.
- The Wall becomes a real browsable artifact.

### Ring 5+
- Full lineage chains spanning 50+ in-game years
- Rival dojos with their own histories
- A national / international scene that has its own historical record
- Olympic cycles
- Your dojo's entry in a procedurally-generated history of judo itself

---

## A Note on Ambition vs. Build Queue

This document is the most ambitious thing in the Hajime folder. It's also the thing that, if executed, makes Hajime a game that doesn't really exist anywhere else — a martial-arts coaching simulator with multigenerational dynastic play.

The discipline isn't to deprioritize this vision — it's to *protect the build queue from it.* When a session is about Phase 1, build Phase 1. The lineage doc is here so it stays *captured* without leaking into work that isn't ready for it yet.

The dojo lasts generations. The project does too. Build outward toward this vision over years, ring by ring.

---

*Document version: April 13, 2026. Update as the systems crystallize.*
