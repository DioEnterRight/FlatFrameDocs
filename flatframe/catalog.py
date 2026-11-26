"""What the 2D engine can draw. The director prompt lists these, and beats.py rejects anything else, so a model can
never ask for an asset that does not exist (no broken / random objects)."""

SET_KINDS = ["office", "home", "lab", "archive", "bank", "courtroom", "newsroom", "workshop", "hall", "street",
             "city_night", "farm", "outback", "camp", "harbor", "desert", "field", "space"]
OUTDOOR = {"street", "city_night", "farm", "outback", "camp", "harbor", "desert", "field", "space"}
GRADES = ["day", "dusk", "night", "dinner", "period", "triumph", "dark"]
WALL_PATTERNS = ["panels", "brick", "stone", "wallpaper", "siding", "tiles", "stripes"]
FLOOR_PATTERNS = ["planks", "checker", "tiles", "carpet", "concrete"]

PROPS = ["desk", "chair", "filing_cabinet", "bookshelf", "lamp_desk", "lamp_floor", "plant", "clock_wall", "calendar_wall",
         "picture_frame", "plaque", "pinned_paper", "rotary_phone", "typewriter", "radio_old", "tv_old", "computer", "safe",
         "vault_door", "crate", "barrel", "sack", "money_stack", "coin", "gold_bar", "document", "letter", "newspaper",
         "book", "map_scroll", "globe", "telescope", "microscope", "flask", "lightbulb", "gear", "magnifier", "key",
         "briefcase", "trophy", "medal", "flag", "sign_post", "banner", "chalkboard", "easel_chart", "podium",
         "microphone", "camera_old", "car_old", "truck", "train", "ship", "plane", "rocket", "bicycle", "cannon",
         "machine_gun", "tent", "house", "factory", "tower", "bridge", "lighthouse", "windmill", "tree", "bush", "rock",
         "fence", "wire_fence", "haystack", "wheat", "mailbox", "lamppost", "statue", "pyramid", "satellite", "ice_block",
         "bottle", "ballot_box", "scales", "hourglass", "dice", "label_box"]
BIG_PROPS = {"car_old", "truck", "train", "ship", "plane", "rocket", "tent", "house", "factory", "tower", "bridge",
             "lighthouse", "windmill", "tree", "pyramid", "statue", "vault_door", "bookshelf"}
CREATURES = ["big_bird", "bird", "dog", "cat", "rat", "fish"]
HAIR = ["side_part", "beanie", "long", "bun", "bald", "curly", "slouch_hat", "cap", "hard_hat", "top_hat", "bowler"]
OUTFITS = ["suit", "uniform", "sweater", "labcoat", "dress", "overalls", "jacket"]
SKINS = ["#F1C9A5", "#E8B48A", "#D9A27A", "#C68B5E", "#A86F48", "#8A5A3B", "#6B4430"]
EXPRS = ["neutral", "happy", "surprised", "thinking", "concerned", "angry", "sad", "deadpan", "panic"]
POSES = ["idle", "talking", "pointing", "holding", "walking", "cheering", "shrugging", "running"]
SHOTS = ["scene", "skit", "insert", "map", "tabletop", "triptych"]   # cards and the title are placed by the compiler
MOVES = ["push", "pull", "pan", "tilt", "still"]
TIMINGS = ["creep", "creep_punch", "settle"]
FRAMINGS = ["wide", "medium", "close"]
BUILDS = ["stack", "side_slide", "slam_sticker", "counter", "compare", "state_flip", "glow_on", "drop_puff", "grow",
          "tag_vanish", "timeline"]
ENTRIES = ["slide", "drop", "grow", "slam", "switch"]
TEXT_KINDS = ["strip", "stamp", "quote", "calendar"]
# effects by scene tone (skill 5.4a table)
FX_BY_TONE = {
    "calm": ["dust"], "tension": ["flicker", "smoke", "sparks"], "night": ["mist"], "outdoors": ["leaves"],
    "loss": ["rain", "mist", "papers"], "technology": ["screen_glow", "sparks"], "industry": ["steam", "smoke"],
}
FX = sorted({x for v in FX_BY_TONE.values() for x in v} | {"snow"})

# words in a line -> a prop that can show it (used by the offline director and to fill sparse beats)
KEYWORD_PROPS = {
    "gun": "machine_gun", "guns": "machine_gun", "machine": "machine_gun", "rifle": "machine_gun", "army": "truck",
    "soldier": "truck", "truck": "truck", "money": "money_stack", "dollar": "money_stack", "dollars": "money_stack",
    "cash": "money_stack", "coin": "coin", "coins": "coin", "gold": "gold_bar", "bank": "safe", "vault": "vault_door",
    "letter": "letter", "report": "document", "paper": "document", "document": "document", "law": "scales",
    "court": "scales", "judge": "scales", "newspaper": "newspaper", "news": "newspaper", "headline": "newspaper",
    "book": "book", "map": "map_scroll", "ship": "ship", "boat": "ship", "sea": "ship", "train": "train",
    "railway": "train", "plane": "plane", "flight": "plane", "rocket": "rocket", "space": "satellite", "car": "car_old",
    "bike": "bicycle", "bridge": "bridge", "tower": "tower", "factory": "factory", "farm": "haystack",
    "farmers": "haystack", "wheat": "wheat", "crops": "wheat", "fence": "wire_fence", "tree": "tree", "house": "house",
    "phone": "rotary_phone", "radio": "radio_old", "tv": "tv_old", "television": "tv_old", "computer": "computer",
    "time": "hourglass", "clock": "hourglass", "idea": "lightbulb", "invention": "lightbulb", "machine_part": "gear",
    "engine": "gear", "secret": "key", "key": "key", "lab": "flask", "chemical": "flask", "scientist": "microscope",
    "telescope": "telescope", "star": "telescope", "vote": "ballot_box", "election": "ballot_box", "medal": "medal",
    "prize": "trophy", "winner": "trophy", "flag": "flag", "war": "cannon", "ice": "ice_block", "bottle": "bottle",
    "beer": "barrel", "box": "crate", "dice": "dice", "luck": "dice", "chart": "easel_chart", "price": "easel_chart",
    "speech": "microphone", "camera": "camera_old", "photo": "camera_old", "lighthouse": "lighthouse", "mill": "windmill",
}
KEYWORD_SETS = {
    "farm": "farm", "farmers": "farm", "wheat": "farm", "crops": "farm", "army": "camp", "soldiers": "camp",
    "military": "camp", "desert": "desert", "egypt": "desert", "outback": "outback", "australia": "outback",
    "bank": "bank", "money": "bank", "court": "courtroom", "trial": "courtroom", "law": "courtroom",
    "newspaper": "newsroom", "reporters": "newsroom", "lab": "lab", "scientist": "lab", "experiment": "lab",
    "factory": "workshop", "workers": "workshop", "engineer": "workshop", "city": "street", "street": "street",
    "town": "street", "night": "city_night", "ship": "harbor", "sea": "harbor", "port": "harbor", "space": "space",
    "moon": "space", "government": "hall", "parliament": "hall", "minister": "hall", "library": "archive",
    "records": "archive", "home": "home", "family": "home", "office": "office", "company": "office", "field": "field",
}
