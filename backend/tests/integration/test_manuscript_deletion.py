import pytest
import uuid

# === 集成测试: 稿件删除 ===

@pytest.mark.asyncio
async def test_manuscript_deletion_with_real_db(db_connection):
    """使用真实数据库删除稿件记录"""
    manuscript_id = str(uuid.uuid4())
    data = {
        "id": manuscript_id,
        "title": "Integration Deletion",
        "abstract": "Deletion abstract",
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "pre_check",
    }

    db_connection.table("manuscripts").insert(data).execute()

    db_connection.table("manuscripts").delete().eq("id", manuscript_id).execute()
    fetched = db_connection.table("manuscripts").select("*").eq("id", manuscript_id).execute()
    assert fetched.data == []
