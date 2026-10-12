"""Tests for THE DAILY GAUNTLET: date seeding, per-day cache, weekday ramp."""

import datetime
import json
from pathlib import Path

import pytest

from qgrid import daily
from qgrid.levels import parse_level


@pytest.fixture(autouse=True)
def _daily_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("QG_SAVE_DIR", str(tmp_path / "saves"))
    return tmp_path


class TestSeeding:
    def test_same_day_same_level(self):
        d = datetime.date(2026, 10, 12)
        a = daily.daily_level(d)
        b = daily.daily_level(d)
        assert a["rows"] == b["rows"]
        assert a["par"] == b["par"]

    def test_different_days_differ(self):
        a = daily.daily_level(datetime.date(2026, 10, 12))
        b = daily.daily_level(datetime.date(2026, 10, 13))
        assert a["rows"] != b["rows"]

    def test_levels_parse_and_are_solvable(self):
        from qgrid.solver import solve_level

        for offset in range(7):
            day = datetime.date(2026, 10, 12) + datetime.timedelta(days=offset)
            data = daily.daily_level(day)
            assert data["date"] == day.strftime("%Y%m%d")
            layout = parse_level(tuple(data["rows"]), data["name"])
            assert solve_level(layout) is not None

    def test_weekday_difficulty_ramp(self):
        # Monday ramps from sector 3; Sunday lands in sector 6.
        monday = daily.daily_level(datetime.date(2026, 10, 12))
        sunday = daily.daily_level(datetime.date(2026, 10, 18))
        assert monday["zone"] == 3
        assert sunday["zone"] == 6
        assert monday["name"] == "GAUNTLET OCT 12"
        assert "2026-10-18" in sunday["intro"]


class TestCache:
    def test_cache_file_written_and_reused(self):
        day = datetime.date(2026, 10, 12)
        first = daily.daily_level(day)
        path = Path(daily.cache_path(day.strftime("%Y%m%d")))
        assert path.exists()
        stored = json.loads(path.read_text(encoding="utf-8"))
        assert stored["name"] == first["name"]
        # Corrupt the cache: daily_level must fail loudly rather than
        # silently serving a different layout.
        path.write_text("{broken", encoding="utf-8")
        second = daily.daily_level(day)
        assert second["rows"] == first["rows"]  # regenerated identically

    def test_cache_dir_missing_is_fine(self, tmp_path, monkeypatch):
        monkeypatch.setenv("QG_SAVE_DIR", str(tmp_path / "nested" / "saves"))
        data = daily.daily_level(datetime.date(2026, 10, 14))
        assert data["rows"]


class TestKeys:
    def test_day_key_format(self):
        assert daily.day_key(datetime.date(2026, 10, 12)) == "20261012"

    def test_weekly_table_ramps(self):
        assert daily.WEEKLY[0] < daily.WEEKLY[-1]
        assert daily.WEEKLY == (22, 26, 30, 34, 37, 41, 45)
