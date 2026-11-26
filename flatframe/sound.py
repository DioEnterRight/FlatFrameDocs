"""SOUND DESIGN: procedural, original music + sound effects mixed under the narration.

  * two beds: a suspense bed up to the reveal, a warmer bed from the reveal (an audible turn for the payoff)
  * the music sits at least `quality.music_under_voice_db` (18 dB, the skill's rule) under the voice and ducks a
    further 4 dB while anyone speaks
  * sound effects follow the plan: drops thud, slams and the reveal hit, whips whoosh, counters tick, the goofy
    skit punchline gets a small boing, cards get soft typing
  * the final mix is loudness-normalised (two-pass ffmpeg loudnorm) for Shorts/Reels, true peak <= -1.5 dBTP
Everything is generated on the runner from code (sound_synth.py): no samples, nothing to license.
"""
import json
import re
import subprocess

import numpy as np
import soundfile as sf

from . import sound_synth
from .common import log

SR = 48000
FPS = 30


def _load(path, channels=2):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", str(channels), "-ar", str(SR), "pipe:1"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).reshape(-1, channels).copy()


def lufs(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    return (float(i[-1]) if i else None), (float(tp[-1]) if tp else None)


def sfx_events(plan, timing):
    """-> [(seconds, name, gain_db)] from the plan's staged events."""
    ev = []
    for s in plan["shots"]:
        t0 = s["from"] / FPS
        if s.get("transition") == "whip":
            ev.append((t0 - 0.12, "whoosh", -8))
        if s["kind"] == "title":
            ev.append((t0, "impact", -6))
        if s["kind"] == "card":
            text = s["card"]["text"]
            start = t0 + s["card"]["typeFrom"] / FPS
            step = 1.0 / s["card"]["cps"]
            for k in range(0, len(text), 3):
                ev.append((start + k * step, "type", -22))
        for p in s.get("props", []):
            if "at" not in p:
                continue
            name = {"drop": "thud", "slam": "impact", "slide": "whoosh", "switch": "pop", "grow": "pop"}.get(p.get("entry"))
            if name:
                ev.append((t0 + p["at"] / FPS, name, -12 if name != "impact" else -10))
        b = s.get("build")
        if b:
            at = [t0 + a / FPS for a in b["at"]]
            if b["recipe"] == "counter":
                ev += [(at[0] + k * 0.05, "tick", -18) for k in range(18)]
            elif b["recipe"] in ("stack", "compare", "drop_puff"):
                ev += [(a + (7 if b["recipe"] != "compare" else 17) / FPS, "thud", -12) for a in at]
            elif b["recipe"] in ("slam_sticker", "state_flip"):
                ev.append((at[0], "impact", -10))
            elif b["recipe"] in ("glow_on", "tag_vanish", "timeline", "side_slide", "grow"):
                ev += [(a, "pop", -14) for a in at]
    lines = timing["lines"]
    reveal = next((l for l in lines if l["section"] == "reveal"), None)
    if reveal:
        ev += [(reveal["start"] - 0.05, "impact", -8), (reveal["start"] + 0.1, "ding", -16)]
    if timing.get("outro"):
        ev.append((timing["outro"]["start"], "ding", -14))
        ev.append((timing["outro"]["start"] + 0.35, "whoosh", -12))
    skit = [l for l in lines if l["speaker"] != "narrator"]
    if skit:
        ev.append((skit[-1]["end"] + 0.05, "boing", -16))
    return sorted(ev)


def mix(cfg, plan, timing, project_dir, seed):
    """voice.wav + music + sfx -> mix.wav (48 kHz stereo). Returns a report for QA."""
    q = cfg["quality"]
    voice = _load(project_dir / "voice.wav", 1)[:, 0]
    n = len(voice)
    dur = n / SR
    reveal_t = next((l["start"] for l in timing["lines"] if l["section"] == "reveal"), dur * 0.75)
    beds = []
    for style, part in (("suspense", "a"), ("keys", "b")):
        out = project_dir / f"bed_{part}.wav"
        sound_synth.bed(style, dur + 1, 92 if style == "suspense" else 84, seed % 7 - 3, seed + (part == "b"), out)
        beds.append(_load(out)[:n])
    x = np.arange(n) / SR
    fade = np.clip((x - (reveal_t - 0.6)) / 1.2, 0, 1)[:, None]
    music = beds[0] * (1 - fade) + beds[1] * fade
    # levels: voice ~ -16 LUFS before the final loudnorm; beds were rendered at -20 LUFS
    v_db_target = -16.0
    v_l = _rms_db(voice)
    gv = 10 ** ((v_db_target - v_l) / 20)
    under = float(q["music_under_voice_db"]) + 3   # 3 dB of headroom over the rule
    gm = 10 ** ((v_db_target - under - (-20.0)) / 20)
    # duck a further 4 dB while speaking (smoothed voice envelope)
    env = np.abs(voice)
    k = int(0.15 * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    speaking = np.clip(env / (np.percentile(env, 90) or 1) * 2, 0, 1)
    duck = 10 ** (-4 * speaking / 20)
    out = np.zeros((n, 2), dtype=np.float32)
    out += (voice * gv)[:, None]
    out += music * gm * duck[:, None]
    sfx_dir = sound_synth.ensure_sfx()
    cache = {}
    events = sfx_events(plan, timing)
    for t, name, gain_db in events:
        if name not in cache:
            cache[name] = _load(sfx_dir / f"{name}.wav")
        sig = cache[name] * (10 ** (gain_db / 20)) * gv * 0.5
        a = int(max(0, t) * SR)
        b = min(n, a + len(sig))
        if b > a:
            out[a:b] += sig[: b - a]
    raw = project_dir / "mix_raw.wav"
    sf.write(raw, np.clip(out, -1, 1), SR)
    final = project_dir / "mix.wav"
    _loudnorm(raw, final, -14.0)
    i, tp = lufs(final)
    music_rel = round(20 * np.log10((np.sqrt(np.mean((music * gm) ** 2)) + 1e-9) / (np.sqrt(np.mean((voice * gv) ** 2)) + 1e-9)), 1)
    rep = {"integrated_lufs": i, "true_peak_db": tp, "music_vs_voice_db": music_rel, "sfx_events": len(events)}
    log(f"mix: {i} LUFS, peak {tp} dBTP, music {music_rel} dB vs voice, {len(events)} sfx")
    return rep


def _rms_db(x):
    active = x[np.abs(x) > 0.02]
    if len(active) == 0:
        return -30.0
    return float(20 * np.log10(np.sqrt(np.mean(active ** 2)) + 1e-9))


def _loudnorm(src, dst, target):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", f"loudnorm=I={target}:TP=-1.5:LRA=9:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    af = (f"loudnorm=I={target}:TP=-1.5:LRA=9:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af", af, "-ar", str(SR), str(dst)], check=True)
