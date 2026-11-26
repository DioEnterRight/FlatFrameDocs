"""RESEARCH: turn one documentary idea into a list of verified claims, or reject the topic.

  1. Wikipedia is the DISCOVERY source: the article text tells us what to check and its citations tell us where.
  2. A free model (role `research`) lists atomic claims, each with the exact Wikipedia sentence it came from.
     A claim whose quoted sentence is not literally in the article, or whose numbers are not in that sentence, is
     dropped: the model cannot add facts.
  3. The cited pages are fetched (HTML or PDF). A claim is VERIFIED only when at least `min_sources_per_claim`
     independent non-Wikipedia sites carry it: either found deterministically (all numbers + most key terms in one
     sentence) or quoted by the model AND that quote found literally in the page text.
  4. Sources that state a different number for the same thing mark the claim as disputed; disputed claims are not used.
  5. The topic is rejected unless enough claims are verified, including one for the hook and one for the payoff.

Output: research.json (sources, claims with supporting quotes, rejected claims, conflicts, verdict). The writer only
ever sees verified claims.
"""
import datetime as dt
import json

from . import facts, sources
from .common import StageError, fill, log, prompt

ROLES = ("hook", "mystery", "background", "escalation", "payoff", "detail")


def _trim_article(text, limit=16000):
    if len(text) <= limit:
        return text
    cut = text.find("\n== See also")
    return (text[:cut] if cut > 0 else text)[:limit]


def candidate_passages(claim, src_text, n=3):
    terms = facts.key_terms(claim)
    scored = []
    for s in facts.windows(src_text):
        shared = len(terms & facts.key_terms(s))
        if terms and shared / len(terms) >= 0.34:
            scored.append((shared, s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:n]]


def extract_claims(session, idea, page):
    sys_p = prompt("research_system.md")
    user = fill(prompt("research_claims.md"), title=idea["title"], question=idea["question"],
                article_title=page["title"], article=_trim_article(page["text"]))
    obj, model = session.json("research", sys_p, user, max_tokens=6000)
    kept, dropped = [], []
    for i, c in enumerate(obj.get("claims") or []):
        text, quote = str(c.get("text", "")).strip(), str(c.get("wiki_quote", "")).strip()
        role = c.get("role") if c.get("role") in ROLES else "detail"
        if not text:
            continue
        if not facts.quote_in(quote, page["text"]):
            dropped.append({"text": text, "why": "quoted Wikipedia sentence not found in the article"})
            continue
        if not facts.numbers(text) <= facts.numbers(quote):
            dropped.append({"text": text, "why": "claim has numbers its Wikipedia sentence does not"})
            continue
        kept.append({"id": f"C{len(kept) + 1}", "text": text, "role": role, "wiki_quote": quote, "support": [],
                     "conflicts": []})
    log(f"research: {len(kept)} claims from the article ({len(dropped)} dropped) by {model}")
    return kept, dropped, model


def corroborate(session, claims, srcs, need):
    ok_srcs = [s for s in srcs if s["ok"]]
    for c in claims:
        for s in ok_srcs:
            if any(x["site"] == s["site"] for x in c["support"]):
                continue
            hit = facts.best_support(c["text"], s["text"])
            if hit:
                c["support"].append({"source": s["id"], "site": s["site"], "quote": hit, "how": "matched"})
    # second pass: the model may point at passages the strict matcher missed; every quote is re-checked literally
    weak = [c for c in claims if len({x["site"] for x in c["support"]}) < need]
    if weak and session is not None:
        items = []
        for c in weak:
            passages = []
            for s in ok_srcs:
                if any(x["site"] == s["site"] for x in c["support"]):
                    continue
                for p in candidate_passages(c["text"], s["text"]):
                    passages.append({"source": s["id"], "passage": p})
            if passages:
                items.append({"claim_id": c["id"], "claim": c["text"], "passages": passages[:8]})
        # small batches: the free models that answer are often small, and long lists get half-answered
        for k in range(0, len(items), VERIFY_BATCH):
            if not _verify_batch(session, claims, ok_srcs, items[k:k + VERIFY_BATCH]):
                break
    for c in claims:
        for s in ok_srcs:
            c["conflicts"] += [{"source": s["id"], "site": s["site"], "sentence": x} for x in facts.conflicting(c["text"], s["text"])]
        sites = {x["site"] for x in c["support"]}
        c["sites"] = sorted(sites)
        c["status"] = ("disputed" if c["conflicts"] and len(sites) < need + 1 else
                       "verified" if len(sites) >= need else "unverified")
    return claims


VERIFY_BATCH = 4


def _verify_batch(session, claims, ok_srcs, items):
    """One model call for a few claims; every quote it returns is re-checked against the real source text.
    -> False when the models are out (stop asking), True otherwise."""
    try:
        obj, model = session.json("research", prompt("research_system.md"),
                                  fill(prompt("research_verify.md"), items=json.dumps(items, ensure_ascii=False, indent=1)),
                                  max_tokens=3000)
    except Exception as e:  # noqa: BLE001  (the strict matcher result stands on its own)
        log(f"research: model verification skipped ({str(e)[:150]})", "WARN")
        return False
    by_id = {c["id"]: c for c in claims}
    src_by_id = {s["id"]: s for s in ok_srcs}
    sent = {(it["claim_id"], p["source"]): [] for it in items for p in it["passages"]}
    for it in items:
        for p in it["passages"]:
            sent[(it["claim_id"], p["source"])].append(p["passage"])
    for v in obj.get("verdicts") or []:
        c, s = by_id.get(v.get("claim_id")), src_by_id.get(v.get("source"))
        q = str(v.get("quote", ""))
        if not (c and s and v.get("supports") is True):
            continue
        if any(x["site"] == s["site"] for x in c["support"]):
            continue
        # models retype quotes with tiny slips: when it is (almost) a passage we showed, keep the source's own
        # words, never the model's
        if not facts.quote_in(q, s["text"]):
            shown = [p for p in sent.get((c["id"], s["id"]), []) if facts.near_copy(q, p)]
            if not shown:
                continue
            q = shown[0]
        nums_ok = facts.numbers(c["text"]) <= facts.numbers(q)
        overlap = len(facts.key_terms(c["text"]) & facts.key_terms(q)) / max(1, len(facts.key_terms(c["text"])))
        if nums_ok and overlap >= 0.34:
            c["support"].append({"source": s["id"], "site": s["site"], "quote": q, "how": f"quoted by {model}, checked"})
    return True


def research(cfg, session, idea, web=None):
    rc = cfg["research"]
    web = web or sources.Web(cfg)
    try:
        page = web.wiki_page(idea["wikipedia_title"])
        if page is None:
            hits = web.wiki_search(idea.get("search") or idea["title"])
            page = web.wiki_page(hits[0]) if hits else None
    except (OSError, ValueError) as e:   # requests' errors are OSErrors; a bad JSON reply is a ValueError
        raise StageError(f"Wikipedia did not answer for '{idea['title']}': {str(e)[:120]}") from None
    if page is None or len(page["text"]) < 2500:
        raise StageError(f"no substantial Wikipedia article for '{idea['title']}'")
    log(f"research: '{page['title']}' ({len(page['text']):,} chars, {len(page['links'])} cited links)")
    claims, dropped, model = extract_claims(session, idea, page)
    srcs = sources.fetch_sources(web, page["links"], int(rc["max_source_fetches"]))
    need = int(rc["min_sources_per_claim"])
    claims = corroborate(session, claims, srcs, need)
    verified = [c for c in claims if c["status"] == "verified"]
    roles = {c["role"] for c in verified}
    log("research: sites per claim " + " ".join(f"{c['id']}:{len(c['sites'])}{'!' if c['status'] == 'disputed' else ''}" for c in claims)
        + f" (need {need}; {len([s for s in srcs if s['ok']])} sources read)")
    record = {
        "idea": idea, "question": idea["question"],
        "article": {"title": page["title"], "url": page["url"], "revision": page.get("lastrevid"), "role": "discovery only"},
        "retrieved": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "rule": f"a claim is verified when {need}+ independent non-Wikipedia sites carry it in their own text",
        "sources": [{k: s[k] for k in ("id", "url", "site", "ok")} | ({"error": s["error"]} if not s["ok"] else {"chars": len(s["text"])})
                    for s in srcs],
        "claims": claims, "dropped": dropped, "extracted_by": model,
        "verified_count": len(verified),
    }
    problems = []
    if len(verified) < int(rc["min_verified_claims"]):
        problems.append(f"only {len(verified)} verified claims (need {rc['min_verified_claims']})")
    if "payoff" not in roles:
        problems.append("the payoff (the answer) is not verified")
    if not roles & {"hook", "mystery"}:
        problems.append("nothing verified for the hook")
    record["verdict"] = "rejected: " + "; ".join(problems) if problems else "accepted"
    log(f"research: {len(verified)} verified of {len(claims)}; {record['verdict']}")
    return record


def verified_claims(record):
    return [c for c in record["claims"] if c["status"] == "verified"]
