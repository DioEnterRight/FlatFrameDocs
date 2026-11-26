"""Cheap workflow gates (only pyyaml needed), so most scheduled runs stop in seconds.

  python -m flatframe.gate make   -> make=true|false   (are fewer than make_ahead videos ready?)
  python -m flatframe.gate post   -> due=true|false    (Instagram slot due / half-done, or a YouTube upload possible)
"""
import os
import sys

from . import schedule, yt_guard
from .common import load_config, load_history, now_ist

IG_DONE = {"posted", "manual_notified", "skipped"}


def make_gate(cfg, hist, now):
    return not cfg.get("paused") and schedule.to_make(cfg, len(schedule.ready_videos(hist)), now) > 0


def post_gate(cfg, hist, now):
    if cfg.get("paused"):
        return False
    queued = [v for v in hist["videos"] if v.get("status") == "queued"]
    ig_busy = any(v.get("slot") and v.get("ig_state") not in IG_DONE for v in queued)
    slot, missed = schedule.due(cfg, schedule.used_slots(hist), now)
    yt = (yt_guard.Guard(cfg, now=now).quick_ok()
          and any(v.get("yt_state") is None and (v.get("qa") or {}).get("passed") for v in queued))
    manual_yt = cfg["publish"]["youtube_mode"] == "manual" and any(v.get("yt_state") is None for v in queued)
    return bool(ig_busy or slot or missed or yt or manual_yt)


def main(argv):
    cfg, hist, now = load_config(), load_history(), now_ist()
    out = {"make": make_gate(cfg, hist, now)} if argv == ["make"] else {"due": post_gate(cfg, hist, now)}
    for k, v in out.items():
        line = f"{k}={'true' if v else 'false'}"
        print(line)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(line + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
