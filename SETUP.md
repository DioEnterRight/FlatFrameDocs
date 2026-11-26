# Setup (about 30 minutes, once)

Everything runs on GitHub Actions. You only click in GitHub, Google Cloud and Meta once.

## 1. Create the repository

1. Create a **public** repository `DioEnterRight/FlatFrameDocs` (public = free Actions minutes and Instagram can fetch the video;
   a private repo burns the 2,000 free minutes/month in a few days and Instagram cannot download the video).
2. Push this folder to it (PowerShell, inside the folder):
   ```powershell
   git init -b main
   git add .
   git commit -m "FlatFrameDocs"
   git remote add origin https://github.com/DioEnterRight/FlatFrameDocs.git
   git push -u origin main
   ```

## 2. Repository settings

- **Settings → Actions → General → Workflow permissions**: choose **Read repository contents and packages permissions**
  (the workflows ask for write access themselves, only in the jobs that need it). Tick **Allow GitHub Actions to create
  and approve pull requests** (used only by *Pin FreeLLMAPI*).
- **Settings → Code security**: turn on **Secret scanning** and **Push protection** (free for public repos), and **Dependabot alerts**.
- **Settings → Branches**: optionally protect `main` and require the **CI** checks for pull requests. Leave direct pushes
  allowed for `github-actions` (the bot saves its state to `data/`).

## 3. Secrets: the token adder (any time later; until then scheduled runs just skip)

```powershell
pip install google-auth-oauthlib
gh auth login
python tools/add_tokens.py --list                          # what is set / missing
python tools/add_tokens.py --youtube C:\path\client_secret.json   # YouTube sign-in + FreeLLMAPI + Instagram
python tools/add_tokens.py                                 # later: add/replace FreeLLMAPI or Instagram only
```

It asks for each value hidden (Enter skips one) and stores it with `gh secret set`, so nothing lands in a file or
your shell history.

| Secret | What | Needed for |
|---|---|---|
| `FREELLMAPI_KEYS` | JSON list of your **free-tier** provider keys, same format as your other bots: `[{"platform":"google","key":"AIza..."},{"platform":"groq","key":"gsk_..."}]` (the adder builds it for you) | ideas, research, script, storyboard, judge |
| `IG_USER_ID` | Instagram professional account id | Instagram |
| `IG_PAGE_TOKEN` | long-lived Facebook Page token | Instagram |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | `--youtube client_secret.json` signs in once and stores all three | YouTube |

Until `FREELLMAPI_KEYS` is set, the hourly **Make video** run stops at its gate with a notice instead of failing.

Include at least one Google AI Studio key: Gemini models are free, strong writers and the only common free **vision**
model (the visual judge). See [FREE_MODELS.md](FREE_MODELS.md).

Use a **separate Google Cloud project / OAuth client and the FlatFrameDocs channel** for the YouTube secrets. Never
reuse the Cons & Coins (shorts-bot) or Dio's Stories (roblox-stories-bot) tokens here: each repository's upload ledger
is meant for exactly one channel (see SECURITY.md).

## 4. Pin the FreeLLMAPI image (once, then on updates)

Actions → **Pin FreeLLMAPI** → Run workflow → tag, e.g. `v0.12.0` (pick the latest from
https://github.com/tashfeenahmed/freellmapi/releases). It pulls the image, resolves its sha256 digest, checks that it
starts, and opens a pull request that edits `freellmapi.lock`. Merge it. Until then every run shows a
"not pinned" warning but still works.

## 5. Test without keys

Actions → **Make video** → Run workflow → keep **Test mode** ticked. In ~10 minutes the run has an artifact
`test-documentary` with `final.mp4`, `sheet.jpg` (one frame per second), `storyboard.jpg` and `qa.json`.

Then run it once with **Test mode unticked** and **force** ticked: a real documentary is researched, written, rendered and
queued as a GitHub Release (nothing is posted yet). Download the `review-pack` artifact to see the research, script,
storyboard and QA.

## 6. Go live

The schedules start by themselves once the workflows are on `main`:

- **Make video** runs every hour (UTC grid) and keeps `schedule.make_ahead` (2) videos ready.
- **Post video** runs every 30 minutes and posts the Instagram slot that is due (01:30, 04:30 … 22:30 IST).

YouTube: uploads only when `yt_guard` clears it — by default **one upload per rolling 24 hours**, the best QA-passed video
of the last 48 hours. While your Google API project is not audited, YouTube keeps API uploads private; the bot then opens
an issue. Set `publish.youtube_mode: manual` until the audit passes (you get one "upload this" issue per day instead).

Optional: put your channel id in `publish.youtube_channel_id` (`UC…`): uploads are refused if the secrets ever point at
another channel.

## 7. Everyday control (config.yaml)

| I want to… | Change |
|---|---|
| stop everything | `paused: true` |
| move the first slot | `schedule.first: "02:00"` |
| post less often | `schedule.every_minutes: 240` (must divide 1440) |
| allow 2 YouTube uploads a day (once the channel has proven it can) | `publish.youtube_channel_daily_cap: 2` |
| turn YouTube or Instagram off | `publish.youtube_mode: off` / `publish.instagram: false` |
| stricter fact checking | `research.min_sources_per_claim: 3` |

Every change is validated at the start of each run; a typo stops the run with a message naming the key.

## Notifications you may see (GitHub issues)

- **⛔ YouTube daily upload limit reached: publishing paused** — YouTube said `uploadLimitExceeded`. Nothing is retried;
  uploads resume by themselves after the pause (≥ 24 h). Consider lowering the cap.
- **⚠️ YouTube API uploads are staying private** — API audit not approved yet (see step 6).
- **📱 Post to Instagram / Upload to YouTube** — a manual post was requested; the issue has the file link and text.
- **⚠️ No video ready** — every topic failed research/QA or the free models were exhausted. Check the latest Make run.
