# Review of the three repositories and the decisions taken (26 Nov 2026)

## What was inspected

| Repo | State at review |
|---|---|
| `roblox-stories-bot` (Dio's Stories) | Remotion + three.js 3D CEO shorts, en/hi, every 3 h. FreeLLMAPI client with roles, rotation, per-video + monthly caps. edge-tts + Kokoro. Releases as queue, JSON merge driver. `checks.yml` (pytest, pyflakes, tsc). `youtube_mode: off` (code present). Floating `freellmapi:latest`, actions on tags, unpinned pip. 38 tests passing. |
| `shorts-bot` (Cons & Coins) | animated-shorts-kit (Remotion 3D toon world) with Claude Code as director plus FreeLLMAPI. **`youtube_mode: api`, 24 uploads/day scheduled.** No CI workflow for the 109 tests (only a manual FreeLLMAPI test). Same floating image, unpinned actions, unpinned global `npm install -g @anthropic-ai/claude-code`. History shows ~14 successful YouTube uploads in 24 h, then the 13:30 and 15:30 videos each failed twice and fell back to manual notices — consistent with the channel's daily upload limit; the error text is not stored, so this is inferred, not confirmed. |
| 2D Documentary Skill | supplied as `2d-documentory-skill.zip` (one `SKILL.md`, read in full; it references no other files). It is not in either repository. shorts-bot's history contains a different, earlier skill (`reachmora-2d-longform`, removed on 25 Nov); it was compared: the documentary skill is more complete on camera, staging, timing and QA, so it is the primary reference, and ReachMora contributed only its idea-strategy influence. |
| `FlatFrameDocs` | did not exist publicly; built here from scratch. |

## Decisions per repository

### YouTube upload protection
| Repo | Decision | Why |
|---|---|---|
| FlatFrameDocs | full controller (`flatframe/yt_guard.py`), cap 1 / rolling 24 h, best video of 48 h | new channel, brief's conservative start |
| shorts-bot | **added** the same controller; cap **10** / rolling 24 h; blocked videos become Instagram-only (`skipped_limit`) | it uploads live via the API and its current logic retried a refused upload on the next run (2 attempts per video); 10 is below the ~14 that succeeded before refusals. Raise only after a week with no pause. |
| roblox-stories-bot | **added** the controller, cap 1 | `youtube_mode: off` today, but the code is live the moment the mode flips; the guard must exist before activation |
| cross-repo | **no shared coordinator service** | the three repos target three different channels. Each guard reconciles with its channel's uploads (so any other uploader on the same channel is counted) and binds its ledger to one channel id. See SECURITY.md for the residual case. |

### CI
| Repo | Decision |
|---|---|
| FlatFrameDocs | `ci.yml`: pyflakes, config/JSON validation, 68 tests, pip-audit (hash-locked), engine `npm ci --ignore-scripts` + tsc + npm audit + a real still render, gitleaks. Read-only, no secrets, PR-safe. |
| shorts-bot | **added** `checks.yml`: tests + pyflakes + pip-audit + npm audit (kit) + gitleaks. **No tsc for the kit**: it imports `@story/*` aliases that only exist inside a per-video project, so a standalone typecheck is always red (verified) and would teach people to ignore CI. |
| roblox-stories-bot | **improved** `checks.yml`: pinned SHAs, no persisted credentials, pip-audit, npm audit, `npm ci --ignore-scripts`, gitleaks. Its tsc step already worked and stays. |

### Dependency hardening
| Item | FlatFrameDocs | shorts-bot / roblox-stories-bot |
|---|---|---|
| GitHub Actions | pinned to SHAs | **pinned to SHAs** of the same major versions they already used (no upgrade) |
| FreeLLMAPI image | `freellmapi.lock` + Pin workflow | **same mechanism added**; default stays `:latest` with a visible warning until the Pin workflow runs, so nothing breaks today |
| Python | hash-locked `requirements.lock` (Python 3.12) | **left as-is (`>=`)** but audited in CI: switching their installs to a lock is a behaviour change I could not test on their runners; recommended next step |
| Node | exact versions + lockfile, `--ignore-scripts` | lockfiles already committed; audits added; `--ignore-scripts` in roblox CI only |
| Claude Code CLI (shorts-bot only) | not used | **pinned** to 2.1.332 instead of "whatever is latest" |
| Dependabot | actions, npm, pip | added (actions, npm, pip) |

At review time `pip-audit` and `npm audit --omit=dev` reported **0 known vulnerabilities** in all three repos.

### Not changed (deliberately)
- Token handling in the two reference repos (job-level `GH_TOKEN`, persisted checkout credentials): restructuring it like
  FlatFrameDocs (token only in Queue/Save steps) is recommended, but it touches every workflow and their state saving; not
  done blind.
- shorts-bot's use of Claude Code as director: that repo is not bound by FlatFrameDocs' no-Claude rule; only pinned.
- No unused YouTube code was added anywhere; no repository was restructured to look like another.

## Test results (local, this environment)

| Repo | Result |
|---|---|
| FlatFrameDocs | 68 passed; pyflakes clean; engine tsc clean; sample documentary rendered end-to-end in test mode, QA 17/17 |
| shorts-bot (with patch) | 115 passed, 1 skipped (was 109 + 2 skipped; 5 new guard tests; the publish fixture now fakes the channel reconciliation) |
| roblox-stories-bot (with patch) | 43 passed (was 38; 5 new guard tests) |

GitHub-hosted CI has **not** run yet for any of these changes (no push access from the build environment).
