"""Publishing slots in India time (Asia/Kolkata, UTC+05:30, no daylight saving). Pure functions, no I/O.

GitHub cron runs in UTC and is often 5-30 minutes late, so the workflows run on a fixed UTC grid and this module
decides in IST whether a slot is due:

  * Make (hourly): produce a video when fewer than `make_ahead` ready videos cover the next slots (max make_per_run).
  * Post (every 30 min): post the ONE most recent slot that started at most `late_minutes` ago and is not used yet.
    Older missed slots are recorded as missed and never posted afterwards, so an outage can never cause a burst.
"""
import datetime as dt
import re

TIME = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


def _hm(t):
    if not TIME.fullmatch(str(t)):
        raise ValueError(f'schedule.first must look like "01:30" (24 h, India time), got {t!r}')
    return int(t[:2]) * 60 + int(t[3:])


def times(cfg):
    """-> ["HH:MM", ...] of one day, IST."""
    s = cfg["schedule"]
    every = int(s["every_minutes"])
    m = _hm(s["first"]) % every
    out = []
    while m < 1440:
        out.append(f"{m // 60:02d}:{m % 60:02d}")
        m += every
    return out


def slot_start(sid, tz):
    day, t = sid.split(" ")[:2]
    return dt.datetime.combine(dt.date.fromisoformat(day), dt.time(int(t[:2]), int(t[3:])), tzinfo=tz)


def slots_between(cfg, a, b):
    """slot ids whose start is in (a, b]"""
    out, day = [], a.date() - dt.timedelta(days=1)
    while day <= b.date():
        for t in times(cfg):
            start = dt.datetime.combine(day, dt.time(int(t[:2]), int(t[3:])), tzinfo=a.tzinfo)
            if a < start <= b:
                out.append(f"{day:%Y-%m-%d} {t}")
        day += dt.timedelta(days=1)
    return out


def upcoming(cfg, now, n):
    """the next n slot ids still ahead of now"""
    out, day = [], now.date()
    while len(out) < n:
        for t in times(cfg):
            start = dt.datetime.combine(day, dt.time(int(t[:2]), int(t[3:])), tzinfo=now.tzinfo)
            if start > now and len(out) < n:
                out.append(f"{day:%Y-%m-%d} {t}")
        day += dt.timedelta(days=1)
    return out


def due(cfg, used, now):
    """-> (slot id or None, [missed slot ids]). Only the newest slot inside the late window can be due; every older
    unused slot in the last day is reported as missed (never posted later = no catch-up bursts)."""
    late = dt.timedelta(minutes=int(cfg["schedule"]["late_minutes"]))
    recent = [s for s in slots_between(cfg, now - dt.timedelta(days=1), now) if s not in used]
    if not recent:
        return None, []
    newest = recent[-1]
    if now - slot_start(newest, now.tzinfo) <= late:
        return newest, recent[:-1]
    return None, recent


def to_make(cfg, ready_count, now):
    """how many videos the Make run should produce now"""
    s = cfg["schedule"]
    need = max(0, int(s["make_ahead"]) - int(ready_count))
    return min(need, int(s["make_per_run"]))


def used_slots(history):
    return {v.get("slot") for v in history["videos"] if v.get("slot")} | set(history.get("missed_slots", []))


def ready_videos(history):
    return [v for v in history["videos"] if v.get("status") == "queued" and not v.get("slot")]

