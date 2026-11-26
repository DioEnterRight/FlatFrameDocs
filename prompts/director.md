Storyboard this 45-second vertical (9:16) documentary. One beat per script line.

TITLE: {title}
HERO OBJECT (the writer's idea): {hero}
LINES (timed narration):
{lines}
VERIFIED FACTS (labels and numbers on screen may only come from these):
{claims}
CATALOG (use these names exactly):
{catalog}
Hero objects used by recent videos (pick something different if you can): {recent}

HOUSE RULES (from the 2D Documentary Skill; the compiler enforces them, so follow them to keep your choices):
- Frame 0: the protagonist WITH the hero object, medium framing, already moving. No establishing shot, no logo.
- Every beat is a complete place: a set from the catalog with 1-3 story props. 4-7 locations in total; inserts count.
  Re-use a location for every beat set there, and change one thing on each return (grade or props).
- Suspense (2-10 s) may be GOOFY and absurd while the facts stay serious: oversized objects, crowds of creatures,
  exaggerated reactions, ridiculous little characters, literal visual metaphors. Do not make every suspense beat dark.
- Tell lines with objects and actions, not captions. Props enter ON the word they illustrate (on_word), with one
  entry: slide, drop, grow, slam or switch. Use builds (staged objects) about every 8-12 s, the first within 5 s:
  counter (a number counts on a board; only numbers from the facts), stack, side_slide (one item per spoken item),
  slam_sticker (a date or verdict), compare (panels with values), state_flip, glow_on, drop_puff, grow, timeline.
- Overlay text only for a place, a date or a name the picture cannot show: max 3 words, kinds strip / stamp / calendar.
  Never restate the narration on screen. Most lettering lives in the world: set "signs", prop "label".
- Shots: scene (default), skit (dialogue lines; the compiler frames them), insert (one object on a patterned wall,
  2-4 s, one every ~20 s), map (whenever the story changes country: give "country" and optional "pins" with lon/lat
  and "on_word"), tabletop (a document or map seen from above with objects dropping on it), triptych (three panels when
  the narrator lists three things).
- Camera per beat: move push (most), pan, tilt, pull, still; timing creep / creep_punch (punch_word = the key word) /
  settle; framing wide (places, groups, "everyone"), medium (one or two people), close (only when the line is about that
  face or object). Groups of 3+ stay wide. Never the same move 4 beats running.
- Cast: people (hair, outfit, outfit_color, accent_color, glasses, skin from the catalog; ONE signature per person;
  real people are generic characters with their real name in "name") and creatures (creature from the catalog).
  Give each character in a beat x (0.1-0.9 across the set), expr, pose and facing (left/right/front/back) so people in
  a scene look at each other. A crowd of identical extras or animals: "count": 2-8.
- Effects: at most on a third of beats, matched to tone (effects_by_tone), each with a purpose.
- Transitions: hard cuts; "whip" at most twice for energy, never into a card.
- The last beat returns to the opening image (same location, the hero object). 

Return JSON:
{"cast": [{"id": "short_id", "name": "...", "type": "person", "hair": "...", "outfit": "...", "outfit_color": "#RRGGBB",
           "accent_color": "#RRGGBB", "skin": "#...", "glasses": "none"},
          {"id": "...", "type": "creature", "creature": "big_bird", "color": "#RRGGBB"}],
 "hero_object": {"prop": "one prop from the catalog"},
 "title_accent": "one word of the title to colour",
 "locations": [{"id": "L1", "kind": "...", "grade": "...", "wall": "optional pattern", "signs": ["short lettering"]}],
 "beats": [{"line": 1, "shot": "scene", "location": "L1",
            "cast": [{"id": "...", "x": 0.4, "expr": "...", "pose": "...", "facing": "right", "count": 1, "hold": "optional prop"}],
            "props": [{"kind": "...", "x": 0.65, "entry": "drop", "on_word": "word", "label": "optional"}],
            "build": {"recipe": "counter", "value": 20000, "label": "emus", "on_words": ["20,000"], "items": [{"label": "...", "kind": "...", "value": 0}]},
            "text": {"kind": "stamp", "text": "NOV 1932", "on_word": "1932"},
            "map": {"country": "Australia", "pins": [{"lon": 0, "lat": 0, "label": "...", "on_word": "..."}]},
            "panels": [{"label": "...", "prop": "...", "on_word": "..."}],
            "camera": {"move": "push", "timing": "creep_punch", "framing": "medium", "punch_word": "..."},
            "effect": {"kind": "dust", "purpose": "a few words"},
            "transition": "cut"}]}
Omit keys you do not need in a beat.
