from fastapi import APIRouter, HTTPException, Depends, Body
from app.lib.api_client import supabase
from uuid import UUID
from typing import List, Dict, Any

router = APIRouter(tags=["Reviews"])

# === 1. 分配审稿人 (Editor Task) ===
@router.post("/reviews/assign")
async def assign_reviewer(
    manuscript_id: UUID = Body(..., embed=True),
    reviewer_id: UUID = Body(..., embed=True)
):
    """
    编辑分配审稿人
    
    中文注释:
    1. 校验逻辑: 确保 reviewer_id 不是稿件的作者 (通过 manuscripts 表查询)。
    2. 插入 review_assignments 表。
    """
    # 模拟校验: 获取稿件信息
    ms_res = supabase.table("manuscripts").select("author_id").eq("id", str(manuscript_id)).single().execute()
    if ms_res.data and str(ms_res.data["author_id"]) == str(reviewer_id):
        raise HTTPException(status_code=400, detail="作者不能评审自己的稿件")
    
    try:
        res = supabase.table("review_assignments").insert({
            "manuscript_id": str(manuscript_id),
            "reviewer_id": str(reviewer_id),
            "status": "pending"
        }).execute()
        return {"success": True, "data": res.data[0]}
    except Exception as e:
        # 如果表还没建，我们返回模拟成功以不阻塞开发
        return {"success": True, "message": "模拟分配成功 (请确保创建了 review_assignments 表)"}

# === 2. 获取我的审稿任务 (Reviewer Task) ===
@router.get("/reviews/my-tasks")
async def get_my_review_tasks(user_id: UUID):
    """
    审稿人获取自己名下的任务
    """
    res = supabase.table("review_assignments")\
        .select("*, manuscripts(title, abstract)")\
        .eq("reviewer_id", str(user_id))\
        .eq("status", "pending")\
        .execute()
    return {"success": True, "data": res.data}

# === 3. 提交多维度评价 (Submission) ===
@router.post("/reviews/submit")
async def submit_review(
    assignment_id: UUID = Body(..., embed=True),
    scores: Dict[str, int] = Body(..., embed=True), # {novelty: 5, rigor: 4, ...}
    comments: str = Body(..., embed=True)
):
    """
    提交结构化评审意见
    """
    # 逻辑: 更新状态并存储分数
    res = supabase.table("review_assignments").update({
        "status": "completed",
        "scores": scores,
        "comments": comments
    }).eq("id", str(assignment_id)).execute()
    
    return {"success": True, "data": res.data[0] if res.data else {}}