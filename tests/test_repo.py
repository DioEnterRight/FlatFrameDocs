"""Repository hygiene: workflows are least-privilege and pinned, secrets never reach PR code, state merges."""
import json
import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows"


def workflows():
    return {p.name: yaml.safe_load(p.read_text()) for p in WF.glob("*.yml")}


def test_actions_pinned_to_full_sha():
    for name, text in ((p.name, p.read_text()) for p in WF.glob("*.yml")):
        for ref in re.findall(r"uses:\s*(\S+)", text):
            assert re.search(r"@[0-9a-f]{40}$", ref), f"{name}: {ref} is not pinned to a commit SHA"


def test_default_permissions_are_minimal():
    for name, wf in workflows().items():
        top = wf.get("permissions")
        assert top in ({}, {"contents": "read"}), f"{name}: top-level permissions {top}"


def test_checkout_does_not_persist_credentials():
    for name, wf in workflows().items():
        for job in wf["jobs"].values():
            for step in job.get("steps", []):
                if "actions/checkout" in str(step.get("uses", "")):
                    assert step.get("with", {}).get("persist-credentials") is False, name


def test_write_token_only_in_steps_that_need_it():
    for name, wf in workflows().items():
        for job in wf["jobs"].values():
            assert "GH_TOKEN" not in (job.get("env") or {}), f"{name}: job-level GH_TOKEN"
            for step in job.get("steps", []):
                run = step.get("run", "")
                if any(k in run for k in ("pip install", "npm ci", "fetch_models", "produce")):
                    assert "GH_TOKEN" not in (step.get("env") or {}), f"{name}: token next to third-party code in '{step.get('name')}'"


def test_pull_request_ci_has_no_secrets_and_no_soft_failures():
    text = (WF / "ci.yml").read_text()
    assert "secrets." not in text
    assert "continue-on-error" not in text
    ci = yaml.safe_load(text)
    assert ci["permissions"] == {"contents": "read"}


def test_publishing_workflows_never_run_on_pull_requests():
    for name in ("make-video.yml", "post-video.yml", "pin-freellmapi.yml"):
        on = workflows()[name][True]   # yaml parses `on:` as True
        assert "pull_request" not in on and "pull_request_target" not in on


def test_no_force_flag_reaches_youtube():
    src = (ROOT / "flatframe" / "publish.py").read_text()
    assert "--force" not in src
    yt = re.search(r"def youtube_step.*?\n(?=def )", src, re.S).group(0)
    assert "force" not in yt


def test_lockfiles_are_hashed_and_engine_locked():
    lock = (ROOT / "requirements.lock").read_text()
    assert "--hash=sha256:" in lock
    pkg = json.loads((ROOT / "engine" / "package.json").read_text())
    for dep, ver in {**pkg["dependencies"], **pkg["devDependencies"]}.items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", ver), f"{dep} is not pinned exactly ({ver})"
    assert (ROOT / "engine" / "package-lock.json").exists()


def test_no_claude_or_paid_ai_in_production_code():
    for p in (ROOT / "flatframe").glob("*.py"):
        text = p.read_text().lower()
        for bad in ("api.anthropic.com", "anthropic import", "import anthropic", "api.openai.com", "import openai"):
            assert bad not in text, f"{p.name} mentions {bad}"


def test_merge_driver_adds_counters_and_keeps_both_sides(tmp_path):
    base = {"videos": [{"id": "a", "status": "queued"}], "n": 1}
    ours = {"videos": [{"id": "a", "status": "published"}], "n": 3}
    theirs = {"videos": [{"id": "a", "status": "queued"}, {"id": "b", "status": "queued"}], "n": 2}
    paths = []
    for k, obj in (("o", base), ("a", ours), ("b", theirs)):
        p = tmp_path / f"{k}.json"
        p.write_text(json.dumps(obj))
        paths.append(str(p))
    subprocess.run([sys.executable, str(ROOT / "tools" / "merge_state.py"), *paths], check=True)
    out = json.loads(pathlib.Path(paths[1]).read_text())
    assert [v["id"] for v in out["videos"]] == ["a", "b"] and out["videos"][0]["status"] == "published" and out["n"] == 4
