"""FreeLLMAPI client (github.com/tashfeenahmed/freellmapi). The container is started inside each GitHub job by
tools/start_freellmapi.sh, which exports FREELLM_BASE_URL and FREELLM_API_KEY. FreeLLMAPI only holds the free-tier
provider keys from the FREELLMAPI_KEYS secret, so nothing here can reach a paid API.

Architecture reused from roblox-stories-bot/pipeline/llm.py (discovery, role ranking, rotation, failover, JSON repair),
tightened for FlatFrameDocs:

  * six roles: ideator, critic, research, writer, director, judge (vision)
  * `freellm.deny` name fragments are filtered out of discovery AND checked against the X-Routed-Via header, so a
    reply that FreeLLMAPI routed to a denied model is thrown away (Claude and paid-only families are denied)
  * per-video caps on requests AND tokens, monthly caps on tokens AND requests (data/freellm_usage.json)
  * the critic is never the writer's / ideator's model, so a model does not grade its own work

When nothing free is available the caller gets LLMUnavailable and the run stops gracefully (no paid fallback).
Check the setup without making a video:  python -m flatframe.llm --check
"""
import base64
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from . import common
from .common import log

RETRY = (408, 429, 500, 502, 503, 504)
ROLES = ("ideator", "critic", "research", "writer", "director", "judge")
FALLBACK = ["auto"]
NOT_CHAT = ("embed", "whisper", "tts", "guard", "rerank", "moderation", "image-gen", "dall")


class LLMUnavailable(RuntimeError):
    """No free model can be used right now (not configured, budget reached, or every model failed)."""


def settings(cfg):
    f = dict(cfg.get("freellm") or {})
    f["base_url"] = os.environ.get("FREELLM_BASE_URL", "").rstrip("/")
    f["key"] = os.environ.get("FREELLM_API_KEY", "")
    return f


def configured(cfg):
    f = settings(cfg)
    return bool(f["base_url"] and f["key"])


def ledger_path():
    return common.DATA / "freellm_usage.json"


def _month():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")


def month_usage():
    return common.read_json(ledger_path(), {}).get(_month(), {})


def _record(routed, role, usage):
    data = common.read_json(ledger_path(), {})
    m = data.setdefault(_month(), {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "by_model": {}, "by_role": {}})
    m["calls"] += 1
    m["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
    m["completion_tokens"] += int(usage.get("completion_tokens") or 0)
    m["by_model"][routed] = m["by_model"].get(routed, 0) + 1
    m.setdefault("by_role", {})[role] = m.get("by_role", {}).get(role, 0) + 1
    for old in sorted(data)[:-6]:
        data.pop(old)
    common.write_json(ledger_path(), data)


def _http(f, path, body=None, timeout=60):
    req = urllib.request.Request(f["base_url"] + path, data=json.dumps(body).encode() if body is not None else None,
                                 method="POST" if body is not None else "GET",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + f["key"]})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read()), r.headers.get("X-Routed-Via")


def denied(model, deny):
    m = str(model or "").lower()
    return any(d.lower() in m for d in deny)


def ready_models(cfg):
    f = settings(cfg)
    data, _ = _http(f, "/models?available=true")
    deny = f.get("deny") or []
    return [m["id"] for m in data.get("data", []) if m.get("id") and not denied(m["id"], deny)]


def rank(ready, prefer, seed, top=4):
    """Ready models ordered by the role's preference list; the best `top` are rotated by the seed (variety between
    videos without dropping to weak models). Models matching nothing in `prefer` come after, in their listed order."""
    ranked, seen = [], set()
    for p in prefer:
        for m in ready:
            if p.lower() in m.lower() and m not in seen:
                ranked.append(m)
                seen.add(m)
    rest = [m for m in ready if m not in seen and not any(x in m.lower() for x in NOT_CHAT)]
    head = ranked[:top]
    if head:
        k = seed % len(head)
        head = head[k:] + head[:k]
    return head + ranked[top:] + rest


class Budget:
    """Per-video caps (requests + tokens) on top of monthly caps (tokens + requests)."""

    def __init__(self, cfg):
        f = settings(cfg)
        self.calls_left = int(f["max_calls_per_video"])
        self.tokens_left = int(f["max_tokens_per_video"])
        m = month_usage()
        used = int(m.get("prompt_tokens", 0)) + int(m.get("completion_tokens", 0))
        if used >= int(f["monthly_token_cap"]):
            raise LLMUnavailable(f"monthly token cap reached ({used:,} of {int(f['monthly_token_cap']):,}); models paused until next month")
        if int(m.get("calls", 0)) >= int(f["monthly_request_cap"]):
            raise LLMUnavailable(f"monthly request cap reached ({m.get('calls')} of {f['monthly_request_cap']})")
        self.month_tokens_left = int(f["monthly_token_cap"]) - used
        self.month_calls_left = int(f["monthly_request_cap"]) - int(m.get("calls", 0))

    def spend_call(self):
        if self.calls_left <= 0:
            raise LLMUnavailable("per-video request cap reached (freellm.max_calls_per_video)")
        if self.month_calls_left <= 0:
            raise LLMUnavailable("monthly request cap reached (freellm.monthly_request_cap)")
        self.calls_left -= 1
        self.month_calls_left -= 1

    def spend_tokens(self, n):
        self.tokens_left -= n
        self.month_tokens_left -= n
        if self.tokens_left < 0:
            raise LLMUnavailable("per-video token cap reached (freellm.max_tokens_per_video)")
        if self.month_tokens_left < 0:
            raise LLMUnavailable("monthly token cap reached during this video")


class Session:
    """One video's model plan: the rotated candidates per role, the budget, and a log of who answered what."""

    def __init__(self, cfg, seed, http=None):
        self.cfg = cfg
        self.f = settings(cfg)
        self.seed = int(seed)
        self.used = {}
        self.tokens = {}
        self._http = http or _http
        if not configured(cfg):
            raise LLMUnavailable("FREELLM_BASE_URL / FREELLM_API_KEY are not set (the 'Start FreeLLMAPI' step did not run)")
        self.budget = Budget(cfg)
        try:
            data, _ = self._http(self.f, "/models?available=true")
            ready = [m["id"] for m in data.get("data", []) if m.get("id") and not denied(m["id"], self.f["deny"])]
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise LLMUnavailable(f"FreeLLMAPI is not reachable: {e}") from None
        if not ready:
            raise LLMUnavailable("FreeLLMAPI has no ready model (every key rejected or used up)")
        self.ready = ready
        roles = self.f.get("roles") or {}
        self.candidates = {}
        for i, role in enumerate(ROLES):
            rc = roles.get(role) or {}
            prefer = rc.get("prefer") or []
            order = rank(ready, prefer, self.seed + i * 7, int(rc.get("rotate_top", 3)))
            if rc.get("vision"):   # never send images to a model that is not known to see
                order = [m for m in order if any(p.lower() in m.lower() for p in prefer)]
                self.candidates[role] = order
            else:
                self.candidates[role] = order + FALLBACK
        authors = {c[0] for c in (self.candidates["writer"][:1], self.candidates["ideator"][:1]) if c}
        crit = self.candidates["critic"]
        self.candidates["critic"] = [m for m in crit if m not in authors] + [m for m in crit if m in authors]
        log("models this video: " + "; ".join(f"{r}={self.candidates[r][:3]}" for r in ROLES))

    def has(self, role):
        return bool(self.candidates.get(role))

    def chat(self, role, messages, json_mode=True, attempts=2, max_tokens=None, avoid=()):
        rc = (self.f.get("roles") or {}).get(role) or {}
        temperature = float(rc.get("temperature", 0.7))
        errors = []
        order = [m for m in self.candidates.get(role, []) if m not in avoid] or self.candidates.get(role, [])
        for model in order:
            jm = json_mode
            i = 0
            while i < attempts:
                self.budget.spend_call()
                body = {"model": model, "messages": messages, "temperature": temperature,
                        "max_tokens": int(max_tokens or rc.get("max_tokens") or self.f.get("max_tokens", 8000))}
                if jm:
                    body["response_format"] = {"type": "json_object"}
                try:
                    data, routed = self._http(self.f, "/chat/completions", body, timeout=int(self.f.get("timeout_seconds", 240)))
                    usage = data.get("usage") or {}
                    routed = routed or data.get("model") or model
                    _record(routed, role, usage)
                    spent = int(usage.get("prompt_tokens") or 0) + int(usage.get("completion_tokens") or 0)
                    self.tokens[role] = self.tokens.get(role, 0) + spent
                    self.budget.spend_tokens(spent)
                    if denied(routed, self.f["deny"]):
                        raise ValueError(f"reply was routed to a denied model ({routed}); discarded")
                    text = data["choices"][0]["message"].get("content") or ""
                    if not text.strip():
                        raise ValueError("empty reply")
                    self.used.setdefault(role, []).append(routed)
                    log(f"{role}: {model} -> {routed} (in {usage.get('prompt_tokens', '?')}, out {usage.get('completion_tokens', '?')})")
                    return text, routed
                except urllib.error.HTTPError as e:
                    detail = e.read()[:300].decode("utf-8", "replace")
                    if e.code == 400 and jm and "response_format" in detail:
                        jm = False   # no JSON mode on this route: the prompt still demands JSON
                        continue
                    errors.append(f"{model}: HTTP {e.code} {detail[:120]}")
                    if e.code in (401, 403):
                        raise LLMUnavailable(f"FreeLLMAPI refused the key (HTTP {e.code})") from None
                    if e.code not in RETRY or "quota" in detail.lower():
                        break
                except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
                    errors.append(f"{model}: {e!r}"[:200])
                i += 1
                if i < attempts:
                    time.sleep(3 * i)
            log(f"{role}: {model} failed ({errors[-1] if errors else '?'}), next model", "WARN")
        raise LLMUnavailable(f"every {role} model failed: " + " | ".join(errors[-4:]))

    def json(self, role, system, user, images=None, attempts_on_bad_json=2, max_tokens=None, avoid=()):
        """Ask for ONE JSON object; a reply that is not valid JSON is asked again (with the parse error).
        Returns (object, routed model)."""
        content = user if not images else [{"type": "text", "text": user}] + [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()}}
            for p in images]
        messages = [{"role": "system", "content": system}, {"role": "user", "content": content}]
        last = None
        for _ in range(attempts_on_bad_json):
            text, routed = self.chat(role, messages, max_tokens=max_tokens, avoid=avoid)
            try:
                return extract_json(text), routed
            except (ValueError, json.JSONDecodeError) as e:
                last = e
                log(f"{role}: reply was not valid JSON ({str(e)[:100]}), asking again", "WARN")
                messages = messages + [{"role": "assistant", "content": text[:4000]},
                                       {"role": "user", "content": f"That was not one valid JSON object ({e}). Reply with ONLY the JSON object."}]
        raise LLMUnavailable(f"{role}: no valid JSON after {attempts_on_bad_json} tries: {last}")

    def report(self):
        return {"used": self.used, "tokens": self.tokens, "calls_left": self.budget.calls_left,
                "tokens_left": self.budget.tokens_left}


def extract_json(text):
    """The first complete top-level JSON object in a reply, after dropping <think> blocks and ``` fences."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    if start < 0:
        raise ValueError("reply has no JSON object")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("JSON object in the reply is cut off (raise freellm.max_tokens?)")


def check(cfg):
    """One tiny request per text role: proves the keys work and shows which models each role would use."""
    s = Session(cfg, seed=int(time.time()) % 1000)
    for role in ("writer", "research"):
        obj, _ = s.json(role, "Reply with JSON only.", 'Reply with exactly this JSON: {"ok": true}')
        if obj.get("ok") is not True:
            raise SystemExit(f"{role} answered, but not with the expected JSON")
    log(f"judge (vision) candidates: {s.candidates.get('judge', [])[:4] or 'NONE (the visual judge will be skipped)'}")
    m = month_usage()
    log(f"FreeLLMAPI OK. This month: {m.get('calls', 0)} calls, {int(m.get('prompt_tokens', 0)) + int(m.get('completion_tokens', 0)):,} tokens")


if __name__ == "__main__":
    if "--check" in sys.argv:
        try:
            check(common.load_config())
        except LLMUnavailable as e:
            sys.exit(f"FreeLLMAPI check failed: {e}")
