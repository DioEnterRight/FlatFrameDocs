# Security

## Secrets

Only in **GitHub Actions secrets**: `FREELLMAPI_KEYS`, `IG_USER_ID`, `IG_PAGE_TOKEN`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`,
`YT_REFRESH_TOKEN`. Nothing secret is committed (`.gitignore` covers `.env*`, `client_secret*.json`, keys); CI runs
gitleaks on every push/PR; enable GitHub secret scanning + push protection (SETUP.md). Logs redact every secret value
(`common.redact`); the FreeLLMAPI unified key and the git auth header are masked with `::add-mask::`.

## Tokens and permissions

- Every workflow starts with `permissions: {}`; each job asks only for what it needs.
- `actions/checkout` runs with `persist-credentials: false`, so no write token sits in `.git/config`.
- The write token (`GH_TOKEN`) is set **only** on the steps that need it: *Queue* (Releases) and *Save memory* in Make;
  *Post* and *Save memory* in Post. pip/npm installs, model downloads, TTS, Remotion/Chrome and the model calls run
  without it (`render.py` also strips it from the renderer's environment). Tested in `tests/test_repo.py`.
- CI (`ci.yml`) has a read-only token and no secrets; it is safe for pull requests from forks. Make/Post/Pin never run on
  pull requests.

## Supply chain

| What | How it is pinned | Update |
|---|---|---|
| GitHub Actions | full commit SHA (resolved with `git ls-remote`, tag in a comment) | Dependabot PRs (weekly) → CI must pass |
| Python | `requirements.lock` with `--hash=sha256` for Python 3.12, installed with `--require-hashes` | edit `requirements.in`, `uv pip compile requirements.in --python-version 3.12 --generate-hashes -o requirements.lock` (same for `-dev`), run tests |
| Node | exact versions in `engine/package.json` + `package-lock.json`, `npm ci --ignore-scripts` | Dependabot (Remotion packages grouped) → CI typecheck + still render |
| FreeLLMAPI image | `freellmapi.lock`: `image@sha256:…` | **Pin FreeLLMAPI** workflow (pull → digest → health check → PR) |
| Kokoro model | `kokoro.lock.json` SHA-256 (written by `python -m flatframe.fetch_models --lock` on first run) | delete the entry, re-lock, review |
| Fonts, map data | vendored from npm (OFL/Apache/ISC), licences in `docs/licenses/` | with the npm update |

Audits: `pip-audit` (hash-locked requirements) and `npm audit --omit=dev --audit-level=high` run in CI and fail the build.
At commit time both reported **no known vulnerabilities**.

**Not yet pinned:** the FreeLLMAPI digest. The build environment could not reach `ghcr.io`, and web pages gave
conflicting version/digest listings, so no digest was written from them. Run the Pin workflow once (SETUP.md step 4).

## YouTube upload safety (`flatframe/yt_guard.py`)

Two different limits are never confused:

- **API project quota** — Google's documentation (checked Nov 2026) gives a default of **100 `videos.insert` calls per
  day** in a separate bucket, plus 10,000 units for other methods, resetting at midnight Pacific. We count every insert
  call per Pacific day (`youtube_api_daily_insert_cap`). `quotaExceeded` → pause until the next Pacific day.
- **Channel daily upload limit** — set by YouTube per channel; the API exposes no number. Our own cap:
  `youtube_channel_daily_cap: 1` successful upload per **rolling 24 h** (conservative start for a new channel, not
  YouTube's limit). `uploadLimitExceeded` (400) → stop, **no retry**, pause ≥ `youtube_pause_hours` (≥ 24), save error +
  time, open an issue, keep the video queued.

Before every upload (all must pass): pause status · successful uploads in the last 24 h (ledger **reconciled with the
channel's real uploads playlist**) · channel cap · Pacific-day insert count · no earlier quotaExceeded today · not already
uploaded / no pending upload · QA passed · status queued · authenticated channel matches the ledger (and
`youtube_channel_id` if set). A `pending` marker is saved before the insert; a transfer hiccup resumes the same upload,
a refusal is never followed by another insert in the same run. There is no force flag; `--now` and manual runs use the
same checks; the config validator refuses `youtube_retry_upload_limit: true`, a pause under 24 h or
`youtube_pause_on_upload_limit: false`.

### Cross-repository coordination — decision

All three repositories contain YouTube upload code, but they target **three different channels**: shorts-bot → Cons & Coins
(`youtube_mode: api`), roblox-stories-bot → Dio's Stories (`youtube_mode: off`, code present), FlatFrameDocs → its own
channel. Per the brief, genuinely different channels keep separate ledgers, so no shared coordinator service was built.

What protects a channel if two repos are ever pointed at it anyway:
1. **The channel is the shared ledger**: each guard reconciles with the channel's uploads before uploading, so uploads by
   any repo (or by hand) count against every repo's rolling cap. This works with no extra infrastructure.
2. **Channel binding**: each ledger stores the channel id it belongs to and refuses to upload if the credentials point to
   a different channel; set `youtube_channel_id` to make it explicit.
3. A pause set by one repo is not visible to another; the other repo would receive one `uploadLimitExceeded` of its own
   and pause too (one refused call, never a retry loop). If you ever *want* two repos on one channel, give both the same
   `youtube_channel_id`, and keep the cap at 1 in only one of them (set the other's `youtube_mode: manual`).

Tests: `tests/test_yt_guard.py`, `tests/test_publish.py` (one upload per day over 40 post runs, no call after
uploadLimitExceeded for a day, `--now` cannot force, reconciliation counts other repos' uploads).

## Reporting

Open a private security advisory on the repository (Security → Advisories) rather than a public issue.
