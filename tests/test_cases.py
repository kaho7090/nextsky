import json
from pathlib import Path

from nexttrip.cases import EXCLUDED_CASE_IDS, load_cases, load_cases_source_note
from nexttrip.config import CASES_JSON


def _write_cases(tmp_path: Path, cases: list[dict]) -> Path:
    path = tmp_path / "cases.json"
    path.write_text(
        json.dumps({"source": "test", "updated": "2026-11-05", "cases": cases}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def test_load_cases_sorts_by_id(tmp_path: Path):
    path = _write_cases(tmp_path, [{"id": "C-02"}, {"id": "C-01"}])
    assert [c["id"] for c in load_cases(path)] == ["C-01", "C-02"]


def test_load_cases_excludes_internal_cases(tmp_path: Path):
    path = _write_cases(
        tmp_path,
        [{"id": "C-01"}, {"id": "C-08"}, {"id": "C-09"}, {"id": "C-07"}],
    )
    loaded = load_cases(path)
    assert [c["id"] for c in loaded] == ["C-01", "C-07"]
    assert not ({c["id"] for c in loaded} & EXCLUDED_CASE_IDS)


def test_bundled_cases_are_exactly_c01_to_c07():
    cases = load_cases(CASES_JSON)
    assert [c["id"] for c in cases] == [f"C-0{i}" for i in range(1, 8)]
    assert not ({c["id"] for c in cases} & EXCLUDED_CASE_IDS)


def test_bundled_cases_preserve_casebook_statuses():
    by_id = {c["id"]: c for c in load_cases(CASES_JSON)}
    # 判定ラベルはケース集の原文どおり（格上げしない）
    assert by_id["C-05"]["verdict"] == "PHANTOM"
    assert by_id["C-06"]["verdict"] == "UNRESOLVED"
    assert by_id["C-07"]["verdict"] == "TICKETED"
    assert by_id["C-01"]["verdict"] is None
    # C-03 は伝聞マーキングを保持する
    assert by_id["C-03"]["hearsay"] is True
    assert all(by_id[cid]["hearsay"] is False for cid in ("C-01", "C-02", "C-04", "C-05", "C-06", "C-07"))


def test_bundled_cases_source_note_mentions_exclusion():
    note = load_cases_source_note(CASES_JSON)
    assert "C-01" in note and "C-08" in note
