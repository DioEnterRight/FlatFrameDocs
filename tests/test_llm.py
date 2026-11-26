"""FreeLLMAPI client: discovery, deny list, failover, budgets, invalid replies."""
import io
import json
import urllib.error

import pytest

from flatframe import llm


class FakeAPI:
    """Stands in for FreeLLMAPI. `script` maps model -> list of replies (dict body, Exception, or (body, routed))."""

    def __init__(self, models, script, usage=(100, 50)):
        self.models, self.script, self.calls, self.usage = models, script, [], usage

    def __call__(self, f, path, body=None, timeout=60):
        if path.startswith("/models"):
            return {"data": [{"id": m} for m in self.models]}, None
        model = body["model"]
        self.calls.append(model)
        queue = self.script.get(model, [])
        item = queue.pop(0) if queue else urllib.error.HTTPError("u", 503, "down", {}, io.BytesIO(b"down"))
        if isinstance(item, Exception):
            raise item
        routed = None
        if isinstance(item, tuple):
            item, routed = item
        return {"choices": [{"message": {"content": item}}], "usage": {"prompt_tokens": self.usage[0], "completion_tokens": self.usage[1]}}, routed


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("FREELLM_BASE_URL", "http://fake/v1")
    monkeypatch.setenv("FREELLM_API_KEY", "k" * 20)


def test_unconfigured_is_unavailable(cfg, monkeypatch):
    monkeypatch.delenv("FREELLM_API_KEY")
    with pytest.raises(llm.LLMUnavailable):
        llm.Session(cfg, 1, http=FakeAPI([], {}))


def test_denied_models_are_never_candidates(cfg):
    api = FakeAPI(["claude-3-opus", "gpt-4o", "gemini-2.5-flash", "llama-3.3-70b"], {})
    s = llm.Session(cfg, 3, http=api)
    for role, models in s.candidates.items():
        assert not any("claude" in m or "gpt-4o" in m for m in models), role


def test_failover_to_next_model(cfg):
    err = urllib.error.HTTPError("u", 503, "busy", {}, io.BytesIO(b"busy"))
    api = FakeAPI(["gemini-2.5-pro", "deepseek-r1"], {"gemini-2.5-pro": [err, err], "deepseek-r1": ['{"ok": true}']})
    s = llm.Session(cfg, 0, http=api)
    s.candidates["writer"] = ["gemini-2.5-pro", "deepseek-r1"]
    obj, routed = s.json("writer", "sys", "user")
    assert obj == {"ok": True} and routed == "deepseek-r1"


def test_reply_routed_to_denied_model_is_discarded(cfg):
    api = FakeAPI(["auto-ish"], {"auto-ish": [('{"ok": true}', "claude-sonnet"), ('{"ok": true}', "claude-sonnet")]})
    s = llm.Session(cfg, 0, http=api)
    s.candidates["writer"] = ["auto-ish"]
    with pytest.raises(llm.LLMUnavailable):
        s.json("writer", "sys", "user")


def test_invalid_json_is_asked_again(cfg):
    api = FakeAPI(["gemini-2.5-pro"], {"gemini-2.5-pro": ["sure! here you go", '```json\n{"a": 1}\n```']})
    s = llm.Session(cfg, 0, http=api)
    s.candidates["writer"] = ["gemini-2.5-pro"]
    assert s.json("writer", "sys", "user")[0] == {"a": 1}


def test_per_video_request_cap(cfg):
    cfg["freellm"]["max_calls_per_video"] = 2
    api = FakeAPI(["m1"], {"m1": ["{}", "{}", "{}"]})
    s = llm.Session(cfg, 0, http=api)
    s.candidates["writer"] = ["m1"]
    s.json("writer", "s", "u")
    s.json("writer", "s", "u")
    with pytest.raises(llm.LLMUnavailable, match="request cap"):
        s.json("writer", "s", "u")


def test_per_video_token_cap(cfg):
    cfg["freellm"]["max_tokens_per_video"] = 200
    api = FakeAPI(["m1"], {"m1": ["{}", "{}"]}, usage=(150, 100))
    s = llm.Session(cfg, 0, http=api)
    s.candidates["writer"] = ["m1"]
    with pytest.raises(llm.LLMUnavailable, match="token cap"):
        s.json("writer", "s", "u")


def test_monthly_cap_blocks_before_any_call(cfg, tmp_data):
    m = llm._month()
    (tmp_data / "freellm_usage.json").write_text(json.dumps({m: {"calls": 1, "prompt_tokens": 10**9, "completion_tokens": 0}}))
    with pytest.raises(llm.LLMUnavailable, match="monthly token cap"):
        llm.Session(cfg, 0, http=FakeAPI(["m1"], {}))


def test_usage_ledger_counts(cfg, tmp_data):
    api = FakeAPI(["m1"], {"m1": ["{}"]})
    s = llm.Session(cfg, 0, http=api)
    s.candidates["writer"] = ["m1"]
    s.json("writer", "s", "u")
    m = llm.month_usage()
    assert m["calls"] == 1 and m["prompt_tokens"] == 100 and m["by_role"]["writer"] == 1


def test_critic_is_not_the_writer(cfg):
    api = FakeAPI(["gemini-2.5-pro", "deepseek-r1", "qwen3-235b"], {})
    for seed in range(6):
        s = llm.Session(cfg, seed, http=api)
        assert s.candidates["critic"][0] != s.candidates["writer"][0]


def test_vision_role_only_known_vision_models(cfg):
    s = llm.Session(cfg, 0, http=FakeAPI(["deepseek-r1", "gemini-2.5-flash"], {}))
    assert s.candidates["judge"] == ["gemini-2.5-flash"]


def test_extract_json_handles_think_and_fences():
    assert llm.extract_json('<think>{"no": 1}</think> ok ```json {"yes": {"n": "}"}} ```') == {"yes": {"n": "}"}}
    with pytest.raises(ValueError):
        llm.extract_json('{"cut": ')
