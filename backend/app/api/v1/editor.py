from fastapi import APIRouter, HTTPException, Body, Depends
from app.lib.api_client import supabase
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/editor", tags=["Editor Command Center"])

def _extract_supabase_data(response):
    """
    兼容 supabase-py / postgrest 在不同版本下的 execute() 返回值形态。
    - 新版: response.data
    - 旧/自定义 mock: (error, data)
    """
    if response is None:
        return None
    data = getattr(response, "data", None)
    if data is not None:
        return data
    if isinstance(response, tuple) and len(response) == 2:
        return response[1]
    return None

@router.get("/pipeline")
async def get_editor_pipeline(
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    获取全站稿件流转状态看板数据
    分栏：待质检、评审中、待录用、已发布
    """
    try:
        # 待质检 (submitted)
        pending_quality_resp = (
            supabase.table("manuscripts")
            .select("*")
            .eq("status", "submitted")
            .execute()
        )
        pending_quality = _extract_supabase_data(pending_quality_resp) or []

        # 评审中 (under_review)
        under_review_resp = (
            supabase.table("manuscripts")
            .select("*")
            .eq("status", "under_review")
            .execute()
        )
        under_review = _extract_supabase_data(under_review_resp) or []

        # 待录用 (pending_decision)
        pending_decision_resp = (
            supabase.table("manuscripts")
            .select("*")
            .eq("status", "pending_decision")
            .execute()
        )
        pending_decision = _extract_supabase_data(pending_decision_resp) or []

        # 已发布 (published)
        published_resp = (
            supabase.table("manuscripts")
            .select("*")
            .eq("status", "published")
            .execute()
        )
        published = _extract_supabase_data(published_resp) or []

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
async def get_available_reviewers(
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
):
    """
    获取可用的审稿人专家池
    """
    try:
        # 从users表获取角色为reviewer的用户
        reviewers_resp = (
            supabase.table("users")
            .select("*")
            .eq("role", "reviewer")
            .execute()
        )
        reviewers = _extract_supabase_data(reviewers_resp) or []

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
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
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

    except HTTPException:
        raise
    except Exception as e:
        print(f"Decision submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit decision")


@router.post("/publish")
async def publish_manuscript_dev(
    current_user: dict = Depends(get_current_user),
    _profile: dict = Depends(require_any_role(["editor", "admin"])),
    manuscript_id: str = Body(..., embed=True),
):
    """
    快捷发布：将稿件直接设置为 published。

    中文注释:
    1) 用于演示/测试，让公开搜索（published-only）能快速看到结果。
    2) 仍然需要 editor/admin 角色，避免普通作者误操作。
    """
    try:
        doi = f"10.1234/sf.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        update_data = {
            "status": "published",
            "published_at": datetime.now().isoformat(),
            "doi": doi,
        }
        response = supabase.table("manuscripts").update(update_data).eq("id", manuscript_id).execute()
        if not getattr(response, "data", None):
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return {"success": True, "data": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Publish failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish manuscript")


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
