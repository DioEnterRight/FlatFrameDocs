# Production guide

## The house style

The methodology is the **2D Documentary Skill** ([.claude/skills/2d-documentory-skill/SKILL.md](.claude/skills/2d-documentory-skill/SKILL.md),
the copy you supplied; the older ReachMora 2D long-form skill that once lived in shorts-bot was compared and used only for
idea strategy, because the documentary skill is the more complete and better-tested production method).
Round-headed stick-figure characters in flat, lit, layered sets; deadpan skits; big ideas turned into physical objects;
a camera that is rarely still but always level; a new thing to look at every second or two; facts sourced, satire only in
skits and metaphors. FlatFrameDocs adds the brief's rule: **suspense scenery may be goofy** (oversized props, crowds of
creatures, absurd metaphors) while the facts stay serious.

## How the skill became code

| Skill rule | Where it is enforced |
|---|---|
| Step 1 title patterns, "nothing the script cannot pay off" | `prompts/ideas.md`, `script_check` title gate (5-10 words, no colon/question mark, shares words with verified claims) |
| Step 3 research first, sources kept, no invented facts/quotes | `research.py` (2+ independent sites per claim, literal quote checks, conflicts), writer sees only verified claims, `facts.script_violations` blocks any number/name not in the cited claims |
| Script DNA: cold open, twist, question, origin, mechanism, close on the opening image | `prompts/script.md` sections; `script_check` order, hook length, payoff only from the reveal, ending callback |
| Voice: short sentences, one sentence one picture, numbers spoken | `script_check` median/max sentence length; `voice.speak_numbers` ("1932" → "nineteen thirty-two") |
| Skits: 2-10 deadpan lines, punchline last and shortest, first inside ~25 s | `script_check` skit rules; `beats.skit_shot` (locked shots, OTS/two-shot, close-up on the punchline, expression change per line); `voice` gives skit lines their own flatter voices |
| `[CARD]` black cards, typed ~19 chars/s, ≥1.4 s | `beats` card shots (cps ≥ 19, hold ≥ 42 frames), `ui/Cards.BlackCard` |
| `[TITLE]` over a live scene with the glowing hero object, lines arriving 0.25-0.5 s apart | `beats` title placement + hero added, `ui/Cards.TitleCard` |
| Step 4 timing locked to the voice | edge-tts word boundaries (`voice.align_words`); every cut, prop entry, build item, punch-in lands on a word (`beats.word_frame`) |
| 5.1 flat lit elevation sets, ≥4 layers, foreground crop, no bare surfaces, drawn light, grades, vignette | `sets/kits.ts` + `Backdrop.tsx` (wall/floor patterns, windows with views, lamp discs, floor pools, window bands), `Scene.tsx` depth layers + blurred foreground + grade + vignette, `qa` vignette check |
| One accent colour for the hero object, halo | `theme.PAL.accent`, `PropView` halo + accent particles only around the hero |
| 5.2 one rig, layered clothing, signature per person, 4 views, expressions, poses, shadows, spacing | `rig/Character.tsx`; `beats._spread` (≥1.2 body widths); real people are generic characters with a name |
| 5.3 shot vocabulary (story, skit, metaphor, hero object, cards, title, inserts, maps, triptych, table-top, data as objects) | `Shot.tsx` + `maps/WorldMap.tsx` + `builds/Builds.tsx` (counter on a board, compare panels, timeline, stacks…) |
| Shot length budget, cuts on speech pauses | `beats.split_long` (lines > 3.4 s become two shots, punch-in on one subject), `beats.metrics`/`audit` |
| Overlay text only for place/date/name/number, ≤3 words, never restating narration, not bottom centre | `beats.overlay` validation, overlay budget, UI positions top corners |
| 5.4 idle life, talking mouths from loudness, props never scale from nothing, staged builds every 8-12 s, counters 60 % in the first third | `Character` blink/breath/`talkMouth`, `PropView` entries (slide/drop/grow/slam/switch), `beats.ensure_builds`, `Builds.countValue` |
| 5.4a effects: selective, tone-matched, ≤ a third of scenes, seeded | `catalog.FX_BY_TONE`, `beats.enforce` budget, `fx/Effects.tsx` |
| 5.5 camera: push ~45 %, pan/tilt ~20 %, creep / creep+punch / settle, no stop-and-go, groups wide, fully in or out of frame, dialogue cut not zoomed | `camera.ts` (single continuous curves), `beats.enforce` (move variety, groups, close-up budget), `beats.solve_framing`/`framing_ok` (geometry check at start/middle/end) |
| 5.6 check before delivering (contact sheet, blank frames, duration, cropping, smoothness) | `qa.py` gates + contact sheets for you and the vision judge |
| "Never pass a gate without the user" | replaced by automated gates (below) — the brief asks for full automation |

## Deliberate adaptations (and why)

| Skill | FlatFrameDocs | Reason |
|---|---|---|
| 16:9, 1-12 min | 9:16, 40-50 s | the brief |
| Human approval at 7 gates | deterministic gates + a second model as critic/judge; every stage saved for review | full automation; quality is protected by rejecting, not by waiting |
| User records the voice-over | edge-tts, Kokoro fallback, ~150-165 wpm, never sped up | free & cloud-only |
| Showpiece 3D shots (≤2) | none; depth comes from parallax layers | the skill allows zero; 3D on CPU runners is ~10x slower; flat sets matched the targets better in the skill's own test |
| Black card text on one unwrapped line at 9 % height | up to 3 balanced lines, cap height ~5 % | a 1080-px-wide frame cannot hold a 9-word line at that size |
| "No running subtitles" | word-by-word captions in the lower third (1-3 words, spoken word in the accent colour), hidden on black cards and the outro | channel owner's decision (most Shorts are watched muted) |
| No calls to action | `@outrichguy` in the top-right corner of every frame + a 3-second outro after the story: the main character says "Follow FlatFrameDocs and @outrichguy" next to a FOLLOW sign (config `brand`) | channel owner's decision; it sits after the story ending, so the ending itself stays a real ending |
| Chapter cards after the title | not used | 2.1 s of silence-carrying black is too costly in 45 s |
| Music only if supplied | original procedural beds 18+ dB under the voice | the brief asks for music; nothing licensed is used |
| Fast pace: 27-40 cuts/min early | ~25-30 cuts/min overall (measured per video in `storyboard_report.json`) | one cut per short line keeps cuts on words; the opening is denser |
| News section of title ideas | evergreen only | news needs fresh search the free pipeline cannot verify reliably |

## Quality gates (a failure rejects the topic or the video)

Script: structure/order, 100-138 words, hook ≤ 9 words and no greeting, short sentences, one skit, 2-4 cards, payoff only
in the reveal, reveal in the last third, ending callback, every number/name backed, honest title; critic ≥ 7.
Duration 40-50 s by pauses only. Storyboard: shots cover the video, cards ≥ 1.4 s, title present, ≥3 builds,
nobody cut by the frame. Video: 1080x1920, 30 fps, audio present, A/V length match, ending not clipped, 130-200 wpm,
loudness −18…−12 LUFS, true peak ≤ −1 dBTP (+0.6 tolerance), music ≥ 18 dB under the voice, no harsh jumps, no blank frames
outside cards, no static stretch > 3.5 s, brightness range, vignette present, vision judge ≥ 7 when available.

## Reviewing and tuning

Every Make run uploads a **review-pack**: idea, research (claims + quotes + URLs), script + critic notes, storyboard
JSON + report (metrics, repairs), storyboard contact sheet, final contact sheet, QA. To redo part of a documentary,
delete the stage file in `out/<id>/` and run `python -m flatframe.produce --resume <id>` (locally or in a workflow).

To change the look, edit one engine file at a time and render the sample (`--test`) for a before/after — the skill's 5.7
rule. To add a location or prop: add it to `engine/src/sets/kits.ts` or `engine/src/props/library.tsx` **and** to
`flatframe/catalog.py` (the director can only use catalogued assets).
