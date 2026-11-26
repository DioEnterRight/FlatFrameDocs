"""QUALITY CONTROL: a video is never "done" because rendering finished. Measured gates (any failure = repair or reject):

  narration : 40-50 s, nothing clipped at the end, natural speaking rate (no speed-up), every line present
  story     : the script gates (script_check) and the critic score were passed upstream; the storyboard audit
              (beats.audit) found no violation; the visual judge (vision model, when one is free) scores the sheet
  visuals   : 1080x1920, 30 fps, no blank / single-colour frames outside black cards, no long static stretch,
              mean brightness in range, a vignette in scene frames (corners darker than the centre)
  audio     : integrated loudness in range, true peak below the limit, music >= 18 dB under the voice, no harsh
              jumps in short-term level
Saves qa.json and a contact sheet with every second of the video for the human to review.
"""
import json
import subprocess

import numpy as np
from PIL import Image

from . import lessons, render
from .common import ffprobe, log, prompt


def _frame_stats(paths):
    out = []
    prev = None
    for p in paths:
        a = np.asarray(Image.open(p).convert("L"), dtype=np.float32)
        h, w = a.shape
        corners = np.concatenate([a[: h // 8, : w // 8].ravel(), a[: h // 8, -w // 8:].ravel(), a[-h // 8:, : w // 8].ravel(), a[-h // 8:, -w // 8:].ravel()])
        centre = a[h // 3: 2 * h // 3, w // 3: 2 * w // 3]
        diff = float(np.mean(np.abs(a - prev))) if prev is not None else 99.0
        out.append({"mean": float(a.mean()), "std": float(a.std()), "corner": float(corners.mean()), "centre": float(centre.mean()), "diff": diff})
        prev = a
    return out


def _window_db(path, win=6400):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "pipe:1"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    return np.array([20 * np.log10(np.sqrt(np.mean(x[i * win:(i + 1) * win] ** 2)) + 1e-9) for i in range(len(x) // win)])


def short_term_jumps(path, voice_path):
    """Largest rise of 400 ms loudness between neighbouring windows (dB), ignoring silence and speech onsets.
    The voice coming back after a pause is meant to stand ~20 dB over the music bed (the skill's rule), so a window
    where the voice itself rises by 10+ dB is not a harsh jump; a sudden sfx or music burst is."""
    db, vdb = _window_db(path), _window_db(voice_path)
    n = min(len(db), len(vdb))
    jumps = [db[i] - db[i - 1] for i in range(1, n)
             if db[i] > -45 and db[i - 1] > -45 and vdb[i] - vdb[i - 1] < 10]
    return float(max(jumps)) if jumps else 0.0


def check(cfg, plan, timing, mix_report, final, project_dir, story_audit, judge_fn=None):
    q, v = cfg["quality"], cfg["video"]
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    info = ffprobe(final)
    vs = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    num, den = (vs.get("r_frame_rate", "0/1").split("/") + ["1"])[:2]
    fps = float(num) / float(den or 1)
    add("resolution", (vs.get("width"), vs.get("height")) == (1080, 1920), f"{vs.get('width')}x{vs.get('height')}")
    add("frame rate", abs(fps - 30) < 0.01, f"{fps:.2f} fps")
    story = timing.get("narration_end", dur)
    add("duration", float(v["min_seconds"]) - 0.5 <= story <= float(v["max_seconds"]) + 0.5 and dur - story <= float(cfg["brand"]["outro_seconds"]) + 1.5,
        f"story {story:.2f} s + outro {dur - story:.2f} s")
    add("audio present", au is not None, au.get("codec_name") if au else "missing")
    add("audio/video length", abs(dur - timing["duration"]) <= 0.25, f"video {dur:.2f}s vs voice {timing['duration']:.2f}s")
    last = timing["lines"][-1]
    add("ending not clipped", last["end"] + 0.4 <= dur, f"last word ends {last['end']:.2f}s of {dur:.2f}s")
    add("all lines voiced", all(l["end"] > l["start"] for l in timing["lines"]), f"{len(timing['lines'])} lines")
    add("natural pace", 130 <= timing["wpm"] <= 200, f"{timing['wpm']} wpm while speaking (no speed-up applied)")
    lo, hi = q["voice_lufs"]
    add("loudness", mix_report["integrated_lufs"] is not None and lo <= mix_report["integrated_lufs"] <= hi, f"{mix_report['integrated_lufs']} LUFS")
    add("true peak", mix_report["true_peak_db"] is not None and mix_report["true_peak_db"] <= float(q["max_true_peak"]) + 0.6, f"{mix_report['true_peak_db']} dBTP")
    add("music under voice", mix_report["music_vs_voice_db"] <= -float(q["music_under_voice_db"]), f"{mix_report['music_vs_voice_db']} dB")
    jump = short_term_jumps(final, project_dir / "voice.wav")
    add("no harsh volume jumps", jump <= 22, f"largest 400 ms rise {jump:.1f} dB")

    frames = render.frames_from_video(final, project_dir / "qa_frames", every=0.5)
    stats = _frame_stats(frames)
    card_ranges = [(s["from"] / 30, (s["from"] + s["dur"]) / 30) for s in plan["shots"] if s["kind"] == "card"]
    add("follow outro", plan["shots"][-1]["kind"] == "outro" and timing.get("outro", {}).get("speech_end", 0) < dur,
        f"outro from {story:.1f}s, speech ends {timing.get('outro', {}).get('speech_end', 0):.1f}s")
    in_card = lambda t: any(a - 0.3 <= t <= b + 0.3 for a, b in card_ranges)   # 2 fps sampling jitter
    blank = [i * 0.5 for i, s in enumerate(stats) if s["std"] < 3.0 and not in_card(i * 0.5)]
    add("no blank frames", not blank, f"blank at {blank[:5]}" if blank else "none")
    run_static, worst = 0, 0
    for s in stats[1:]:
        run_static = run_static + 1 if s["diff"] < 0.35 else 0
        worst = max(worst, run_static)
    add("no static stretch", worst * 0.5 <= float(q["max_static_seconds"]), f"longest near-static run {worst * 0.5:.1f}s")
    mean_b = float(np.mean([s["mean"] for s in stats]))
    add("brightness", float(q["min_mean_brightness"]) <= mean_b <= float(q["max_mean_brightness"]), f"mean {mean_b:.0f}/255")
    scene_stats = [s for i, s in enumerate(stats) if not in_card(i * 0.5)]
    vig = float(np.mean([s["centre"] - s["corner"] for s in scene_stats])) if scene_stats else 0
    add("vignette", vig > 4, f"centre brighter than corners by {vig:.0f}")
    add("storyboard rules", not story_audit, "; ".join(story_audit[:3]) or "all rules hold")

    sheet = render.contact_sheet(frames[::2], project_dir / "sheet.jpg", cols=8, labels=[f"{i:.0f}s" for i in range(0, len(frames[::2]))])
    judge = judge_fn(sheet) if judge_fn else None
    if judge is not None:
        add("visual judge", judge["score"] >= float(q["min_story_score"]), f"{judge['score']} by {judge['by']}: {judge['note'][:120]}")
    passed = all(c["ok"] for c in checks)
    score = round(10 * sum(c["ok"] for c in checks) / len(checks), 2)
    if judge is not None:
        score = round((score + judge["score"]) / 2, 2)
    res = {"passed": passed, "score": score, "checks": checks, "judge": judge, "sheet": sheet.name}
    for c in checks:
        if not c["ok"]:
            log(f"QA FAIL {c['check']}: {c['detail']}", "WARN")
    log(f"QA: {'PASSED' if passed else 'FAILED'} ({sum(c['ok'] for c in checks)}/{len(checks)} checks, score {score})")
    (project_dir / "qa.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


def make_judge(session):
    """Vision judge on the contact sheet (skill 5.6 checks: blank frames, characters cut, captions, variety...)."""
    if session is None or not session.has("judge"):
        return None

    def judge(sheet):
        try:
            obj, model = session.json("judge", lessons.system("judge_system.md", "judge"), prompt("judge.md"), images=[sheet], max_tokens=1500)
            s = obj.get("scores") or {}
            vals = [max(0.0, min(10.0, float(x))) for x in s.values() if isinstance(x, (int, float))]
            return {"score": round(sum(vals) / len(vals), 2) if vals else 0.0, "scores": s,
                    "note": str(obj.get("note", "")), "fixes": obj.get("fixes", []), "by": model}
        except Exception as e:  # noqa: BLE001  (no vision model answered: the measured gates still decide)
            log(f"visual judge skipped: {str(e)[:150]}", "WARN")
            return None
    return judge
