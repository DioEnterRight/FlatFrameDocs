"""Publishing flow with fake platforms: slots, no catch-up bursts, uploadLimitExceeded handling, --now cannot force."""
import datetime as dt
import json

import pytest

from flatframe import common, publish, yt_guard

IST = common.IST


class LimitError(Exception):
    def __init__(self):
        self.resp = type("R", (), {"status": 400})()
        self.content = json.dumps({"error": {"errors": [{"reason": "uploadLimitExceeded"}]}}).encode()


@pytest.fixture
def fakes(monkeypatch, tmp_path):
    calls = {"upload": 0, "ig": 0, "issues": []}
    monkeypatch.setattr(publish, "fetch", lambda v: (tmp_path / "f.mp4", {"title": v["title"], "caption": "c " + v["id"], "description": "d", "hashtags": ["#x"]}))
    monkeypatch.setattr(publish, "open_issue_once", lambda t, b: calls["issues"].append(t))
    monkeypatch.setattr(publish.instagram, "find_existing", lambda c: None)

    def ig(video, caption, video_url=None, ai_label=True):
        calls["ig"] += 1
        return "m" + str(calls["ig"]), "link"
    monkeypatch.setattr(publish.instagram, "publish", ig)
    monkeypatch.setattr(publish.youtube, "client", lambda: object())
    monkeypatch.setattr(publish.youtube, "channel_state", lambda yt: ("UC" + "x" * 22, []))
    return calls


def hist(n=3, created=None):
    created = created or dt.datetime(2026, 11, 26, 9, 0, tzinfo=IST)
    return {"videos": [{"id": f"v{i}", "tag": f"doc-v{i}", "title": f"Video {i}", "status": "queued",
                        "created": (created + dt.timedelta(minutes=i)).isoformat(), "qa": {"passed": True, "score": 9 - i * 0.1}} for i in range(n)]}


def test_due_slot_posts_one_video(cfg, fakes):
    h = hist()
    now = dt.datetime(2026, 11, 26, 10, 40, tzinfo=IST)   # slot 10:30
    publish.instagram_step(cfg, h, now, False)
    assert fakes["ig"] == 1 and h["videos"][0]["slot"] == "2026-11-26 10:30"


def test_outage_never_bursts(cfg, fakes):
    h = hist(5)
    h["videos"][0]["slot"] = "2026-11-26 01:30"
    h["videos"][0]["ig_state"] = "posted"
    now = dt.datetime(2026, 11, 26, 13, 45, tzinfo=IST)   # 04:30, 07:30, 10:30 missed; 13:30 due
    publish.instagram_step(cfg, h, now, False)
    assert fakes["ig"] == 1
    assert set(h["missed_slots"]) >= {"2026-11-26 04:30", "2026-11-26 07:30", "2026-11-26 10:30"}
    assert h["videos"][1]["slot"] == "2026-11-26 13:30"
    publish.instagram_step(cfg, h, now + dt.timedelta(minutes=30), False)   # next run: nothing due
    assert fakes["ig"] == 1


def test_upload_limit_stops_youtube_and_keeps_video(cfg, fakes, monkeypatch):
    h = hist(2, created=dt.datetime(2026, 11, 26, 9, 0, tzinfo=IST))

    def boom(yt, path, meta):
        fakes["upload"] += 1
        raise LimitError()
    monkeypatch.setattr(publish.youtube, "upload", boom)
    now = dt.datetime(2026, 11, 26, 10, 0, tzinfo=IST)
    err = publish.youtube_step(cfg, h, now)
    assert "uploadLimitExceeded" in err and fakes["upload"] == 1
    assert any("upload limit" in t for t in fakes["issues"])
    assert h["videos"][0]["status"] == "queued" and h["videos"][0].get("yt_state") is None
    led = yt_guard.load()
    assert led["pause"]["reason"] == "uploadLimitExceeded"
    for k in range(1, 48):   # every post run for the next day: no further insert call
        publish.youtube_step(cfg, h, now + dt.timedelta(minutes=30 * k))
    assert fakes["upload"] == 1


def test_one_upload_per_rolling_day(cfg, fakes, monkeypatch):
    h = hist(3)
    monkeypatch.setattr(publish.youtube, "upload", lambda yt, p, m: (fakes.__setitem__("upload", fakes["upload"] + 1), ("vid" + str(fakes["upload"]), "public"))[1])
    now = dt.datetime(2026, 11, 26, 10, 0, tzinfo=IST)
    for k in range(0, 40):
        publish.youtube_step(cfg, h, now + dt.timedelta(minutes=30 * k))
    assert fakes["upload"] == 1
    best = max(h["videos"], key=lambda v: v["qa"]["score"])
    assert best.get("yt_state") == "posted"


def test_now_button_cannot_force_youtube(cfg, fakes, monkeypatch, tmp_data):
    h = hist(2)
    led = yt_guard.empty_ledger()
    led["pause"] = {"until": "2099-01-01T00:00:00+00:00", "reason": "uploadLimitExceeded", "set_at": "x", "detail": ""}
    yt_guard.save(led)
    monkeypatch.setattr(publish.youtube, "upload", lambda *a: pytest.fail("upload must not be called"))
    common.save_history(h)
    monkeypatch.setattr(publish.sys, "argv", ["publish", "--now"])
    monkeypatch.setattr(publish, "finalize", lambda *a: None)
    publish.main()
    assert fakes["ig"] == 1


def test_instagram_daily_cap(cfg, fakes):
    cfg["publish"]["instagram_daily_cap"] = 1
    h = hist(3)
    h["videos"][0].update(slot="2026-11-26 07:30", ig_state="posted", ig_posted_at="2026-11-26T07:31+05:30")
    publish.instagram_step(cfg, h, dt.datetime(2026, 11, 26, 10, 35, tzinfo=IST), False)
    assert fakes["ig"] == 0 and h["videos"][1]["ig_state"] == "skipped"
