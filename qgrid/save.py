"""Persistent player saves for Quantum Grid 2099.

One JSON file per SSH username under QG_SAVE_DIR (default: ./saves).
Usernames are sanitized; anything outside [A-Za-z0-9_.-] is replaced so
the save key can never escape the save directory.
"""

import hashlib
import json
import os
import re

SAVE_VERSION = 2
_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


def save_dir() -> str:
    return os.environ.get("QG_SAVE_DIR", "saves")


def save_path(username: str) -> str:
    clean = _SAFE.sub("_", username)[:32] or "guest"
    return os.path.join(save_dir(), f"{clean}.json")


def default_save() -> dict:
    return {
        "version": SAVE_VERSION,
        "unlocked": 0,
        "total_score": 0,
        "total_actions": 0,
        "shards": {},  # global node index (str) -> sorted list of shard indexes
        "codex": [],
        "endings": [],
    }


def load(username: str) -> dict:
    """Load a save, falling back to defaults on any problem."""
    path = save_path(username)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
            return default_save()
        base = default_save()
        base.update({k: v for k, v in data.items() if k in base})
        return base
    except (OSError, ValueError, TypeError):
        return default_save()


def store(username: str, data: dict) -> None:
    path = save_path(username)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        pass  # saving is best-effort; never crash a session over it


def shards_total(data: dict) -> int:
    return sum(len(v) for v in data.get("shards", {}).values())


def fingerprint(username: str) -> str:
    """Stable short fingerprint for anonymous save identification."""
    return hashlib.sha256(username.encode()).hexdigest()[:8]
