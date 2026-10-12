"""Tests for lore structures: event cutscenes, records, codex integrity."""

from qgrid.lore import (
    CODEX,
    CODEX_ON_EVENT,
    CODEX_ON_NODE,
    ENDING_CUTSCENES,
    EVENT_CUTSCENES,
    OPENING_CUTSCENE,
    RECORDS,
    SECTOR_CUTSCENES,
    evaluate_records,
)

VALID_SPEAKERS = {"", "NYX", "MIRAGE", "VEX", "ORACLE-9", "KAI"}


def check_cutscene(scene: dict, name: str = "?"):
    assert scene.get("title"), f"{name}: missing title"
    pages = scene.get("pages")
    assert pages, f"{name}: no pages"
    for i, page in enumerate(pages):
        speaker, text = page
        assert speaker in VALID_SPEAKERS, f"{name} p{i}: bad speaker {speaker!r}"
        assert text and len(text) > 10, f"{name} p{i}: empty page"


class TestCampaignCutscenes:
    def test_opening_scene_well_formed(self):
        check_cutscene(OPENING_CUTSCENE, "opening")

    def test_all_sector_scenes_well_formed(self):
        # Sectors 1..5 have clear scenes; sector 6 flows into the ending.
        assert len(SECTOR_CUTSCENES) == 5
        for i, scene in enumerate(SECTOR_CUTSCENES):
            check_cutscene(scene, f"sector{i + 1}")

    def test_both_endings_well_formed(self):
        assert set(ENDING_CUTSCENES) == {"true", "standard"}
        for scene in ENDING_CUTSCENES.values():
            check_cutscene(scene)


class TestEventCutscenes:
    def test_all_event_scenes_well_formed(self):
        assert set(EVENT_CUTSCENES) == {
            "meet_sentinel",
            "meet_hunter",
            "meet_corruptor",
            "first_ice",
            "first_emp",
            "meet_wraith",
            "meet_lancer",
            "meet_volt",
            "first_death",
        }
        for key, scene in EVENT_CUTSCENES.items():
            check_cutscene(scene, key)

    def test_meet_scenes_cover_all_daemon_kinds(self):
        from qgrid.levels import ENEMY_KIND_BY_CHAR

        for kind in set(ENEMY_KIND_BY_CHAR.values()):
            assert f"meet_{kind}" in EVENT_CUTSCENES, f"no intro scene for {kind}"


class TestCodexIntegrity:
    def test_codex_keys_unique(self):
        keys = [c[0] for c in CODEX]
        assert len(keys) == len(set(keys)), "duplicate codex keys"

    def test_codex_entries_have_body(self):
        for key, title, body in CODEX:
            assert title and len(body) > 40, f"{key}: codex body too thin"

    def test_event_codex_keys_exist(self):
        for event, codex_key in CODEX_ON_EVENT.items():
            assert any(c[0] == codex_key for c in CODEX), (
                f"{event} unlocks unknown codex key {codex_key}"
            )

    def test_node_codex_keys_exist(self):
        for node, codex_key in CODEX_ON_NODE.items():
            assert any(c[0] == codex_key for c in CODEX), (
                f"node {node} unlocks unknown codex key {codex_key}"
            )

    def test_codex_grew_with_ice_and_events(self):
        assert len(CODEX) == 22  # 16 originals + 3 daemons + 3 systems


class TestRecords:
    def test_record_keys_unique_with_titles(self):
        keys = [r[0] for r in RECORDS]
        assert len(keys) == len(set(keys))
        for key, title, desc in RECORDS:
            assert title and len(desc) > 20

    def test_first_win_grants_first_descent(self):
        save = {"records": [], "unlocked": 1, "shards": {}}
        game = type("G", (), {"strikes": 2})()
        earned = evaluate_records(save, "win", game)
        assert "first_descent" in earned
        assert "clean_room" not in earned
        assert "survivor" not in earned

    def test_flawless_and_survivor(self):
        game = type("G", (), {"strikes": 0})()
        earned = evaluate_records(
            {"records": [], "unlocked": 3, "shards": {}}, "win", game
        )
        assert "clean_room" in earned and "survivor" not in earned
        game = type("G", (), {"strikes": 3})()
        earned = evaluate_records(
            {"records": [], "unlocked": 3, "shards": {}}, "win", game
        )
        assert "survivor" in earned and "clean_room" not in earned

    def test_progression_records(self):
        save = {"records": [], "unlocked": 26, "shards": {"0": list(range(10))}}
        game = type("G", (), {"strikes": 1})()
        earned = evaluate_records(save, "win", game)
        assert "deep_runner" in earned
        assert "shard_10" in earned
        assert "core_bound" not in earned

    def test_victory_events(self):
        earned = evaluate_records({"records": []}, "victory", False)
        assert earned == ["liberator"]
        earned = evaluate_records({"records": []}, "victory", True)
        assert set(earned) == {"liberator", "true_ending"}

    def test_daily_win(self):
        assert evaluate_records({"records": []}, "daily_win") == ["daily_star"]

    def test_no_repeat_awards(self):
        save = {"records": ["liberator", "true_ending"]}
        assert evaluate_records(save, "victory", True) == []

    def test_records_screen_renders(self):
        from qgrid.render import _strip_ansi, render_records

        save = {"records": ["first_descent", "clean_room", "daily_star"]}
        frame = _strip_ansi(render_records(save, 90, 32))
        assert "3/10 INSCRIPTIONS" in frame
        assert "FIRST DESCENT" in frame
        assert "????????????" in frame  # locked titles hidden
