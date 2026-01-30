import pytest
from app.services.editorial_service import handle_plagiarism_result
from uuid import uuid4

# === 查重业务规则测试 ===
# 中文注释: 验证 0.3 门控逻辑的边界

@pytest.mark.asyncio
async def test_plagiarism_gate_high_similarity():
    """验证得分 > 0.3 时自动标记为 high_similarity"""
    manuscript_id = uuid4()
    result = await handle_plagiarism_result(manuscript_id, 0.35)
    assert result == "high_similarity"

@pytest.mark.asyncio
async def test_plagiarism_gate_safe():
    """验证得分 <= 0.3 时状态维持 submitted"""
    manuscript_id = uuid4()
    result = await handle_plagiarism_result(manuscript_id, 0.15)
    assert result == "submitted"
