"""POST: runs every 30 minutes (Post workflow). Instagram and YouTube are decided independently.

Instagram  the slot that is due right now (schedule.py) gets the oldest ready video; missed slots are recorded and
           never posted later (no catch-up bursts); `instagram_daily_cap` successful Reels per rolling 24 h.
YouTube    every run asks the safety controller (yt_guard.py). With the default cap of 1 per rolling 24 h,
           YouTube gets the best QA-passed video of the last 48 h; uploadLimitExceeded pauses YouTube for >= 24 h.

  python -m flatframe.publish          scheduled run
  python -m flatframe.publish --now    manual button: posts the oldest ready video to Instagram now (still capped);
                                       YouTube is NOT forced: the same guard checks run as always.
State is saved after every step (data/history.json + data/youtube_ledger.json), so a crash never double-posts.
"""
import datetime as dt
import json
import os
import sys

from . import instagram, schedule, youtube, yt_guard
from .common import OUT, load_config, load_history, log, now_ist, parse_time, run, save_history

IG_DONE = {"posted", "manual_notified", "skipped"}
YT_DONE = {"posted", "private", "manual_notified", "skipped_window", "skipped_mode"}


def open_issue_once(title, body):
    res = run(["gh", "issue", "list", "--state", "open", "--search", f'"{title}" in:title', "--json", "title"], check=False, capture=True)
    if res.returncode == 0:
        try:
            if any(i.get("title") == title for i in json.loads(res.stdout or "[]")):
                return
        except ValueError:
            pass
    run(["gh", "issue", "create", "--title", title, "--body", body], check=False)


def fetch(v):
    work = OUT / v["id"]
    work.mkdir(parents=True, exist_ok=True)
    if not (work / "final.mp4").exists():
        run(["gh", "release", "download", v["tag"], "-p", "final.mp4", "-p", "meta.json", "-D", work, "--clobber"])
    return work / "final.mp4", json.loads((work / "meta.json").read_text(encoding="utf-8"))


def ig_posts_24h(history, now):
    cut = now - dt.timedelta(hours=24)
    return sum(1 for v in history["videos"] if v.get("ig_posted_at") and parse_time(v["ig_posted_at"]) > cut)


# ---------------------------------------------------------------- Instagram
def instagram_step(cfg, history, now, force):
    p = cfg["publish"]
    queued = sorted((v for v in history["videos"] if v.get("status") == "queued"), key=lambda v: v["created"])
    busy = [v for v in queued if v.get("slot") and v.get("ig_state") not in IG_DONE]
    if busy:
        v = busy[0]
    else:
        slot, missed = (now.strftime("%Y-%m-%d %H:%M") + " manual", []) if force else schedule.due(cfg, schedule.used_slots(history), now)
        if missed:
            history.setdefault("missed_slots", []).extend(missed)
            history["missed_slots"] = history["missed_slots"][-60:]
            log(f"slots missed (not posted later): {missed}")
            save_history(history)
        if not slot:
            return None
        ready = [v for v in queued if not v.get("slot")]
        if not ready:
            history.setdefault("missed_slots", []).append(slot)
            save_history(history)
            open_issue_once(f"⚠️ No video ready for {slot[:10]}", f"Nothing was ready for the {slot} slot. "
                            "Check the latest 'Make video' run (a topic may have failed research or QA, which is by design).")
            return None
        v = ready[0]
        v["slot"] = slot
        save_history(history)
    if not p["instagram"]:
        v["ig_state"] = "skipped"
        return None
    if not (os.environ.get("IG_USER_ID", "").strip() and os.environ.get("IG_PAGE_TOKEN", "").strip()):
        log("Instagram secrets are not set (python tools/add_tokens.py); this video is not posted to Instagram", "WARN")
        v["ig_state"] = "skipped"
        save_history(history)
        return None
    if ig_posts_24h(history, now) >= int(p["instagram_daily_cap"]):
        log("Instagram daily cap reached; this slot stays unposted on Instagram")
        v["ig_state"] = "skipped"
        save_history(history)
        return None
    video, meta = fetch(v)
    try:
        existing = instagram.find_existing(meta["caption"])
        if existing:
            v["ig_media_id"], v["ig_state"] = existing, "posted"
        else:
            url = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/releases/download/{v['tag']}/final.mp4" if os.environ.get("GITHUB_REPOSITORY") else None
            v["ig_media_id"], v["ig_link"] = instagram.publish(video, meta["caption"], video_url=url, ai_label=meta.get("ai_label_instagram", True))
            v["ig_state"] = "posted"
        v["ig_posted_at"] = now.isoformat(timespec="minutes")
        return None
    except Exception as e:  # noqa: BLE001
        v["ig_attempts"] = v.get("ig_attempts", 0) + 1
        if v["ig_attempts"] >= int(p["instagram_max_attempts"]):
            instagram.notify_manual(meta, v["tag"])
            v["ig_state"] = "manual_notified"
            return f"Instagram failed {v['ig_attempts']}x; manual post requested: {e}"
        return f"Instagram failed (attempt {v['ig_attempts']}): {e}"
    finally:
        save_history(history)


# ---------------------------------------------------------------- YouTube (through the guard, always)
def youtube_step(cfg, history, now):
    p = cfg["publish"]
    mode = p["youtube_mode"]
    if mode == "off":
        for v in history["videos"]:
            if v.get("status") == "queued" and v.get("yt_state") is None:
                v["yt_state"] = "skipped_mode"
        return None
    utc_now = now.astimezone(dt.timezone.utc)
    guard = yt_guard.Guard(cfg, now=utc_now, repo=os.environ.get("GITHUB_REPOSITORY", "local"))
    cand = yt_guard.pick_candidate(cfg, history, utc_now)
    save_history(history)
    if cand is None:
        return None
    if mode == "manual":
        if len(guard.successes_24h()) >= int(p["youtube_channel_daily_cap"]):
            return None
        _, meta = fetch(cand)
        youtube.notify_manual(meta, cand["tag"])
        cand["yt_state"] = "manual_notified"
        guard.led["uploads"].append({"ts": yt_guard._iso(utc_now), "video_id": "manual:" + cand["id"], "local_id": cand["id"], "source": "manual issue"})
        yt_guard.save(guard.led)
        save_history(history)
        return None
    if guard.paused() or not guard.quick_ok():
        log("YouTube: " + "; ".join(guard.clearance(cand)[1]))
        return None
    try:
        yt = youtube.client()
        channel_id, recent = youtube.channel_state(yt)
        guard.reconcile(channel_id, recent, history)
    except PermissionError as e:
        yt_guard.save(guard.led)
        open_issue_once("⛔ YouTube channel mismatch", str(e))
        return f"YouTube refused: {e}"
    except Exception as e:  # noqa: BLE001  (no reconciliation = no upload this run)
        log(f"YouTube reconciliation failed, not uploading this run: {e}", "WARN")
        return None
    finally:
        save_history(history)
    ok, reasons = guard.clearance(cand)
    if not ok:
        guard.reject(cand, reasons)
        yt_guard.save(guard.led)
        log("YouTube not cleared: " + "; ".join(reasons))
        return None
    video, meta = fetch(cand)
    guard.begin(cand)
    yt_guard.save(guard.led)          # the pending marker is on disk before the insert call
    try:
        vid, privacy = youtube.upload(yt, video, meta)
        guard.success(cand, vid)
        cand["yt_video_id"], cand["yt_state"] = vid, ("posted" if privacy == "public" else "private")
        cand["yt_posted_at"] = utc_now.isoformat(timespec="minutes")
        if privacy != "public":
            open_issue_once("⚠️ YouTube API uploads are staying private",
                            f"Video `{vid}` was uploaded but YouTube kept it **{privacy}** (usually: the Google API audit is not approved yet). "
                            "Make it public in YouTube Studio, or set `publish.youtube_mode: manual` until the audit passes.")
        log(f"YouTube uploaded {vid} ({privacy})")
        return None
    except Exception as e:  # noqa: BLE001
        kind = yt_guard.classify(e)
        pause = guard.failure(cand, kind, e)
        if kind == "upload_limit":
            open_issue_once("⛔ YouTube daily upload limit reached: publishing paused",
                            f"YouTube answered `uploadLimitExceeded` at {utc_now:%Y-%m-%d %H:%M} UTC. Uploads are paused until "
                            f"**{pause['until']}** (at least 24 h). The video `{cand['id']}` stays queued. Nothing will be retried "
                            "or uploaded another way. If this keeps happening, lower `publish.youtube_channel_daily_cap`.")
            return "YouTube: uploadLimitExceeded, paused"
        if kind == "quota":
            log(f"YouTube API quota exhausted; paused until {pause['until']} (next Pacific quota day)", "WARN")
            return None
        cand["yt_attempts"] = cand.get("yt_attempts", 0) + 1
        if cand["yt_attempts"] >= int(p["youtube_max_attempts"]):
            youtube.notify_manual(meta, cand["tag"])
            cand["yt_state"] = "manual_notified"
        return f"YouTube upload failed ({kind}): {str(e)[:300]}"
    finally:
        guard.prune(int(cfg["retention"]["ledger_days"]))
        yt_guard.save(guard.led)
        save_history(history)


def finalize(cfg, history, now):
    for v in history["videos"]:
        if v.get("status") == "queued" and v.get("ig_state") in IG_DONE and v.get("yt_state") in YT_DONE:
            v["status"] = "published"
            v["published_at"] = now.isoformat(timespec="minutes")
    cutoff = now - dt.timedelta(days=int(cfg["retention"]["keep_releases_days"]))
    for v in history["videos"]:
        if v.get("status") == "published" and not v.get("release_deleted") and parse_time(v.get("published_at", v["created"])) < cutoff:
            if run(["gh", "release", "delete", v["tag"], "--yes", "--cleanup-tag"], check=False).returncode == 0:
                v["release_deleted"] = True
    history["videos"] = history["videos"][-int(cfg["retention"]["history_max_videos"]):]
    save_history(history)


def main():
    cfg = load_config()
    if cfg.get("paused"):
        log("Paused in config.yaml: not posting.")
        return
    history, now = load_history(), now_ist()
    errors = [e for e in (instagram_step(cfg, history, now, "--now" in sys.argv), youtube_step(cfg, history, now)) if e]
    finalize(cfg, history, now)
    for e in errors:
        log(e, "ERROR")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
