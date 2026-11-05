"""エラー運賃ケース集（C-01〜C-07）の読み込み。

データは data/cases.json（NextTicket エラー運賃ケース集から抜粋）。
内部案件の C-08 / C-09 は抜粋時点で除外しているが、将来ファイルが
差し替わってもアプリ側に混入しないよう、読み込み時にも除外する。
"""

import json
from pathlib import Path

# 内部案件として公開対象から外すケース ID
EXCLUDED_CASE_IDS = frozenset({"C-08", "C-09"})


def _read_cases_file(json_path: Path) -> dict:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError("cases file must be a JSON object with a 'cases' list")
    return data


def load_cases_source_note(json_path: Path) -> str:
    """ケース集の出典メモ（出典・更新日）を返す。"""
    return str(_read_cases_file(json_path).get("source", ""))


def load_cases(json_path: Path) -> list[dict]:
    """ケース一覧を ID 順に返す。除外 ID（C-08 / C-09）は読み込まない。"""
    cases: list[dict] = []
    for case in _read_cases_file(json_path)["cases"]:
        case_id = str(case.get("id", "")).strip().upper()
        if not case_id:
            raise ValueError("each case must have an 'id'")
        if case_id in EXCLUDED_CASE_IDS:
            continue
        cases.append(case)
    cases.sort(key=lambda c: str(c["id"]))
    return cases
