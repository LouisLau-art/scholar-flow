import re

from app.core.storage_filename import sanitize_storage_filename


def test_sanitize_storage_filename_keeps_ascii_filename():
    assert sanitize_storage_filename("paper_v2-final.pdf", default_name="file") == "paper_v2-final.pdf"


def test_sanitize_storage_filename_transforms_non_ascii_with_hash_fallback():
    out = sanitize_storage_filename("稿件测试模板20260304.pdf", default_name="review_attachment")
    assert out.endswith(".pdf")
    # 仅允许 ASCII 安全字符
    assert re.fullmatch(r"[A-Za-z0-9._-]+", out) is not None


def test_sanitize_storage_filename_removes_path_separators():
    out = sanitize_storage_filename("nested/path\\evil.docx", default_name="file")
    assert "/" not in out
    assert "\\" not in out
    assert out.endswith(".docx")
