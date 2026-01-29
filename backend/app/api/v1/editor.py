from fastapi import APIRouter, HTTPException, Body, Depends
from app.lib.api_client import supabase
from app.core.auth_utils import get_current_user
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/editor", tags=["Editor Command Center"])

@router.get("/pipeline")
async def get_editor_pipeline(current_user: dict = Depends(get_current_user)):
    """
    获取全站稿件流转状态看板数据
    分栏：待质检、评审中、待录用、已发布
    """
    try:
        # 待质检 (submitted)
        pending_quality = supabase.table("manuscripts").select("*").eq("status", "submitted").execute()[1]

        # 评审中 (under_review)
        under_review = supabase.table("manuscripts").select("*").eq("status", "under_review").execute()[1]

        # 待录用 (pending_decision)
        pending_decision = supabase.table("manuscripts").select("*").eq("status", "pending_decision").execute()[1]

        # 已发布 (published)
        published = supabase.table("manuscripts").select("*").eq("status", "published").execute()[1]

        return {
            "success": True,
            "data": {
                "pending_quality": pending_quality,
                "under_review": under_review,
                "pending_decision": pending_decision,
                "published": published
            }
        }

    except Exception as e:
        print(f"Pipeline query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline data")

@router.get("/available-reviewers")
async def get_available_reviewers(current_user: dict = Depends(get_current_user)):
    """
    获取可用的审稿人专家池
    """
    try:
        # 从users表获取角色为reviewer的用户
        reviewers = supabase.table("users").select("*").eq("role", "reviewer").execute()[1]

        # 格式化返回数据，包含必要信息
        formatted_reviewers = []
        for reviewer in reviewers:
            formatted_reviewers.append({
                "id": reviewer["id"],
                "name": reviewer["name"],
                "email": reviewer["email"],
                "affiliation": reviewer.get("affiliation", "Unknown"),
                "expertise": reviewer.get("expertise", []),
                "review_count": reviewer.get("review_count", 0)
            })

        return {
            "success": True,
            "data": formatted_reviewers
        }

    except Exception as e:
        print(f"Reviewers query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available reviewers")

@router.post("/decision")
async def submit_final_decision(
    current_user: dict = Depends(get_current_user),
    manuscript_id: str = Body(..., embed=True),
    decision: str = Body(..., embed=True),
    comment: str = Body("", embed=True)
):
    """
    提交最终录用或退回决策
    decision: "accept" | "reject"
    """
    # 验证决策类型
    if decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid decision type")

    try:
        # 更新稿件状态
        if decision == "accept":
            # 录用：设置为已发布，生成DOI，记录发布时间
            doi = f"10.1234/sf.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            update_data = {
                "status": "published",
                "published_at": datetime.now().isoformat(),
                "doi": doi
            }
        else:
            # 退回：设置为需要修改，添加拒绝理由
            update_data = {
                "status": "revision_required",
                "reject_comment": comment
            }

        # 执行更新
        response = supabase.table("manuscripts").update(update_data).eq("id", manuscript_id).execute()

        if len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        return {
            "success": True,
            "message": "Decision submitted successfully",
            "data": {
                "manuscript_id": manuscript_id,
                "decision": decision,
                "status": update_data["status"]
            }
        }

    except Exception as e:
        print(f"Decision submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit decision")


# 测试端点 - 不需要身份验证
@router.get("/test/pipeline")
async def get_editor_pipeline_test():
    """
    测试端点：获取全站稿件流转状态看板数据（无需身份验证）
    """
    try:
        # Mock数据用于测试
        return {
            "success": True,
            "data": {
                "pending_quality": [{"id": "1", "title": "Test Manuscript 1", "status": "submitted"}],
                "under_review": [{"id": "2", "title": "Test Manuscript 2", "status": "under_review"}],
                "pending_decision": [{"id": "3", "title": "Test Manuscript 3", "status": "pending_decision"}],
                "published": [{"id": "4", "title": "Test Manuscript 4", "status": "published"}]
            }
        }

    except Exception as e:
        print(f"Pipeline query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pipeline data")


@router.get("/test/available-reviewers")
async def get_available_reviewers_test():
    """
    测试端点：获取可用的审稿人专家池（无需身份验证）
    """
    try:
        # Mock数据用于测试
        return {
            "success": True,
            "data": [
                {
                    "id": "1",
                    "name": "Dr. Jane Smith",
                    "email": "jane.smith@example.com",
                    "affiliation": "MIT",
                    "expertise": ["AI", "Machine Learning"],
                    "review_count": 15
                },
                {
                    "id": "2",
                    "name": "Prof. John Doe",
                    "email": "john.doe@example.com",
                    "affiliation": "Stanford University",
                    "expertise": ["Computer Science", "Data Science"],
                    "review_count": 20
                }
            ]
        }

    except Exception as e:
        print(f"Reviewers query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available reviewers")


@router.post("/test/decision")
async def submit_final_decision_test(
    manuscript_id: str = Body(..., embed=True),
    decision: str = Body(..., embed=True),
    comment: str = Body("", embed=True)
):
    """
    测试端点：提交最终录用或退回决策（无需身份验证）
    decision: "accept" | "reject"
    """
    # 验证决策类型
    if decision not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid decision type")

    # Mock响应
    if decision == "accept":
        doi = f"10.1234/sf.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        status = "published"
    else:
        status = "revision_required"

    return {
        "success": True,
        "message": "Decision submitted successfully",
        "data": {
            "manuscript_id": manuscript_id,
            "decision": decision,
            "status": status
        }
    }