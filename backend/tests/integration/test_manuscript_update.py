import pytest
import uuid

# === 集成测试: 稿件更新 ===

@pytest.mark.asyncio
async def test_manuscript_update_with_real_db(db_connection):
    """使用真实数据库更新稿件记录"""
    manuscript_id = str(uuid.uuid4())
    data = {
        "id": manuscript_id,
        "title": "Integration Update",
        "abstract": "Update abstract",
        "author_id": "00000000-0000-0000-0000-000000000000",
        "status": "submitted",
    }

    db_connection.table("manuscripts").insert(data).execute()

    db_connection.table("manuscripts").update({"status": "under_review"}).eq("id", manuscript_id).execute()
    fetched = db_connection.table("manuscripts").select("status").eq("id", manuscript_id).single().execute()
    assert fetched.data["status"] == "under_review"

    # 清理测试数据
    db_connection.table("manuscripts").delete().eq("id", manuscript_id).execute()
