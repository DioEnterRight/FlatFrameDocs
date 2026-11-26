"""LESSONS: what makes the free models write like the 2D Documentary Skill instead of like a generic chatbot.

Every model call's system prompt gets the matching part of the skill itself (.claude/skills/2d-documentory-skill/SKILL.md)
plus worked examples of the level we want:

  ideator / idea critic : Step 1 (title patterns + rules) and 4 hand-picked topics as examples of the bar (never to copy)
  writer / script critic: Step 3 Script DNA and the full Emu War sample script (samples/emu-war/script.json)
  director              : 5.3 visual beats, 5.4a effects and a slice of the sample storyboard (camera rules live in code)
  judge                 : 5.6 render checks and "Rules that always hold"

The sections are cut out of SKILL.md by heading at run time, so editing the skill teaches the models immediately.
Code gates (script_check.py, beats.py, qa.py) still enforce the hard rules; the lessons raise the level of what the
models propose in the first place.
"""
import json
import random
import re

from .common import ROOT, read_json

SKILL = ROOT / ".claude" / "skills" / "2d-documentory-skill" / "SKILL.md"
SAMPLE = ROOT / "samples" / "emu-war"
CURATED = ROOT / "prompts" / "curated_topics.json"

ROLE_SECTIONS = {
    "ideator": ["## Step 1 - Title ideas"],
    "idea_critic": ["## Step 1 - Title ideas"],
    "writer": ["### Script DNA"],
    "script_critic": ["### Script DNA"],
    "director": ["### 5.3 Visual beats", "### 5.4a Environmental effects system"],   # camera (5.5) is enforced by beats.py
    "judge": ["### 5.6 Render", "## Rules that always hold"],
}
# the parts of Step 1 that are about a chat with a person (web search, numbered sections, asking the user) are not tasks
# for a scheduled bot; the title patterns and title rules are what the ideator learns
DROP_LINES = ("search the web", "present two numbered", "**section a", "**section b")
DROP_TEXT = ("The user's seed titles are the foundation. ", " End by asking the user to pick a number or give their own topic.")


def _bot_only(text):
    lines = [l for l in text.splitlines() if not l.strip().lower().startswith(DROP_LINES)]
    text = "\n".join(lines)
    for t in DROP_TEXT:
        text = text.replace(t, "")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def section(heading):
    """The text under one heading of SKILL.md, up to the next heading of the same or a higher level."""
    text = SKILL.read_text(encoding="utf-8")
    i = text.find(heading + "\n")
    if i < 0:
        raise ValueError(f"skill heading not found: {heading!r}")
    level = len(heading) - len(heading.lstrip("#"))
    rest = text[i + len(heading) + 1:]
    m = re.search(r"(?m)^#{1,%d} " % level, rest)
    return heading + "\n" + (rest[: m.start()] if m else rest).strip()


def _examples_topics(seed, n=4):
    topics = read_json(CURATED, {"topics": []})["topics"]
    pick = random.Random(seed).sample(topics, min(n, len(topics)))
    keep = ("title", "question", "hook", "payoff", "why_visual", "visual_metaphors")
    return json.dumps([{k: t[k] for k in keep if k in t} for t in pick], ensure_ascii=False, indent=1)


def _example_script():
    sc = read_json(SAMPLE / "script.json", {}).get("script", {})
    return json.dumps({"title": sc.get("title"), "lines": [{k: l.get(k) for k in ("section", "speaker", "text", "card") if k in l}
                                                          for l in sc.get("lines", [])]}, ensure_ascii=False, indent=1)


def _example_board(n=6):
    board = read_json(SAMPLE / "board.json", {})
    shots = board.get("shots") or board.get("beats") or []
    return json.dumps({**{k: v for k, v in board.items() if k not in ("shots", "beats")}, "shots": shots[:n]},
                      ensure_ascii=False, indent=1)[:6000]


def for_role(role, seed=0):
    """Text appended to a role's system prompt."""
    parts = [_bot_only(section(h)) for h in ROLE_SECTIONS.get(role, [])]
    if role in ("ideator", "idea_critic"):
        parts.append("EXAMPLES OF THE LEVEL WE WANT (true, well documented, concrete, visual; a paradox stated as fact "
                     "in the hook; a real answer in the payoff). Never pitch these exact stories:\n" + _examples_topics(seed))
    if role in ("writer", "script_critic"):
        parts.append("A FINISHED SCRIPT AT THE LEVEL WE WANT (rhythm, line length, hook, skit, reveal, ending). Learn the "
                     "craft, never reuse its words or facts:\n" + _example_script())
    if role == "director":
        parts.append("THE FIRST SHOTS OF A FINISHED STORYBOARD (structure and variety to learn from; your story needs its "
                     "own sets, props and moves):\n" + _example_board())
    if not parts:
        return ""
    return "\n\n=== HOUSE STYLE: from the 2D Documentary Skill. Follow it. ===\n\n" + "\n\n".join(parts)


def system(name, role, seed=0):
    """A prompts/<name> system prompt with the role's lessons appended."""
    from .common import prompt
    return prompt(name) + for_role(role, seed)
