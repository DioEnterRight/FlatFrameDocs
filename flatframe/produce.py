"""MAKE: one documentary from idea to a QA-passed video in the Releases queue.

  python -m flatframe.produce --release          real run (Make workflow)
  python -m flatframe.produce --test [--sample emu-war]   no keys, no queue: renders a bundled, pre-researched sample
  python -m flatframe.produce --resume <id> [--release]   continue / redo a project from its saved stages

Stages (each saved in out/<id>/ so one documentary can be reproduced, debugged or revised without regenerating
everything): idea.json -> research.json -> script.json -> voice.wav + timing.json -> board.json + plan.json ->
mix.wav -> final.mp4 -> qa.json + sheet.jpg -> meta.json. Delete a stage file to redo it on --resume.

Anything that fails a gate (research, script, duration, storyboard, QA) rejects the topic; the next shortlisted idea
is tried, and if none survives the slot is simply skipped. Quality over schedule.
"""
import argparse
import shutil
import sys

from . import director, ideas, llm, metadata, qa, render, research, schedule, sound, voice, writer
from .common import (OUT, SAMPLES, StageError, load_config, load_history, log, now_ist, read_json, save_history,
                     slugify, stable_seed, write_json)


def _cached(P, name, fn):
    path = P / name
    if path.exists():
        log(f"stage {name}: reusing saved result")
        return read_json(path, None)
    obj = fn()
    write_json(path, obj)
    return obj


def voice_stage(cfg, session, idea, claims, script, P, test):
    try:
        return voice.synthesize(cfg, script, P, test=test)
    except voice.DurationError as e:
        if session is None:
            raise StageError(str(e)) from None
        target = cfg["video"]["target_seconds"]
        log(f"{e}; asking the writer for a {'shorter' if e.seconds > target else 'longer'} version", "WARN")
        delta = round((e.seconds - target) * 2.6)
        fix = [f"The narration runs {e.seconds:.1f} s; it must be about {target} s. "
               f"{'Cut' if delta > 0 else 'Add'} about {abs(delta)} words without losing the hook, the skit or the reveal."]
        draft = writer._draft(cfg, session, idea, claims, fix, script)
        from . import script_check
        probs = script_check.check(cfg, draft, claims)
        if probs:
            raise StageError("duration rewrite broke the script rules: " + "; ".join(probs[:3])) from None
        write_json(P / "script.json", {"script": draft, "review": {"note": "duration rewrite"}})
        try:
            return voice.synthesize(cfg, draft, P, test=test)
        except voice.DurationError as e2:
            raise StageError(str(e2)) from None


def build_video(cfg, session, idea, rec, script, P, history, seed, test=False, board_override=None):
    """voice -> storyboard -> mix -> render -> QA. Returns (qa result, timing, plan)."""
    claims = research.verified_claims(rec)
    timing = read_json(P / "timing.json", None) if (P / "voice.wav").exists() else None
    if timing is None:
        timing = voice_stage(cfg, session, idea, claims, script, P, test)
        script = read_json(P / "script.json", {}).get("script", script)
    if board_override is not None:
        from . import beats
        plan, report = beats.compile_plan(cfg, script, timing, board_override, claims, seed, P.name)
        board = board_override
    else:
        plan, board, report = director.direct(cfg, session, script, timing, claims, history, seed, P.name)
    write_json(P / "board.json", board)
    write_json(P / "storyboard_report.json", report)
    if report["violations"]:
        raise StageError("storyboard rules still fail: " + "; ".join(report["violations"][:3]))
    mids = [s["from"] + s["dur"] // 2 for s in plan["shots"]]
    stills = render.stills(plan, P, mids)
    render.contact_sheet(stills, P / "storyboard.jpg", cols=6, labels=[f"{m / 30:.1f}s {s['kind']}" for m, s in zip(mids, plan["shots"])])
    mix_report = sound.mix(cfg, plan, timing, P, seed)
    final = render.video(cfg, plan, P)
    result = qa.check(cfg, plan, timing, mix_report, final, P, report["violations"], qa.make_judge(session))
    return result, timing, plan


def produce_test(cfg, sample):
    """Test mode: the bundled sample (real research, a written script and storyboard) through the real engine."""
    src = SAMPLES / sample
    if not src.exists():
        sys.exit(f"no sample {sample!r} in samples/")
    P = OUT / f"test-{now_ist():%Y%m%d-%H%M%S}-{sample}"
    P.mkdir(parents=True)
    for name in ("research.json", "script.json", "idea.json"):
        shutil.copy(src / name, P / name)
    rec, sc, idea = read_json(P / "research.json", {}), read_json(P / "script.json", {}), read_json(P / "idea.json", {})
    from . import script_check
    probs = script_check.check(cfg, sc["script"], research.verified_claims(rec))
    if probs:
        sys.exit("sample script fails the gates: " + "; ".join(probs))
    board = read_json(src / "board.json", None)
    result, timing, plan = build_video(cfg, None, idea, rec, sc["script"], P, load_history(), 4242, test=True, board_override=board)
    write_json(P / "meta.json", metadata.build(cfg, idea, sc["script"], rec, result))
    log(f"TEST video: {P / 'final.mp4'} (QA {'passed' if result['passed'] else 'FAILED'}, voice: {timing['engine']})")
    return 0 if result["passed"] else 1


def mark_ready(P, idea, meta, rec, result, session, script, plan):
    """Write ready.json: the queue step (flatframe.queue, the only step holding a write token) turns it into a
    GitHub Release + a history entry. Keeping the token out of this step means no model/TTS/render dependency
    ever runs next to a write-capable credential."""
    write_json(P / "ready.json", {
        "id": P.name, "tag": "doc-" + P.name, "created": now_ist().isoformat(timespec="minutes"), "status": "queued",
        "title": meta["title"], "question": idea["question"], "category": idea["category"],
        "hook_pattern": idea.get("hook_pattern"), "article": rec["article"]["title"], "hero": plan["hero"]["kind"],
        "locations": sorted({s["set"]["kind"] for s in plan["shots"] if s.get("set")}),
        "qa": {"passed": result["passed"], "score": result["score"]}, "verified_claims": rec["verified_count"],
        "models": session.report() if session else {}, "words": sum(len(l["text"].split()) for l in script["lines"]),
    })


def produce_real(cfg, args):
    history = load_history()
    now = now_ist()
    if not args.resume and schedule.to_make(cfg, len(schedule.ready_videos(history)), now) == 0 and not args.force:
        log("Enough videos are ready for the next slots; nothing to make.")
        return 0
    seed = stable_seed(now.isoformat())
    try:
        session = llm.Session(cfg, seed)
    except llm.LLMUnavailable as e:
        print(f"::warning::No free model available, no video made this run: {e}")
        return 0
    if args.resume:
        P = OUT / args.resume
        idea = read_json(P / "idea.json", None)
        if idea is None:
            sys.exit(f"nothing to resume in {P}")
        candidates = [idea]
    else:
        try:
            candidates = ideas.shortlist(cfg, session, history)[: int(cfg["ideas"]["research_attempts"])]
        except llm.LLMUnavailable as e:
            print(f"::warning::Idea stage stopped: {e}")
            return 0
    for idea in candidates:
        P = OUT / (args.resume or f"{now:%Y%m%d-%H%M%S}-{slugify(idea['title'], 32)}")
        P.mkdir(parents=True, exist_ok=True)
        write_json(P / "idea.json", idea)
        try:
            rec = _cached(P, "research.json", lambda: research.research(cfg, session, idea))
            if rec["verdict"] != "accepted":
                raise StageError(rec["verdict"])
            claims = research.verified_claims(rec)
            sc = _cached(P, "script.json", lambda: dict(zip(("script", "review"), writer.write(cfg, session, idea, claims))))
            result, timing, plan = build_video(cfg, session, idea, rec, sc["script"], P, history, seed)
            if not result["passed"]:
                raise StageError("quality control failed: " + ", ".join(c["check"] for c in result["checks"] if not c["ok"]))
            script = read_json(P / "script.json", {})["script"]
            meta = metadata.build(cfg, idea, script, rec, result)
            write_json(P / "meta.json", meta)
            write_json(P / "models.json", session.report())
            if args.release:
                mark_ready(P, idea, meta, rec, result, session, script, plan)
                ideas.bank_unused(candidates, idea["title"])
            log(f"DONE: {meta['title']} ({P.name})")
            return 0
        except StageError as e:
            log(f"topic rejected: {idea['title']}: {e}", "WARN")
            ideas.reject_banked(idea["title"], str(e))
            history.setdefault("rejected", []).append({"title": idea["title"], "why": str(e)[:300], "at": now.isoformat(timespec="minutes")})
            history["rejected"] = history["rejected"][-100:]
            save_history(history)
        except llm.LLMUnavailable as e:
            print(f"::warning::Free models ran out mid-video ({e}); stopping without publishing. Saved stages: {P}")
            return 0
        except Exception as e:  # noqa: BLE001  (a bug or bad model output on one topic: log it, try the next topic)
            import traceback
            log(f"topic failed with an error: {idea['title']}: {e!r}\n{traceback.format_exc()[-1500:]}", "ERROR")
            history.setdefault("rejected", []).append({"title": idea["title"], "why": f"error: {e!r}"[:300], "at": now.isoformat(timespec="minutes")})
            history["rejected"] = history["rejected"][-100:]
            save_history(history)
    print("::warning::No topic survived research and quality control this run; the slot is skipped (by design).")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--sample", default="emu-war")
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--resume")
    ap.add_argument("--force", action="store_true", help="make a video even if the queue is full (never affects posting)")
    args = ap.parse_args(argv)
    cfg = load_config()
    if args.test:
        return produce_test(cfg, args.sample)
    if cfg.get("paused"):
        log("Paused in config.yaml: nothing made.")
        return 0
    return produce_real(cfg, args)


if __name__ == "__main__":
    sys.exit(main())

