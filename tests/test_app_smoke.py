from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "src" / "nexttrip" / "app.py"


def test_app_boots_and_cases_matrix_tab_renders():
    at = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    assert not at.exception
    tab_labels = [t.label for t in at.tabs]
    assert "ケース＆マトリクス" in tab_labels
    markdown_text = "\n".join(m.value for m in at.markdown)
    caption_text = "\n".join(c.value or "" for c in at.caption)
    assert "C-01" in markdown_text
    assert "C-07" in markdown_text
    # 内部案件は画面にも出さない
    assert "C-08" not in markdown_text
    assert "C-09" not in markdown_text
    assert "C-08" not in caption_text
    assert "C-09" not in caption_text
