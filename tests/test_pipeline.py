"""Schedule, research verification, script gates, voice helpers, the beat compiler, ideas."""
import json
import datetime as dt

import pytest

from flatframe import beats, facts, gate, ideas, research, schedule, script_check, sources, voice
from flatframe.common import IST


# ---------------------------------------------------------------- schedule
def test_eight_slots_a_day_in_ist(cfg):
    assert schedule.times(cfg) == ["01:30", "04:30", "07:30", "10:30", "13:30", "16:30", "19:30", "22:30"]


def test_first_time_configurable(cfg):
    cfg["schedule"]["first"] = "02:15"
    assert schedule.times(cfg)[0] == "02:15" and len(schedule.times(cfg)) == 8


def test_due_window_and_midnight(cfg):
    now = dt.datetime(2026, 11, 27, 0, 10, tzinfo=IST)
    slot, missed = schedule.due(cfg, set(), now)
    assert slot is None and "2026-11-26 22:30" in missed
    slot, _ = schedule.due(cfg, set(), dt.datetime(2026, 11, 26, 22, 45, tzinfo=IST))
    assert slot == "2026-11-26 22:30"


def test_to_make_respects_ahead_and_per_run(cfg):
    now = dt.datetime(2026, 11, 26, 9, 0, tzinfo=IST)
    assert schedule.to_make(cfg, 0, now) == 1
    assert schedule.to_make(cfg, 2, now) == 0


def test_make_gate_and_paused(cfg):
    hist = {"videos": []}
    now = dt.datetime(2026, 11, 26, 9, 0, tzinfo=IST)
    assert gate.make_gate(cfg, hist, now)
    cfg["paused"] = True
    assert not gate.make_gate(cfg, hist, now) and not gate.post_gate(cfg, hist, now)


# ---------------------------------------------------------------- facts / research
def test_quote_check_is_literal():
    text = "The emus were reported to number about 20,000 [3]. Rain delayed the operation."
    assert facts.quote_in("The emus were reported to number about 20,000.", text)
    assert not facts.quote_in("The emus were reported to number about 30,000.", text)


def test_numbers_and_support():
    assert facts.numbers("nineteen thirty-two, 9,860 rounds and 2.3 million") >= {1932.0, 9860.0, 2300000.0}
    assert facts.supports("Soldiers fired 2,500 rounds by 8 November", "By November 8, a total of 2500 rounds of ammunition had been fired by soldiers.")
    assert not facts.supports("Soldiers fired 2,500 rounds by 8 November", "By November 8, a total of 3000 rounds had been fired by soldiers.")


def test_conflict_detection():
    c = "The soldiers fired 2,500 rounds of ammunition"
    assert facts.conflicting(c, "The soldiers fired 4,000 rounds of ammunition in the end.")


def test_script_number_must_be_backed():
    assert facts.script_violations("They fired 9,000 rounds.", "fired 2,500 rounds") == ["number 9000"]
    assert facts.script_violations("Then Meredith quit.", "Major Meredith reported") == []
    assert facts.script_violations("Then Napoleon quit.", "Major Meredith reported") == ["name 'napoleon'"]


def test_site_independence():
    assert sources.site_of("https://web.archive.org/web/2019/https://www.bbc.co.uk/news/x") == "bbc.co.uk"
    assert sources.is_wiki("https://en.m.wikipedia.org/wiki/X") and not sources.usable_source("https://wikiwand.com/en/X")


class FakeWeb:
    def __init__(self, article, pages):
        self.article, self.pages = article, pages

    def wiki_page(self, title):
        return {"title": title, "pageid": 1, "url": "https://en.wikipedia.org/wiki/X", "text": self.article, "links": list(self.pages)}

    def wiki_search(self, q):
        return []

    def fetch_text(self, url):
        return self.pages[url]


class FakeSession:
    def __init__(self, claims):
        self.claims = claims

    def json(self, role, system, user, **kw):
        if "verdicts" in user:
            return {"verdicts": []}, "fake-model"
        return {"claims": self.claims}, "fake-model"


ARTICLE = ("In 1932 the army sent soldiers with two machine guns against emus in Western Australia. " * 2 +
           "The soldiers fired 2,500 rounds by 8 November. The emus scattered into small groups whenever the guns opened fire. "
           "Meredith reported that 986 emus were killed during the campaign. ") * 12


def test_research_verifies_only_with_two_independent_sites(cfg):
    cfg["research"]["min_verified_claims"] = 2
    pages = {
        "https://a.com/1": "Long page. " * 150 + "By 8 November the soldiers had fired 2,500 rounds at the emus. Meredith reported that 986 emus were killed.",
        "https://b.org/2": "Other page. " * 150 + "Around 8 November, soldiers had fired 2,500 rounds. The emus scattered into small groups whenever the guns fired.",
        "https://c.net/3": "Third. " * 250 + "Meredith reported 986 emus killed in the campaign. The emus scattered into small groups when the guns fired.",
    }
    claims = [
        {"text": "The soldiers fired 2,500 rounds by 8 November.", "role": "escalation", "wiki_quote": "The soldiers fired 2,500 rounds by 8 November."},
        {"text": "Meredith reported 986 emus killed.", "role": "payoff", "wiki_quote": "Meredith reported that 986 emus were killed during the campaign."},
        {"text": "The emus scattered into small groups whenever the guns opened fire.", "role": "mystery", "wiki_quote": "The emus scattered into small groups whenever the guns opened fire."},
        {"text": "The army had 40 machine guns.", "role": "hook", "wiki_quote": "The army had 40 machine guns."},   # not in the article
    ]
    idea = {"title": "Emu", "question": "q", "wikipedia_title": "Emu War"}
    rec = research.research(cfg, FakeSession(claims), idea, web=FakeWeb(ARTICLE, pages))
    by_text = {c["text"]: c for c in rec["claims"]}
    assert "The army had 40 machine guns." not in by_text            # invented quote dropped
    assert by_text["The soldiers fired 2,500 rounds by 8 November."]["status"] == "verified"
    assert by_text["Meredith reported 986 emus killed."]["status"] == "verified"
    assert rec["verdict"] == "accepted"


def test_research_rejects_unverifiable_topic(cfg):
    pages = {"https://a.com/1": "Nothing relevant here. " * 60}
    claims = [{"text": "Meredith reported 986 emus killed.", "role": "payoff", "wiki_quote": "Meredith reported that 986 emus were killed during the campaign."}]
    rec = research.research(cfg, FakeSession(claims), {"title": "E", "question": "q", "wikipedia_title": "Emu War"}, web=FakeWeb(ARTICLE, pages))
    assert rec["verdict"].startswith("rejected")


# ---------------------------------------------------------------- script gates
def test_sample_script_passes(cfg, sample):
    assert script_check.check(cfg, sample["script"]["script"], research.verified_claims(sample["research"])) == []


@pytest.mark.parametrize("mutate,needle", [
    (lambda s: s["lines"][0].update(text="Hey guys, welcome back to a story about birds and guns."), "hook"),
    (lambda s: s["lines"][1].update(text="Two Lewis guns. 50,000 rounds of ammunition."), "facts no cited claim"),
    (lambda s: s["lines"][2].update(claims=["C10"]), "gives away the answer"),
    (lambda s: s["lines"].append({"section": "ending", "speaker": "narrator", "text": "Subscribe for more.", "claims": [], "card": False}), "call to action"),
    (lambda s: [l.update(speaker="narrator") for l in s["lines"]], "skit"),
    (lambda s: s.update(title="Why?"), "title"),
])
def test_script_gates_catch_problems(cfg, sample, mutate, needle):
    s = sample["script"]["script"]
    mutate(s)
    probs = script_check.check(cfg, s, research.verified_claims(sample["research"]))
    assert any(needle in p for p in probs), probs


# ---------------------------------------------------------------- voice helpers
def test_numbers_spoken_naturally():
    assert voice.speak_numbers("In 1932, 9,860 rounds.") == "In nineteen thirty-two, nine thousand eight hundred sixty rounds."
    assert voice.speak_numbers("$2.3 million, 45%") == "two point three million dollars, forty-five percent"


def test_gap_fitter_never_touches_speech(cfg):
    lines = [{"section": "build", "speaker": "narrator", "card": False}] * 18
    gap, total = voice.fit_gap(cfg, lines, [2.2] * 18)
    assert cfg["voice"]["min_gap"] <= gap <= cfg["voice"]["max_gap"]
    assert abs(total - 45) < abs(0.15 + 2.2 * 18 + 0.9 + 17 * cfg["voice"]["gap_seconds"] - 45) + 1e-6


# ---------------------------------------------------------------- beat compiler
def fake_timing(script, wps=2.6):
    t, lines = 0.15, []
    for i, l in enumerate(script["lines"]):
        words = l["text"].split()
        ws = []
        for w in words:
            d = 0.12 + 0.045 * len(w)
            ws.append({"w": w, "s": round(t, 3), "e": round(t + d, 3)})
            t += d
        lines.append({"i": i, "speaker": l["speaker"], "section": l["section"], "text": l["text"], "card": l["card"],
                      "start": ws[0]["s"], "end": ws[-1]["e"], "words": ws, **({"env": [0.5] * 20} if l["speaker"] != "narrator" else {})})
        t += 0.3
    end = round(t + 0.05, 3)
    return {"duration": round(end + 3.0, 3), "narration_end": end, "lines": lines, "wpm": 160, "engine": "fake",
            "outro": {"start": end, "speech_end": end + 2.2, "end": end + 3.0, "text": "Follow FlatFrameDocs and @outrichguy", "env": [0.5] * 60}}


def test_compiled_sample_obeys_rules(cfg, sample):
    sc = sample["script"]["script"]
    plan, rep = beats.compile_plan(cfg, sc, fake_timing(sc), sample["board"], research.verified_claims(sample["research"]), 1, "t")
    assert rep["violations"] == []
    shots = plan["shots"]
    assert shots[0]["kind"] != "card" and any(p.get("glow") for p in shots[0]["props"])   # frame 0: hero object
    assert sum(s["dur"] for s in shots) == plan["durationInFrames"]
    assert all(s["dur"] >= 42 for s in shots if s["kind"] == "card")
    assert sum(1 for s in shots if s["kind"] == "title") == 1
    assert rep["metrics"]["builds"] >= 3
    cast = {c["id"]: c for c in plan["cast"]}
    assert all(beats.framing_ok(s, cast) or s["camera"]["move"] == "still" for s in shots if s["kind"] in ("scene", "skit", "title"))
    for k in range(3, len(shots)):
        moves = [s["camera"]["move"] for s in shots[k - 3:k + 1] if s["kind"] not in ("card", "skit")]
        assert not (len(moves) == 4 and len(set(moves)) == 1)


def test_years_are_never_counted(cfg, sample):
    sc = sample["script"]["script"]
    board = dict(sample["board"], beats=[])
    plan, _ = beats.compile_plan(cfg, sc, fake_timing(sc), board, research.verified_claims(sample["research"]), 1, "t")
    assert not any(s.get("build", {}).get("value") == 1932 for s in plan["shots"])


def test_offline_director_still_valid(cfg, sample):
    from flatframe import director
    sc = sample["script"]["script"]
    t = fake_timing(sc)
    board = director.offline_board(sc, t, [])
    plan, rep = beats.compile_plan(cfg, sc, t, board, research.verified_claims(sample["research"]), 2, "t")
    assert rep["violations"] == []


def test_unknown_assets_are_rejected(cfg, sample):
    sc = sample["script"]["script"]
    board = {"cast": [{"id": "x", "hair": "mohawk-of-doom", "outfit": "spacesuit"}], "hero_object": {"prop": "laser_shark"},
             "locations": [{"id": "L1", "kind": "moon_base_9"}], "beats": [{"line": 1, "props": [{"kind": "laser_shark", "x": 0.5}]}]}
    plan, _ = beats.compile_plan(cfg, sc, fake_timing(sc), board, research.verified_claims(sample["research"]), 3, "t")
    from flatframe import catalog
    for s in plan["shots"]:
        for p in s.get("props", []):
            assert p["kind"] in catalog.PROPS
        if s.get("set"):
            assert s["set"]["kind"] in catalog.SET_KINDS


# ---------------------------------------------------------------- ideas
def test_idea_filters(cfg):
    past = ideas.past({"videos": [{"title": "The Australian Army Lost a War to Emus", "question": "How did birds beat machine guns?",
                                   "article": "Emu War", "category": "strange but documented historical events"}]})
    base = {"title": "The Army That Lost a War to Emus", "question": "How did birds beat soldiers with machine guns?",
            "hook": "Soldiers lost to birds.", "payoff": "p", "category": "unusual economic events", "wikipedia_title": "Emu War"}
    assert ideas.filter_reason(cfg, base, past)
    assert "hook" in ideas.filter_reason(cfg, dict(base, title="Totally different thing here", question="what else entirely", wikipedia_title="X", hook="Hey guys this one is wild"), past)
    ok = dict(base, title="The Town That Paid Its Taxes in Cheese", question="Why did a town pay tax in cheese?", wikipedia_title="Cheese tax", hook="A town paid taxes in cheese.")
    assert ideas.filter_reason(cfg, ok, past) is None


def test_weighted_score(cfg):
    assert ideas.weighted(cfg, {k: 10 for k in ideas.CRITERIA}) == 10.0


def test_outro_captions_and_corner_tag(cfg, sample):
    sc = sample["script"]["script"]
    t = fake_timing(sc)
    plan, rep = beats.compile_plan(cfg, sc, t, sample["board"], research.verified_claims(sample["research"]), 1, "t")
    assert rep["violations"] == []
    last = plan["shots"][-1]
    assert last["kind"] == "outro" and last["outro"]["text"] == "Follow FlatFrameDocs and @outrichguy"
    assert last["actors"][0]["talk"]["env"] and last["from"] + last["dur"] == plan["durationInFrames"]
    assert plan["brand"]["corner"] == "@outrichguy"
    card_words = {w["w"] for l in t["lines"] if l["card"] for w in l["words"]}
    cap_words = [w["w"] for c in plan["captions"] for w in c["words"]]
    assert cap_words and all(len(c["words"]) <= 3 for c in plan["captions"])
    assert not (set(cap_words) & card_words - {w for l in t["lines"] if not l["card"] for w in (x["w"] for x in l["words"])})


def test_voice_appends_spoken_outro(cfg, tmp_path, monkeypatch):
    import numpy as np
    seen = []

    def fake_render(cfg_, lines, test=False):
        seen.extend(lines)
        return "edge", [(np.full(int(voice.SR * 2.2), 0.1, dtype=np.float32), [(0.0, 0.1)] * len(l["text"].split())) for l in lines]
    monkeypatch.setattr(voice, "render_lines", fake_render)
    script = {"lines": [{"section": "build", "speaker": "narrator", "card": False, "text": "Word " * 6} for _ in range(18)]}
    t = voice.synthesize(cfg, script, tmp_path)
    assert seen[-1]["spoken"] == cfg["brand"]["outro_spoken"] and seen[-1]["speaker"] == "outro"
    assert t["outro"]["start"] == t["narration_end"] and t["duration"] >= t["narration_end"] + cfg["brand"]["outro_seconds"] - 0.05
    assert len(t["lines"]) == 18


def test_volume_jump_check_ignores_speech_onsets_but_catches_bursts(tmp_path):
    import wave

    import numpy as np
    from flatframe import qa

    def wav(path, x):
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())

    t = np.arange(32000) / 16000
    bed = 0.015 * np.sin(2 * np.pi * 220 * t)                          # music bed around -40 dB
    speech = np.where(t >= 1.0, 0.3 * np.sin(2 * np.pi * 150 * t), 0)  # voice comes back after a pause
    wav(tmp_path / "voice.wav", speech)
    wav(tmp_path / "speech.wav", bed + speech)
    assert qa.short_term_jumps(tmp_path / "speech.wav", tmp_path / "voice.wav") < 22
    wav(tmp_path / "quiet.wav", np.zeros_like(t))
    wav(tmp_path / "burst.wav", bed + np.where(t >= 1.0, 0.4 * np.sin(2 * np.pi * 90 * t), 0))  # a boom over the bed
    assert qa.short_term_jumps(tmp_path / "burst.wav", tmp_path / "quiet.wav") > 22


def test_model_quote_with_small_slips_counts_as_the_shown_passage():
    from flatframe import facts
    passage = "In November 1944 the Japanese launched about 9,300 balloons toward North America."
    assert facts.near_copy("In November 1944, the Japanese launched about 9,300 balloons towards North America.", passage)
    assert not facts.near_copy("In November 1944 the Japanese launched about 12,000 balloons toward North America.", passage)
    assert not facts.near_copy("Balloons were launched.", passage)


def test_html_served_as_pdf_is_not_parsed_as_pdf(cfg, monkeypatch):
    from flatframe import sources

    class R:
        headers = {"Content-Type": "application/pdf"}
        encoding = "utf-8"

        def raise_for_status(self):
            pass

        class raw:
            @staticmethod
            def read(n, decode_content=True):
                return b"<html><body>nope</body></html>"

    w = sources.Web(cfg)
    monkeypatch.setattr(w.s, "get", lambda *a, **k: R())
    with pytest.raises(ValueError, match="not one"):
        w.fetch_text("https://example.com/report.pdf")


def test_fact_split_over_two_sentences_is_found():
    from flatframe import facts
    src = "Filler sentence about nothing at all here. In August 1976 the soldiers arrived at the bridge. They cut down the poplar tree in 42 minutes."
    assert facts.best_support("Soldiers cut down the poplar tree at the bridge in August 1976.", src)


def test_junk_and_duplicate_sources_are_skipped(cfg):
    assert not sources.usable_source("https://tools.wmflabs.org/x") and not sources.usable_source("https://x.toolforge.org/y")
    assert not sources.usable_source("https://podcasts.apple.com/us/podcast/1")
    text = "A real page with a lot of words in it. " * 60
    pages = {"https://a.com/1": text, "https://b.com/2": text, "https://c.com/3": "tiny"}
    got = sources.fetch_sources(FakeWeb("", pages), list(pages), 10)
    assert [s["ok"] for s in got] == [True, False, False]


def test_wikipedia_outage_rejects_the_topic_instead_of_crashing(cfg):
    class Down(FakeWeb):
        def wiki_page(self, title):
            raise ConnectionError("wikipedia down")
    with pytest.raises(research.StageError, match="did not answer"):
        research.research(cfg, FakeSession([]), {"title": "X", "question": "q", "wikipedia_title": "X"}, web=Down("", {}))


def test_curated_topics_are_valid_and_used_before_brainstorming(cfg, monkeypatch, tmp_path):
    from flatframe import ideas
    cfg["ideas"]["curated"] = "first"
    data = json.loads(ideas.CURATED.read_text(encoding="utf-8"))
    p = ideas.past({"videos": []})
    assert len(data["topics"]) >= 30
    for t in data["topics"]:
        assert ideas.filter_reason(cfg, t, p) is None, t["title"]
    monkeypatch.setattr(ideas, "BANK", tmp_path / "ideas.json")

    class NoModel:
        def json(self, *a, **k):
            raise AssertionError("brainstorm should not run while curated topics are left")
    ranked = ideas.shortlist(cfg, NoModel(), {"videos": []})
    assert len(ranked) >= int(cfg["ideas"]["research_attempts"]) and ranked[0]["pitched_by"] == "curated"
    used = {"videos": [{"title": ranked[0]["title"], "question": ranked[0]["question"], "article": ranked[0]["wikipedia_title"]}]}
    assert ranked[0]["title"] not in [i["title"] for i in ideas.shortlist(cfg, NoModel(), used)]


def test_models_pitch_their_own_ideas_and_curated_is_only_the_last_try(cfg, monkeypatch, tmp_path):
    from flatframe import ideas
    monkeypatch.setattr(ideas, "BANK", tmp_path / "ideas.json")
    topics = [("Volcano", "lava swallowed fishing villages"), ("Lighthouse", "keepers vanished overnight"),
              ("Glacier", "ancient arrows melted free"), ("Canal", "engineers moved mountains"), ("Comet", "tails frightened sailors")]
    own = [{"title": f"The {a} Where {b}", "question": f"How {b}?", "hook": "A strange thing happened once.",
            "payoff": "Because of a reason.", "category": f"cat {a}", "wikipedia_title": f"{a} article"} for a, b in topics]

    class Models:
        def json(self, role, system, user, **k):
            if role == "ideator":
                return {"ideas": [dict(i) for i in own]}, "model-a"
            return {"scores": [{"n": n, **{c: 9 for c in ideas.CRITERIA}} for n in range(len(own))]}, "model-b"
    ranked = ideas.shortlist(cfg, Models(), {"videos": []})
    k = int(cfg["ideas"]["research_attempts"])
    assert all(i["pitched_by"] == "model-a" for i in ranked[:k - 1])
    assert ranked[k - 1]["pitched_by"] == "curated"


def test_every_model_role_is_taught_from_the_skill():
    from flatframe import lessons
    for role, needle in (("ideator", "Title rules"), ("writer", "Script DNA"), ("director", "Visual beats"), ("judge", "Rules that always hold")):
        text = lessons.for_role(role, 3)
        assert needle in text, role
        assert "Search the web" not in text and "End by asking" not in text
    assert "The Australian Army Lost a War to Emus" in lessons.for_role("writer")
