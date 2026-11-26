# Architecture

## Data flow (one documentary)

```
Make workflow (hourly gate)                                   out/<id>/  (every stage saved; --resume <id> continues)
 1 gate.py        is a video needed for the next slots?        -
 2 ideas.py       pitch 10 (ideator) → dedupe/variety filters → score 8 criteria (critic, different model)   idea.json
 3 research.py    Wikipedia (discovery) → claims with exact quotes → cited pages fetched →
                  verified when 2+ independent non-Wikipedia sites carry it → conflicts flagged → accept/reject  research.json
 4 writer.py      script from verified claims only ⇄ script_check.py (deterministic) + critic, up to 2 rewrites script.json
 5 voice.py       edge-tts (word timestamps) → Kokoro fallback; pauses fitted to 40-50 s (never sped up)   voice.wav timing.json
 6 director.py    storyboard JSON (director) → beats.py compiles + repairs against the skill rules        board.json plan.json
 7 render.py      storyboard stills → contact sheet                                                   storyboard.jpg
 8 sound.py       procedural beds + SFX from plan events, ducking, loudnorm                           mix.wav
 9 render.py      Remotion renders the muted 1080x1920 video, ffmpeg muxes the mix                    final.mp4
10 qa.py          17 measured gates + optional vision judge                                           qa.json sheet.jpg
11 metadata.py    title (checked), description with sources, hashtags, disclosure                    meta.json
12 queue.py       (write token) GitHub Release + history entry `queued`                               ready.json → Release
Post workflow (every 30 min)
13 publish.py     Instagram: due slot → oldest ready video (daily cap, no catch-up)
                  YouTube: yt_guard.pick_candidate → reconcile with channel → clearance → ONE insert → ledger
```

A failure in 3, 4, 5, 6 or 10 raises `StageError`: the next shortlisted idea is tried (`ideas.research_attempts`), and
if none survives the run ends without a video. `LLMUnavailable` (no free model / budget reached) ends the run gracefully.

## Modules (`flatframe/`)

| Module | Responsibility |
|---|---|
| `common.py` | paths, config loading, redacted logging, atomic JSON writes |
| `config_check.py` | validates every config key; refuses unsafe YouTube settings |
| `llm.py` | FreeLLMAPI client: discovery, role ranking/rotation, deny list, failover, budgets, usage ledger |
| `schedule.py`, `gate.py` | IST slot maths, make/post gates |
| `ideas.py` | idea generation, filters, critic scoring, idea bank |
| `sources.py`, `facts.py`, `research.py` | free web access, literal quote checks, numbers, corroboration, research record |
| `writer.py`, `script_check.py` | script drafting/critique loop and deterministic gates |
| `voice.py`, `fetch_models.py` | TTS engines, number speaking, alignment, pause fitting, Kokoro download with hash lock |
| `catalog.py`, `director.py`, `beats.py` | engine asset catalog, storyboard prompt, skill-rule compiler + metrics |
| `sound_synth.py`, `sound.py` | procedural music/SFX, mix |
| `render.py`, `qa.py`, `metadata.py` | rendering, quality gates, publishing text |
| `produce.py`, `queue.py` | orchestration with stage caching; release creation |
| `yt_guard.py`, `youtube.py`, `instagram.py`, `publish.py` | YouTube safety controller, platform clients, posting |

## The 2D engine (`engine/`, Remotion 4 + React + SVG)

`plan.json` (written by `beats.py`) is the only interface. `src/Doc.tsx` renders one `<Sequence>` per shot; `Shot.tsx`
dispatches to scene / skit / title (`Scene.tsx`: layered world), card, insert, tabletop, triptych and map
(`maps/WorldMap.tsx`, Natural Earth via world-atlas + d3-geo). Parts: `rig/Character.tsx` (one rig: 4 views, 9
expressions, 8 poses, blink/breath, loudness mouths), `creatures/`, `props/library.tsx` (~90 drawn props),
`sets/` (18 location kits, patterns, drawn light), `camera/camera.ts` (depth layers, moves, timings), `builds/`
(staged object builds), `fx/` (seeded environmental effects), `ui/` (cards, title, strips, tags, quote bar, calendar).
All motion is a pure function of the frame; randomness is seeded; fonts are embedded as base64.
Flat SVG needs no GPU: a 45 s video renders in ~4 minutes on a 2-core machine (faster on the 4-core runner).

## State (`data/`, committed by the bot)

| File | Contents |
|---|---|
| `history.json` | every video: status, slot, QA, platform states, missed slots, rejected topics |
| `ideas.json` | banked ideas and rejected topics |
| `freellm_usage.json` | monthly calls/tokens by model and role (budget enforcement) |
| `youtube_ledger.json` | uploads, insert calls, attempts, errors, rejected clearances, pause, pending marker, channel id |

Writes are atomic (temp file + rename). Make and Post can save at the same time: `tools/save_state.sh` rebases and
`tools/merge_state.py` (git merge driver) merges JSON (lists by id, counters added).

## Concurrency and duplicates

- `concurrency: ffd-make` and `ffd-post` — one Make and one Post at a time; they never block each other.
- A video is tied to its slot the moment it is picked; reruns finish the same video, never post a second one.
- YouTube: a `pending` marker is saved **before** the insert call; reconciliation with the channel resolves it.
- Instagram/YouTube duplicate checks by caption/title before posting.

## Reused from the reference repositories

| From | Reused (adapted) |
|---|---|
| roblox-stories-bot | FreeLLMAPI client design, start script, voice engine + alignment, procedural music, Instagram client, schedule model, state saving + merge driver, Releases-as-queue |
| shorts-bot | same FreeLLMAPI/Instagram/state infrastructure; the toon2d experience (flat 2D in the cloud) informed choosing flat SVG over 3D |
| 2D Documentary Skill | the whole production methodology (see PRODUCTION_GUIDE.md) |
