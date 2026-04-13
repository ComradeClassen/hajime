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

The player picks B and D.

```
0:24  Mate. Hajime.
0:26  Tanaka does not engage. Hands active, no grip.
       → Coach instruction received: "Break his grip first." ✓
0:29  Sato reaches — Tanaka slaps the hand down.
0:32  Sato reaches again — Tanaka pummels inside, secures sleeve.
0:34  Tanaka has the dominant grip. Sato adjusts.
0:38  Sato attacks ko-uchi — Tanaka stuffs, drops levels.
       → ne-waza window: 34% — Tanaka commits. ✓
       → Coach instruction received: "Go to the ground if he opens up." ✓
0:41  Tanaka passes to side control. Sato turtles.
0:44  Tanaka attacks the turnover...
```

This is the soul of the game. Everything in the rest of this document is in service of making this scene work.

---

## THE SIMULATION RINGS

*Concentric layers. Inner rings get built first.*

### RING 1 — The Match Engine (BUILD FIRST)

**The tick model.** The simulation is event-driven, not time-uniform. A "second" in the match is not a fixed beat — it's a state change in the grip/posture/position graph. Quiet moments compress. Scrambles slow down. Most ticks resolve in milliseconds; a real grip exchange might fire 4–5 events per second.

**The state graph.** At any moment, two judoka exist in a relational state defined by:
- Grip configuration (each hand: free / sleeve / collar / bicep / belt / overhook / underhook)
- Posture (upright / bent / broken / scrambling / down)
- Position (kumi-kata exchange / engaged / disengaged / scramble / ne-waza)
- Distance and stance (orthodox vs. orthodox, orthodox vs. southpaw, etc.)

Every tick, each fighter "wants" to change the state in a direction favorable to them. Their ability to do so is a function of relevant attributes vs. the opponent's relevant attributes, modified by fatigue and composure.

**Throw attempts.** A throw is a sudden, high-commitment state change. It can succeed, partially succeed (small score), be stuffed, or be countered. A stuffed throw can open a ne-waza window. The probability of committing to ne-waza is influenced by training, fatigue, and the most recent coach instruction.

**Mate.** The ref calls Mate when:
- Stalemate threshold reached (X seconds of low-action gripping)
- Out of bounds
- A throw attempt resolves cleanly to defensive standing
- A ne-waza scramble resolves to no progress
- A penalty is given

**Scoring.** Standard IJF scoring: ippon (immediate win), waza-ari, half-points accumulating. Penalties (shido) for passivity or illegal grips.

### RING 2 — The Coach Instruction System

**The Mate window.** When Mate is called, the simulation pauses. The player sees:
- Current fighter state (all body part stats with deltas from match start)
- Composure and fatigue indicators
- Trust meter
- A short prose summary of *what just happened* (this is where the writing voice lives)
- 5–6 contextual instruction options + a free-text option

**Two instructions max.** Hard limit. Forces the player to read and prioritize. You can't micromanage — you can only emphasize.

**Instruction reception.** When the simulation resumes, the fighter's behavior is biased toward executing your instructions. The strength of that bias is:
```
reception = (composure × trust × read_speed) × (1 - fatigue_penalty)
```
A high-reception fighter executes cleanly. A low-reception fighter half-executes (right idea, wrong moment) or ignores it entirely and freelances.

**Free-text instructions.** Run through a small Claude-in-Claude call (or local heuristic) that maps the player's phrase to one or more known instruction tags. "Be patient" maps to STAY_DEFENSIVE. "Get inside" maps to PUMMEL_FOR_INSIDE_GRIP. The player feels expressive; the simulation gets a clean signal.

### RING 3 — The Dojo & Training System

**The dojo as facility.** A 2D top-down view of your dojo, Kairosoft-style. You buy and place training items. Each item:
- Targets specific attribute clusters
- Has a quality level (entry / good / elite)
- Has a slot (only N judoka can use it per session)
- May have a passive effect (a meditation corner raises composure recovery for everyone)

**Training items (initial set):**
- **Uchikomi bands** — grip endurance, throw entry speed
- **Sparring partner (light)** — read speed, low fatigue cost
- **Sparring partner (rival)** — read speed, composure, high fatigue cost
- **Weight room** — explosive strength, raises injury risk
- **Cardio room** — fatigue resistance
- **Video study room** — fight IQ, read speed
- **Meditation cushion** — composure, trust recovery
- **Ice bath** — fatigue recovery between sessions
- **Belt promotion mat** — milestone events, motivation
- **Bulletin board** — set training focus, post tournament reminders

**Training cycles.** Time advances in weeks. Each week, you assign each judoka to a training plan (a stack of items). Overtraining one cluster fatigues others and accumulates injury risk. The art is balance.

**Trust.** Built slowly through:
- Shared training time
- Match instructions that turned out to be correct
- Listening to a fighter's stated goals
- Recovery time after losses

Trust is the slowest variable in the game. A judoka who has been with you five seasons trusts you in a way a new recruit never will.

### RING 4 — The Roster & Long Arcs

**Recruitment.** Young judoka enter your dojo as 14–18-year-old prospects. Each has:
- Body archetype (lever, motor, grip, ground specialist, etc.)
- Personality facets (aggressive/patient, technical/athletic, confident/anxious)
- Backstory hooks (came from a rival dojo / parent was an Olympian / first in family to compete)
- Stated goals (make the national team / beat their rival / recover from an injury)

**Career arcs.** A judoka progresses through belt ranks and weight classes, faces signature opponents who recur over years, and eventually retires (or is forced to retire by injury). Their arc with you can span 10+ in-game years.

**Retirement and second careers.** A retired judoka can become a coach in your dojo, raising the cap on training quality. The Boxing Gym Story instinct: yesterday's stars become tomorrow's infrastructure.

### RING 5 — The 2D Visual Layer (POST-PROTOTYPE)

**The match view.** Two small pixel-art figures, side view. Stripes/lines indicate grip connections — a line from Tanaka's right hand to Sato's collar, pulsing red when strained, snapping when broken. Posture indicated by the angle of the figure. A faint stress halo around fighters under high load.

**The dojo view.** Top-down or isometric, Kairosoft-style. You see your judoka moving between training items. Click a fighter for details.

**The match log.** Always present. The visual is a companion to the prose, not a replacement for it.

**Design principle:** symbols that change state, not animation frames. Information density over fluidity. We are making a sport-as-information-flow, not a fighting game.

### RING 6 — Sound (LATE)

The designer is a musician (12-string guitar, Moog synthesizers). Eventually:
- A dojo ambient theme that shifts with the time of day
- Match tension layers that respond to score and fatigue
- A signature motif that plays when one of *your* judoka enters their finals

Build the world in text first. Add the sound when the world is ready to hold it.

---

## THE INSTRUCTION TAXONOMY

*Initial set. Will grow with playtesting.*

**Grip-focused**
- Break his grip first
- Get the dominant grip before you commit
- Switch stance — attack the other side
- Stop reaching with your tired hand

**Tempo-focused**
- Stay patient. Let him come to you.
- Push the pace. Tire him out.
- Slow it down. Reset.
- Attack on his next breath.

**Tactical**
- Go to the ground if he opens up
- Stay standing — he's better on the mat
- Attack his weak leg
- Counter, don't initiate

**Composure**
- Tighten up. He's reading you.
- Trust your training.
- Forget the last exchange.
- Breathe. You have time.

**Risk**
- Take the chance. Go for ippon.
- Play for shidos. He'll panic.
- Defensive grip. Run the clock.

---

## TONE RULES (the writing guide)

**The voice of the match log is a knowledgeable sportswriter.** Specific. Calm. Loves the sport. Doesn't explain what kuzushi is — assumes the reader is paying attention or willing to learn.

**The voice of the coach window is intimate.** It's the player's view of their fighter. Quiet, focused, slightly worried.

**The voice of the dojo is warm.** This is home. This is where the work happens. The dojo prose has the texture of routine — sweat, repetition, small jokes, the smell of the mats.

**No hype. No announcer voice.** Tachiwaza is not the UFC. It is judo — a sport with deep roots, formal etiquette, and an understated culture. The writing should respect that.

**Every fighter is treated with dignity.** Including the opponents. Including the ones who lose. Especially the ones who lose.

---

## OPEN QUESTIONS

**Q1: How real-time is the match?**
Options: (a) live-scrolling log with pause-on-Mate, (b) tick-by-tick with player-controlled speed, (c) full replay after the fact with Mate windows surfaced as decision points. Probably (b) — gives the player agency over their own attention.

**Q2: How many judoka in a stable?**
Boxing Gym Story manages ~5 active fighters. That feels right for a starting cap. Eventually unlock more.

**Q3: How long is a "season"?**
A real judo season is roughly a year with 4–6 major tournaments. In-game time should compress so a full career arc fits in a play session of reasonable length. Maybe 1 in-game month = 5 minutes of play.

**Q4: Single-discipline or multiple?**
Pure judo for v1. BJJ, sambo, freestyle wrestling could be future expansions sharing the same engine.

**Q5: How does the player learn judo through play?**
A non-judoka should be able to play and understand. Possible solution: a glossary tooltip on every term in the match log. Hover "ko-uchi-gari" → see a one-line description and a tiny diagram. The game teaches the sport as you play.

**Q6: AI prose generation for matches?**
Same question as Player Two. The simulation generates the structured event stream. A Claude-in-Claude call wraps each event in prose using the tone guide. Every match reads differently. This is experimental and powerful — but build the deterministic prose templates first as a fallback.

**Q7: Is there a metagame above the dojo?**
National rankings, federation politics, sponsorships, media coverage of your fighters. All possible later. v1 is just dojo + matches.

---

## WHAT TO BUILD FIRST (priority order)

**Phase 1 — The Match Engine in Isolation (weeks 1–4)**
Goal: a Python script that simulates one judo match between two hand-built fighters and prints a readable log to the terminal. No dojo, no roster, no UI. Just the match.
- `Judoka` class with body-part stats, fatigue, composure
- `Match` class that runs the tick loop
- Grip state graph
- Throw attempt resolution
- Ne-waza window logic
- Mate detection
- Scoring
- A first pass of the prose template system

**Phase 2 — The Mate Window (weeks 4–6)**
Goal: pause the match, show the coach panel, accept input, resume.
- Pause logic
- Stat panel rendering (terminal first)
- Instruction menu
- Reception calculation
- Resumption with biased behavior

**Phase 3 — A Single Training Cycle (weeks 6–10)**
Goal: between two matches, the player can train one fighter and see the effect.
- `Dojo` class with a small set of training items
- Weekly time advancement
- Attribute change calculations
- Fatigue and injury risk

**Phase 4 — A Roster & Career (weeks 10–14)**
Goal: 3 fighters in a stable, a 6-month season, an end-of-season ranking.
- Recruitment screen
- Calendar / tournament schedule
- Multiple judoka simulating in parallel
- Career stats tracking

**Phase 5 — The 2D Layer (weeks 14+)**
Only after the loop is undeniably fun in pure text.

---

## WHAT YOU NEED TO LEARN / EXPERIMENT WITH

**Python concepts that will come up:**
- State machines (the grip graph is one)
- Probability and weighted choice (already familiar from Player Two)
- Class composition (a Judoka *has* a Body, a Mind, a History)
- Event queues (the match tick loop)

**Things to just try:**
- Watch 30 minutes of high-level judo with the sound off and try to write a tick log of one match by hand. See what events you notice. That's your event taxonomy.
- Play one Boxing Gym Story session and pay attention to the *rhythm* — when do you get bored, when does it sing.
- Re-read the DF combat log for one battle. Notice how it builds tension through accumulation of small events.

---

## RELATIONSHIP TO PLAYER TWO

Tachiwaza and Player Two share architectural DNA but are independent projects:

- Both use tick-based simulation
- Both layer prose over structured events
- Both treat *systems as the author*
- Both run in Python with the same toolchain

But:
- Player Two is a life simulator (decades, single subject, narrative weight)
- Tachiwaza is a sport simulator (matches, stable of subjects, tactical weight)
- Player Two release: January 9, 2027
- Tachiwaza release: TBD — explicitly second priority

**Scope discipline.** Tachiwaza work happens in dedicated sessions. It does not bleed into Player Two time. When working on one, the other repo stays closed.

---

## WHAT'S BEEN BUILT

*Nothing yet. This is day one.*

## WHAT'S NEXT

1. Sync the local repo to GitHub
2. Commit this design doc and the orientation doc
3. Sketch the `Judoka` data model on paper or in Obsidian
4. First Python file: `match_engine.py` — start with two hardcoded judoka and a tick loop that prints "Tanaka steps in" and ends. Build outward from there.

---

*Document version: April 13, 2026. Update after every session.*
