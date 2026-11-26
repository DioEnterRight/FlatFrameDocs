"""Deterministic script gates. A script that fails any of these is rewritten (once per round) or rejected.

Rules come from two places:
  * the brief: 0-2 s hook, 2-10 s suspense without the answer, build, escalation, revelation, satisfying ending;
  * the 2D Documentary Skill's Script DNA (.claude/skills/2d-documentory-skill/SKILL.md, Step 3): short sentences
    (median about 6 words, most under 12), one drawable picture per sentence, a deadpan skit with the punchline last
    and shortest, [CARD] lines, the close returning to the opening image, no summary / moral / "subscribe",
    and facts only from sources.
"""
import re
import statistics

from . import facts
from .common import content_words, words_of

SECTIONS = ("hook", "suspense", "build", "escalation", "reveal", "ending")
MIN_LINES = {"hook": 1, "suspense": 2, "build": 2, "escalation": 2, "reveal": 1, "ending": 1}
BANNED = re.compile(r"\b(subscribe|like and share|smash that|in this video|welcome back|hey guys|hi everyone|"
                    r"comment below|follow for more|link in bio)\b", re.I)
OPENERS = re.compile(r"^(hi|hey|hello|welcome|today|so,|did you know|let's|have you ever)\b", re.I)
MORAL = re.compile(r"\b(the lesson|the moral|in conclusion|to sum up|in summary)\b", re.I)


def spoken_lines(script):
    return [l for l in script.get("lines", []) if str(l.get("text", "")).strip()]


def word_count(script):
    return sum(len(words_of(l["text"])) for l in spoken_lines(script))


def check(cfg, script, claims):
    """-> list of problems (empty = passes)."""
    w = cfg["writing"]
    probs = []
    lines = spoken_lines(script)
    if not lines:
        return ["script has no lines"]
    by_id = {c["id"]: c for c in claims}
    payoff_ids = {c["id"] for c in claims if c.get("role") == "payoff"}

    # ---- structure, in order
    order = [l.get("section") for l in lines]
    for s in order:
        if s not in SECTIONS:
            probs.append(f"unknown section {s!r} (use {', '.join(SECTIONS)})")
            return probs
    idx = [SECTIONS.index(s) for s in order]
    if idx != sorted(idx):
        probs.append("sections are out of order (hook, suspense, build, escalation, reveal, ending)")
    for s, n in MIN_LINES.items():
        if order.count(s) < n:
            probs.append(f"section {s} needs at least {n} line(s)")
    if order.count("hook") > 1:
        probs.append("the hook must be ONE line")

    # ---- length
    n = word_count(script)
    if not int(w["words_min"]) <= n <= int(w["words_max"]):
        probs.append(f"{n} words; needs {w['words_min']}-{w['words_max']} for 40-50 seconds")

    # ---- hook: two seconds, straight in
    hook = lines[0]["text"].strip()
    if len(words_of(hook)) > int(w["hook_max_words"]):
        probs.append(f"hook is {len(words_of(hook))} words; max {w['hook_max_words']} (it must land in 2 seconds)")
    if OPENERS.search(hook):
        probs.append("hook starts with a greeting or filler; start with the strangest fact")
    if lines[0].get("speaker", "narrator") != "narrator":
        probs.append("the hook is spoken by the narrator")

    # ---- voice (skill: short sentences, fragments carry weight)
    lens = [len(words_of(x)) for l in lines for x in re.split(r"(?<=[.!?])\s+", l["text"]) if words_of(x)]
    if lens and statistics.median(lens) > 9:
        probs.append(f"median sentence is {statistics.median(lens):.0f} words; keep it near 6 (max 9)")
    long = [x for x in lens if x > int(w["max_sentence_words"])]
    if long:
        probs.append(f"{len(long)} sentence(s) longer than {w['max_sentence_words']} words")
    for l in lines:
        if BANNED.search(l["text"]):
            probs.append(f"channel talk / call to action is not allowed: {l['text'][:50]!r}")
        if MORAL.search(l["text"]):
            probs.append(f"no summary or moral (skill rule): {l['text'][:50]!r}")

    # ---- skit (skill: deadpan, ~4 words a line, punchline last and shortest)
    skit = [l for l in lines if l.get("speaker", "narrator") != "narrator"]
    if not 2 <= len(skit) <= 6:
        probs.append(f"needs one deadpan skit of 2-6 lines (has {len(skit)})")
    elif skit:
        if any(len(words_of(l["text"])) > 8 for l in skit):
            probs.append("skit lines must be short (8 words max, about 4)")
        if len(words_of(skit[-1]["text"])) > min(len(words_of(l["text"])) for l in skit[:-1]) + 1:
            probs.append("the skit's punchline (last line) should be its shortest")
        first = lines.index(skit[0])
        words_before = sum(len(words_of(l["text"])) for l in lines[:first])
        if words_before > 80:
            probs.append("the skit must start by about second 25 (within the first ~70 words)")
        if any(l.get("section") in ("hook", "reveal") for l in skit):
            probs.append("no skit in the hook or the reveal")

    # ---- cards
    cards = [l for l in lines if l.get("card")]
    if not 2 <= len(cards) <= 4:
        probs.append(f"mark 2-4 lines as [CARD] black text cards (has {len(cards)})")
    if any(len(words_of(l["text"])) > 9 for l in cards):
        probs.append("a [CARD] line must be 9 words or fewer (one unwrapped line on screen)")

    # ---- no early answer: payoff claims are only cited from the reveal on
    reveal_at = order.index("reveal") if "reveal" in order else len(lines)
    for k, l in enumerate(lines[:reveal_at]):
        if set(l.get("claims") or []) & payoff_ids:
            probs.append(f"line {k + 1} gives away the answer before the reveal")
    words_to_reveal = sum(len(words_of(l["text"])) for l in lines[:reveal_at])
    if words_to_reveal < 0.55 * n:
        probs.append("the reveal comes too early (keep the answer for the last third)")
    if words_to_reveal > 0.85 * n:
        probs.append("the reveal comes too late (the answer needs time to land)")

    # ---- ending returns to the opening image
    ending = " ".join(l["text"] for l in lines if l.get("section") == "ending")
    hero = str(script.get("hero_object", ""))
    if not (content_words(ending) & (content_words(hook) | content_words(hero))):
        probs.append("the ending must call back to the opening image (reuse a word from the hook or the hero object)")

    # ---- facts: every number and name is backed by the claims the line cites
    for k, l in enumerate(lines):
        ids = [c for c in (l.get("claims") or []) if c in by_id]
        bad_ids = [c for c in (l.get("claims") or []) if c not in by_id]
        if bad_ids:
            probs.append(f"line {k + 1} cites unknown claim ids {bad_ids}")
        backing = " ".join(by_id[c]["text"] + " " + " ".join(s["quote"] for s in by_id[c]["support"]) for c in ids)
        v = facts.script_violations(l["text"], backing, allowed_names=content_words(script.get("title", "")))
        if v:
            probs.append(f"line {k + 1} has facts no cited claim supports: {', '.join(v)}")
    cited = {c for l in lines for c in (l.get("claims") or [])}
    if not cited & payoff_ids:
        probs.append("the reveal must cite the verified payoff claim")

    # ---- title (skill: 5-10 words, concrete subject, no colon/question mark, honest)
    t = str(script.get("title", "")).strip()
    tw = len(words_of(t))
    if not 4 <= tw <= 10 or ":" in t or "?" in t or len(t) > 70:
        probs.append("title: 4-10 words, max 70 characters, no colon, no question mark")
    claim_words = set().union(*(content_words(c["text"]) for c in claims)) if claims else set()
    if len(content_words(t) & claim_words) < 1:
        probs.append("title must be about the verified story (it shares no word with the claims)")
    return probs
