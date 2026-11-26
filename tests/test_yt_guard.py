"""YouTube safety controller: limits, pause, quota, reconciliation across repos, error handling, no forcing."""
import datetime as dt
import json

import pytest

from flatframe import config_check, yt_guard

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 26, 12, 0, tzinfo=UTC)


def video(i="v1", score=9.0, passed=True, status="queued", created=None):
    return {"id": i, "status": status, "qa": {"passed": passed, "score": score}, "created": (created or NOW).isoformat(), "title": f"T {i}"}


def test_rolling_24h_channel_cap(cfg):
    led = yt_guard.empty_ledger()
    led["uploads"].append({"ts": (NOW - dt.timedelta(hours=23)).isoformat(), "video_id": "x", "local_id": "old"})
    g = yt_guard.Guard(cfg, led, NOW)
    ok, why = g.clearance(video())
    assert not ok and any("channel cap" in w for w in why)
    g2 = yt_guard.Guard(cfg, led, NOW + dt.timedelta(hours=1, minutes=1))
    assert g2.clearance(video())[0]


def test_upload_limit_pauses_at_least_24h_and_never_retries(cfg):
    g = yt_guard.Guard(cfg, yt_guard.empty_ledger(), NOW)
    v = video()
    g.begin(v)
    pause = g.failure(v, "upload_limit", "uploadLimitExceeded")
    assert pause["reason"] == "uploadLimitExceeded"
    assert yt_guard._utc(pause["until"]) - NOW >= dt.timedelta(hours=24)
    later = yt_guard.Guard(cfg, g.led, NOW + dt.timedelta(hours=23, minutes=59))
    ok, why = later.clearance(video("v2"))
    assert not ok and any("paused" in w for w in why)
    assert not later.quick_ok()


def test_quota_exceeded_waits_for_next_pacific_day(cfg):
    g = yt_guard.Guard(cfg, yt_guard.empty_ledger(), NOW)   # 12:00 UTC = 04:00 PST
    v = video()
    g.begin(v)
    pause = g.failure(v, "quota", "quotaExceeded")
    until = yt_guard._utc(pause["until"])
    assert until == dt.datetime(2026, 11, 27, 8, 10, tzinfo=UTC)   # 00:10 PST next day
    assert pause["reason"] == "quotaExceeded"


def test_api_insert_cap_per_pacific_day(cfg):
    cfg["publish"]["youtube_api_daily_insert_cap"] = 2
    cfg["publish"]["youtube_channel_daily_cap"] = 10
    led = yt_guard.empty_ledger()
    led["insert_calls"] = [{"ts": (NOW - dt.timedelta(hours=1)).isoformat(), "local_id": "a"}, {"ts": (NOW - dt.timedelta(hours=2)).isoformat(), "local_id": "b"}]
    ok, why = yt_guard.Guard(cfg, led, NOW).clearance(video())
    assert not ok and any("API insert allowance" in w for w in why)


def test_pending_and_duplicates_block(cfg):
    led = yt_guard.empty_ledger()
    led["pending"] = {"local_id": "v1", "started": NOW.isoformat()}
    assert not yt_guard.Guard(cfg, led, NOW).clearance(video("v9"))[0]
    led = yt_guard.empty_ledger()
    led["uploads"].append({"ts": (NOW - dt.timedelta(days=3)).isoformat(), "video_id": "y", "local_id": "v1"})
    ok, why = yt_guard.Guard(cfg, led, NOW).clearance(video("v1"))
    assert not ok and any("already on YouTube" in w for w in why)


def test_qa_failed_or_not_queued_is_refused(cfg):
    g = yt_guard.Guard(cfg, yt_guard.empty_ledger(), NOW)
    assert not g.clearance(video(passed=False))[0]
    assert not g.clearance(video(status="published"))[0]


def test_reconcile_counts_uploads_from_other_repos(cfg):
    g = yt_guard.Guard(cfg, yt_guard.empty_ledger(), NOW)
    recent = [{"video_id": "abc", "title": "Something another repo posted", "published_at": (NOW - dt.timedelta(hours=3)).isoformat()}]
    g.reconcile("UC" + "x" * 22, recent, {"videos": []})
    ok, why = g.clearance(video())
    assert not ok and any("channel cap" in w for w in why)
    assert g.led["uploads"][0]["source"].startswith("channel")


def test_reconcile_resolves_pending_upload(cfg):
    led = yt_guard.empty_ledger()
    led["pending"] = {"local_id": "v1", "started": NOW.isoformat()}
    hist = {"videos": [video("v1")]}
    g = yt_guard.Guard(cfg, led, NOW + dt.timedelta(minutes=30))
    g.reconcile("UC" + "x" * 22, [{"video_id": "zz", "title": "T v1 #shorts", "published_at": NOW.isoformat()}], hist)
    assert g.led["pending"] is None and hist["videos"][0]["yt_video_id"] == "zz"


def test_channel_binding(cfg):
    cfg["publish"]["youtube_channel_id"] = "UC" + "a" * 22
    g = yt_guard.Guard(cfg, yt_guard.empty_ledger(), NOW)
    with pytest.raises(PermissionError):
        g.reconcile("UC" + "b" * 22, [], {"videos": []})
    led = yt_guard.empty_ledger()
    led["channel_id"] = "UC" + "c" * 22
    cfg["publish"]["youtube_channel_id"] = ""
    with pytest.raises(PermissionError):
        yt_guard.Guard(cfg, led, NOW).reconcile("UC" + "d" * 22, [], {"videos": []})


class FakeHttpError(Exception):
    def __init__(self, status, reason):
        self.resp = type("R", (), {"status": status})()
        self.content = json.dumps({"error": {"errors": [{"reason": reason}]}}).encode()


def test_classify_errors():
    assert yt_guard.classify(FakeHttpError(400, "uploadLimitExceeded")) == "upload_limit"
    assert yt_guard.classify(FakeHttpError(403, "quotaExceeded")) == "quota"
    assert yt_guard.classify(FakeHttpError(503, "backendError")) == "transient"
    assert yt_guard.classify(FakeHttpError(400, "invalidTitle")) == "other"


def test_candidate_is_best_recent_and_old_ones_are_skipped(cfg):
    hist = {"videos": [video("old", 9.9, created=NOW - dt.timedelta(hours=60)), video("a", 8.1), video("b", 9.3), video("c", 9.9, passed=False)]}
    best = yt_guard.pick_candidate(cfg, hist, NOW)
    assert best["id"] == "b"
    assert hist["videos"][0]["yt_state"] == "skipped_window"


def test_config_refuses_unsafe_settings(cfg):
    for key, val in (("youtube_retry_upload_limit", True), ("youtube_pause_on_upload_limit", False), ("youtube_pause_hours", 12)):
        bad = json.loads(json.dumps(cfg))
        bad["publish"][key] = val
        with pytest.raises(config_check.ConfigError):
            config_check.validate(bad)


def test_pacific_dst():
    assert yt_guard.pacific(dt.datetime(2026, 7, 1, 12, tzinfo=UTC)).utcoffset() == dt.timedelta(hours=-7)
    assert yt_guard.pacific(dt.datetime(2026, 12, 1, 12, tzinfo=UTC)).utcoffset() == dt.timedelta(hours=-8)
