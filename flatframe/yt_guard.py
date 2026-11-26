"""YouTube publishing safety controller. Every YouTube upload in this repo goes through `Guard`.

Two different limits, never confused:

  A. API project quota. Google's default allowance (checked Nov 2026 on developers.google.com/youtube/v3/
     determine_quota_cost) is a separate bucket of 100 videos.insert calls per day, next to 10,000 units for other
     methods. Quota days reset at midnight Pacific time. We count every insert CALL (success or failure) per
     Pacific day against `youtube_api_daily_insert_cap`. A `quotaExceeded` (403) pauses uploads until the next
     Pacific quota day.
  B. Channel daily upload limit. Set by YouTube per channel (region, history...). The API exposes no number for it.
     We keep our own conservative cap (`youtube_channel_daily_cap`, successful uploads per ROLLING 24 h) and treat
     `uploadLimitExceeded` (400, "The channel's daily video upload limit has been reached") as final: no retry,
     publishing paused for at least `youtube_pause_hours` (>= 24), a GitHub issue, the video stays queued.

The ledger (data/youtube_ledger.json) is persisted with the repo state. Before each upload the ledger is reconciled
with the authenticated channel's recent uploads, so uploads made by hand or by ANY other repository on the same
channel count against the rolling cap too: the channel itself is the shared, authoritative record of uploads.

There is no force flag. `--now`, workflow_dispatch and manual Instagram posting all go through the same checks.
"""
import datetime as dt
import json

from . import common
from .common import log

LEDGER = "youtube_ledger.json"
PACIFIC_STD = dt.timezone(dt.timedelta(hours=-8))
PACIFIC_DST = dt.timezone(dt.timedelta(hours=-7))


def _utc(t):
    if isinstance(t, str):
        t = dt.datetime.fromisoformat(t)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc)


def _iso(t):
    return _utc(t).isoformat(timespec="seconds")


def pacific(t):
    """US Pacific time (DST: 2nd Sunday of March 02:00 -> 1st Sunday of November 02:00, local)."""
    t = _utc(t)
    y = t.year

    def nth_sunday(month, n):
        d = dt.date(y, month, 1)
        d += dt.timedelta(days=(6 - d.weekday()) % 7)
        return d + dt.timedelta(weeks=n - 1)
    start = dt.datetime.combine(nth_sunday(3, 2), dt.time(10), tzinfo=dt.timezone.utc)   # 02:00 PST = 10:00 UTC
    end = dt.datetime.combine(nth_sunday(11, 1), dt.time(9), tzinfo=dt.timezone.utc)     # 02:00 PDT = 09:00 UTC
    return t.astimezone(PACIFIC_DST if start <= t < end else PACIFIC_STD)


def quota_day(t):
    return pacific(t).date().isoformat()


def next_quota_reset(t, minutes=10):
    """UTC time `minutes` after the next Pacific midnight (when the daily API quota resets)."""
    day = pacific(t).date() + dt.timedelta(days=1)
    guess = dt.datetime.combine(day, dt.time(0, minutes), tzinfo=pacific(t).tzinfo)
    return _utc(dt.datetime.combine(day, dt.time(0, minutes), tzinfo=pacific(guess).tzinfo))


def empty_ledger():
    return {"version": 1, "channel_id": None, "uploads": [], "insert_calls": [], "attempts": [], "rejected": [],
            "errors": [], "pause": None, "pending": None, "last_reconcile": None}


def load():
    led = common.read_json(common.DATA / LEDGER, empty_ledger())
    for k, v in empty_ledger().items():
        led.setdefault(k, v)
    return led


def save(led):
    common.write_json(common.DATA / LEDGER, led)


def classify(error):
    """HttpError (or its JSON text) -> 'upload_limit' | 'quota' | 'auth' | 'transient' | 'other'."""
    status = getattr(getattr(error, "resp", None), "status", None)
    text = ""
    content = getattr(error, "content", None)
    if content:
        text = content.decode("utf-8", "replace") if isinstance(content, (bytes, bytearray)) else str(content)
    text = text or str(error)
    reasons = set()
    try:
        for e in json.loads(text).get("error", {}).get("errors", []):
            reasons.add(e.get("reason"))
    except (ValueError, AttributeError):
        pass
    if "uploadLimitExceeded" in reasons or "uploadLimitExceeded" in text:
        return "upload_limit"
    if reasons & {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"} or "quotaExceeded" in text:
        return "quota"
    if status in (401,) or reasons & {"authError", "forbidden", "insufficientPermissions"}:
        return "auth"
    if status in (500, 502, 503, 504):
        return "transient"
    return "other"


class Guard:
    """Pure decision logic over the ledger; the caller does the API calls and reports results back."""

    def __init__(self, cfg, ledger=None, now=None, repo=""):
        self.p = cfg["publish"]
        self.led = ledger if ledger is not None else load()
        self.now = _utc(now or dt.datetime.now(dt.timezone.utc))
        self.repo = repo

    # ---------------- counting
    def successes_24h(self):
        cut = self.now - dt.timedelta(hours=24)
        return [u for u in self.led["uploads"] if _utc(u["ts"]) > cut]

    def inserts_today(self):
        day = quota_day(self.now)
        return [c for c in self.led["insert_calls"] if quota_day(c["ts"]) == day]

    def paused(self):
        p = self.led.get("pause")
        if p and _utc(p["until"]) > self.now:
            return p
        return None

    # ---------------- the mandatory checks (pure; channel reconciliation is applied before via reconcile())
    def clearance(self, video):
        """-> (ok, [reasons it may not upload]). `video` is a history entry with its QA result."""
        reasons = []
        p = self.paused()
        if p:
            reasons.append(f"publishing paused until {p['until']} ({p['reason']})")
        n = len(self.successes_24h())
        cap = int(self.p["youtube_channel_daily_cap"])
        if n >= cap:
            reasons.append(f"channel cap: {n} successful upload(s) in the last 24 h (cap {cap})")
        calls = len(self.inserts_today())
        if calls >= int(self.p["youtube_api_daily_insert_cap"]):
            reasons.append(f"API insert allowance used: {calls} call(s) this Pacific day (cap {self.p['youtube_api_daily_insert_cap']})")
        if self.p.get("youtube_require_quota_clearance"):
            day = quota_day(self.now)
            if any(e["kind"] == "quota" and quota_day(e["ts"]) == day for e in self.led["errors"]):
                reasons.append("quotaExceeded earlier this Pacific quota day: waiting for the reset")
        if any(u.get("local_id") == video.get("id") for u in self.led["uploads"]) or video.get("yt_video_id"):
            reasons.append("this video is already on YouTube")
        pend = self.led.get("pending")
        if pend:
            reasons.append(f"an upload is still marked pending ({pend['local_id']} since {pend['started']}); reconcile first")
        if not (video.get("qa") or {}).get("passed"):
            reasons.append("video has not passed quality control")
        if video.get("status") != "queued":
            reasons.append(f"video status is {video.get('status')}, not queued")
        return (not reasons), reasons

    def quick_ok(self):
        """Cheap local check used by the workflow gate (no API, no video): could ANY upload be allowed now?"""
        return (self.p.get("youtube_mode") == "api" and not self.paused()
                and len(self.successes_24h()) < int(self.p["youtube_channel_daily_cap"])
                and len(self.inserts_today()) < int(self.p["youtube_api_daily_insert_cap"]))

    # ---------------- reconciliation with the real channel
    def reconcile(self, channel_id, recent, history):
        """recent = [{"video_id", "title", "published_at"}] from the authenticated channel's uploads playlist.
        Adds uploads made outside this repo to the rolling count, resolves a pending upload, binds the channel."""
        want = self.p.get("youtube_channel_id") or ""
        if want and channel_id != want:
            raise PermissionError(f"authenticated channel {channel_id} is not publish.youtube_channel_id {want}: refusing to upload")
        if self.led.get("channel_id") and self.led["channel_id"] != channel_id:
            raise PermissionError(f"YouTube credentials now point at channel {channel_id}, but this ledger belongs to "
                                  f"{self.led['channel_id']}. Fix the YT_* secrets (or start a new ledger on purpose).")
        self.led["channel_id"] = channel_id
        known = {u["video_id"] for u in self.led["uploads"]}
        key = lambda t: common.norm_text(str(t).lower().replace("#shorts", ""))
        titles = {key(v.get("title", "")): v for v in history["videos"]}
        for r in recent:
            if r["video_id"] in known:
                continue
            local = titles.get(key(r["title"]))
            pend = self.led.get("pending")
            if pend and local and local.get("id") == pend["local_id"]:
                self.led["pending"] = None
                local["yt_video_id"], local["yt_state"] = r["video_id"], "posted"
                log(f"Pending upload {pend['local_id']} found on the channel as {r['video_id']}")
            self.led["uploads"].append({"ts": _iso(r["published_at"]), "video_id": r["video_id"],
                                        "local_id": local.get("id") if local else None,
                                        "source": "this-repo" if local else "channel (other repo or manual)"})
        pend = self.led.get("pending")
        if pend and self.now - _utc(pend["started"]) > dt.timedelta(hours=2):
            log(f"Pending upload {pend['local_id']} never appeared on the channel; clearing it", "WARN")
            self.led["pending"] = None
        self.led["last_reconcile"] = _iso(self.now)

    # ---------------- recording outcomes
    def begin(self, video):
        self.led["pending"] = {"local_id": video["id"], "started": _iso(self.now), "repo": self.repo}
        self.led["insert_calls"].append({"ts": _iso(self.now), "local_id": video["id"]})
        self.led["attempts"].append({"ts": _iso(self.now), "local_id": video["id"], "result": "started"})

    def success(self, video, video_id):
        self.led["pending"] = None
        self.led["uploads"].append({"ts": _iso(self.now), "video_id": video_id, "local_id": video["id"], "source": "this-repo"})
        self.led["attempts"][-1]["result"] = "ok"

    def failure(self, video, kind, detail):
        """Record a failed insert and apply the pause rules. Returns the pause dict when one was set."""
        self.led["pending"] = None
        if self.led["attempts"]:
            self.led["attempts"][-1]["result"] = kind
        self.led["errors"].append({"ts": _iso(self.now), "local_id": video["id"], "kind": kind, "detail": str(detail)[:500]})
        if kind == "upload_limit":
            hours = max(24, int(self.p["youtube_pause_hours"]))
            self.led["pause"] = {"until": _iso(self.now + dt.timedelta(hours=hours)), "reason": "uploadLimitExceeded",
                                 "set_at": _iso(self.now), "detail": str(detail)[:300]}
            return self.led["pause"]
        if kind == "quota":
            reset = next_quota_reset(self.now)
            self.led["pause"] = {"until": _iso(reset), "reason": "quotaExceeded", "set_at": _iso(self.now),
                                 "detail": str(detail)[:300]}
            return self.led["pause"]
        return None

    def reject(self, video, reasons):
        self.led["rejected"].append({"ts": _iso(self.now), "local_id": video.get("id"), "reasons": reasons[:4]})
        self.led["rejected"] = self.led["rejected"][-200:]

    def prune(self, days):
        cut = self.now - dt.timedelta(days=days)
        for k in ("uploads", "insert_calls", "attempts", "errors", "rejected"):
            self.led[k] = [x for x in self.led[k] if _utc(x["ts"]) > cut]


def pick_candidate(cfg, history, now):
    """YouTube gets at most `youtube_channel_daily_cap` videos a day while the schedule makes 8: pick the best
    QA-passed video of the last `youtube_candidate_max_age_hours` that is not on YouTube yet. Older pending videos
    are marked skipped (they stay on Instagram; nothing is uploaded late in a burst)."""
    p = cfg["publish"]
    now = _utc(now)
    window = dt.timedelta(hours=int(p["youtube_candidate_max_age_hours"]))
    best = None
    for v in history["videos"]:
        if v.get("yt_state") is not None or v.get("status") not in ("queued", "published"):
            continue
        if not v.get("release_ok", True):
            continue
        age = now - _utc(common.parse_time(v["created"]))
        if age > window:
            v["yt_state"] = "skipped_window"
            continue
        if not (v.get("qa") or {}).get("passed"):
            continue
        score = (v.get("qa") or {}).get("score", 0)
        if best is None or score > (best.get("qa") or {}).get("score", 0):
            best = v
    return best
