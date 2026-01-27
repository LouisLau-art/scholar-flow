from fastapi import HTTPException
from uuid import UUID
from datetime import datetime

async def publish_manuscript(
    manuscript_id: UUID,
    is_finance_confirmed: bool,
    is_eic_approved: bool
):
    """
    稿件发布最终门控逻辑
    
    中文注释:
    1. 遵循章程: 财务与权限逻辑必须在代码中显性化、清晰可见。
    2. 严格拦截: 必须同时满足 [财务到账] 和 [主编审核通过] 两个条件。
    3. 防止非法上线: 任何一个条件不满足均抛出 403 异常。
    """
    
    # 显性校验 1: 财务状态
    if not is_finance_confirmed:
        raise HTTPException(
            status_code=403, 
            detail="发布拦截: 必须由财务人员手动确认到账后方可发布"
        )
        
    # 显性校验 2: 权限状态
    if not is_eic_approved:
        raise HTTPException(
            status_code=403, 
            detail="发布拦截: 必须获得主编 (Editor-in-Chief) 的终审批准"
        )
        
    # 执行状态流转 (此处为存根，实际需更新 manuscripts 表)
    print(f"Manuscript {manuscript_id} is NOW LIVE.")
    
    return {
        "id": manuscript_id,
        "status": "published",
        "published_at": datetime.now()
    }
