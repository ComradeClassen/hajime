# Viewer Visual Language

*Drafted May 9, 2026, following the post-HAJ-74 playtest. The viewer that
ships from this spec is both a developer diagnostic instrument and the
working prototype for the eventual player-facing match UI. Section 1
specifies what gets surfaced; Section 2 specifies how; Section 3 commits
to the data architecture that keeps the viewer 1:1 with the engine;
Sections 4–6 close out with host-agnosticism, scope boundaries, and
phased implementation.*

---

## Section 1: What the viewer surfaces

The viewer is the visual rendering of engine state during a match,
designed to be read at a glance by both developers (for diagnostic
calibration) and players (as the eventual match UI). Every layer of
information surfaced here is information already present in the engine;
the viewer's job is to make it legible without forcing the reader into
the prose log.

The viewer has three temporal layers: persistent state (visible whenever
it's true), event firings (flash on engine event, fade after), and
slow-burn buildup (gradually intensifies as engine prerequisites stack).

### Persistent state — always visible

**Two anatomical-diagram body silhouettes** showing the two judoka in
3/4 diagrammatic view. Bodies are positioned to make the grip war
legible rather than to be spatially accurate to mat coordinates.
Standard anatomical regions are individually rendered: head, neck,
shoulders, biceps (per side), forearms (per side), hands (per side),
chest, core, lower back, hips, thighs (per side), shins (per side),
feet (per side). These regions match the engine's 15 body parts plus
cardio.

**Body damage tinting.** Each anatomical region tints toward red as it
weakens. The tinting reflects per-body-part wear, fatigue, or injury
state from the engine. A judoka's right forearm reddening visibly means
the engine's right-forearm capability for that judoka is degrading.
Universal-readable: red = hurt, no learning required.

**Conditioning indicator.** Separately from body damage, a stamina bar
per judoka shows global cardio state. May include a subtle
desperation/press-state cue when conditioning has crossed a threshold
that affects engine behavior.

**Grip edges.** Lines connecting hand-nodes on one judoka to body-nodes
on the other, representing the grip graph. Each edge encodes:

- Owner (who controls the grip — color or directional)
- Thickness (depth/strength of the grip)
- State (stable, contested, deepening, stripping, compromised)

Stable grips are solid, calm lines. Contested grips visibly oscillate
or shimmer. Deepening grips have a subtle inward animation. Stripping
grips have a subtle outward animation. Compromised grips are visibly
broken or dashed. The visual encoding is fluent-readable — players will
learn it; developers can read it from day one.

**Position state.** Standing, transitional fall, ne-waza. Made
unambiguous by body silhouette positioning plus a small explicit
indicator for ambiguous moments.

**Ne-waza state (when applicable).** Per HAJ-185, ne-waza has at least
three distinct states (osaekomi, submission attempt, transitional). The
viewer makes which one is active unambiguous via dedicated indicators:
osaekomi shows a visible clock and a "PIN" indicator on the dominant
judoka; submission attempt shows the type (joint lock vs strangle)
without a clock; transitional/scramble shows neither but visibly
indicates active grappling.

**Intent and actual force arrows.** When grip exchange is active, each
judoka has up to two arrows visible:

- Gray (ghost) arrow: where the judoka is *trying* to apply force /
  direct kuzushi
- Solid arrow: where force is *actually* being delivered through grips
  and structure

The gap between intent and actual is itself diagnostic. Both arrows
fade when the engine is in a quiet phase. Solid arrows are visually
dominant; gray intent arrows are recessive. Intent arrows fade entirely
when no active intent state — they are not constantly present, only
when the engine reports a kuzushi attempt is firing.

**Mini-map mat geometry.** Corner widget showing top-down view of the
competition area as a square with two circles representing the
judoka's actual mat positions. Surfaces boundary proximity, mat-edge
tactical situations, and shido-bait setups without crowding the main
viewer.

**Match clock and score panel.** Standard judo match UI elements — time
remaining, score for each judoka, shido count for each. Always
visible. Becomes the basis for the eventual player-facing match UI.

### Event firings — flash on engine event

**Kuzushi attempts.** The intent and actual arrows brighten or pulse
when an active kuzushi attempt is firing.

**Kuzushi results.** When Uke responds to a kuzushi attempt, Uke's
actual arrow updates to show the response direction. May or may not
mirror Tori's input direction depending on whether Uke is countering,
absorbing, or stumbling.

**Throw commits.** Sharper, more emphatic visual marker when the
engine shifts from kuzushi-attempt to throw-execution. Brief sweep or
flare animation. Corresponds 1:1 with the prose log's "[throw] Tori
commits to <technique>" line.

**Grip state changes.** Brief flash on the affected grip node when an
edge changes state — red flash for stripped, green pulse for deepened,
yellow ring for compromised, ownership-flip animation for switched
ownership. Paired with a one-line text burst at the bottom of the
viewer matching the prose log entry.

**Score events.** Yuko, waza-ari, ippon. Prominent flash, brief text
overlay, score panel updates.

**Referee events.** Shido (visible card or marker), hansoku-make
(prominent), matte (action freezes briefly), hajime (action resumes),
osaekomi clock starts/stops.

**State transitions.** Tachiwaza → transitional → ne-waza. Ne-waza
substate transitions per HAJ-185. Each transition has a visible event
marker.

### Slow-burn buildup — gradual intensification

**Signature setup.** When Tori's grip configuration approaches the
prerequisites for a known signature throw, a continuous glow intensity
scales with signature-readiness from threshold (~0.2, just-barely
visible) to armed (1.0, fully bright with slow pulse). Below
threshold: invisible. Above threshold: smooth gradient. The glow
visibly intensifies in real time as Tori's grip configuration deepens
toward the prerequisite set, and visibly dims as Tori shifts away.

When a signature crosses ~0.6 readiness, the technique name fades in
near the glowing grip nodes as small text. Fades to full opacity if
the signature commits; fades out if signature fails. Teaches novices
throw vocabulary by association.

This layer is the most coach-useful because it surfaces information
that's currently in the engine but invisible to the player. The
signature stacking is happening; the viewer makes it visible.

**Tactical shift.** When a judoka's underlying tactical mode changes
(conservative, aggressive, shido-baiting, ippon-hunting,
conditioning-driven press), a subtle indicator hints at it. Smaller,
less prominent than other layers — it's a slow background signal, not
an event.

### The 1:1 prose-log mapping commitment

Every prose log line corresponds to a viewer event in the same tick.
Every viewer event corresponds to a prose log line. Both are rendered
from the same engine state windows. This is what makes the viewer
diagnostic. Right now they're decoupled; this spec commits them to the
same data feed.

### What the viewer doesn't show

- Realistic limb articulation or character animation
- Photorealistic bodies or muscle definition
- Mat texture, dojo background, crowd
- Camera angles, cinematic framing
- Anything that competes with diagnostic legibility for visual real
  estate

The viewer is a diagnostic instrument that doubles as the player UI
prototype. Cinematic match presentation is a separate, much later
question.

### Two-audience accommodation

Some elements are *novice-readable* (no learning required): body
damage tinting, score panel, match clock, mini-map, ippon flash, matte
freeze.

Some elements are *fluent-readable* (learn over a few hours of
watching): grip edge thickness/state encoding, intent vs actual arrow
grammar, signature setup intensification, tactical shift cues.

Both are fine. The spec is honest about which is which so neither is
over-simplified to accommodate the other.

---

## Section 2: The visual vocabulary

This section commits to actual visual choices — shapes, colors, sizes,
animation timing. It does not commit to a final art style or polished
aesthetic. It specifies the diagnostic visual grammar that the
implementation can render in pygame today and migrate to Godot later
without redesigning the language. Aesthetic polish is a Ring 6
concern. Section 2 is about what carries information; Section 4
handles the host-agnostic implementation note.

### 2.1 — Body silhouettes

Two anatomical-diagram bodies rendered in 3/4 diagrammatic view. Each
body is composed of explicit anatomical regions, individually
addressable for damage tinting:

- Head, neck
- Shoulders (left, right)
- Biceps (left, right)
- Forearms (left, right)
- Hands (left, right)
- Chest
- Core (abdomen)
- Lower back
- Hips
- Thighs (left, right)
- Shins (left, right)
- Feet (left, right)

That's 19 named regions per body. The engine's 15 body parts plus
cardio map onto these (cardio is global, rendered as the stamina bar,
not as a region tint). The 19-vs-15 split is a display choice; the
implementation may collapse some regions to match the engine 1:1 if
that reads better.

The bodies are *not* fully rendered humans. They are diagrammatic —
flat-shaded regions with clear boundaries between them, like an
anatomical chart. The boundaries between regions need to be visible at
viewer-zoom because each region is independently tintable. Think
medical-diagram-meets-Tron-grid, not figure drawing.

Bodies are positioned facing each other in 3/4 view, roughly centered
in the viewer, scaled so the full silhouette is visible at all times.
They reposition continuously as the match progresses — drifting closer
when grip exchange is happening, separating during disengagement,
descending to the mat when transitioning to ne-waza. The repositioning
is informational (it tells you what state the match is in) but not
spatially-accurate to mat coordinates (that's the mini-map's job).

Each body has a base color/identity tint that distinguishes the two
judoka — **blue** for one, **white** for the other. This mirrors actual
judo competition (blue gi vs white gi). The white silhouette requires a
visible outline (light gray or thin black) so it doesn't disappear
against a light background.

### 2.2 — Damage tinting

Each anatomical region tints toward red as the engine's damage state
for that body part increases. Discrete bands for damage state, four
levels:

- *Healthy*: base body tint, no red modulation
- *Worked*: 25% red mix — visibly tinted but clearly not concerning
- *Compromised*: 50% red mix — clearly hurt, attention-drawing
- *Critical*: 75–100% red mix — pulsing slowly to indicate ongoing
  degradation

Damage tinting is implemented as a saturation/luminance shift toward
red, not a pure hue replacement. This means:

- A heavily-damaged white judoka shifts toward red cleanly (white →
  pink → red).
- A heavily-damaged blue judoka shifts through purple toward dark red
  (blue → purple → dark red). Still legible.

Both judoka remain identifiable by their base identity color even when
heavily damaged. Identity is preserved.

Universal-readable. No learning required. Same visual language as UFC
body damage rendering.

### 2.3 — Grip nodes and grip edges

Grip nodes are small filled circles overlaid on the body silhouettes
at locations where grips can land. Probably 8–10 nodes per body: each
lapel (left, right), each sleeve (left forearm, right forearm), the
back of the collar, the belt, each leg (left thigh, right thigh), and
the head/neck for ne-waza. Nodes are normally invisible. They become
visible when an active grip is on or near them.

Grip edges are lines connecting hand-nodes on one judoka to body-nodes
on the other. Each edge encodes:

**Owner.** The edge is colored with the gripping judoka's identity
tint — blue or white (with outline). When two grips contest the same
node (a stripping attempt over an existing grip), the edge briefly
shows both tints striped or oscillating until one resolves.

**Thickness.** Maps to grip depth from 1px (shallow, just-acquired or
actively-being-stripped) to 6px (deep, well-set, hard to break).
Linear scale. Continuous, not discrete steps.

**State (animation):**

- *Stable*: solid line, no animation
- *Contested*: line shimmers or oscillates subtly along its length
- *Deepening*: subtle inward animation — small dashes flowing from the
  hand-node toward the body-node
- *Stripping*: subtle outward animation — small dashes flowing from
  the body-node away
- *Compromised*: the line itself becomes dashed rather than solid,
  indicating the grip is structurally broken

When an edge changes state, a brief flash fires on the affected node
(see 2.6). This is the bridge to the event firing layer.

### 2.4 — Intent and actual arrows

Each judoka can have up to two arrows visible during active grip
exchange:

**Intent arrow** (gray, ghost-like). Fires when the engine's
kuzushi-attempt logic is active for that judoka — they're trying to
apply force in a specific direction. Renders as a gray arrow
originating from the judoka's center mass, extending toward where they
're trying to drive the opponent. Length encodes attempted force
magnitude. The arrow has a brief fade-in (~200ms at 1× playback) when
the intent fires and a brief fade-out (~200ms at 1× playback) when the
intent ends. Hidden when the engine is not in an active kuzushi-attempt
state for that judoka.

**Actual arrow** (solid, identity-tinted). Renders the force actually
being delivered through grips and structure. Originates from the
judoka's center mass. Length encodes delivered force magnitude. The
arrow is visually dominant — thicker than the intent arrow, fully
saturated in identity color (blue or white-with-outline).

The white judoka's intent arrow needs a darker gray tone so it's
distinguishable from the white actual arrow. Both white arrows have
outlines for visibility.

The gap between intent and actual is itself diagnostic. When intent
points one direction at full length and actual is much shorter or
pointed elsewhere, the structure isn't delivering. When intent and
actual closely align in direction and length, the kuzushi attempt is
succeeding.

Up to four arrows can be visible at once (Tori intent + Tori actual +
Uke intent + Uke actual). To prevent visual collision, arrows are
slightly offset from the body center mass — Tori's arrows originate
slightly to one side of their center, Uke's to the other.

Arrows fade when their underlying state ends. Intent arrows
specifically fade entirely when no active intent — they are not
constantly present.

### 2.5 — Throw commit marker

When the engine shifts from kuzushi-attempt to throw-execution, a
sharper, more emphatic visual fires: a brief arc-sweep emanating from
the committing judoka in the direction of the technique, lasting
roughly 300ms at 1× playback, followed by either a successful throw
(body silhouettes reposition to reflect the throw landing) or a
failed/countered commit (the sweep cuts off, judoka silhouettes recover
toward neutral or transitional).

The arc-sweep is colored with the committing judoka's identity tint at
high saturation. Its shape encodes the technique *family* (not
individual technique), drawn from a small set of distinguishable
shapes:

**Five throw families:**

1. **Forward throws** (seoi-nage, ippon-seoi, sode-tsurikomi-goshi,
   morote-seoi) — sweep arcs forward and down, like throwing the
   opponent forward over a shoulder.
2. **Hip throws** (o-goshi, harai-goshi, uchi-mata, hane-goshi,
   tsuri-komi-goshi) — sweep rotates around the throwing judoka's
   hips.
3. **Leg sweeps and reaps** (ouchi-gari, kouchi-gari, osoto-gari,
   kosoto-gari, deashi-harai) — sweep moves laterally at low angle,
   foot/leg level.
4. **Sutemi (sacrifice) throws** (tomoe-nage, sumi-gaeshi,
   yoko-tomoe-nage, ura-nage) — sweep descends, both judoka going to
   ground together.
5. **Leg-attack throws** (kata-guruma, te-guruma, morote-gari,
   kuchiki-taoshi) — sweep arcs low, attacking the legs directly.
   *Era-restricted: only renders in tachiwaza when era's ruleset
   permits leg grabs. Always available in ne-waza.*

This is fluent-readable (players will learn the shapes) but the *fact*
that a commit is firing is novice-readable (the sweep is unmistakable
as "something just happened").

Paired with a text burst at the viewer bottom: "[throw] <judoka>
commits to <technique>."

### 2.5.1 — Era-aware vocabulary

The viewer reads the engine's era stamp and ruleset version per match.
This affects:

- Whether the leg-attack family renders in tachiwaza (post-2010 IJF
  ruleset: no; pre-2010: yes; ne-waza: always yes regardless of era)
- Which shido infractions are visible (false attack rules have evolved,
  passive judoka rules have evolved)
- Match duration norms (4:00 vs 5:00 vs other)
- Other ruleset-specific behaviors

Era is a property of the match, queried from the engine. The viewer
does not need to know *why* the ruleset permits or forbids something;
it just renders what the engine reports as legal/illegal/scoring.

### 2.6 — Grip state-change flashes

When a grip edge changes state, a brief flash on the affected grip
node:

- *Stripped*: red ring expanding outward from the node, fading over
  ~400ms at 1× playback
- *Deepened*: green pulse on the node, brief
- *Compromised*: yellow ring, slower pulse over ~600ms at 1× playback
- *Switched ownership*: a quick swap animation — the previous owner's
  tint fades while the new owner's tint takes over, ~300ms at 1×
  playback

Each flash pairs with a corresponding text burst at the viewer bottom
matching the prose log entry.

### 2.7 — Score events and referee events

**Score events.** Yuko, waza-ari, ippon. The score panel at the top of
the viewer updates with a brief flash on the relevant judoka's score.
For ippon specifically, a larger flash sweeps across the full viewer
briefly before settling into the score update — ippon is match-ending
and warrants visual emphasis.

**Shido.** A small yellow card icon appears next to the affected
judoka's score panel. Stacks visibly (one card, two cards, three cards
= hansoku-make).

**Hansoku-make.** Larger red card, prominent.

**Matte.** Brief screen-edge dim or pulse, action visibly freezes
(body silhouettes stop repositioning, all arrows fade, grip edges hold
their state). Indicates the referee has called the action to stop.

**Hajime.** Brief screen-edge brighten, action resumes.

**Osaekomi clock.** When osaekomi starts (per HAJ-185 state machine),
a circular countdown timer appears prominently in the viewer, attached
to or near the dominant judoka's silhouette. Counts up visibly toward
the 10s waza-ari and 20s ippon thresholds. Disappears when the pin is
broken or the threshold is reached.

### 2.8 — Position state and ne-waza substates

**Standing (tachiwaza).** Default body silhouette positioning, both
judoka upright facing each other.

**Transitional.** Body silhouettes mid-movement — partial fall,
in-air during a throw committal, scrambling. The visual should make
clear that this is an unstable, in-progress state, not a steady
position.

**Ne-waza.** Body silhouettes positioned on the ground in their
specific ne-waza configuration. The configuration is informational —
kesa-gatame looks structurally different from juji-gatame which looks
different from a turtle defense.

**Ne-waza substate indicators (per HAJ-185):**

- **Osaekomi (pin):** a "PIN" badge appears near the dominant judoka,
  accompanied by the osaekomi clock (Section 2.7). The grip
  configuration shows the specific hold.
- **Submission attempt:** a "JOINT LOCK" or "STRANGLE" badge appears,
  depending on which class. The affected body region on the defending
  judoka tints orange (distinct from damage red) to indicate which
  limb or which neck position is under attack. No osaekomi clock. If
  the submission is held long enough without resolution, a slow
  tightening animation builds tension.
- **Transitional / scramble:** no badge, no clock. The body
  silhouettes show active grappling motion. The viewer makes clear
  that grappling is happening but neither pin nor submission has been
  established.

### 2.9 — Signature setup glow (continuous slow-burn buildup)

Continuous intensity scaling driven by the engine's signature-
readiness score per active signature in Tori's vocabulary:

- *Below threshold (~0.2):* invisible. Engine is tracking but no
  meaningful prerequisites are met yet.
- *Above threshold:* glow intensity scales smoothly with readiness
  score. A signature at readiness 0.4 glows faintly. At 0.6 it's
  clearly visible. At 0.8 it's bright. At 1.0 it's fully bright with
  a slow pulse — armed.

The glow appears on the grip nodes that are part of the signature's
prerequisite set, and may extend to relevant body regions on Tori
(e.g., a leg-attack signature would glow Tori's leg silhouette).

When multiple signatures are simultaneously building, each renders
independently. They may share grip nodes (a grip node can be a
prerequisite for multiple throws), and in that case the glow is the
union — but tagged with which signatures are involved if hover/inspect
is supported.

When a signature commits (becomes a throw commit per Section 2.5), the
glow resolves into the commit arc-sweep.

When a signature fails (Tori's grip configuration shifts away from
prerequisites), the glow dims smoothly back toward invisibility.

**Implementation note.** Continuous rendering requires the engine to
expose signature-readiness as a continuous score (0.0–1.0) per tick,
not just a discrete state. If the engine currently computes signature
stacking as discrete states internally, this is a small refactor —
make the score continuous, derive any discrete states from it where
needed.

**Watch for:** if discrete steps would feel insufficient (multiple
simultaneous signatures feeling falsely identical, "how close to armed"
not readable within a state, dynamics feeling step-y), continuous
fixes those problems. Continuous is the chosen direction.

### 2.9.1 — Technique name fade-in

When a signature crosses ~0.6 readiness (clearly visible glow), the
technique name fades in near the glowing grip nodes as small text:

- White text with low-opacity backdrop for legibility
- Fades in slowly as the signature continues to build toward armed
- If the signature commits: text fades to full opacity briefly during
  the throw commit before the standard text burst takes over the
  captioning role
- If the signature fails: text fades out as the glow dims

This means the viewer is *teaching the player Japanese throw vocabulary
by association*. After 20 matches, a player who's been ignoring the
prose log entirely will know what uchi-mata looks like, what
harai-goshi looks like, what ouchi-gari looks like — because they've
watched the names fade in over the corresponding glow patterns dozens
of times. Pure novice-readable scaffolding for fluent-readable
vocabulary.

The signature name text lives near the body silhouettes; the text
burst (Section 2.13) stays at the bottom for prose log captioning.
They don't compete for the same screen real estate.

### 2.10 — Tactical shift cues

Subtle. A small icon near each judoka's identity panel showing their
current tactical mode:

- Conservative / defending
- Aggressive / pressing
- Shido-baiting
- Ippon-hunting
- Conditioning-driven press

Icon changes when the engine's tactical state changes. The icon is
small enough that it doesn't crowd the viewer but visible enough that
a coach watching attentively can read shifts. Fluent-readable (players
will learn the icons over time).

### 2.11 — Mini-map

Corner widget, top-right or bottom-right. Top-down view of the
competition area:

- Outer dashed square representing the safety boundary
- Inner solid square representing the contest area
- Two filled circles representing the judoka, identity-tinted (blue
  and white)
- A brief tail behind each circle showing recent movement direction

Updates continuously with actual mat coordinates from the engine.
Stays small enough that it doesn't dominate the viewer. When a judoka
approaches the boundary, their circle pulses briefly to draw
attention.

### 2.12 — Match clock and score panel

Top of the viewer. Standard judo match UI:

- Match clock: time remaining, prominently displayed, identity-neutral
- Score for each judoka: yuko count, waza-ari count, plus visible
  ippon/hansoku-make/etc when match-ending
- Shido count for each judoka (yellow cards as in 2.7)
- Judoka names / identifiers

Always visible. This panel is the most directly transferable element
to the eventual player UI — it doesn't change between
viewer-as-diagnostic and viewer-as-player-UI.

### 2.13 — Text burst captioning

Bottom of the viewer, single line, fades in/out as engine events fire.
Matches the prose log entry corresponding to the visual event
happening on screen. Roughly 1–2 second fade-in, holds for 1–2 seconds
depending on event significance, fades out (timing scaled by playback
speed per Section 3.5).

The text burst is the bridge that lets a player ignore the prose log
entirely while still understanding what just happened. For developers,
it's redundancy that confirms viewer events match prose log events
tick-for-tick.

When multiple events fire in rapid succession (common during a throw
commit + score + matte sequence), text bursts queue and display
sequentially rather than overlapping. Each burst gets at least 800ms
of visibility (at 1× playback) before the next replaces it.

### 2.14 — The 1:1 prose-log mapping commitment, restated visually

Every prose log line corresponds to a visible viewer event in the same
tick. Every visible viewer event corresponds to a prose log line. The
text burst captioning at the viewer bottom is the explicit
visualization of this commitment — it shows the prose log line at the
moment its corresponding visual event fires.

If a viewer event fires without a prose log line, that's a bug. If a
prose log line fires without a viewer event, that's a bug. Both should
be caught during development by watching the viewer with the prose log
open in parallel.

---

## Section 3: Data architecture and the 1:1 mapping commitment

This section is shorter than Section 2 because it's specifying *how*
the viewer stays 1:1 with the engine, not *what* it shows. But the
commitments here are the ones that determine whether the viewer is
actually diagnostic or just decorative.

### 3.1 — Single source of truth

The viewer reads from the same engine state windows that the prose log
narration module reads. There is no separate "viewer state" computed
independently from "engine state." The viewer is a rendering of engine
state, period.

In implementation: the engine produces a stream of state snapshots per
tick. The narration module consumes that stream and emits prose log
lines. The viewer consumes the same stream and emits visual state.
Both consumers read identical data; they render it differently.

If the viewer ever shows something the prose log doesn't reflect, or
the prose log emits something the viewer doesn't render, the bug is in
the consumer layer (the rendering), not in disagreement about what
happened. There is no "the engine thinks X happened but the viewer
thinks Y" — both consumers agree because they read the same source.

### 3.2 — What the viewer reads per tick

Per engine tick, the viewer needs access to the following state:

**Per-judoka state:**

- Position state (tachiwaza / transitional / ne-waza-substate)
- Body part damage state (15 body parts, each with a 0.0–1.0 wear/
  injury value)
- Cardio state (stamina value, possibly split into capacity vs
  efficiency per existing data model)
- Active grips owned (list of grip edges this judoka is currently
  maintaining)
- Active grip targets (list of grip edges this judoka is currently
  being gripped by)
- Tactical mode (one of the five modes)
- Active kuzushi attempt (target direction + magnitude, if any)
- Active force delivery (actual direction + magnitude based on current
  structure)
- Active throw commit (technique + family + phase, if any)
- Active signature stacking (per signature in vocabulary: continuous
  readiness score 0.0–1.0)
- Active ne-waza substate detail (if in ne-waza: pin type / submission
  type / scramble)

**Per-grip-edge state:**

- Owner judoka ID
- Source node (hand-node on owner)
- Target node (body-node on opponent)
- Depth (continuous, 0.0–1.0 scaled to 1px–6px display)
- State (stable / contested / deepening / stripping / compromised)

**Per-tick events:**

- Score events (yuko, waza-ari, ippon, with which judoka)
- Referee events (shido + which judoka, hansoku-make + which, matte,
  hajime, osaekomi-start, osaekomi-end)
- Grip state-change events (which edge changed to which state)
- State-transition events (tachiwaza → transitional, transitional →
  ne-waza, ne-waza substate transitions)
- Throw commit events (which judoka, technique, family)
- Signature-readiness threshold crossings (signature crossed 0.6 going
  up, signature crossed below threshold going down — for technique
  name fade-in/out)

**Match-level state:**

- Match clock (time remaining)
- Score for each judoka
- Shido count for each judoka
- Era stamp (Paper-and-Radio / Phone-and-Fax / Email-and-Web /
  Smartphone — drives ruleset)
- Ruleset version (active ruleset for this match — drives leg-grab
  legality, etc.)

**Mat coordinates (for mini-map):**

- Each judoka's actual mat position (x, y in mat coordinate space)
- Mat boundaries (contest area square, safety boundary square)

### 3.3 — How the viewer reads it

The engine exposes state via a per-tick query interface. Per tick:

1. Engine advances simulation by one tick
2. Engine emits any events that fired this tick
3. Narration module consumes events + state, renders prose log line(s)
   if appropriate
4. Viewer consumes events + state, updates visual rendering

The narration module and viewer both subscribe to the same per-tick
output. They run as parallel consumers. Neither blocks the other.

For pygame implementation today: the engine runs as the simulation
loop, narration module and viewer run as observers that update on each
tick. For Godot implementation later: same pattern, with the engine
subprocess emitting structured events the Godot frontend consumes via
the existing JSON bridge.

### 3.4 — Synchronization invariant

The viewer's rendered state at any tick T is a pure function of the
engine's state at tick T plus events fired between T-1 and T. The
viewer does not compute or infer any state independently.

This means:

- If the engine pauses, the viewer pauses (no continued animation
  that's not driven by engine state)
- If the engine reverses (replay scenarios, calibration tool re-runs),
  the viewer reverses cleanly
- If the engine emits a state that "shouldn't be possible" (a bug),
  the viewer renders it faithfully — and the bug becomes visible
  because viewer + prose log + engine internals can be cross-referenced

### 3.5 — Animation timing

Visual transitions in the viewer (arrow fades, glow intensification,
body silhouette repositioning) animate over real time, scaled by
engine playback speed. This means a single engine tick can drive
multiple frames of viewer animation as the visual state interpolates
from previous-tick state to current-tick state.

**Animation timing constants** (specified in Section 2 throughout) are
expressed as durations at 1× playback. At any other playback rate:

- 0.5× playback: animations scale to 2× duration (slower, easier to
  follow)
- 2× playback: animations scale to 0.5× duration (faster, no lag
  behind engine)
- 0.1× playback: animations scale to 10× duration (slow study mode)

This preserves the ability to slow time down to study the grip war
while keeping the viewer feeling natural at any playback speed.

If during testing some animations should *not* scale (e.g., the score
flash should always be readable regardless of playback speed), we can
carve out a small list of "real-time-locked" animations as exceptions.
But default is scale-with-playback.

### 3.6 — The synchronization test

A regression test runs the viewer alongside the prose log on a
recorded match, asserting that for every prose log line emitted, a
corresponding visual event fires in the viewer within the same tick
window, and vice versa. This test is the executable form of the 1:1
mapping commitment.

If the test ever fails, either:

- The engine emitted an event that the prose log captured but the
  viewer didn't render (viewer bug)
- The engine emitted an event that the viewer captured but the prose
  log didn't render (prose log bug)
- The engine's state stream is itself inconsistent (engine bug —
  unlikely but possible)

The test is the diagnostic instrument that ensures the diagnostic
instrument works.

It ships as a follow-up ticket after the viewer's first phase lands,
not as a blocker.

---

## Section 4: Host-agnostic implementation

The visual language specified in Sections 1–3 commits to *what gets
shown* and *how it stays in sync with the engine*. It does not commit
to a rendering host.

The current viewer is in pygame. The eventual host is Godot, when the
simulation moves there. Both can render this spec.

The visual vocabulary in Section 2 is specified at a level of
abstraction that translates: "blue body silhouette with damage tinting
and grip nodes" is implementable in pygame as drawn polygons with
color modulation, and in Godot as Control nodes or sprite layers with
shader tints. The spec doesn't require host-specific features.

The synchronization invariant in Section 3 also translates: pygame can
subscribe to engine state via Python observer pattern; Godot can
subscribe via the existing JSON bridge or a future GDExtension. Either
consumer reads the same engine state stream.

**Implementation strategy:**

- **First pass (pygame, near term):** build the viewer in pygame
  against the current engine. Validate the visual language. This is
  what gets built when the viewer fidelity tickets ship.
- **Second pass (Godot, post-engine-migration):** when the simulation
  core moves to Godot or Godot-with-Python-backend, port the viewer.
  Visual language is preserved; rendering primitives are
  re-implemented.

The pygame pass is throwaway-ok in the same sense HAJ-150's pygame
implementation was throwaway-ok. The visual language is permanent; the
pygame code is interim.

This means:

- Don't over-invest in pygame-specific visual polish. The polish work
  belongs in the Godot pass (and ultimately Ring 6 — 2D Visual Layer).
- Don't pick a pygame implementation pattern that won't translate to
  Godot. If a pygame approach doesn't have a clean Godot analog, find
  a different pygame approach.
- Document any pygame-specific shortcuts as `# TODO: revisit at Godot
  port` in code so the migration is informed.

---

## Section 5: Out of scope

What the viewer is *not* doing, named explicitly so the implementation
doesn't drift:

**Aesthetic polish.** This is a diagnostic instrument that doubles as
a player UI prototype. It is not the final art treatment. Backgrounds,
dojo environment, character likeness, mat texture, lighting effects,
particle systems — all out. Aesthetic polish belongs in Ring 6.

**Cinematic match presentation.** No camera angles, replay cuts,
slow-motion replays, dramatic close-ups. The viewer renders one
continuous diagrammatic view of the match.

**Realistic limb articulation.** Bodies are anatomical diagrams that
reposition, not animated humans. No inverse kinematics, no muscle
deformation, no individual finger positions, no facial expressions.

**3D rendering.** The viewer is 2D. Three-dimensional match
visualization is documented in the project corpus as deferred to
post-EA.

**Audio.** The viewer is silent. Match sound (referee calls, mat
impact, breath, crowd) is Ring 7 work.

**Player input during a match.** The viewer is observational. The
player watches matches; they do not control judoka in real time. Coach
instructions to a judoka before/during/between matches are Ring 3 work
and not part of this spec.

**Cosmetic customization.** No alternate gi colors beyond blue/white
identity, no dojo branding on the visual presentation, no skins.
Identity is functional, not personalized.

**Localization of throw names.** Technique names are rendered in their
standard romaji forms (uchi-mata, harai-goshi, ouchi-gari, etc.). No
translation to player language. This is the convention judo uses
worldwide.

**Detailed mini-map information.** The mini-map shows mat geometry,
judoka positions, recent movement. It does not show grip state,
scores, clock, or anything that lives in the main viewer.
Single-purpose: spatial position only.

---

## Section 6: Implementation phasing

The viewer is a substantial piece of work. Shipping it as one giant
ticket would be unmanageable. Instead, implement in three phases, each
shippable independently:

### Phase 1 — Foundation. The synchronization-correct minimum.

Body silhouettes (anatomical regions, blue and white identity, base
coloring without damage tinting yet). Match clock. Score panel.
Position state (tachiwaza vs ne-waza visible in body positioning).
Text burst captioning for prose log mirroring. The 1:1 mapping
commitment in working form — every prose log line corresponds to a
visible event, even if "visible event" is just a text burst at this
stage.

**Goal of Phase 1:** prove the data architecture (Section 3) works and
the viewer is genuinely synchronized with the engine. No grips visible
yet, no arrows yet, no damage yet — just the skeleton plus captioning,
with provable 1:1 correspondence. This is the smallest viewer that's
still diagnostic.

Ships as one Linear ticket.

### Phase 2 — Tachiwaza grammar. The grip war made visible.

Grip nodes and grip edges (with all encoding from 2.3). Intent and
actual arrows (2.4). Body damage tinting (2.2). Throw commit family
shapes (2.5, with era-aware vocabulary). Grip state-change flashes
(2.6). Score event flashes and referee event indicators (2.7).
Mini-map (2.11).

**Goal of Phase 2:** tachiwaza is fully diagnostic. You can watch a
black-belt vs black-belt match and read the grip war, the kuzushi
attempts, the throw commits, body damage accumulation, and conditioning
differential — all from the viewer alone, without needing to consult
the prose log to understand what's happening.

This is where the original problem (the viewer doesn't represent what's
happening) gets solved.

Ships as 2–3 Linear tickets, since this phase has substantial
sub-pieces (grip rendering, arrow grammar, commit shapes are each
meaty).

### Phase 3 — Full vocabulary. Ne-waza, signatures, tactical shifts.

Ne-waza substate indicators (2.8 — depends on HAJ-185 ne-waza state
machine fix landing first). Signature setup glow with continuous
intensity scaling (2.9). Technique name fade-in (2.9.1). Tactical
shift cues (2.10).

**Goal of Phase 3:** viewer is fully expressive. Every layer of engine
state has a visual surface. Coach can read everything at a glance.

This is also where the viewer becomes valuable as a *teaching
instrument* (technique name fade-in builds vocabulary association) and
as a *coach UI prototype* (signature setup glow surfaces the most
coach-useful information).

Ships as 2–3 Linear tickets.

### Synchronization test (Section 3.6)

Ships as a follow-up after Phase 1 lands. It validates that Phase 1's
foundation is correct before Phases 2 and 3 build on top of it.

---

## Engine-side dependencies

This spec surfaces several engine-side commitments that are required
for the viewer to render the spec faithfully. These are filed as
separate Ring 1 tickets, not part of the viewer work itself:

1. **Body damage state should accelerate conditioning loss when
   affected body parts are doing active work.** A judoka with
   reddened forearms gases faster doing grip work than one with fresh
   forearms. Calibration relationship between body damage and cardio
   tank.

2. **Define what state recovers during matte vs between matches.** A
   small sliver of stamina recovery during matte is plausible; body
   damage and grip state should not recover. Calibrate.

3. **Signature-readiness as continuous score.** If currently discrete
   internally, refactor to continuous (0.0–1.0 per active signature).
   Required for continuous glow rendering in 2.9.

4. **Era-aware ruleset confirmation.** Verify the engine's ruleset
   handling correctly toggles leg-grab legality across the simulated
   time window (pre-2010 tachiwaza permitted; post-2010 tachiwaza
   forbidden; ne-waza always permitted regardless of era). The viewer
   reads era stamp from the engine and renders accordingly.

---

*Drafted May 9, 2026, in chat session immediately following HAJ-74
post-ship playtest. This spec governs the viewer fidelity work that
follows. The pygame pass is throwaway-ok; the visual language is
permanent.*
