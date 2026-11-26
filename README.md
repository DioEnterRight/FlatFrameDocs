# FlatFrameDocs

Fully automated, free, cloud-only production of **45-second 2D animated documentaries** (YouTube Shorts + Instagram Reels).
Every video is researched from real sources, written to a strict hook → suspense → build → escalation → reveal → ending
structure, storyboarded and animated in code in a flat, lit, layered 2D documentary style, voiced, mixed, quality-checked,
queued, and posted on a 3-hour India-time schedule — with a YouTube safety controller that never forces uploads.

- **No paid AI, no Claude in production.** All model work goes through [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi)
  with free-tier provider keys, with per-video and monthly request/token caps.
- **Runs only on GitHub Actions.** Nothing runs on your computer.
- **Facts first.** A claim reaches the script only if two independent non-Wikipedia sources carry it (quotes checked
  literally). Unverifiable topics are rejected.
- **Branded.** `@outrichguy` in the top-right corner of every frame, word-by-word captions, and a 3-second outro where
  the main character says "Follow FlatFrameDocs and @outrichguy" (config `brand`).
- **Voices like shorts-bot.** edge-tts `en-US-AndrewNeural` at natural pace, Kokoro `am_michael` as the fallback.
- **Quality over schedule.** A topic that fails research, the script gates, the storyboard rules or video QA is dropped and
  the slot is skipped.

| Doc | What it covers |
|---|---|
| [SETUP.md](SETUP.md) | Step-by-step: secrets, settings, test run, going live |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Modules, data flow, state, workflows, failure handling |
| [PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md) | How a documentary is made; how the 2D Documentary Skill became code; tuning |
| [FREE_MODELS.md](FREE_MODELS.md) | FreeLLMAPI roles, budgets, failover, what happens when free capacity runs out |
| [SECURITY.md](SECURITY.md) | Secrets, token scoping, pinning, YouTube upload safety, update procedures |
| [docs/REPO_REVIEW.md](docs/REPO_REVIEW.md) | Review of the three repositories and every engineering decision |

```
idea engine ─► research (Wikipedia → cited sources, 2+ independent sites) ─► writer ⇄ critic ─► voice (edge-tts / Kokoro)
   ─► director (storyboard) ─► beat compiler (skill rules) ─► 2D engine (Remotion + SVG) ─► sound design ─► QA ─► Release queue
   ─► Post: Instagram slot every 3 h  +  YouTube via yt_guard (1 per rolling 24 h by default)
```

The production methodology is the **2D Documentary Skill**, kept at
[.claude/skills/2d-documentory-skill/SKILL.md](.claude/skills/2d-documentory-skill/SKILL.md);
[PRODUCTION_GUIDE.md](PRODUCTION_GUIDE.md) maps each of its rules to the code that enforces it.

Try it without any keys: **Actions → Make video → Run workflow (Test mode ✔)** renders the bundled sample documentary
(*The Australian Army Lost a War to Emus*) and attaches the MP4, contact sheet and QA report to the run.
