"""Unit tests for the persistent save system."""

import json
from pathlib import Path

import pytest

from qgrid import save as save_mod


@pytest.fixture
def tmp_env(tmp_path, monkeypatch):
    monkeypatch.setenv("QG_SAVE_DIR", str(tmp_path / "saves"))
    return tmp_path


def test_default_save_shape(tmp_env):
    data = save_mod.load("nobody")
    assert data["version"] == save_mod.SAVE_VERSION
    assert data["unlocked"] == 0
    assert data["total_score"] == 0
    assert data["shards"] == {}
    assert data["codex"] == []


def test_store_and_load_round_trip(tmp_env):
    data = save_mod.default_save()
    data["unlocked"] = 17
    data["total_score"] = 4242
    data["codex"] = ["omnicorp", "mirage"]
    data["shards"] = {"3": [0, 1], "7": [0]}
    save_mod.store("nyx", data)
    loaded = save_mod.load("nyx")
    assert loaded["unlocked"] == 17
    assert loaded["total_score"] == 4242
    assert loaded["codex"] == ["omnicorp", "mirage"]
    assert loaded["shards"] == {"3": [0, 1], "7": [0]}


def test_corrupt_save_falls_back_to_defaults(tmp_env):
    path = Path(save_mod.save_path("glitch"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    data = save_mod.load("glitch")
    assert data["unlocked"] == 0


def test_old_version_save_rejected(tmp_env):
    path = Path(save_mod.save_path("legacy"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "unlocked": 5}), encoding="utf-8")
    assert save_mod.load("legacy")["unlocked"] == 0


def test_username_sanitized_no_traversal(tmp_env):
    evil = "../../etc/passwd"
    path = Path(save_mod.save_path(evil))
    # no path separators may survive sanitization
    assert "/" not in path.name
    save_mod.store(evil, save_mod.default_save())
    # file landed inside the save dir, not elsewhere
    assert path.exists()
    assert path.parent == Path(save_mod.save_dir())


def test_shards_total(tmp_env):
    data = save_mod.default_save()
    data["shards"] = {"1": [0, 1], "2": [0, 1, 2]}
    assert save_mod.shards_total(data) == 5
