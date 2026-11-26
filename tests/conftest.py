import copy
import json
import pathlib

import pytest

from flatframe import common

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def cfg():
    return copy.deepcopy(common.load_config())


@pytest.fixture(autouse=True)
def tmp_data(tmp_path, monkeypatch):
    """Every test gets its own data/ and out/ (state files never touch the repo)."""
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(common, "DATA", data)
    monkeypatch.setattr(common, "HISTORY", data / "history.json")
    monkeypatch.setattr(common, "OUT", tmp_path / "out")
    return data


@pytest.fixture
def sample():
    d = ROOT / "samples" / "emu-war"
    return {n: json.loads((d / f"{n}.json").read_text()) for n in ("research", "script", "board", "idea")}
