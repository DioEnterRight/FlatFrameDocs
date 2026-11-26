"""BEAT COMPILER: script + voice timing + the director's storyboard -> the engine's render plan (plan.json).

The director (a free model) proposes; this module enforces the 2D Documentary Skill deterministically, repairing
what it can and reporting the rest:

  * cuts on words / speech pauses; long lines split, so shots average ~2.3-2.9 s (Fast pace, 5.3 shot budget)
  * [CARD] lines become black cards typed at >= 19 characters per second, held >= 1.4 s
  * intro recipe: frame 0 = protagonist + glowing hero object, already moving; the title over a live scene
  * skits: one locked shot per line, over-the-shoulder / two-shot profile, an earned close-up on the punchline,
    the speaker's mouth driven by loudness, an expression change on every line
  * camera mix (push ~45 %, pan/tilt ~20 %, pull ~5 %, still ~10 %), never the same move more than 3 shots running,
    timings rotated, groups of 3+ stay wide, nobody cut by the frame edge (geometry check below)
  * a staged object build within 5 s and then every 8-12 s; props never scale up from nothing
  * overlay text only for places / dates / names / numbers, at most 3 words, never at bottom centre
  * effects on about a third of scenes, matched to tone; hard cuts >= 85 % of transitions
  * the hero object in every section and the last image returns to the opening one
"""
import copy
import re

from . import catalog as K
from .common import norm_text, words_of

FPS = 30
W, H, WORLD_W, CAST_Y = 1080, 1920, 1404, 1530
BASE_SCALE = 1.3
ZOOM = {"wide": 1.0, "medium": 1.5, "close": 2.8}   # vertical frame: medium puts a full body at ~44 % height


def fr(sec):
    return int(round(sec * FPS))


# ------------------------------------------------------------------ words -> frames
def word_frame(line, needle, shot_from):
    """Frame (relative to the shot) where `needle` is spoken in `line`, or None."""
    if not needle:
        return None
    key = norm_text(needle)
    for w in line["words"]:
        if key and (norm_text(w["w"]) == key or key in norm_text(w["w"]) or norm_text(w["w"]).startswith(key[:5])):
            return max(0, fr(w["s"]) - shot_from)
    return None


# ------------------------------------------------------------------ cast
def build_cast(board):
    cast = []
    for i, c in enumerate(board.get("cast") or []):
        cid = re.sub(r"[^a-z0-9_]", "", str(c.get("id", f"c{i}")).lower()) or f"c{i}"
        if c.get("creature") in K.CREATURES or c.get("type") == "creature":
            cast.append({"id": cid, "name": c.get("name", ""), "skin": "#000", "hair": {"style": "bald", "color": "#000"},
                         "outfit": {"kind": "sweater", "color": _color(c.get("color"), "#6B5E4E"), "accent": "#000"},
                         "creature": c.get("creature") if c.get("creature") in K.CREATURES else "bird"})
            continue
        cast.append({
            "id": cid, "name": str(c.get("name", ""))[:40],
            "skin": c.get("skin") if c.get("skin") in K.SKINS else K.SKINS[(i * 3 + 1) % len(K.SKINS)],
            "hair": {"style": c.get("hair") if c.get("hair") in K.HAIR else K.HAIR[i % 6],
                     "color": _color(c.get("hair_color"), ["#3B2A20", "#7A3B2E", "#2B2B2B", "#8C6A4F", "#C9A35A"][i % 5])},
            "outfit": {"kind": c.get("outfit") if c.get("outfit") in K.OUTFITS else K.OUTFITS[i % len(K.OUTFITS)],
                       "color": _color(c.get("outfit_color"), ["#4A6B6E", "#2C3E50", "#8C7F55", "#6E4726", "#7B4A5E"][i % 5]),
                       "accent": _color(c.get("accent_color"), ["#C33631", "#F4F1EA", "#5A4A2E", "#E8C547"][i % 4])},
            "glasses": c.get("glasses") if c.get("glasses") in ("none", "round", "square") else "none",
        })
    if not cast:
        cast.append({"id": "narr", "name": "", "skin": "#E8B48A", "hair": {"style": "side_part", "color": "#3B2A20"},
                     "outfit": {"kind": "suit", "color": "#2C3E50", "accent": "#C33631"}, "glasses": "none"})
    return cast


def _color(c, default):
    return c if isinstance(c, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", c) else default


# ------------------------------------------------------------------ geometry (mirror of engine/src/camera/camera.ts)
def actor_box(a, cast_by_id):
    who = cast_by_id.get(a["id"], {})
    s = BASE_SCALE * a.get("scale", 1)
    x = a["x"] * WORLD_W
    if who.get("creature") == "big_bird":
        return x - 155 * s, x + 155 * s, CAST_Y - 480 * s, CAST_Y + 20
    if who.get("creature"):
        return x - 160 * s, x + 160 * s, CAST_Y - 240 * s, CAST_Y + 20
    reach = 175 if a.get("pose") in ("pointing", "shrugging", "cheering") else 110
    left, right = (110, reach) if a.get("facing") == "right" else (reach, 110) if a.get("facing") == "left" else (reach, reach)
    if a.get("pose") in ("shrugging", "cheering"):
        left = right = reach
    return x - left * s, x + right * s, CAST_Y - 440 * s, CAST_Y + 20


def cam_view(cam, t):
    z = ZOOM[cam["framing"]]
    amt = cam.get("amount", 0.14)
    prog = t if cam["timing"] != "settle" else min(1, t * 3)
    if cam["move"] == "push":
        z *= 1 + amt * prog
    elif cam["move"] == "pull":
        z *= 1 + amt * (1 - prog)
    if cam["timing"] == "creep_punch" and t > 0.6:
        z *= 1.12
    cx, cy = cam["focus"][0] * WORLD_W, cam["focus"][1] * H
    if cam["move"] == "pan":
        cx += cam.get("dir", 1) * W * amt * (prog - 0.5) / ZOOM[cam["framing"]]
    if cam["move"] == "tilt":
        cy += cam.get("dir", 1) * H * amt * (prog - 0.5) / ZOOM[cam["framing"]]
    hw, hh = W / (2 * z), H / (2 * z)
    cx = min(max(cx, hw), WORLD_W - hw)
    cy = min(max(cy, hh), H - hh)
    return cx - hw, cx + hw, cy - hh, cy + hh


def framing_ok(shot, cast_by_id, margin=0.02):
    """Fully in or fully out (skill 5.5): every character stays inside the frame at start, middle and end."""
    actors = [a for a in shot.get("actors", []) if a.get("pose") != "running" and a.get("count", 1) == 1
              and not (shot.get("ots") and a["id"] == shot["ots"]["near"]) and a.get("enterAt") is None]
    close = shot["camera"]["framing"] == "close"
    for t in (0, 0.5, 1):
        x0, x1, y0, y1 = cam_view(shot["camera"], t)
        mx, my = (x1 - x0) * margin, (y1 - y0) * margin
        for a in actors:
            ax0, ax1, ay0, ay1 = actor_box(a, cast_by_id)
            if close:   # an earned close-up frames the head; the body may leave the frame
                s = BASE_SCALE * a.get("scale", 1)
                ax0, ax1, ay0, ay1 = a["x"] * WORLD_W - 95 * s, a["x"] * WORLD_W + 95 * s, CAST_Y - 430 * s, CAST_Y - 240 * s
            if ax0 < x0 + mx or ax1 > x1 - mx or ay0 < y0 + my or ay1 > y1 + 60:
                return False
    return True


def solve_framing(shot, cast_by_id):
    """Repair a shot so every character is fully in frame: recentre, pull the cast together (keeping the 1.2 body
    width spacing), soften the push, then go wider, and as a last resort lock the camera wide."""
    if not shot.get("actors") or shot["kind"] not in ("scene", "skit", "title"):
        return []
    actors = [a for a in shot["actors"] if a.get("pose") != "running" and a.get("count", 1) == 1
              and not (shot.get("ots") and a["id"] == shot["ots"]["near"])]
    if not actors or framing_ok(shot, cast_by_id):
        return []
    cam = shot["camera"]

    def centre():
        boxes = [actor_box(a, cast_by_id) for a in actors]
        cam["focus"][0] = round(((min(b[0] for b in boxes) + max(b[1] for b in boxes)) / 2) / WORLD_W, 3)
        if cam["framing"] == "close":
            cam["focus"][1] = round((CAST_Y - 330 * BASE_SCALE) / H, 3)
        else:
            cam["focus"][1] = round(min(0.8, max(0.5, ((min(b[2] for b in boxes) + CAST_Y) / 2 + 20) / H)), 3)
        return framing_ok(shot, cast_by_id)

    if centre():
        return ["recentred"]
    for squeeze in (0.8, 0.6, 0.45):
        mid = sum(a["x"] for a in actors) / len(actors)
        for a in actors:
            a["x"] = round(mid + (a["x"] - mid) * squeeze, 3)
        _spread(actors, cast_by_id)
        if centre():
            return ["cast pulled together"]
    fixes = []
    if cam["move"] in ("push", "pull") and cam.get("amount", 0) > 0.06:
        cam["amount"] = 0.06
        cam["timing"] = "creep" if cam["timing"] == "creep_punch" else cam["timing"]
        cam.pop("punchAt", None)
        fixes.append("push softened")
        if centre():
            return fixes
    order = ["close", "medium", "wide"]
    while cam["framing"] != "wide":
        cam["framing"] = order[order.index(cam["framing"]) + 1]
        fixes.append(f"framing widened to {cam['framing']}")
        if centre():
            return fixes
    cam["move"], cam["amount"] = "still", 0.0
    fixes.append("camera locked wide")
    return fixes


def _spread(actors, cast_by_id):
    """Characters side by side stay >= 1.2 body widths apart, centre to centre (skill 5.2 spacing); the group keeps
    its centre so the spacing never pushes anyone out of the set."""
    if len(actors) < 2:
        return
    mid = sum(a["x"] for a in actors) / len(actors)
    order = sorted(actors, key=lambda a: a["x"])
    for i in range(1, len(order)):
        big = any(cast_by_id.get(a["id"], {}).get("creature") for a in order[i - 1:i + 1])
        need = 1.2 * (1.25 if big else 1.0) * (150 * BASE_SCALE * order[i].get("scale", 1)) / WORLD_W
        if order[i]["x"] - order[i - 1]["x"] < need:
            order[i]["x"] = order[i - 1]["x"] + need
    shift = mid - sum(a["x"] for a in actors) / len(actors)
    for a in actors:
        a["x"] = round(min(0.88, max(0.12, a["x"] + shift)), 3)


# ------------------------------------------------------------------ helpers
def _loc(board, lid):
    for l in board.get("locations") or []:
        if l.get("id") == lid:
            return l
    return None


def _set_of(loc, variant):
    kind = loc.get("kind") if loc and loc.get("kind") in K.SET_KINDS else "office"
    grade = loc.get("grade") if loc and loc.get("grade") in K.GRADES else "day"
    signs = [str(s)[:18] for s in (loc.get("signs") or [])][:4] if loc else []
    s = {"kind": kind, "grade": grade, "variant": variant, "signs": signs}
    if loc and loc.get("wall") in K.WALL_PATTERNS:
        s["wall"] = loc["wall"]
    if loc and loc.get("floor") in K.FLOOR_PATTERNS:
        s["floor"] = loc["floor"]
    return s


def _keyword_prop(text):
    for w in words_of(text):
        p = K.KEYWORD_PROPS.get(w.lower().strip(".,!?"))
        if p:
            return p, w
    return None, None


def _actor(spec, cast_ids, default_id, x):
    aid = spec.get("id") if spec.get("id") in cast_ids else default_id
    a = {"id": aid, "x": float(min(0.9, max(0.1, spec.get("x", x)))),
         "expr": spec.get("expr") if spec.get("expr") in K.EXPRS else "neutral",
         "pose": spec.get("pose") if spec.get("pose") in K.POSES else "idle",
         "facing": spec.get("facing") if spec.get("facing") in ("left", "right", "front", "back") else "front"}
    if isinstance(spec.get("count"), int) and 2 <= spec["count"] <= 8:
        a["count"] = spec["count"]
    if spec.get("hold") in K.PROPS:
        a["hold"], a["pose"] = spec["hold"], "holding"
    return a


def _prop(spec, line, shot_from, i):
    kind = spec.get("kind") if spec.get("kind") in K.PROPS else None
    if not kind:
        return None
    p = {"kind": kind, "x": float(min(0.92, max(0.08, spec.get("x", 0.3 + 0.4 * (i % 2))))),
         "layer": "mid" if kind in K.BIG_PROPS else "cast"}
    if spec.get("label"):
        p["label"] = str(spec["label"])[:16]
    entry = spec.get("entry")
    at = word_frame(line, spec.get("on_word"), shot_from)
    if entry in K.ENTRIES and at is not None:
        p["entry"], p["at"] = entry, at
    if spec.get("scale"):
        p["scale"] = float(min(2.2, max(0.5, spec["scale"])))
    return p


# ------------------------------------------------------------------ main
def compile_plan(cfg, script, timing, board, claims, seed, video_id="doc"):
    lines = timing["lines"]
    total = fr(timing["duration"])
    story_end = fr(timing.get("narration_end", timing["duration"]))
    cast = build_cast(board)
    cast_by_id = {c["id"]: c for c in cast}
    cast_ids = [c["id"] for c in cast]
    people = [c["id"] for c in cast if not c.get("creature")] or cast_ids
    hero_kind = (board.get("hero_object") or {}).get("prop")
    if hero_kind not in K.PROPS:
        hero_kind = _keyword_prop(script.get("hero_object", "") + " " + script.get("title", ""))[0] or "lightbulb"
    beats_by_line = {}
    for b in board.get("beats") or []:
        try:
            beats_by_line[int(b.get("line")) - 1] = b
        except (TypeError, ValueError):
            continue
    report = {"repairs": [], "auto_beats": 0}
    shots = []
    visits = {}
    title_done = False
    title_line = next((i for i, l in enumerate(lines) if l["section"] == "build"), 2)
    skit_idx = [i for i, l in enumerate(lines) if l["speaker"] != "narrator"]
    # script speakers ("A", "B") -> cast ids: the director's mapping, else the first two people
    smap = {str(k): v for k, v in (board.get("speakers") or {}).items() if v in cast_ids}
    for k, spk in enumerate(dict.fromkeys(lines[i]["speaker"] for i in skit_idx)):
        smap.setdefault(spk, people[k % len(people)])
    report["speakers"] = smap
    for i, l in enumerate(lines):
        start = 0 if i == 0 else fr(l["start"])
        end = fr(lines[i + 1]["start"]) if i + 1 < len(lines) else story_end
        b = beats_by_line.get(i)
        if b is None:
            report["auto_beats"] += 1
            b = auto_beat(l, i, board, cast_ids, hero_kind)
        if l["card"]:
            text = l["text"]
            speech = max(0.5, l["end"] - l["start"])
            cps = max(19, round(len(text) / (speech * 0.92)))
            shots.append({"from": start, "dur": max(end - start, 42), "kind": "card", "line": text,
                          "card": {"text": text, "typeFrom": max(0, fr(l["start"]) - start), "cps": cps},
                          "camera": {"move": "still", "timing": "creep", "framing": "wide", "focus": [0.5, 0.5]}})
            continue
        loc = _loc(board, b.get("location")) or (board.get("locations") or [None])[0]
        lid = (loc or {}).get("id", "L0")
        visits[lid] = visits.get(lid, -1) + 1
        kind = b.get("shot") if b.get("shot") in K.SHOTS else "scene"
        if l["speaker"] != "narrator":
            kind = "skit"
        shot = {"from": start, "dur": end - start, "kind": kind, "line": l["text"],
                "set": _set_of(loc, visits[lid]), "actors": [], "props": []}
        default_id = l["speaker"] if l["speaker"] in cast_ids else people[0]
        for k, a in enumerate(b.get("cast") or []):
            shot["actors"].append(_actor(a, cast_ids, default_id, 0.35 + 0.3 * k))
        if kind == "skit":
            shot = skit_shot(shot, dict(l, speaker=smap.get(l["speaker"], people[0])), i, skit_idx, cast_ids, people, start)
        for k, p in enumerate(b.get("props") or []):
            pp = _prop(p, l, start, k)
            if pp:
                shot["props"].append(pp)
        if b.get("build") and b["build"].get("recipe") in K.BUILDS:
            shot["build"] = make_build(b["build"], l, start, claims)
        if kind == "map":
            shot["map"] = make_map(b.get("map") or {}, l, start)
        if kind == "triptych":
            shot["panels"] = make_panels(b.get("panels") or [], l, start)
        if kind in ("insert", "tabletop") and not shot["props"]:
            pk, _ = _keyword_prop(l["text"])
            shot["props"].append({"kind": pk or hero_kind, "x": 0.5})
        if b.get("text") and b["text"].get("kind") in K.TEXT_KINDS:
            t = overlay(b["text"], l, start, claims)
            if t:
                shot["texts"] = [t]
        shot["camera"] = make_camera(b.get("camera") or {}, l, start, shot)
        if b.get("effect") and b["effect"].get("kind") in K.FX:
            shot["fx"] = {"main": {"kind": b["effect"]["kind"], "purpose": str(b["effect"].get("purpose", ""))[:60]}}
        if b.get("transition") in ("whip", "flash"):
            shot["transition"] = b["transition"]
        if not title_done and i >= title_line and kind == "scene":
            shot["kind"] = "title"
            shot["title"] = make_title(script["title"], board.get("title_accent"))
            title_done = True
        shots.extend(split_long(shot, l, start))
    plan = {"id": video_id, "fps": FPS, "width": W, "height": H, "durationInFrames": total, "seed": seed,
            "accent": "#8FD23F", "cast": cast, "hero": {"kind": hero_kind}, "shots": shots}
    enforce(plan, script, timing, claims, report, cast_by_id, hero_kind)
    add_outro(cfg, plan, timing, people, story_end, total)
    plan["captions"] = captions(timing) if cfg["brand"]["captions"] else []
    plan["brand"] = {"corner": cfg["brand"]["corner_handle"]}
    report["metrics"] = metrics(plan)
    report["violations"] = audit(plan, cast_by_id)
    return plan, report


def add_outro(cfg, plan, timing, people, story_end, total):
    """Last ~3 s: back at the opening place, the main character turns to camera and says the follow line, with the
    channel name and the handle lettered on a sign (config `brand`)."""
    if total <= story_end or not timing.get("outro"):
        return
    o = timing["outro"]
    first = next((s for s in plan["shots"] if s.get("set")), None)
    hero = first["actors"][0]["id"] if first and first.get("actors") else people[0]
    if plan_cast_creature(plan, hero):
        hero = people[0]
    st = dict(first["set"], variant=first["set"]["variant"] + 2) if first else {"kind": "office", "grade": "day", "variant": 2}
    plan["shots"].append({
        "from": story_end, "dur": total - story_end, "kind": "outro", "line": o["text"], "set": st,
        "actors": [{"id": hero, "x": 0.3, "expr": "happy", "pose": "pointing", "facing": "right",
                    "talk": {"start": max(0, fr(o["start"]) - story_end), "env": o.get("env", [])}}],
        "props": [{"kind": plan["hero"]["kind"], "x": 0.18, "layer": "mid", "glow": True}],
        "outro": {"text": o["text"]},
        "camera": {"move": "push", "timing": "settle", "framing": "wide", "focus": [0.5, 0.5], "amount": 0.06}})


def plan_cast_creature(plan, cid):
    return any(c["id"] == cid and c.get("creature") for c in plan["cast"])


def captions(timing, max_words=3):
    """Word-by-word caption chunks for every spoken story line except black cards (the card already shows the words)."""
    out = []
    for l in timing["lines"]:
        if l["card"]:
            continue
        chunk = []
        for w in l["words"]:
            chunk.append({"w": w["w"], "s": fr(w["s"]), "e": fr(w["e"])})
            if len(chunk) >= max_words or w["w"][-1:] in ".,!?;:":
                out.append({"from": chunk[0]["s"], "to": chunk[-1]["e"], "words": chunk})
                chunk = []
        if chunk:
            out.append({"from": chunk[0]["s"], "to": chunk[-1]["e"], "words": chunk})
    for a, b in zip(out, out[1:]):   # hold each chunk until the next one starts (no flicker in short gaps)
        if b["from"] - a["to"] < 12:
            a["to"] = b["from"]
    return out


def auto_beat(l, i, board, cast_ids, hero_kind):
    """Offline director for one line: a location from keywords, the narrator's protagonist, a prop from keywords."""
    locs = board.get("locations") or []
    lid = locs[i % len(locs)]["id"] if locs else None
    pk, word = _keyword_prop(l["text"])
    beat = {"line": i + 1, "shot": "scene", "location": lid,
            "cast": [{"id": cast_ids[0], "x": 0.38, "expr": ["concerned", "surprised", "thinking", "deadpan"][i % 4],
                      "pose": ["pointing", "talking", "shrugging", "idle"][i % 4], "facing": "right"}],
            "props": [{"kind": pk or hero_kind, "x": 0.66, "entry": ["drop", "slide", "slam"][i % 3], "on_word": word or l["words"][0]["w"]}],
            "camera": {"move": "push"}}
    return beat


def skit_shot(shot, l, i, skit_idx, cast_ids, people, start):
    """One locked shot per skit line: over-the-shoulder for the first lines, two-shot profile in the middle, an earned
    close-up on the punchline (the last, shortest line)."""
    speaker = l["speaker"] if l["speaker"] in cast_ids else people[0]
    others = [c for c in people if c != speaker] or [c for c in cast_ids if c != speaker] or [speaker]
    listener = others[0]
    k = skit_idx.index(i)
    last = k == len(skit_idx) - 1
    by = {a["id"]: a for a in shot["actors"]}
    sp = by.get(speaker) or {"id": speaker, "expr": "deadpan", "pose": "talking"}
    li = by.get(listener) or {"id": listener, "expr": "deadpan", "pose": "idle"}
    exprs = ["deadpan", "concerned", "surprised", "thinking", "angry", "sad", "panic"]
    sp_expr = sp.get("expr", "deadpan")
    li_expr = li.get("expr", "deadpan")
    if k % 2:
        sp_expr = exprs[(exprs.index(sp_expr) + 1) % len(exprs)] if sp_expr in exprs else "concerned"
    left_is_speaker = k % 2 == 0
    a_sp = {"id": speaker, "x": 0.4 if left_is_speaker else 0.6, "expr": sp_expr, "pose": "talking",
            "facing": "right" if left_is_speaker else "left",
            "talk": {"start": max(0, fr(l["start"]) - start), "env": l.get("env", [])}}
    a_li = {"id": listener, "x": 0.6 if left_is_speaker else 0.4, "expr": li_expr, "pose": "idle",
            "facing": "left" if left_is_speaker else "right"}
    shot["actors"] = [a_sp, a_li]
    if last:
        shot["actors"] = [dict(a_sp, x=0.5, facing="front")]
        shot["camera_hint"] = "close"
    elif k == 0 or k == 2:
        shot["ots"] = {"near": listener, "far": speaker}
        a_li["x"] = 0.22 if a_li["x"] < 0.5 else 0.78
        a_sp["x"] = 0.56 if a_sp["x"] > 0.5 else 0.44
    return shot


def make_build(spec, line, start, claims):
    words = spec.get("on_words") or ([spec.get("on_word")] if spec.get("on_word") else [])
    at = [w for w in (word_frame(line, x, start) for x in words) if w is not None] or [max(0, fr(line["start"]) - start + 6)]
    b = {"recipe": spec["recipe"], "at": at}
    if spec.get("label"):
        b["label"] = str(spec["label"])[:20]
    if spec["recipe"] == "counter":
        nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", line["text"])]
        val = spec.get("value")
        b["value"] = val if isinstance(val, (int, float)) and (not nums or val in nums) else (nums[0] if nums else 0)
        b["from"] = 0
        if spec.get("prefix") in ("$", "£", "€"):
            b["prefix"] = spec["prefix"]
        if spec.get("suffix") in ("%",):
            b["suffix"] = "%"
    items = []
    for it in spec.get("items") or []:
        item = {"label": str(it.get("label", ""))[:14]}
        if it.get("kind") in K.PROPS:
            item["kind"] = it["kind"]
        if isinstance(it.get("value"), (int, float)):
            item["value"] = it["value"]
        if it.get("accent"):
            item["accent"] = True
        items.append(item)
    if items:
        b["items"] = items[:5]
        while len(b["at"]) < len(items):
            b["at"].append(b["at"][-1] + [10, 5, 3, 3, 3, 2][min(len(b["at"]) - 1, 5)])
    if spec.get("x") is not None:
        b["x"] = float(min(0.85, max(0.15, spec["x"])))
    return b


def make_map(spec, line, start):
    m = {"style": "dark" if spec.get("style") == "dark" else "light", "focus": str(spec.get("country") or "world")[:40]}
    pins = []
    for p in spec.get("pins") or []:
        try:
            pins.append({"lon": float(p["lon"]), "lat": float(p["lat"]), "label": str(p.get("label", ""))[:16],
                         "at": word_frame(line, p.get("on_word"), start) or 12})
        except (KeyError, TypeError, ValueError):
            continue
    if pins:
        m["pins"] = pins[:3]
    m["zoomFrom"] = 0.45
    return m


def make_panels(panels, line, start):
    out = []
    for i, p in enumerate(panels[:3]):
        out.append({"label": str(p.get("label", ""))[:14], "prop": p.get("prop") if p.get("prop") in K.PROPS else "label_box",
                    "at": word_frame(line, p.get("on_word") or p.get("label"), start) or i * 12})
    return out


def make_title(title, accent):
    words = title.split()
    n = 3 if len(words) >= 7 else 2
    per = -(-len(words) // n)
    lines = [" ".join(words[k:k + per]) for k in range(0, len(words), per)]
    if not accent or accent.lower() not in title.lower():
        accent = max(words, key=lambda w: len(re.sub(r"\W", "", w)))
    return {"lines": lines, "accentWord": re.sub(r"\W", "", accent), "at": [0, 10, 20][:len(lines)]}


def make_camera(spec, line, start, shot):
    move = spec.get("move") if spec.get("move") in K.MOVES else "push"
    framing = spec.get("framing") if spec.get("framing") in K.FRAMINGS else ("medium" if shot["kind"] in ("scene", "title", "skit") else "wide")
    if shot["kind"] == "skit" and framing == "wide":
        framing = "medium"
    if shot.pop("camera_hint", None) == "close":
        framing, move = "close", "still"
        return {"move": "still", "timing": "creep", "framing": "close", "focus": [0.5, round((CAST_Y - 330 * BASE_SCALE) / H, 3)]}
    timing = spec.get("timing") if spec.get("timing") in K.TIMINGS else "creep"
    cam = {"move": move, "timing": timing, "framing": framing, "focus": [0.5, 0.62 if framing != "wide" else 0.5]}
    secs = shot["dur"] / FPS
    if move in ("push", "pull"):
        cam["amount"] = round(min(0.2, max(0.1, 0.05 * secs)), 3)
    elif move in ("pan", "tilt"):
        cam["amount"] = 0.12
        cam["dir"] = 1 if (start // 7) % 2 else -1
    if timing == "creep_punch":
        pw = word_frame(line, spec.get("punch_word"), start)
        if pw is None:
            cam["timing"] = "creep"
        else:
            cam["punchAt"] = pw
    if shot["kind"] == "skit":
        cam.update({"move": "still", "timing": "creep"})
        cam.pop("amount", None)
    if shot.get("actors"):
        xs = [a["x"] for a in shot["actors"] if not (shot.get("ots") and a["id"] == shot["ots"]["near"])]
        if xs:
            cam["focus"][0] = round((min(xs) + max(xs)) / 2, 3)
    return cam


def overlay(spec, line, start, claims):
    """Only a place, date, name or number the picture cannot show; max 3 words; never restating the line."""
    text = re.sub(r"\s+", " ", str(spec.get("text", ""))).strip()[:28]
    if not text or len(text.split()) > 3 and spec["kind"] != "quote":
        return None
    claim_text = " ".join(c["text"] for c in claims).lower()
    informative = bool(re.search(r"\d", text)) or all(w.lower() in claim_text for w in re.findall(r"[A-Za-z]{3,}", text))
    if spec["kind"] != "quote" and not informative:
        return None
    if spec["kind"] == "quote":
        return None   # real quotes need a sourced quote claim; not used by the automated pipeline
    at = word_frame(line, spec.get("on_word"), start)
    return {"kind": spec["kind"], "text": text, "at": at if at is not None else 4}


def split_long(shot, l, start, max_sec=3.4):
    """Fast pace: lines over ~3.4 s become two shots, cut on a word near the middle (punch-in on the second)."""
    if shot["dur"] <= fr(max_sec) or shot["kind"] in ("skit", "card", "title", "map", "triptych"):
        return [shot]
    mid = start + shot["dur"] // 2
    words = [fr(w["s"]) for w in l["words"] if start + 25 < fr(w["s"]) < start + shot["dur"] - 25]
    if not words:
        return [shot]
    cut = min(words, key=lambda x: abs(x - mid))
    a, b = copy.deepcopy(shot), copy.deepcopy(shot)
    a["dur"] = cut - start
    b["from"], b["dur"] = cut, shot["dur"] - (cut - start)
    for k, x in ((a, 0), (b, cut - start)):
        k["props"] = [dict(p, at=max(0, p["at"] - x)) if "at" in p else p for p in k["props"] if p.get("at", 0) - x < k["dur"]]
        if k.get("build"):
            k["build"]["at"] = [max(0, t - x) for t in k["build"]["at"]]
        for t in k.get("texts", []):
            t["at"] = max(0, t["at"] - x)
    if b.get("build") and all(t >= b["dur"] for t in b["build"]["at"]):
        b.pop("build")
    if a.get("build") and min(a["build"]["at"]) >= a["dur"]:
        a.pop("build")
    b["texts"] = []
    if len(b.get("actors", [])) > 1:   # punch-in cut on one subject: something new to look at
        b["actors"] = [dict(b["actors"][-1], x=0.5)]
        b["props"] = [dict(p, x=0.22 if p["x"] < 0.5 else 0.78) for p in b["props"]]
    b["camera"] = dict(b["camera"], move="push", timing="settle", framing="close" if b["camera"]["framing"] == "medium" else "medium")
    b["camera"].pop("punchAt", None)
    b["camera"]["amount"] = 0.1
    if b["camera"]["timing"] == "settle" and a["camera"]["timing"] == "settle":
        a["camera"]["timing"] = "creep"
    return [a, b]


# ------------------------------------------------------------------ global rules
def enforce(plan, script, timing, claims, report, cast_by_id, hero_kind):
    shots = plan["shots"]
    rep = report["repairs"]
    scenes = [s for s in shots if s["kind"] in ("scene", "title", "skit")]
    # intro recipe (a): frame 0 = protagonist + glowing hero object, medium framing, already moving
    first = shots[0]
    if first["kind"] in ("scene", "title"):
        if not any(p["kind"] == hero_kind for p in first["props"]):
            first["props"].append({"kind": hero_kind, "x": 0.68, "layer": "cast"})
            rep.append("hero object added to frame 0")
        for p in first["props"]:
            if p["kind"] == hero_kind:
                p["glow"] = True
                p.pop("entry", None)
        first["camera"].update({"framing": "medium", "move": "push"})
        first["camera"].setdefault("amount", 0.14)
    # the title lands over a live scene that contains the glowing hero object
    for s in shots:
        if s["kind"] == "title" and not any(p["kind"] == hero_kind for p in s["props"]):
            s["props"].append({"kind": hero_kind, "x": 0.5, "layer": "mid"})
            rep.append("hero object added under the title")
    # hero object glows wherever it appears; it appears in every section
    for s in shots:
        for p in s.get("props", []):
            if p["kind"] == hero_kind:
                p["glow"] = True
    # groups stay wide and still (no push into 3+ people)
    for s in scenes:
        crowd = sum(a.get("count", 1) for a in s.get("actors", []))
        if crowd >= 3 and s["camera"]["move"] in ("push",) and s["camera"]["framing"] != "wide":
            s["camera"].update({"framing": "wide", "move": "pan", "amount": 0.08})
            rep.append("group shot kept wide")
    # camera move mix: never the same move more than 3 shots running; rotate timings
    moving = [s for s in shots if s["kind"] not in ("card",)]
    for k in range(3, len(moving)):
        last = [m["camera"]["move"] for m in moving[k - 3:k]]
        if len(set(last)) == 1 and moving[k]["camera"]["move"] == last[0] and moving[k]["kind"] != "skit":
            alt = "pan" if last[0] == "push" else "push"
            moving[k]["camera"]["move"] = alt
            moving[k]["camera"].setdefault("amount", 0.12)
            rep.append(f"camera variety: shot at {moving[k]['from'] / FPS:.1f}s -> {alt}")
    for k in range(2, len(moving)):
        if moving[k]["camera"]["timing"] == moving[k - 1]["camera"]["timing"] == moving[k - 2]["camera"]["timing"]:
            moving[k]["camera"]["timing"] = "settle" if moving[k]["camera"]["timing"] != "settle" else "creep"
            moving[k]["camera"].pop("punchAt", None)
    # close-ups are earned: at most 2 in a short (skit punchline + one object)
    closes = [s for s in shots if s["camera"]["framing"] == "close"]
    for s in closes[2:]:
        s["camera"]["framing"] = "medium"
        rep.append("extra close-up widened")
    # framing: nobody cut by the frame edge
    for s in shots:
        for fx in solve_framing(s, cast_by_id):
            rep.append(f"framing {s['from'] / FPS:.1f}s: {fx}")
    # staged builds: one within 5 s, then every 8-12 s, always inside the frame
    ensure_builds(plan, timing, claims, rep, hero_kind)
    place_builds(plan, cast_by_id)
    # effects: about a third of scenes, never two main effects in a row
    with_fx = [s for s in scenes if s.get("fx")]
    budget = max(1, round(len(scenes) / 3))
    for s in with_fx[budget:]:
        s.pop("fx")
        rep.append("effect dropped (budget: a third of scenes)")
    # transitions: >= 85 % hard cuts
    designed = [s for s in shots if s.get("transition") in ("whip", "flash")]
    for s in designed[max(1, int(len(shots) * 0.12)):]:
        s.pop("transition")
        rep.append("designed transition removed (>= 85 % hard cuts)")
    for s in shots:
        if s.get("transition") and s["kind"] in ("card", "skit"):
            s.pop("transition")
    # overlay text budget: at most 6, one at a time
    n = 0
    for s in shots:
        if s.get("texts"):
            n += 1
            if n > 6:
                s.pop("texts")
    # the ending returns to the opening image (skill: close on the opening image), camera pulls out
    last = shots[-1]
    if last["kind"] != "card" and first["kind"] in ("scene", "title"):
        last["set"] = copy.deepcopy(first["set"])
        last["set"]["variant"] = first["set"]["variant"] + 1   # change one thing on the return
        if not any(p["kind"] == hero_kind for p in last.get("props", [])):
            last.setdefault("props", []).append({"kind": hero_kind, "x": 0.62, "layer": "cast", "glow": True})
        if first.get("actors") and not last.get("actors"):
            last["actors"] = [dict(first["actors"][0], expr="deadpan", pose="idle")]
        last["camera"] = {"move": "pull", "timing": "creep", "framing": "wide", "focus": list(first["camera"]["focus"]), "amount": 0.18}
        last["kind"] = "scene"
        solve_framing(last, cast_by_id)


def ensure_builds(plan, timing, claims, rep, hero_kind):
    shots = [s for s in plan["shots"] if s["kind"] in ("scene", "title")]
    times = [s["from"] / FPS + (s["build"]["at"][0] / FPS) for s in plan["shots"] if s.get("build")]
    targets = [3.0] + [t for t in range(12, int(plan["durationInFrames"] / FPS) - 4, 10)]
    for t in targets:
        if any(abs(x - t) <= (2.5 if t == 3.0 else 5.5) for x in times):
            continue
        cand = [s for s in shots if s["from"] / FPS <= t + 3 and s["from"] / FPS + s["dur"] / FPS >= t - 2 and not s.get("build")]
        for s in cand:
            shown = " ".join(x["text"] for x in s.get("texts", []))
            nums = [n for n in re.findall(r"\d{1,3}(?:,\d{3})+|\d+", s.get("line", ""))
                    if not (len(n) == 4 and "," not in n and 1000 <= int(n) <= 2100) and n not in shown]   # never count a year
            if nums:
                s["build"] = {"recipe": "counter", "at": [min(12, s["dur"] - 20)], "value": float(nums[0].replace(",", "")), "from": 0, "x": 0.66}
                rep.append(f"counter build added at {t}s")
                break
            pk, _ = _keyword_prop(s.get("line", ""))
            kind = pk if pk and not any(p["kind"] == pk for p in s.get("props", [])) else None
            if kind is None and not any(p["kind"] == hero_kind for p in s.get("props", [])):
                kind = hero_kind
            if kind is None:   # documentary evidence objects as a neutral last resort
                have = {p["kind"] for p in s.get("props", [])}
                kind = next(k for k in ("document", "newspaper", "map_scroll", "hourglass", "letter") if k not in have)
            if kind:   # never a second copy of an object already in the shot
                s["build"] = {"recipe": "drop_puff", "at": [min(8, max(0, s["dur"] - 30))], "items": [{"label": "", "kind": kind}], "x": 0.7}
                rep.append(f"drop build added at {t}s")
                break
        else:
            continue
        times.append(t)


def place_builds(plan, cast_by_id):
    """Keep every staged build inside the frame and clear of the cast: counters become signs hung in the empty upper
    part of the vertical frame, on the side away from the characters; other builds are centred in the view."""
    for s in plan["shots"]:
        b = s.get("build")
        if not b or s["kind"] not in ("scene", "title"):
            continue
        x0, x1, y0, y1 = cam_view(s["camera"], 0.5)
        vw, vh = x1 - x0, y1 - y0
        actors = [a for a in s.get("actors", []) if a.get("pose") != "running"]
        mid = (x0 + x1) / 2
        side = 1
        if actors:
            ax = sum(a["x"] for a in actors) / len(actors) * WORLD_W
            side = -1 if ax > mid else 1
        if b["recipe"] in ("counter", "state_flip"):
            scale = round(min(1.0, 0.62 * vw / 560), 3)
            bx = mid + side * max(0, vw / 2 - 280 * scale - vw * 0.04) * (1 if actors else 0)
            top = y0 + 0.07 * vh
            b.update({"x": round(bx / WORLD_W, 3), "y": round((top + 420 * scale) / CAST_Y, 3), "scale": scale, "hang": True})
        elif b["recipe"] in ("drop_puff", "grow", "glow_on", "stack") and actors:
            scale = round(min(1.0, vw / 1100), 3)
            b.update({"x": round((mid + side * vw * 0.3) / WORLD_W, 3), "scale": scale})
        elif b["recipe"] in ("slam_sticker", "tag_vanish"):
            b.update({"x": round(mid / WORLD_W, 3), "y": round((y0 + 0.3 * vh + 520) / CAST_Y, 3), "scale": round(min(1.0, vw / 700), 3)})
        else:
            b.update({"x": round(mid / WORLD_W, 3), "scale": round(min(1.0, vw / 1100), 3)})


# ------------------------------------------------------------------ measurement
def metrics(plan):
    shots = plan["shots"]
    secs = [s["dur"] / FPS for s in shots]
    n = len(secs)
    moves = {}
    for s in shots:
        m = "still" if s["kind"] == "card" else s["camera"]["move"]
        moves[m] = moves.get(m, 0) + 1
    dur = plan["durationInFrames"] / FPS
    events = []
    for s in shots:
        events.append(s["from"])
        events += [s["from"] + p["at"] for p in s.get("props", []) if "at" in p]
        if s.get("build"):
            events += [s["from"] + a for a in s["build"]["at"]]
        events += [s["from"] + t["at"] for t in s.get("texts", [])]
        if s["camera"].get("punchAt") is not None:
            events.append(s["from"] + s["camera"]["punchAt"])
    title_at = next((s["from"] for s in shots if s["kind"] == "title"), 300)
    pre = [e for e in events if e < title_at]
    return {
        "shots": n, "avg_shot": round(sum(secs) / n, 2), "share_1_5_to_3": round(sum(1.5 <= x <= 3 for x in secs) / n, 2),
        "share_3_plus": round(sum(x >= 3 for x in secs) / n, 2),
        "under_1s": sum(1 for s in shots if s["dur"] < 30 and s["kind"] != "skit"),
        "holds_over_5s": sum(x > 5 for x in secs), "cuts_per_min": round(n / dur * 60, 1),
        "moves": {k: round(v / n, 2) for k, v in moves.items()},
        "cards": sum(s["kind"] == "card" for s in shots), "builds": sum(1 for s in shots if s.get("build")),
        "locations": len({(s["set"]["kind"], s["set"]["grade"]) for s in shots if s.get("set")}),
        "events_per_10s_before_title": round(len(pre) / max(1, title_at / FPS) * 10, 1),
        "events_per_10s_after": round((len(events) - len(pre)) / max(1, dur - title_at / FPS) * 10, 1),
        "effects_share": round(sum(1 for s in shots if s.get("fx")) / max(1, sum(s["kind"] in ("scene", "title") for s in shots)), 2),
        "close_ups": sum(s["camera"]["framing"] == "close" for s in shots),
        "overlay_texts": sum(len(s.get("texts", [])) for s in shots),
    }


def audit(plan, cast_by_id):
    """Rules that must hold after repair. A non-empty list fails the storyboard gate."""
    v = []
    shots = plan["shots"]
    end = 0
    for s in shots:
        if s["from"] != end:
            v.append(f"gap/overlap at frame {s['from']}")
        end = s["from"] + s["dur"]
        if s["dur"] < 8:
            v.append(f"shot at {s['from'] / FPS:.1f}s is {s['dur']} frames")
        if s["kind"] == "card" and s["dur"] < 42:
            v.append(f"card at {s['from'] / FPS:.1f}s shorter than 1.4 s")
        if s["kind"] in ("scene", "skit", "title") and not framing_ok(s, cast_by_id) and s["camera"]["move"] != "still":
            v.append(f"character cut by the frame at {s['from'] / FPS:.1f}s")
        if s["kind"] in ("scene", "title") and not s.get("set"):
            v.append("scene without a set")
    if end != plan["durationInFrames"]:
        v.append("shots do not cover the whole video")
    if shots[0]["kind"] == "card":
        v.append("the first frame must be a picture, not a card")
    if not any(s["kind"] == "title" for s in shots):
        v.append("no title card")
    m = metrics(plan)
    if sum(1 for s in shots if s["dur"] < 30 and s["kind"] != "skit") > 5:
        v.append(f"{m['under_1s']} shots under 1 s (max 5)")
    if m["builds"] < 3:
        v.append(f"only {m['builds']} staged builds (need one within 5 s and every 8-12 s)")
    return v
