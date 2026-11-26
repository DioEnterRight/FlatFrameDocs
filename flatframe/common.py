"""Shared helpers: paths, config, logging (secrets redacted), atomic state files, shell calls, small text utils.

Adapted from roblox-stories-bot/pipeline/common.py (same atomic-write and redaction design)."""
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unicodedata

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"
MODELS = ROOT / "models"
PROMPTS = ROOT / "prompts"
SAMPLES = ROOT / "samples"
ENGINE = ROOT / "engine"
PROJECTS = ENGINE / "public" / "projects"
HISTORY = DATA / "history.json"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
HISTORY_VERSION = 1

SECRET_ENV = ("FREELLM_API_KEY", "FREELLMAPI_KEYS", "IG_PAGE_TOKEN", "IG_USER_ID", "YT_CLIENT_SECRET",
              "YT_REFRESH_TOKEN", "YT_CLIENT_ID", "GH_TOKEN", "GITHUB_TOKEN")


class StageError(RuntimeError):
    """A production stage could not produce an acceptable result. The slot is skipped; nothing is published."""


def redact(text):
    """Never let a secret reach the log (values of the secret env vars are replaced by ***)."""
    text = str(text)
    for name in SECRET_ENV:
        val = os.environ.get(name, "").strip()
        if len(val) >= 6:
            text = text.replace(val, "***")
    return text


def log(msg, level="INFO"):
    print(f"[{dt.datetime.now(IST):%H:%M:%S}] {level:<5} {redact(msg)}", flush=True)


def load_config(path=None):
    from . import config_check
    cfg = yaml.safe_load(pathlib.Path(path or ROOT / "config.yaml").read_text(encoding="utf-8"))
    config_check.validate(cfg)
    return cfg


def now_ist():
    return dt.datetime.now(IST)


def parse_time(s):
    t = dt.datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=IST)


def env(name, required=False):
    val = os.environ.get(name, "").strip()
    if required and not val:
        sys.exit(f"Missing secret/env var: {name}. Add it in GitHub > Settings > Secrets and variables > Actions.")
    return val


def run(cmd, check=True, capture=False, timeout=None, **kw):
    """Run a command (no shell). Logs it with long arguments shortened."""
    short = " ".join(str(c) if len(str(c)) < 120 else str(c)[:60] + "..." for c in cmd)
    log(f"$ {short}")
    try:
        res = subprocess.run([str(c) for c in cmd], check=False, text=True, capture_output=capture, timeout=timeout, **kw)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Command timed out after {timeout}s: {short}") from e
    if check and res.returncode != 0:
        if capture:
            print(redact((res.stdout or "")[-4000:]), redact((res.stderr or "")[-4000:]))
        raise RuntimeError(f"Command failed ({res.returncode}): {short}")
    return res


def ffprobe(path):
    res = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path], capture=True)
    return json.loads(res.stdout)


def duration_of(path):
    return float(ffprobe(path)["format"]["duration"])


def slugify(text, n=40):
    s = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower())
    return s.strip("-")[:n].strip("-") or "video"


def norm_text(s):
    """Lower-case letters and digits only (for duplicate checks)."""
    return "".join(ch for ch in str(s).lower() if unicodedata.category(ch)[0] in "LN")


def words_of(text):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.,%$-]*", str(text))


STOP = set("""a an the and or but of to in on at for with from by as is was were are be been being it its this that these
those he she they them his her their we you i our your my me not no so if then than there here what which who whom whose
when where why how all any each few more most other some such only own same too very can will just do does did had has
have into out up down over under again once about after before between through during until while because""".split())


def content_words(text):
    return {w.lower().strip(".,'’%$-") for w in words_of(text) if w.lower() not in STOP and len(w) > 2}


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / max(1, len(a | b))


def stable_seed(*parts, mod=1_000_000):
    """Deterministic seed (Python's hash() changes every process)."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return int(h[:12], 16) % mod


# ---------------- state files (atomic) ----------------
def read_json(path, default):
    path = pathlib.Path(path)
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else default


def write_json(path, obj):
    """Write via temp file + rename so a crash never leaves a half-written state file."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_history():
    hist = read_json(HISTORY, {"version": HISTORY_VERSION, "videos": []})
    hist.setdefault("videos", [])
    hist["version"] = HISTORY_VERSION
    return hist


def save_history(hist):
    hist["version"] = HISTORY_VERSION
    write_json(HISTORY, hist)


def prompt(name):
    return (PROMPTS / name).read_text(encoding="utf-8")


def fill(template, **values):
    """Replace {name} placeholders only (prompts contain JSON braces, so str.format cannot be used)."""
    for k, v in values.items():
        template = template.replace("{" + k + "}", v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
    left = re.findall(r"\{([a-z_]+)\}", template)
    if left:
        raise ValueError(f"prompt placeholders not filled: {sorted(set(left))}")
    return template
