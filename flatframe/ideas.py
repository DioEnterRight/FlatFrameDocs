"""IDEAS: pitch many documentary concepts, throw out repeats, have a DIFFERENT model score them, keep the best.

Selection is not "whatever the model scored highest":
  * deterministic filters first: duplicates of past videos (word overlap and same Wikipedia article), blocked recent
    categories, repeated hook patterns, hooks too long for two seconds, greetings / channel talk;
  * the critic (never the ideator's model) scores the 8 criteria from config `ideas.weights`; `variety` is recomputed
    from history instead of trusted;
  * the shortlist then has to survive RESEARCH (research.py): an idea that cannot be verified is rejected however
    exciting it sounded.
Good ideas that were not used are banked in data/ideas.json for later runs.
"""
import datetime as dt
import json
import re

from .common import DATA, content_words, fill, jaccard, log, prompt, read_json, write_json

BANK = DATA / "ideas.json"
CRITERIA = ("curiosity", "uniqueness", "hook", "suspense", "visual", "payoff", "reliability", "variety")
PATTERNS = ("impossible situation", "contradiction", "unexpected consequence", "bizarre fact", "question", "strange event")
BANNED_OPENERS = re.compile(r"^(hi|hey|hello|welcome|today|in this video|did you know|let's|lets|have you ever)\b", re.I)


def past(history):
    vids = [v for v in history["videos"] if v.get("title")]
    return {
        "texts": [content_words(v.get("title", "") + " " + v.get("question", "")) for v in vids],
        "articles": {str(v.get("article", "")).lower() for v in vids if v.get("article")},
        "categories": [v.get("category") for v in vids[-10:]],
        "patterns": [v.get("hook_pattern") for v in vids[-6:]],
        "titles": [v.get("title") for v in vids[-40:]],
    }


def filter_reason(cfg, idea, p, bank_texts=()):
    ic, wc = cfg["ideas"], cfg["writing"]
    for k in ("title", "question", "hook", "payoff", "category", "wikipedia_title"):
        if not str(idea.get(k, "")).strip():
            return f"missing {k}"
    hook = idea["hook"].strip()
    if len(hook.split()) > int(wc["hook_max_words"]):
        return f"hook has {len(hook.split())} words (max {wc['hook_max_words']})"
    if BANNED_OPENERS.search(hook) or "subscribe" in hook.lower():
        return "hook opens with a greeting / filler"
    words = content_words(idea["title"] + " " + idea["question"])
    thr = float(ic["similarity_threshold"])
    for old in list(p["texts"]) + list(bank_texts):
        if jaccard(words, old) >= thr:
            return "too similar to an earlier video"
    if idea["wikipedia_title"].lower() in p["articles"]:
        return "same Wikipedia article as an earlier video"
    blocked = [c for c in p["categories"][-int(ic["recent_categories_blocked"]):] if c]
    if idea["category"] in blocked:
        return "category used by one of the last videos"
    return None


def variety_score(idea, p):
    s = 10.0
    if idea.get("hook_pattern") in p["patterns"][-2:]:
        s -= 3
    if idea.get("category") in p["categories"][-4:]:
        s -= 2
    near = max((jaccard(content_words(idea["title"] + " " + idea["question"]), t) for t in p["texts"]), default=0)
    return max(1.0, s - near * 10)


def weighted(cfg, scores):
    w = cfg["ideas"]["weights"]
    return round(sum(float(scores.get(k, 0)) * w[k] for k in CRITERIA) / sum(w.values()), 2)


def generate(cfg, session, history, avoid_titles):
    ic = cfg["ideas"]
    user = fill(prompt("ideas.md"), n=str(ic["candidates"]), categories="\n".join(f"- {c}" for c in ic["categories"]),
                avoid="\n".join(f"- {t}" for t in avoid_titles[-40:]) or "- (none yet)",
                patterns=", ".join(PATTERNS), hook_words=str(cfg["writing"]["hook_max_words"]))
    obj, model = session.json("ideator", prompt("ideas_system.md"), user, max_tokens=6000)
    ideas = [i for i in (obj.get("ideas") or []) if isinstance(i, dict)]
    for i in ideas:
        i["pitched_by"] = model
    log(f"ideas: {len(ideas)} pitched by {model}")
    return ideas, model


def score(cfg, session, ideas, avoid_model):
    if not ideas:
        return []
    listing = [{"n": k, **{f: i.get(f) for f in ("title", "question", "hook", "payoff", "category", "why_visual")}}
               for k, i in enumerate(ideas)]
    obj, model = session.json("critic", prompt("critic_system.md"),
                              fill(prompt("idea_critic.md"), ideas=json.dumps(listing, ensure_ascii=False, indent=1)),
                              max_tokens=5000, avoid=(avoid_model,))
    by_n = {int(s.get("n", -1)): s for s in obj.get("scores") or [] if isinstance(s, dict)}
    out = []
    for k, i in enumerate(ideas):
        s = by_n.get(k)
        if not s:
            continue
        i["scores"] = {c: max(0.0, min(10.0, float(s.get(c, 0) or 0))) for c in CRITERIA}
        i["critic_note"] = str(s.get("note", ""))[:300]
        i["scored_by"] = model
        out.append(i)
    return out


def shortlist(cfg, session, history):
    """-> ideas ready for research, best first (banked ideas are re-checked and reused before pitching new ones)."""
    p = past(history)
    bank = read_json(BANK, {"bank": []})
    fresh_cut = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=21)).isoformat()
    banked = [i for i in bank["bank"] if i.get("banked_at", "") >= fresh_cut and not filter_reason(cfg, i, p)]
    pool, model = [], None
    if len(banked) < int(cfg["ideas"]["research_attempts"]):
        raw, model = generate(cfg, session, history, p["titles"] + [i["title"] for i in banked])
        seen = []
        for i in raw:
            why = filter_reason(cfg, i, p, bank_texts=seen)
            if why:
                log(f"idea dropped: {i.get('title', '?')!r}: {why}")
                continue
            seen.append(content_words(i["title"] + " " + i["question"]))
            pool.append(i)
        pool = score(cfg, session, pool, model)
    for i in pool + banked:
        i["scores"]["variety"] = variety_score(i, p)
        i["score"] = weighted(cfg, i["scores"])
    ranked = sorted((i for i in pool + banked if i["score"] >= float(cfg["ideas"]["min_score"])), key=lambda i: -i["score"])
    for i in ranked[:6]:
        log(f"idea {i['score']:.1f}: {i['title']} [{i['category']}]")
    return ranked


def bank_unused(ranked, used_title):
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    bank = read_json(BANK, {"bank": []})
    titles = {i["title"] for i in bank["bank"]}
    for i in ranked:
        if i["title"] != used_title and i["title"] not in titles and not i.get("rejected"):
            bank["bank"].append({**i, "banked_at": i.get("banked_at", now)})
    bank["bank"] = [i for i in bank["bank"] if i["title"] != used_title][-40:]
    write_json(BANK, bank)


def reject_banked(title, why):
    bank = read_json(BANK, {"bank": []})
    bank["bank"] = [i for i in bank["bank"] if i["title"] != title]
    bank.setdefault("rejected", []).append({"title": title, "why": why[:200]})
    bank["rejected"] = bank["rejected"][-60:]
    write_json(BANK, bank)
