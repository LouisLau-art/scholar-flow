from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks
from app.lib.api_client import supabase, supabase_admin
from app.core.auth_utils import get_current_user
from app.core.roles import require_any_role
from datetime import datetime
from app.core.mail import EmailService
from app.services.notification_service import NotificationService

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

def _extract_supabase_error(response):
    """
    兼容不同版本的 supabase-py 错误字段。
    """
    if response is None:
        return None
    error = getattr(response, "error", None)
    if error:
        return error
    if isinstance(response, tuple) and len(response) == 2:
        return response[0]
    return None

def _is_missing_column_error(error_text: str) -> bool:
    if not error_text:
        return False
    lowered = error_text.lower()
    return "column" in lowered or "published_at" in lowered or "reject_comment" in lowered or "doi" in lowered

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
        user_id = current_user.get("id")
        email = current_user.get("email")
        self_candidate = None
        if user_id and email:
            name_part = email.split("@")[0].replace(".", " ").title()
            self_candidate = {
                "id": str(user_id),
                "name": f"{name_part} (You)",
                "email": email,
                "affiliation": "Your Account",
                "expertise": ["AI", "Systems"],
                "review_count": 0,
            }

        reviewers_resp = (
            supabase.table("user_profiles")
            .select("id, email, roles")
            .contains("roles", ["reviewer"])
            .execute()
        )
        reviewers = _extract_supabase_data(reviewers_resp) or []

        formatted_reviewers = []
        for reviewer in reviewers:
            email = reviewer.get("email") or "reviewer@example.com"
            name_part = email.split("@")[0].replace(".", " ").title()
            formatted_reviewers.append({
                "id": reviewer["id"],
                "name": name_part or "Reviewer",
                "email": email,
                "affiliation": "Independent Researcher",
                "expertise": ["AI", "Systems"],
                "review_count": 0
            })

        if formatted_reviewers:
            if self_candidate and not any(r["id"] == self_candidate["id"] for r in formatted_reviewers):
                formatted_reviewers.insert(0, self_candidate)
            return {"success": True, "data": formatted_reviewers}

        # fallback: demo reviewers for empty dataset
        if self_candidate:
            return {
                "success": True,
                "data": [
                    self_candidate,
                    {
                        "id": "88888888-8888-8888-8888-888888888888",
                        "name": "Dr. Demo Reviewer",
                        "email": "reviewer1@example.com",
                        "affiliation": "Demo Lab",
                        "expertise": ["AI", "NLP"],
                        "review_count": 12
                    },
                    {
                        "id": "77777777-7777-7777-7777-777777777777",
                        "name": "Prof. Sample Expert",
                        "email": "reviewer2@example.com",
                        "affiliation": "Sample University",
                        "expertise": ["Machine Learning", "Computer Vision"],
                        "review_count": 8
                    },
                    {
                        "id": "66666666-6666-6666-6666-666666666666",
                        "name": "Dr. Placeholder",
                        "email": "reviewer3@example.com",
                        "affiliation": "Research Institute",
                        "expertise": ["Security", "Blockchain"],
                        "review_count": 5
                    }
                ]
            }
        return {
            "success": True,
            "data": [
                {
                    "id": "88888888-8888-8888-8888-888888888888",
                    "name": "Dr. Demo Reviewer",
                    "email": "reviewer1@example.com",
                    "affiliation": "Demo Lab",
                    "expertise": ["AI", "NLP"],
                    "review_count": 12
                },
                {
                    "id": "77777777-7777-7777-7777-777777777777",
                    "name": "Prof. Sample Expert",
                    "email": "reviewer2@example.com",
                    "affiliation": "Sample University",
                    "expertise": ["Machine Learning", "Computer Vision"],
                    "review_count": 8
                },
                {
                    "id": "66666666-6666-6666-6666-666666666666",
                    "name": "Dr. Placeholder",
                    "email": "reviewer3@example.com",
                    "affiliation": "Research Institute",
                    "expertise": ["Security", "Blockchain"],
                    "review_count": 5
                }
            ]
        }

    except Exception as e:
        print(f"Reviewers query failed: {e}")
        if self_candidate:
            return {"success": True, "data": [self_candidate]}
        return {"success": True, "data": []}

@router.post("/decision")
async def submit_final_decision(
    background_tasks: BackgroundTasks = None,
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
        try:
            response = supabase.table("manuscripts").update(update_data).eq("id", manuscript_id).execute()
        except Exception as e:
            error_text = str(e)
            print(f"Decision update error: {error_text}")
            if _is_missing_column_error(error_text):
                response = supabase.table("manuscripts").update({"status": update_data["status"]}).eq("id", manuscript_id).execute()
            else:
                raise

        error = _extract_supabase_error(response)
        if error and _is_missing_column_error(str(error)):
            response = supabase.table("manuscripts").update({"status": update_data["status"]}).eq("id", manuscript_id).execute()
        elif error:
            raise HTTPException(status_code=500, detail="Failed to submit decision")

        data = _extract_supabase_data(response) or []
        if len(data) == 0:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        # === 通知中心 (Feature 011) ===
        # 中文注释:
        # 1) 稿件决策变更属于核心状态变化：作者必须同时收到站内信 + 邮件（异步）。
        try:
            ms_res = (
                supabase.table("manuscripts")
                .select("author_id, title")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            ms = getattr(ms_res, "data", None) or {}
            author_id = ms.get("author_id")
            manuscript_title = ms.get("title") or "Manuscript"
        except Exception:
            author_id = None
            manuscript_title = "Manuscript"

        if author_id:
            decision_label = "Accepted" if decision == "accept" else "Revision Required"
            decision_title = "Editorial Decision" if decision == "accept" else "Editorial Decision: Revision Required"

            NotificationService().create_notification(
                user_id=str(author_id),
                manuscript_id=manuscript_id,
                type="decision",
                title=decision_title,
                content=f"Decision for '{manuscript_title}': {decision_label}.",
            )

            try:
                author_profile = (
                    supabase_admin.table("user_profiles")
                    .select("email")
                    .eq("id", str(author_id))
                    .single()
                    .execute()
                )
                author_email = (getattr(author_profile, "data", None) or {}).get("email")
            except Exception:
                author_email = None

            if author_email and background_tasks is not None:
                email_service = EmailService()
                background_tasks.add_task(
                    email_service.send_template_email,
                    to_email=author_email,
                    subject=decision_title,
                    template_name="decision.html",
                    context={
                        "subject": decision_title,
                        "recipient_name": author_email.split("@")[0].replace(".", " ").title(),
                        "manuscript_title": manuscript_title,
                        "manuscript_id": manuscript_id,
                        "decision_title": decision_title,
                        "decision_label": decision_label,
                        "comment": comment or "",
                    },
                )

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
        try:
            response = supabase.table("manuscripts").update(update_data).eq("id", manuscript_id).execute()
        except Exception as e:
            error_text = str(e)
            print(f"Publish update error: {error_text}")
            if _is_missing_column_error(error_text):
                response = supabase.table("manuscripts").update({"status": update_data["status"]}).eq("id", manuscript_id).execute()
            else:
                raise

        error = _extract_supabase_error(response)
        if error and _is_missing_column_error(str(error)):
            response = supabase.table("manuscripts").update({"status": update_data["status"]}).eq("id", manuscript_id).execute()
        elif error:
            raise HTTPException(status_code=500, detail="Failed to publish manuscript")

        data = _extract_supabase_data(response) or []
        if not data:
            raise HTTPException(status_code=404, detail="Manuscript not found")
        return {"success": True, "data": data[0]}
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
