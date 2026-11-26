"""Validate config.yaml before anything runs. Errors name the exact key and what is allowed."""
import re

TIME = re.compile(r"([01]\d|2[0-3]):[0-5]\d")
ROLES = ("ideator", "critic", "research", "writer", "director", "judge")


class ConfigError(ValueError):
    pass


def _need(cond, msg):
    if not cond:
        raise ConfigError(f"config.yaml: {msg}")


def _num(d, key, lo, hi, where):
    v = d.get(key)
    _need(isinstance(v, (int, float)) and not isinstance(v, bool), f"{where}.{key} must be a number")
    _need(lo <= v <= hi, f"{where}.{key} must be between {lo} and {hi} (got {v})")
    return v


def validate(cfg):
    _need(isinstance(cfg, dict), "file is empty or not a mapping")
    for block in ("brand", "channel", "video", "schedule", "voice", "ideas", "research", "writing", "quality", "render",
                  "freellm", "publish", "disclosure", "retention"):
        _need(isinstance(cfg.get(block), dict), f"missing block `{block}:`")
    _need(isinstance(cfg.get("paused", False), bool), "paused must be true or false")
    _need(cfg["channel"].get("language") == "en", "channel.language: only 'en' has prompts today")

    v = cfg["video"]
    _need((v.get("width"), v.get("height")) == (1080, 1920), "video must be 1080 x 1920 (vertical 9:16)")
    _need(v.get("fps") == 30, "video.fps must be 30")
    lo, hi = _num(v, "min_seconds", 20, 60, "video"), _num(v, "max_seconds", 20, 60, "video")
    _need(lo < _num(v, "target_seconds", 20, 60, "video") < hi, "video: min_seconds < target_seconds < max_seconds")

    s = cfg["schedule"]
    every = _num(s, "every_minutes", 60, 1440, "schedule")
    _need(1440 % every == 0, "schedule.every_minutes must divide a day (60, 90, 120, 180, 240, 360, 480, 720, 1440)")
    _need(TIME.fullmatch(str(s.get("first", ""))), 'schedule.first must look like "01:30" (24 h, India time)')
    _num(s, "make_ahead", 1, 6, "schedule")
    _num(s, "make_per_run", 1, 2, "schedule")
    _need(_num(s, "late_minutes", 5, 180, "schedule") < every, "schedule.late_minutes must be shorter than every_minutes")

    vo = cfg["voice"]
    _need(vo.get("engine") in ("edge", "kokoro"), "voice.engine must be edge or kokoro")
    for k in ("edge_voice", "kokoro_voice"):
        _need(vo.get("narrator", {}).get(k), f"voice.narrator.{k} is required")
    _need(isinstance(vo.get("skit_voices"), list) and len(vo["skit_voices"]) >= 2, "voice.skit_voices needs 2 voices")
    _need(_num(vo, "min_gap", 0.05, 1, "voice") <= _num(vo, "gap_seconds", 0.05, 1, "voice") <= _num(vo, "max_gap", 0.05, 1, "voice"),
          "voice: min_gap <= gap_seconds <= max_gap")

    b = cfg["brand"]
    _need(str(b.get("corner_handle", "")).startswith("@"), "brand.corner_handle must look like @name")
    _need(isinstance(b.get("captions"), bool), "brand.captions must be true or false")
    _num(b, "outro_seconds", 2, 6, "brand")
    _need(b.get("outro_text") and b.get("outro_spoken"), "brand.outro_text and brand.outro_spoken are required")

    i = cfg["ideas"]
    _num(i, "candidates", 4, 20, "ideas")
    _num(i, "research_attempts", 1, 5, "ideas")
    _num(i, "min_score", 1, 10, "ideas")
    _num(i, "similarity_threshold", 0.1, 0.9, "ideas")
    _need(isinstance(i.get("categories"), list) and len(i["categories"]) >= 3, "ideas.categories needs 3 or more")
    _need(set(i.get("weights", {})) == {"curiosity", "uniqueness", "hook", "suspense", "visual", "payoff", "reliability", "variety"},
          "ideas.weights needs exactly the 8 criteria")

    r = cfg["research"]
    _num(r, "min_verified_claims", 3, 30, "research")
    _need(_num(r, "min_sources_per_claim", 2, 4, "research") >= 2, "research.min_sources_per_claim must be at least 2")

    w = cfg["writing"]
    _need(_num(w, "words_min", 60, 200, "writing") < _num(w, "words_max", 60, 200, "writing"), "writing.words_min < words_max")
    _num(w, "hook_max_words", 4, 14, "writing")

    f = cfg["freellm"]
    for role in ROLES:
        rc = f.get("roles", {}).get(role)
        _need(isinstance(rc, dict) and isinstance(rc.get("prefer"), list), f"freellm.roles.{role}.prefer must be a list")
    _need(isinstance(f.get("deny"), list) and any("claude" in d for d in f["deny"]), "freellm.deny must keep 'claude'")
    for k, hi in (("max_calls_per_video", 80), ("max_tokens_per_video", 2_000_000), ("monthly_token_cap", 2_000_000_000),
                  ("monthly_request_cap", 100_000)):
        _num(f, k, 1, hi, "freellm")

    p = cfg["publish"]
    _need(p.get("youtube_mode") in ("api", "manual", "off"), "publish.youtube_mode must be api, manual or off")
    _need(p.get("youtube_pause_on_upload_limit") is True, "publish.youtube_pause_on_upload_limit must stay true")
    _need(p.get("youtube_retry_upload_limit") is False, "publish.youtube_retry_upload_limit must stay false (never retry uploadLimitExceeded)")
    _need(_num(p, "youtube_pause_hours", 24, 168, "publish") >= 24, "publish.youtube_pause_hours must be >= 24")
    _num(p, "youtube_channel_daily_cap", 0, 50, "publish")
    _num(p, "youtube_api_daily_insert_cap", 0, 100, "publish")
    _need(isinstance(p.get("youtube_require_quota_clearance"), bool), "publish.youtube_require_quota_clearance must be true/false")
    cid = p.get("youtube_channel_id", "")
    _need(cid == "" or re.fullmatch(r"UC[\w-]{22}", str(cid)), "publish.youtube_channel_id must be empty or a UC... channel id")
    _num(p, "instagram_daily_cap", 0, 50, "publish")
    _num(cfg["retention"], "keep_releases_days", 1, 90, "retention")
    return cfg
