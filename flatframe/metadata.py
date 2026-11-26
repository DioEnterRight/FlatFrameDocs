"""Title, description, hashtags and captions. Honest by construction: the title is the checked script title, the
description is built from verified claims and lists the sources, and the AI-voice disclosure is always present."""
import re

from .common import content_words

DISCLOSURE = "Animated with code. Narration is a synthetic (text-to-speech) voice. Facts checked against the sources below."


def hashtags(idea, n=5):
    tags = ["#documentary", "#history" if "histor" in idea["category"] else "#didyouknow"]
    for w in sorted(content_words(idea["title"]), key=len, reverse=True):
        t = "#" + re.sub(r"[^a-z0-9]", "", w.lower())
        if len(t) > 3 and t not in tags:
            tags.append(t)
        if len(tags) >= n - 1:
            break
    tags.append("#shorts")
    return tags[:n]


def build(cfg, idea, script, research_record, qa):
    claims = [c for c in research_record["claims"] if c["status"] == "verified"]
    payoff = next((c for c in claims if c["role"] == "payoff"), claims[-1] if claims else None)
    hook = next((c for c in claims if c["role"] in ("hook", "mystery")), claims[0] if claims else None)
    used = {s["source"] for c in claims for s in c["support"]}
    srcs = [s for s in research_record["sources"] if s["id"] in used and s["ok"]][:6]
    summary = " ".join(x["text"].rstrip(".") + "." for x in (hook, payoff) if x)
    title = script["title"].strip()
    tags = hashtags(idea)
    description = (f"{idea['question']}\n\n{summary}\n\nSources:\n" + "\n".join(f"- {s['url']}" for s in srcs) +
                   f"\n- Background: {research_record['article']['url']}\n\n{DISCLOSURE}")
    caption = f"{title}\n\n{idea['question']}\n\n{' '.join(tags)}\n\n{DISCLOSURE}"
    return {"title": title, "description": description[:4800], "hashtags": tags, "caption": caption[:2150],
            "language": cfg["channel"]["language"], "synthetic_youtube": bool(cfg["disclosure"]["youtube_synthetic"]),
            "ai_label_instagram": bool(cfg["disclosure"]["instagram_ai_label"]), "qa_score": qa["score"]}
