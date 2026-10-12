"""Server-wide hall of fame for Quantum Grid 2099.

A single JSON file under the save directory ranks every runner who has
jacked in: best career score, furthest node, shards banked. Updated on
every node clearance and at campaign victory; rendered on the LEADERBOARD
screen (L from the menus) and on the victory screen.

Writes are atomic (temp file + rename) and best-effort: a corrupted or
missing file degrades to an empty board, never a crashed session.
"""

import json
import os

from .save import save_dir

MAX_ENTRIES = 100


def path(name: str = "main") -> str:
    """One JSON file per board: main campaign + daily-YYYYMMDD gauntlets."""
    fname = "leaderboard.json" if name == "main" else f"leaderboard-{name}.json"
    return os.path.join(save_dir(), fname)


def _load(name: str = "main") -> list[dict]:
    try:
        with open(path(name), encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            return []
        return [e for e in data if isinstance(e, dict) and "username" in e]
    except (OSError, ValueError, TypeError):
        return []


def _store(entries: list[dict], name: str = "main") -> None:
    try:
        os.makedirs(os.path.dirname(path(name)) or ".", exist_ok=True)
        tmp = f"{path(name)}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(entries[:MAX_ENTRIES], fh, sort_keys=True)
        os.replace(tmp, path(name))
    except OSError:
        pass  # the board is best-effort; never crash a session over it


def sort_key(entry: dict) -> tuple:
    return (
        -entry.get("score", 0),
        -entry.get("cleared", 0),
        -entry.get("shards", 0),
        entry.get("username", "").lower(),
    )


def board(name: str = "main") -> list[dict]:
    """The ranked board: best score first."""
    return sorted(_load(name), key=sort_key)


def record(
    username: str, score: int, cleared: int, shards: int, name: str = "main"
) -> None:
    """Upsert a runner's entry, keeping their best score and furthest node."""
    entries = _load(name)
    for entry in entries:
        if entry.get("username") == username:
            entry["score"] = max(entry.get("score", 0), score)
            entry["cleared"] = max(entry.get("cleared", 0), cleared)
            entry["shards"] = max(entry.get("shards", 0), shards)
            break
    else:
        entries.append(
            {
                "username": username,
                "score": score,
                "cleared": cleared,
                "shards": shards,
            }
        )
    entries.sort(key=sort_key)
    _store(entries[:MAX_ENTRIES], name)


def rank_of(
    username: str, score: int, cleared: int, shards: int, name: str = "main"
) -> int:
    """Where this runner would sit on the board right now (1-based)."""
    probe = {
        "username": username,
        "score": score,
        "cleared": cleared,
        "shards": shards,
    }
    entries = board(name)
    for i, entry in enumerate(entries):
        if entry.get("username") == username:
            return i + 1
    entries.append(probe)
    entries.sort(key=sort_key)
    for i, entry in enumerate(entries):
        if entry.get("username") == username:
            return i + 1
    return len(entries)  # pragma: no cover - unreachable
