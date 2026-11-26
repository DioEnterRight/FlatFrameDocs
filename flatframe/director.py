"""DIRECTOR: the storyboard. A free model plans cast, locations, a hero object and one beat per script line using
the engine catalog and the 2D Documentary Skill's visual rules (prompts/director.md). beats.py then compiles and
repairs it. If the plan still breaks rules, the director gets one revision with the exact violations. With no model
available, the offline director (keywords -> sets and props) produces a plain but valid storyboard.
"""
import json

from . import beats, catalog as K, lessons
from .common import fill, log, prompt
from .llm import LLMUnavailable


def _lines_for_prompt(timing):
    out = []
    for i, l in enumerate(timing["lines"]):
        out.append({"line": i + 1, "section": l["section"], "speaker": l["speaker"], "card": l["card"],
                    "start": round(l["start"], 2), "end": round(l["end"], 2), "text": l["text"]})
    return out


def catalog_text():
    return json.dumps({"set_kinds": K.SET_KINDS, "grades": K.GRADES, "wall_patterns": K.WALL_PATTERNS,
                       "floor_patterns": K.FLOOR_PATTERNS, "props": K.PROPS, "creatures": K.CREATURES, "hair": K.HAIR,
                       "outfits": K.OUTFITS, "skins": K.SKINS, "expressions": K.EXPRS, "poses": K.POSES,
                       "shots": K.SHOTS, "camera_moves": K.MOVES, "camera_timings": K.TIMINGS, "framings": K.FRAMINGS,
                       "builds": K.BUILDS, "entries": K.ENTRIES, "texts": ["strip", "stamp", "calendar"],
                       "effects_by_tone": K.FX_BY_TONE}, ensure_ascii=False)


def offline_board(script, timing, claims):
    text = " ".join(l["text"] for l in timing["lines"]).lower()
    kinds = []
    for w, k in K.KEYWORD_SETS.items():
        if w in text and k not in kinds:
            kinds.append(k)
    kinds = (kinds + ["office", "archive", "street", "hall"])[:4]
    speakers = [s for s in dict.fromkeys(l["speaker"] for l in timing["lines"]) if s != "narrator"]
    cast = [{"id": "lead", "name": "", "hair": "side_part", "outfit": "suit"}] + [{"id": s, "hair": K.HAIR[i + 2], "outfit": K.OUTFITS[i + 1]} for i, s in enumerate(speakers)]
    return {"cast": cast, "hero_object": {"prop": beats._keyword_prop(script.get("hero_object", "") + " " + text)[0] or "lightbulb"},
            "locations": [{"id": f"L{i}", "kind": k, "grade": ["day", "dusk", "night", "period"][i % 4]} for i, k in enumerate(kinds)],
            "beats": [], "offline": True}


def direct(cfg, session, script, timing, claims, history, seed, video_id):
    """-> (plan, board, report)"""
    recent = [v.get("hero") for v in history["videos"][-8:] if v.get("hero")]
    board = None
    if session is not None:
        user = fill(prompt("director.md"), title=script["title"], hero=script.get("hero_object", ""),
                    lines=json.dumps(_lines_for_prompt(timing), ensure_ascii=False, indent=1),
                    claims=json.dumps([{"id": c["id"], "fact": c["text"]} for c in claims], ensure_ascii=False),
                    catalog=catalog_text(), recent=json.dumps(recent))
        try:
            board, model = session.json("director", lessons.system("director_system.md", "director"), user, max_tokens=8000)
            board["directed_by"] = model
        except LLMUnavailable as e:
            log(f"director unavailable ({e}); using the offline director", "WARN")
    if board is not None:
        try:
            plan, report = beats.compile_plan(cfg, script, timing, board, claims, seed, video_id)
        except Exception as e:  # noqa: BLE001  (a malformed board from a model must not end the video)
            log(f"storyboard from {board.get('directed_by')} could not be compiled ({str(e)[:120]}); offline director", "WARN")
            board = None
    if board is None:
        board = offline_board(script, timing, claims)
        plan, report = beats.compile_plan(cfg, script, timing, board, claims, seed, video_id)
    if report["violations"] and session is not None and not board.get("offline"):
        log(f"storyboard has {len(report['violations'])} violation(s); one revision", "WARN")
        try:
            fix = (f"\n\n# REVISE\nYour storyboard:\n{json.dumps(board, ensure_ascii=False)[:12000]}\n\nAfter compiling, these rules "
                   "still fail. Return the whole corrected storyboard JSON:\n" + "\n".join(f"- {v}" for v in report["violations"]))
            board2, model = session.json("director", lessons.system("director_system.md", "director"), user + fix, max_tokens=8000)
            board2["directed_by"] = model
            plan2, report2 = beats.compile_plan(cfg, script, timing, board2, claims, seed, video_id)
            if len(report2["violations"]) < len(report["violations"]):
                plan, board, report = plan2, board2, report2
        except Exception as e:  # noqa: BLE001  (models out, or a malformed revision)
            log(f"director revision skipped: {str(e)[:150]}", "WARN")
    if report["violations"] and not board.get("offline"):
        off = offline_board(script, timing, claims)
        plan3, report3 = beats.compile_plan(cfg, script, timing, off, claims, seed, video_id)
        if len(report3["violations"]) < len(report["violations"]):
            log("the model storyboard still breaks rules; using the offline director's storyboard", "WARN")
            plan, board, report = plan3, off, report3
    log(f"storyboard: {report['metrics']['shots']} shots, avg {report['metrics']['avg_shot']}s, "
        f"{report['metrics']['builds']} builds, {len(report['repairs'])} repairs, {len(report['violations'])} violations")
    return plan, board, report
