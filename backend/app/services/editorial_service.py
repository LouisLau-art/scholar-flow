from uuid import UUID
from typing import Optional

async def process_quality_check(
    manuscript_id: UUID, 
    passed: bool, 
    owner_id: UUID,
    revision_notes: Optional[str] = None
):
    """
    处理编辑质检逻辑
    
    中文注释:
    1. 遵循章程: 核心业务逻辑必须清晰可见。
    2. 质检通过 -> 进入 under_review 状态。
    3. 质检不通过 -> 状态回滚至 returned_for_revision，并记录修改意见。
    4. 强制绑定 owner_id 以供后续绩效统计。
    """
    new_status = "under_review" if passed else "returned_for_revision"
    
    # 模拟数据库更新操作 (实际逻辑应通过 Supabase Client 执行)
    # update_data = {
    #     "status": new_status,
    #     "owner_id": owner_id,
    #     "updated_at": datetime.now()
    # }
    
    if not passed and revision_notes:
        # 这里应记录修改意见并触发邮件通知逻辑 (T019 之后扩展)
        print(f"退回稿件 {manuscript_id}: {revision_notes}")
        
    return {"id": manuscript_id, "status": new_status, "owner_id": owner_id}

async def handle_plagiarism_result(manuscript_id: UUID, score: float):
    """
    处理查重结果并执行拦截预警
    
    中文注释:
    1. 显性门控逻辑: 如果相似度得分超过 30% (0.3)，自动标记为高风险。
    2. 符合章程: 核心安全逻辑清晰可见。
    """
    if score > 0.3:
        # 自动拦截状态
        print(f"检测到高重复率风险: {manuscript_id}, 得分: {score}")
        # 发送预警邮件 (模拟触发)
        # trigger_email_notification(manuscript_id, "high_similarity")
        return "high_similarity"
    
    return "submitted"
