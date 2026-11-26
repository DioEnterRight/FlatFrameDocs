"""VOICE: Microsoft edge-tts (free read-aloud service, real per-word timestamps) with Kokoro (free, offline,
Apache-2.0) as the fallback. Reused from roblox-stories-bot/pipeline/voice.py (line-by-line synthesis, sequence
alignment of word marks, whole-video fallback so the voice never changes mid-video) and extended for documentaries:

  * narrator + skit voices (the skill: "skit lines flatter and slower")
  * numbers are spoken naturally ("1932" -> "nineteen thirty-two") while timings stay on the written words
  * pauses: a beat after each [CARD] line and before the reveal; the DURATION FITTER only moves pauses inside
    voice.min_gap..max_gap. The speech itself is never sped up. A script that still misses 40-50 s goes back to
    the writer (produce.py).
  * a per-frame loudness envelope for every skit line drives the speaking character's mouth (skill 5.4)

edge-tts uses Microsoft's public read-aloud endpoint without an official licence: it can rate-limit or stop at any
time, which is why Kokoro stays wired in (models downloaded by flatframe.fetch_models, cached by Actions).
Output: voice.wav (48 kHz mono) + timing.json.
"""
import asyncio
import difflib
import re
import subprocess
import time

import numpy as np
import soundfile as sf

from .common import MODELS, log, norm_text, write_json

SR = 24000
FPS = 30


class DurationError(RuntimeError):
    def __init__(self, seconds, lo, hi):
        super().__init__(f"narration is {seconds:.1f}s, outside {lo}-{hi}s even with the pauses adjusted")
        self.seconds = seconds


# ---------------------------------------------------------------- numbers spoken naturally
ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS_W = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def int_words(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS_W[n // 10] + ("" if n % 10 == 0 else "-" + ONES[n % 10])
    if n < 1000:
        return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + int_words(n % 100))
    for div, name in ((10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= div:
            return int_words(n // div) + " " + name + ("" if n % div == 0 else " " + int_words(n % div))
    return str(n)


def year_words(y):
    if 2000 <= y <= 2009:
        return int_words(y)
    hi, lo = divmod(y, 100)
    if lo == 0:
        return int_words(hi) + " hundred"
    return int_words(hi) + " " + ("oh-" + ONES[lo] if lo < 10 else int_words(lo))


def speak_numbers(text):
    def repl(m):
        cur, raw, scale, pct = m.group(1), m.group(2), m.group(3), m.group(4)
        val = raw.replace(",", "")
        if "." in val:
            whole, frac = val.split(".", 1)
            words = int_words(int(whole)) + " point " + " ".join(ONES[int(d)] for d in frac)
        else:
            n = int(val)
            is_year = not cur and not scale and not pct and "," not in raw and 1100 <= n <= 2099
            words = year_words(n) if is_year else int_words(n)
        if scale:
            words += " " + scale
        if pct:
            words += " percent"
        if cur:
            words += " dollars"
        return words
    return re.sub(r"(\$)?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?:\s*(thousand|million|billion|trillion))?(%)?", repl, text)


# ---------------------------------------------------------------- alignment (from roblox-stories-bot)
def align_words(words, marks, dur):
    """Spoken-word timestamps -> the script's words (sequence alignment). Unmatched words (numbers read as several
    words) share the gap between their matched neighbours by length. Monotonic, inside [0, dur]."""
    if not words:
        return []
    keys = [norm_text(w) for w in words]
    mkeys = [norm_text(m[2]) for m in marks]
    times = [None] * len(words)
    sm = difflib.SequenceMatcher(a=keys, b=mkeys, autojunk=False)
    for blk in sm.get_matching_blocks():
        for j in range(blk.size):
            m = marks[blk.b + j]
            times[blk.a + j] = [m[0], m[1]]
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "replace" and b1 > b0:
            lo, hi = marks[b0][0], marks[b1 - 1][1]
            sizes = [max(1, len(keys[i])) for i in range(a0, a1)]
            edges = np.concatenate([[0], np.cumsum(sizes)]) / sum(sizes) * (hi - lo) + lo
            for k, i in enumerate(range(a0, a1)):
                times[i] = [edges[k], edges[k + 1]]
    i = 0
    while i < len(words):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(words) and times[j] is None:
            j += 1
        lo = times[i - 1][1] if i > 0 else 0.0
        hi = max(times[j][0] if j < len(words) else dur, lo)
        sizes = [max(1, len(keys[x])) for x in range(i, j)]
        edges = np.concatenate([[0], np.cumsum(sizes)]) / sum(sizes) * (hi - lo) + lo
        for k, x in enumerate(range(i, j)):
            times[x] = [edges[k], edges[k + 1]]
        i = j
    prev = 0.0
    for t in times:
        t[0] = min(max(t[0], prev), dur)
        t[1] = min(max(t[1], t[0] + 0.04), dur)
        prev = t[0]
    return [(float(a), float(b)) for a, b in times]


def spread_words(words, dur):
    """No timestamps (Kokoro): spread by length with extra weight at punctuation."""
    weights = np.array([1.2 + 0.55 * len(re.sub(r"\W", "", w)) + (2.0 if re.search(r"[,;:]$", w) else 2.6 if re.search(r"[.!?]$", w) else 0)
                        for w in words])
    bounds = np.concatenate([[0], np.cumsum(weights)]) / weights.sum() * dur
    return [(float(bounds[j]), float(bounds[j + 1])) for j in range(len(words))]


def _trim(x, thresh=0.01, pad=0.03):
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - int(pad * SR)): min(len(x), idx[-1] + int(pad * SR))]


def _decode(data, fmt=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-f", fmt] if fmt else []) + ["-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"]
    out = subprocess.run(cmd, input=data, capture_output=True, check=True)
    return np.frombuffer(out.stdout, dtype=np.float32).copy()


# ---------------------------------------------------------------- engines
async def _edge_stream(text, voice, rate):
    import edge_tts
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    audio, marks = bytearray(), []
    async for ch in com.stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":   # 100-nanosecond ticks
            marks.append((ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7, ch["text"]))
    if not audio:
        raise RuntimeError("edge-tts returned no audio")
    return bytes(audio), marks


def edge_line(text, spoken, vp, vcfg):
    waits = [3, 6, 12, 20, 30]
    retries = int(vcfg.get("edge_retries", 5))
    for attempt in range(1, retries + 1):
        try:
            data, marks = asyncio.run(_edge_stream(spoken, vp["edge_voice"], vp.get("edge_rate", "+0%")))
            raw = _decode(data)
            break
        except Exception as e:  # noqa: BLE001
            if attempt == retries:
                raise
            w = waits[min(attempt, len(waits)) - 1]
            log(f"edge-tts attempt {attempt} failed ({str(e)[:120]}); retrying in {w} s", "WARN")
            time.sleep(w)
    idx = np.where(np.abs(raw) > 0.01)[0]
    if len(idx) == 0 or len(raw) < SR * 0.2:
        raise RuntimeError("edge-tts line came out empty")
    a, b = max(0, idx[0] - int(0.03 * SR)), min(len(raw), idx[-1] + int(0.03 * SR))
    samples, lead = raw[a:b], a / SR
    words = text.split()
    spans = align_words(words, [(m0 - lead, m1 - lead, t) for m0, m1, t in marks], len(samples) / SR)
    return samples, spans


def kokoro_line(k, text, spoken, vp):
    samples, sr = k.create(spoken, voice=vp["kokoro_voice"], speed=float(vp.get("kokoro_speed", 1.0)), lang="en-us")
    if sr != SR:
        raise RuntimeError(f"unexpected Kokoro sample rate {sr}")
    samples = _trim(np.asarray(samples, dtype=np.float32))
    if len(samples) < SR * 0.2:
        raise RuntimeError(f"Kokoro line came out empty: {text[:60]}")
    return samples, spread_words(text.split(), len(samples) / SR)


def available_engines(cfg, test=False):
    order = []
    if cfg["voice"]["engine"] == "edge":
        order.append("edge")
    if (MODELS / "kokoro.onnx").exists():
        order.append("kokoro")
    return order


def _voice_for(cfg, speaker, cast_order):
    if speaker in ("narrator", "outro"):
        return cfg["voice"]["narrator"]
    sv = cfg["voice"]["skit_voices"]
    return sv[cast_order.index(speaker) % len(sv)]


def render_lines(cfg, lines, test=False):
    """-> (engine, [(samples, word spans)]). One engine for the whole video."""
    vcfg = cfg["voice"]
    cast_order = [s for s in dict.fromkeys(l.get("speaker", "narrator") for l in lines) if s not in ("narrator", "outro")]
    errors = []
    for engine in available_engines(cfg, test):
        try:
            out, k = [], None
            if engine == "kokoro":
                from kokoro_onnx import Kokoro
                k = Kokoro(str(MODELS / "kokoro.onnx"), str(MODELS / "voices.bin"))
            for i, l in enumerate(lines):
                vp = _voice_for(cfg, l.get("speaker", "narrator"), cast_order)
                spoken = l.get("spoken") or speak_numbers(l["text"])
                if engine == "edge":
                    if i:
                        time.sleep(float(vcfg.get("edge_pause", 1.0)))
                    out.append(edge_line(l["text"], spoken, vp, vcfg))
                else:
                    out.append(kokoro_line(k, l["text"], spoken, vp))
            log(f"voice: {len(lines)} lines with {engine}")
            return engine, out
        except Exception as e:  # noqa: BLE001  (any failure = next engine for the WHOLE video)
            errors.append(f"{engine}: {str(e)[:160]}")
            log(f"voice engine {engine} failed ({str(e)[:160]}); trying the next one", "WARN")
    raise RuntimeError("no voice engine worked: " + " | ".join(errors) + " (run python -m flatframe.fetch_models for Kokoro)")


def plan_gaps(cfg, lines, durations, gap):
    """Pause after each line: base gap, + card_pause after a card, + card_pause before the reveal, a little more
    around skit lines. Returns the list of pauses (len = len(lines))."""
    vcfg = cfg["voice"]
    out = []
    for i, l in enumerate(lines):
        g = gap
        if l.get("card"):
            g += float(vcfg["card_pause"])
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if nxt and nxt.get("section") == "reveal" and l.get("section") != "reveal":
            g += float(vcfg["card_pause"])
        if nxt and (nxt.get("speaker", "narrator") != l.get("speaker", "narrator")):
            g += 0.08
        out.append(g if nxt else 0.0)
    return out


def fit_gap(cfg, lines, durations):
    """The base gap (inside min_gap..max_gap) that brings the total closest to the target. Speech is untouched."""
    v, vc = cfg["video"], cfg["voice"]
    lead, tail = 0.15, 0.9
    speech = sum(durations)

    def total(g):
        return lead + speech + sum(plan_gaps(cfg, lines, durations, g)) + tail
    lo_g, hi_g = float(vc["min_gap"]), float(vc["max_gap"])
    best = min(np.linspace(lo_g, hi_g, 34), key=lambda g: abs(total(g) - float(v["target_seconds"])))
    return float(best), total(best)


def envelope(samples, fps=FPS):
    hop = SR // fps
    n = int(np.ceil(len(samples) / hop))
    rms = np.array([np.sqrt(np.mean(samples[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    peak = float(np.percentile(rms, 95)) or 1.0
    return [round(float(min(1.0, x / peak)), 2) for x in rms]


def synthesize(cfg, script, project_dir, test=False):
    """-> timing dict. Writes voice.wav + timing.json. Raises DurationError if 40-50 s cannot be met by pauses.
    After the story, the main character says the follow line (config `brand`) over a 3-second outro."""
    lines = [l for l in script["lines"] if l["text"].strip()]
    brand = cfg["brand"]
    outro_line = {"speaker": "outro", "section": "outro", "card": False, "text": brand["outro_text"], "spoken": brand["outro_spoken"]}
    engine, rendered = render_lines(cfg, lines + [outro_line], test)
    outro_samples, _ = rendered.pop()
    durations = [len(s) / SR for s, _ in rendered]
    gap, total = fit_gap(cfg, lines, durations)
    lo, hi = float(cfg["video"]["min_seconds"]), float(cfg["video"]["max_seconds"])
    if not lo <= total <= hi:
        raise DurationError(total, lo, hi)
    gaps = plan_gaps(cfg, lines, durations, gap)
    t = 0.15
    pieces = [np.zeros(int(t * SR), dtype=np.float32)]
    out_lines = []
    for i, ((samples, spans), l) in enumerate(zip(rendered, lines)):
        words = l["text"].split()
        ws = [{"w": w, "s": round(t + a, 3), "e": round(t + b, 3)} for w, (a, b) in zip(words, spans)]
        entry = {"i": i, "speaker": l.get("speaker", "narrator"), "section": l.get("section"), "text": l["text"],
                 "card": bool(l.get("card")), "start": round(t, 3), "end": round(t + len(samples) / SR, 3), "words": ws}
        if entry["speaker"] != "narrator":
            entry["env"] = envelope(samples)
        out_lines.append(entry)
        pieces += [samples.astype(np.float32), np.zeros(int(gaps[i] * SR), dtype=np.float32)]
        t += len(samples) / SR + gaps[i]
    # outro: 0.35 s beat, the follow line, held to at least `brand.outro_seconds`
    t += 0.35
    pieces.append(np.zeros(int(0.35 * SR), dtype=np.float32))
    narration_end = round(t, 3)
    outro_len = max(float(brand["outro_seconds"]), len(outro_samples) / SR + 0.6)
    pieces += [outro_samples.astype(np.float32), np.zeros(int((outro_len - len(outro_samples) / SR) * SR), dtype=np.float32)]
    outro = {"start": narration_end, "speech_end": round(narration_end + len(outro_samples) / SR, 3),
             "end": round(narration_end + outro_len, 3), "text": brand["outro_text"], "env": envelope(outro_samples)}
    audio = np.concatenate(pieces)
    audio = audio / (float(np.max(np.abs(audio))) or 1.0) * 0.89
    tmp = project_dir / "voice24k.wav"
    sf.write(tmp, audio, SR)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-ar", "48000", "-ac", "1", str(project_dir / "voice.wav")], check=True)
    tmp.unlink()
    seconds = len(audio) / SR
    nwords = sum(len(l["words"]) for l in out_lines)
    speech_time = sum(l["end"] - l["start"] for l in out_lines)
    timing = {"duration": round(seconds, 3), "engine": engine, "gap": round(gap, 3), "lines": out_lines,
              "narration_end": narration_end, "outro": outro,
              "wpm": round(nwords / max(1e-6, speech_time) * 60)}
    write_json(project_dir / "timing.json", timing)
    log(f"voice: {seconds:.1f}s, {nwords} words, {timing['wpm']} wpm while speaking, base gap {gap:.2f}s ({engine})")
    return timing
