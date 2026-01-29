import pytest
import uuid

# === 集成测试: 稿件创建 ===

@pytest.mark.asyncio
async def test_manuscript_creation_with_real_db(db_connection):
    """使用真实数据库创建稿件记录"""
    manuscript_id = str(uuid.uuid4())
    data = {
        "id": manuscript_id,
        "title": "Integration Test Manuscript",
        "abstract": "Integration abstract",
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "submitted",
    }

    response = db_connection.table("manuscripts").insert(data).execute()
    assert response.data
    assert response.data[0]["id"] == manuscript_id

    # 清理测试数据
    db_connection.table("manuscripts").delete().eq("id", manuscript_id).execute()
