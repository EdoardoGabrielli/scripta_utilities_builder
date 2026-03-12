"""
Tests for move_anomalie.py

Run with:  pytest standalones/tests/ -v
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from move_anomalie import load_ids, get_target, find_matches, move_files


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def image_tree(tmp_path):
    """
    tmp_path/
      E033006.jpg        <- match
      E033007.tif        <- match
      unrelated.png      <- no match
      subdir/
        F041332.jpg      <- match (in subdirectory)
        other.jpg        <- no match
      Anomalie/
        E033006.jpg      <- already moved, must be skipped
    """
    (tmp_path / "subdir").mkdir()
    (tmp_path / "Anomalie").mkdir()
    (tmp_path / "E033006.jpg").touch()
    (tmp_path / "E033007.tif").touch()
    (tmp_path / "unrelated.png").touch()
    (tmp_path / "subdir" / "F041332.jpg").touch()
    (tmp_path / "subdir" / "other.jpg").touch()
    (tmp_path / "Anomalie" / "E033006.jpg").touch()
    return tmp_path


# ── load_ids ──────────────────────────────────────────────────────────────────

class TestLoadIds:
    def test_basic_pipe_format(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("E033006 | ANOMALIA\nF041332 | ERRORE\n")
        assert load_ids(f) == {"e033006", "f041332"}

    def test_without_pipe(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("E033006\nF041332\n")
        assert load_ids(f) == {"e033006", "f041332"}

    def test_empty_lines_ignored(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("E033006 | X\n\n   \nF041332 | Y\n")
        assert load_ids(f) == {"e033006", "f041332"}

    def test_normalizes_to_lowercase(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("E033006BIS | X\n")
        assert "e033006bis" in load_ids(f)

    def test_strips_whitespace(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("  E033006  | ANOMALIA\n")
        assert "e033006" in load_ids(f)

    def test_empty_file_returns_empty_set(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("")
        assert load_ids(f) == set()

    def test_deduplicates_ids(self, tmp_path):
        f = tmp_path / "ids.txt"
        f.write_text("E033006 | A\nE033006 | B\n")
        assert len(load_ids(f)) == 1


# ── get_target ────────────────────────────────────────────────────────────────

class TestGetTarget:
    def test_root_level_file(self, tmp_path):
        base = tmp_path
        anomalie = tmp_path / "Anomalie"
        src = tmp_path / "E033006.jpg"
        assert get_target(src, base, anomalie) == anomalie / "E033006.jpg"

    def test_preserves_subdirectory(self, tmp_path):
        base = tmp_path
        anomalie = tmp_path / "Anomalie"
        src = tmp_path / "sub" / "E033006.jpg"
        assert get_target(src, base, anomalie) == anomalie / "sub" / "E033006.jpg"

    def test_deep_nesting(self, tmp_path):
        base = tmp_path
        anomalie = tmp_path / "Anomalie"
        src = tmp_path / "a" / "b" / "c" / "E033006.jpg"
        assert get_target(src, base, anomalie) == anomalie / "a" / "b" / "c" / "E033006.jpg"


# ── find_matches ──────────────────────────────────────────────────────────────

class TestFindMatches:
    def test_finds_expected_files(self, image_tree):
        ids = {"e033006", "e033007", "f041332"}
        anomalie = image_tree / "Anomalie"
        matches, _ = find_matches(image_tree, ids, anomalie)
        names = {src.name for src, _ in matches}
        assert names == {"E033006.jpg", "E033007.tif", "F041332.jpg"}

    def test_skips_anomalie_folder(self, image_tree):
        ids = {"e033006"}
        anomalie = image_tree / "Anomalie"
        matches, _ = find_matches(image_tree, ids, anomalie)
        # Only the root-level E033006.jpg should match, not the one in Anomalie/
        assert len(matches) == 1
        src, _ = matches[0]
        assert src.parent == image_tree

    def test_case_insensitive_match_uppercase_file(self, tmp_path):
        (tmp_path / "Anomalie").mkdir()
        (tmp_path / "E033006.jpg").touch()      # uppercase filename
        ids = {"e033006"}                        # lowercase id (as load_ids produces)
        matches, _ = find_matches(tmp_path, ids, tmp_path / "Anomalie")
        assert len(matches) == 1

    def test_case_insensitive_match_lowercase_file(self, tmp_path):
        (tmp_path / "Anomalie").mkdir()
        (tmp_path / "e033006.jpg").touch()      # lowercase filename
        ids = {"e033006"}
        matches, _ = find_matches(tmp_path, ids, tmp_path / "Anomalie")
        assert len(matches) == 1

    def test_no_matches_returns_empty(self, image_tree):
        ids = {"notexistent"}
        anomalie = image_tree / "Anomalie"
        matches, _ = find_matches(image_tree, ids, anomalie)
        assert matches == []

    def test_scan_count_excludes_anomalie(self, image_tree):
        anomalie = image_tree / "Anomalie"
        _, scan_count = find_matches(image_tree, set(), anomalie)
        # 5 non-anomalie files in the fixture (E033006.jpg, E033007.tif,
        # unrelated.png, subdir/F041332.jpg, subdir/other.jpg)
        assert scan_count == 5

    def test_progress_callback_triggered(self, tmp_path):
        (tmp_path / "Anomalie").mkdir()
        for i in range(1001):
            (tmp_path / f"file_{i:04d}.jpg").touch()
        callback = MagicMock()
        find_matches(tmp_path, set(), tmp_path / "Anomalie", on_progress=callback)
        # Called at 500 and 1000
        assert callback.call_count == 2
        callback.assert_any_call(500)
        callback.assert_any_call(1000)

    def test_progress_callback_not_triggered_for_small_trees(self, image_tree):
        anomalie = image_tree / "Anomalie"
        callback = MagicMock()
        find_matches(image_tree, set(), anomalie, on_progress=callback)
        callback.assert_not_called()

    def test_target_path_preserves_structure(self, image_tree):
        ids = {"f041332"}
        anomalie = image_tree / "Anomalie"
        matches, _ = find_matches(image_tree, ids, anomalie)
        assert len(matches) == 1
        src, dst = matches[0]
        assert dst == anomalie / "subdir" / "F041332.jpg"

    def test_empty_ids_set_finds_nothing(self, image_tree):
        anomalie = image_tree / "Anomalie"
        matches, scan_count = find_matches(image_tree, set(), anomalie)
        assert matches == []
        assert scan_count == 5  # still scanned all files


# ── move_files ────────────────────────────────────────────────────────────────

class TestMoveFiles:
    def test_moves_file(self, tmp_path):
        src = tmp_path / "E033006.jpg"
        src.touch()
        dst = tmp_path / "Anomalie" / "E033006.jpg"
        (tmp_path / "Anomalie").mkdir()

        success, errors = move_files([(src, dst)])

        assert success == 1
        assert errors == []
        assert not src.exists()
        assert dst.exists()

    def test_creates_missing_directories(self, tmp_path):
        src = tmp_path / "E033006.jpg"
        src.touch()
        dst = tmp_path / "Anomalie" / "sub" / "deep" / "E033006.jpg"
        # Anomalie/ does NOT exist yet

        success, errors = move_files([(src, dst)])

        assert success == 1
        assert errors == []
        assert dst.exists()

    def test_reports_error_for_missing_source(self, tmp_path):
        src = tmp_path / "ghost.jpg"   # does not exist
        dst = tmp_path / "Anomalie" / "ghost.jpg"
        (tmp_path / "Anomalie").mkdir()

        success, errors = move_files([(src, dst)])

        assert success == 0
        assert len(errors) == 1
        assert "ghost.jpg" in errors[0]

    def test_multiple_files(self, tmp_path):
        files = [tmp_path / f"file_{i}.jpg" for i in range(5)]
        for f in files:
            f.touch()
        anomalie = tmp_path / "Anomalie"
        anomalie.mkdir()
        pairs = [(f, anomalie / f.name) for f in files]

        success, errors = move_files(pairs)

        assert success == 5
        assert errors == []
        for f in files:
            assert not f.exists()
            assert (anomalie / f.name).exists()

    def test_partial_failure(self, tmp_path):
        good = tmp_path / "good.jpg"
        good.touch()
        bad = tmp_path / "ghost.jpg"   # does not exist
        anomalie = tmp_path / "Anomalie"
        anomalie.mkdir()

        success, errors = move_files([
            (good, anomalie / "good.jpg"),
            (bad, anomalie / "ghost.jpg"),
        ])

        assert success == 1
        assert len(errors) == 1
        assert (anomalie / "good.jpg").exists()

    def test_empty_matches_list(self, tmp_path):
        success, errors = move_files([])
        assert success == 0
        assert errors == []
