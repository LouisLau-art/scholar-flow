import pytest
import uuid

# === 集成测试: 稿件查询 ===

@pytest.mark.asyncio
async def test_manuscript_retrieval_with_real_db(db_connection):
    """使用真实数据库查询稿件记录"""
    manuscript_id = str(uuid.uuid4())
    data = {
        "id": manuscript_id,
        "title": "Integration Retrieval",
        "abstract": "Retrieve abstract",
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "pre_check",
    }

    db_connection.table("manuscripts").insert(data).execute()

    fetched = db_connection.table("manuscripts").select("*").eq("id", manuscript_id).single().execute()
    assert fetched.data
    assert fetched.data["id"] == manuscript_id

    # 清理测试数据
    db_connection.table("manuscripts").delete().eq("id", manuscript_id).execute()
