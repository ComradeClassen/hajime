# Hajime — Game UI Kit

The in-match coaching experience: the core loop of Hajime. Built from the Anchoring Scene in `hajime-master-doc.md` and the visual direction in `uploads/hajime_design_kit.html`.

## What this recreates

A pre-Ring-5 rendition of the match screen. Ring 5 adds a pixel-art top-down view of two judoka with visible grip indicators. Until then, the match is **prose + stat panel + coach's chair** — and those are the three elements this kit hi-fis.

## Screens

1. **Title card** — the wordmark on ink, enter-dojo CTA.
2. **Dojo / pre-match** — fighter selector, opponent card, referee card.
3. **Live match** — the scrolling prose stream with score strip.
4. **Matte window (coach's chair)** — paused sim, stat panel, two-instruction picker.
5. **Post-match** — score resolution with referee call.

## Components

- `TitleCard.jsx` — ink title with amber wordmark
- `ScoreStrip.jsx` — broadcast sans caps header
- `MatchLog.jsx` — timecoded prose stream with fade-in
- `CoachChair.jsx` — stat panel + instruction chips
- `InstructionChip.jsx` — the instruction button primitive
- `FighterCard.jsx` — roster card, paper surface

## Notes

- Components use plain React, inline styles keyed to CSS vars from `../../colors_and_type.css`.
- The simulation is faked — a scripted event timeline drives the match log.
- Uses component-scoped style objects to avoid collisions.
