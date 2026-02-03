from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID


def generate_mock_doi(*, manuscript_id: str | UUID, prefix: str = "10.5555") -> str:
    """
    Feature 024: DOI Mock 生成

    规则（MVP）:
    - 格式: 10.5555/scholarflow.{year}.{8_char_uuid}
    - 8_char_uuid 取 manuscript UUID 的前 8 位（去掉短横线后）
    """
    year = datetime.now(timezone.utc).year
    mid = str(manuscript_id)
    short = mid.replace("-", "")[:8].lower()
    if not short:
        short = "unknown"
    return f"{prefix}/scholarflow.{year}.{short}"

