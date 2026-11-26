"""Deterministic fact tools. Models suggest; these functions decide.

  * quote_in(quote, text)      : a quote a model claims to have read really is in the source text
  * numbers(text)              : every number in a text as values (digits, '1,500', 'two thousand', '1.5 million')
  * supports(claim, sentence)  : does one source sentence carry the claim's numbers and most of its key terms?
  * script_violations(...)     : numbers / names in a narration line that no verified claim backs
"""
import re
import unicodedata

from .common import STOP

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
         "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
         "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
SCALES = {"hundred": 100, "thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000, "trillion": 1_000_000_000_000}
NUMWORD = set(UNITS) | set(TENS) | set(SCALES) | {"and", "a"}
ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
            "ninth": 9, "tenth": 10}


def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).lower()
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    s = re.sub(r"\[\d+\]", " ", s)                 # citation marks
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)        # 1,500 -> 1500
    s = re.sub(r"[^a-z0-9%$.' -]+", " ", s)
    return re.sub(r"\s+", " ", s).strip(" .")


def quote_in(quote, text):
    """True when the quote (ellipses allowed) appears, in order, in the text after normalisation."""
    q = str(quote or "").strip()
    if len(norm(q)) < 12:
        return False
    hay = norm(text)
    pos = 0
    for part in re.split(r"\.\.\.|…", q):
        p = norm(part)
        if not p:
            continue
        i = hay.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


def near_copy(quote, passage, min_ratio=0.9):
    """The quote is the passage (or a sentence of it) retyped with small slips: same numbers, >= 90 % similar."""
    from difflib import SequenceMatcher
    q = norm(quote)
    if len(q) < 12 or not numbers(quote) <= numbers(passage):
        return False
    for cand in [passage] + sentences(passage):
        if SequenceMatcher(None, q, norm(cand)).ratio() >= min_ratio:
            return True
    return False


def _words_to_number(tokens):
    total, cur, seen = 0, 0, False
    for t in tokens:
        if t in UNITS:
            cur += UNITS[t]
            seen = True
        elif t in TENS:
            cur += TENS[t]
            seen = True
        elif t == "hundred":
            cur = max(cur, 1) * 100
            seen = True
        elif t in SCALES:
            total += max(cur, 1) * SCALES[t]
            cur = 0
            seen = True
    return total + cur if seen else None


def numbers(text):
    """Set of numeric values mentioned in the text (years included). '2.3 million' -> 2300000."""
    s = norm(text)
    vals = set()
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(hundred|thousand|million|billion|trillion)?", s):
        v = float(m.group(1))
        if m.group(2):
            v *= SCALES[m.group(2)]
        vals.add(round(v, 3))
    words = re.findall(r"[a-z]+", re.sub(r"\d+(?:\.\d+)?\s*(hundred|thousand|million|billion|trillion)", " ", s))
    i = 0
    while i < len(words):
        if words[i] in NUMWORD and words[i] not in ("and", "a"):
            j = i
            while j < len(words) and words[j] in NUMWORD:
                j += 1
            seq = [w for w in words[i:j] if w not in ("and", "a")]
            v = _words_to_number(seq)
            if v is not None:
                vals.add(float(v))
                # spoken years: "nineteen thirty-two" -> 1932
                if len(seq) >= 2 and seq[0] in UNITS and 10 <= UNITS[seq[0]] <= 20:
                    rest = _words_to_number(seq[1:])
                    if rest is not None and rest < 100:
                        vals.add(float(UNITS[seq[0]] * 100 + rest))
            i = j
        else:
            i += 1
    return vals


def key_terms(text):
    out = set()
    for w in re.findall(r"[a-z][a-z'-]+", norm(text)):
        w = w.strip("'-")
        if len(w) < 3 or w in STOP or w in NUMWORD or w in ORDINALS:
            continue
        out.add(w[:-1] if w.endswith("s") and len(w) > 4 else w)
    return out


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])|\n+", str(text))
    return [p.strip() for p in parts if 25 <= len(p.strip()) <= 700]


def supports(claim, sentence, min_overlap=0.5):
    """A sentence supports a claim when it contains ALL the claim's numbers and at least `min_overlap` of its key
    terms (and at least 3 of them)."""
    need_nums = numbers(claim)
    if need_nums and not need_nums <= numbers(sentence):
        return False
    terms = key_terms(claim)
    if not terms:
        return False
    shared = terms & key_terms(sentence)
    return len(shared) >= min(3, len(terms)) and len(shared) / len(terms) >= min_overlap


def best_support(claim, text, min_overlap=0.5):
    best, score = None, 0.0
    terms = key_terms(claim)
    for s in sentences(text):
        if supports(claim, s, min_overlap):
            sc = len(terms & key_terms(s)) / max(1, len(terms))
            if sc > score:
                best, score = s, sc
    return best


def conflicting(claim, text):
    """Sentences that talk about the same thing (>=60 % of key terms) but give different numbers and none of the
    claim's: a sign that sources disagree. Only for claims that contain numbers."""
    need = numbers(claim)
    if not need:
        return []
    terms = key_terms(claim)
    out = []
    for s in sentences(text):
        shared = terms & key_terms(s)
        if len(terms) and len(shared) / len(terms) >= 0.6:
            have = numbers(s)
            if have and not (need & have) and any(_same_kind(n, h) for n in need for h in have):
                out.append(s)
    return out[:3]


def _same_kind(a, b):
    """Both look like years, or both are counts of a similar size (within 10x): worth flagging as a conflict."""
    year = lambda x: 1000 <= x <= 2100 and float(x).is_integer()
    if year(a) or year(b):
        return year(a) and year(b)
    return a > 0 and b > 0 and 0.1 <= a / b <= 10


NAME = re.compile(r"\b([A-Z][a-z]+(?:[ -][A-Z][a-z]+)*)\b")


def names(text):
    """Capitalised words that are not the first word of a sentence."""
    out = set()
    for sent in re.split(r"(?<=[.!?])\s+", str(text)):
        toks = sent.split()
        for i, t in enumerate(toks):
            w = re.sub(r"[^A-Za-z'-]", "", t)
            if i > 0 and w[:1].isupper() and w.lower() not in STOP and len(w) > 1:
                out.add(w.lower().strip("'"))
    return out


def script_violations(line_text, backing_text, allowed_names=()):
    """Numbers or names in a script line that the backing claims do not contain."""
    bad = []
    have = numbers(backing_text)
    for n in numbers(line_text):
        if n not in have and n != 1.0:   # every number except a plain "one" must be in a verified claim
            bad.append(f"number {n:g}")
    allowed = {a.lower() for a in allowed_names} | {w.lower() for w in re.findall(r"[A-Za-z'-]+", backing_text)}
    stems = {a[:6] for a in allowed if len(a) >= 6}
    for n in names(line_text):
        if n not in allowed and not (len(n) >= 6 and n[:6] in stems):
            bad.append(f"name '{n}'")
    return sorted(set(bad))
