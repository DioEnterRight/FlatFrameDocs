"""WRITER + CRITIC: a 40-50 s documentary script built only from verified claims.

  draft (writer) -> deterministic gates (script_check) + critic (a different model) -> rewrite with both sets of
  fixes -> ... (writing.rewrite_rounds). The best passing draft wins; if none passes the topic is rejected.
"""
import json

from . import lessons, script_check
from .common import StageError, fill, log, prompt


def _claims_for_prompt(claims):
    return [{"id": c["id"], "role": c["role"], "fact": c["text"]} for c in claims]


def _draft(cfg, session, idea, claims, fixes=None, previous=None, avoid=()):
    w = cfg["writing"]
    user = fill(prompt("script.md"), title=idea["title"], question=idea["question"], hook=idea["hook"],
                payoff=idea["payoff"], claims=json.dumps(_claims_for_prompt(claims), ensure_ascii=False, indent=1),
                words_min=str(w["words_min"]), words_max=str(w["words_max"]), hook_words=str(w["hook_max_words"]),
                metaphors=json.dumps(idea.get("visual_metaphors") or [], ensure_ascii=False))
    if fixes:
        user += ("\n\n# REWRITE\nYour previous draft:\n" + json.dumps(previous, ensure_ascii=False, indent=1) +
                 "\n\nFix ALL of these problems, keep what works:\n" + "\n".join(f"- {f}" for f in fixes))
    obj, model = session.json("writer", lessons.system("writer_system.md", "writer"), user, max_tokens=5000, avoid=avoid)
    obj["written_by"] = model
    for l in obj.get("lines", []):
        l.setdefault("speaker", "narrator")
        l.setdefault("claims", [])
        l["card"] = bool(l.get("card"))
    return obj


def tidy(script, claims):
    """Mechanical fixes that change no fact: section order, one hook line, unknown claim ids dropped, 2-4 short [CARD]
    lines. Everything with meaning (facts, skit, reveal) stays with the writer and the rules."""
    order = list(script_check.SECTIONS)
    lines = [l for l in script.get("lines", []) if str(l.get("text", "")).strip()]
    for l in lines:
        if l.get("section") not in order:
            l["section"] = "build"
    lines.sort(key=lambda l: order.index(l["section"]))          # stable: keeps the writer's order inside a section
    for l in [l for l in lines if l["section"] == "hook"][1:]:
        l["section"] = "suspense"
    known = {c["id"] for c in claims}
    for l in lines:
        l["claims"] = [c for c in l.get("claims") or [] if c in known]
        words = len(str(l["text"]).split())
        if l.get("card") and (words > 9 or l.get("speaker", "narrator") != "narrator" or l["section"] == "hook"):
            l["card"] = False
    cards = [l for l in lines if l.get("card")]
    for l in cards[4:]:
        l["card"] = False
    if len(cards) < 2:
        spare = sorted((l for l in lines if not l.get("card") and l.get("speaker", "narrator") == "narrator"
                        and l["section"] in ("suspense", "build", "escalation") and len(str(l["text"]).split()) <= 9),
                       key=lambda l: len(str(l["text"]).split()))
        for l in spare[: 2 - len(cards)]:
            l["card"] = True
    script["lines"] = lines
    return script


def _critique(cfg, session, script, claims, avoid):
    obj, model = session.json("critic", lessons.system("critic_system.md", "script_critic"),
                              fill(prompt("script_critic.md"), script=json.dumps(script, ensure_ascii=False, indent=1),
                                   claims=json.dumps(_claims_for_prompt(claims), ensure_ascii=False, indent=1)),
                              max_tokens=3000, avoid=avoid)
    keys = ("hook", "suspense", "progression", "clarity", "payoff", "ending", "visual")
    scores = {k: max(0.0, min(10.0, float(obj.get("scores", {}).get(k, 0) or 0))) for k in keys}
    overall = round(sum(scores.values()) / len(keys), 2)
    if obj.get("accuracy_flags"):
        overall = min(overall, 5.0)
    return {"scores": scores, "overall": overall, "fixes": [str(f) for f in obj.get("fixes") or []][:8],
            "accuracy_flags": obj.get("accuracy_flags") or [], "by": model}


def write(cfg, session, idea, claims):
    """-> (script, review) or raises StageError."""
    w = cfg["writing"]
    best, best_key, draft, fixes = None, None, None, None
    for rnd in range(int(w["rewrite_rounds"]) + 1):
        draft = tidy(_draft(cfg, session, idea, claims, fixes, draft), claims)
        probs = script_check.check(cfg, draft, claims)
        review = _critique(cfg, session, draft, claims, avoid=(draft["written_by"],))
        log(f"script round {rnd + 1}: {script_check.word_count(draft)} words, critic {review['overall']} "
            f"({review['by']}), {len(probs)} rule problem(s)")
        for p in probs[:6]:
            log(f"  rule: {p}", "WARN")
        key = (not probs, review["overall"])
        if best is None or key > best_key:
            best, best_key = (draft, review, probs), key
        if not probs and review["overall"] >= float(w["good_enough"]):
            break
        fixes = probs + review["fixes"] + [f"ACCURACY: {a}" for a in review["accuracy_flags"]]
    draft, review, probs = best
    review["rule_problems"] = probs
    if probs:
        raise StageError("script failed the rules after rewrites: " + "; ".join(probs[:4]))
    if review["overall"] < float(cfg["quality"]["min_script_score"]):
        raise StageError(f"script scored {review['overall']} (< {cfg['quality']['min_script_score']}) after rewrites")
    return draft, review
