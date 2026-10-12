"""Tests for the server-wide hall of fame (leaderboard.json)."""

from pathlib import Path

import pytest

from qgrid import leaderboard


@pytest.fixture(autouse=True)
def _board_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("QG_SAVE_DIR", str(tmp_path / "saves"))
    return tmp_path


class TestRecord:
    def test_record_creates_entry(self):
        leaderboard.record("nyx", 15000, 10, 5)
        entries = leaderboard.board()
        assert len(entries) == 1
        assert entries[0]["username"] == "nyx"
        assert entries[0]["score"] == 15000
        assert entries[0]["cleared"] == 10

    def test_upsert_keeps_best(self):
        leaderboard.record("nyx", 15000, 10, 5)
        leaderboard.record("nyx", 9000, 12, 7)
        entries = leaderboard.board()
        assert len(entries) == 1
        assert entries[0]["score"] == 15000
        assert entries[0]["cleared"] == 12  # furthest progress kept
        assert entries[0]["shards"] == 7

    def test_board_sorted_by_score(self):
        leaderboard.record("a", 100, 1, 0)
        leaderboard.record("b", 5000, 5, 2)
        leaderboard.record("c", 3000, 3, 1)
        names = [e["username"] for e in leaderboard.board()]
        assert names == ["b", "c", "a"]

    def test_rank_of_existing_and_newcomer(self):
        leaderboard.record("a", 100, 1, 0)
        leaderboard.record("b", 5000, 5, 2)
        assert leaderboard.rank_of("b", 5000, 5, 2) == 1
        assert leaderboard.rank_of("a", 100, 1, 0) == 2
        # a newcomer with a middling score slots between them
        assert leaderboard.rank_of("c", 3000, 3, 1) == 2

    def test_corrupt_file_degrades_to_empty(self):
        p = Path(leaderboard.path())
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{not json", encoding="utf-8")
        assert leaderboard.board() == []
        leaderboard.record("nyx", 1, 0, 0)
        assert len(leaderboard.board()) == 1

    def test_entries_capped(self):
        for i in range(leaderboard.MAX_ENTRIES + 10):
            leaderboard.record(f"runner{i}", i * 100, 1, 0)
        assert len(leaderboard.board()) == leaderboard.MAX_ENTRIES


class TestScreen:
    def test_render_leaderboard_lists_entries(self):
        from qgrid.render import _strip_ansi, render_leaderboard

        leaderboard.record("nyx", 42000, 48, 20)
        leaderboard.record("vex", 1000, 3, 1)
        save = {"total_score": 42000, "unlocked": 47, "shards": {"0": [0, 1]}}
        frame = _strip_ansi(render_leaderboard(save, "nyx", 90, 30))
        assert "HALL OF FAME" in frame
        assert "nyx" in frame
        assert "vex" in frame
        assert "YOU" in frame

    def test_render_leaderboard_empty(self):
        from qgrid.render import _strip_ansi, render_leaderboard

        frame = _strip_ansi(render_leaderboard({}, "nyx", 90, 30))
        assert "board is empty" in frame.lower()
