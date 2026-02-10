"""
Revision Service: 处理稿件修订工作流的核心业务逻辑

中文注释:
1. 遵循章程: 所有核心业务逻辑在 Service 层实现，API 层仅做请求验证和路由。
2. 状态机保证: 所有状态变更通过 Service 统一管理，避免客户端直接修改。
3. 文件安全: 从不覆盖原始文件，始终创建新版本。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
from app.lib.api_client import supabase_admin
from app.services.notification_service import NotificationService
from app.models.manuscript import ManuscriptStatus, normalize_status


class RevisionService:
    """Revision 工作流的核心服务类"""

    def __init__(self):
        # 中文注释:
        # - 修订工作流属于服务端受控流程：API 层负责鉴权与 RBAC 校验。
        # - DB 层的 RLS 在某些表上会阻止 anon client 读取（例如 revisions/manuscript_versions），
        #   若 read_client 仍用 anon key，会导致“找不到 pending revision”等错误。
        # - 因此 service 层统一使用 service_role client 做读写，保证工作流在启用 RLS 的云端环境可用。
        self.client = supabase_admin
        self.read_client = supabase_admin

    def _extract_data(self, response):
        """兼容 supabase-py 不同版本的响应格式"""
        if response is None:
            return None
        data = getattr(response, "data", None)
        if data is not None:
            return data
        if isinstance(response, tuple) and len(response) == 2:
            return response[1]
        return None

    def _extract_error(self, response):
        """兼容不同版本的错误提取"""
        if response is None:
            return None
        error = getattr(response, "error", None)
        if error:
            return error
        if isinstance(response, tuple) and len(response) == 2:
            return response[0]
        return None

    def get_manuscript(self, manuscript_id: str) -> Optional[dict]:
        """获取稿件信息"""
        try:
            response = (
                self.read_client.table("manuscripts")
                .select("*")
                .eq("id", manuscript_id)
                .single()
                .execute()
            )
            return self._extract_data(response)
        except Exception as e:
            print(f"[RevisionService] get_manuscript error: {e}")
            return None

    def get_pending_revision(self, manuscript_id: str) -> Optional[dict]:
        """
        获取该稿件最新的待处理修订请求

        中文注释: 只获取 status='pending' 的记录，表示作者尚未提交修订稿
        """
        try:
            response = (
                self.read_client.table("revisions")
                .select("*")
                .eq("manuscript_id", manuscript_id)
                .eq("status", "pending")
                .order("round_number", desc=True)
                .limit(1)
                .execute()
            )
            data = self._extract_data(response) or []
            return data[0] if data else None
        except Exception as e:
            print(f"[RevisionService] get_pending_revision error: {e}")
            return None

    def _latest_revision_feedback_comment(self, manuscript_id: str) -> str | None:
        """
        从状态流转日志中提取最近一次“退修”反馈。

        中文注释:
        - 兼容 ME/AE 预审退回场景：这类场景可能先有状态流转日志，再由作者进入修回页面；
        - 若未落 `revisions.pending`，可用该评论补一条 pending 记录，避免作者端报错。
        """
        try:
            resp = (
                self.read_client.table("status_transition_logs")
                .select("to_status,comment,payload,created_at")
                .eq("manuscript_id", manuscript_id)
                .order("created_at", desc=True)
                .limit(30)
                .execute()
            )
            rows = self._extract_data(resp) or []
        except Exception as e:
            print(f"[RevisionService] load transition logs failed: {e}")
            return None

        for row in rows:
            comment = str(row.get("comment") or "").strip()
            if not comment:
                continue
            to_status_raw = str(row.get("to_status") or "").strip().lower()
            to_status = normalize_status(to_status_raw) or to_status_raw
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            action = str(payload.get("action") or "").strip().lower()
            if to_status in {
                ManuscriptStatus.MAJOR_REVISION.value,
                ManuscriptStatus.MINOR_REVISION.value,
            } or ("revision" in action):
                return comment
        return None

    def ensure_pending_revision_for_submit(
        self, manuscript_id: str, manuscript: dict | None = None
    ) -> Optional[dict]:
        """
        确保作者修回前存在 pending revision 记录（幂等）。

        中文注释:
        - 正常链路（Editor 发起修回）本来就有 pending 记录；
        - ME Intake 技术退回等兼容链路可能只有状态流转，没有 pending；
        - 这里做一次“补齐”，保证作者提交修回不会卡在 `No pending revision`.
        """
        existing = self.get_pending_revision(manuscript_id)
        if existing:
            return existing

        ms = manuscript or self.get_manuscript(manuscript_id)
        if not ms:
            return None

        current_status_raw = str(ms.get("status") or "").strip().lower()
        current_status = normalize_status(current_status_raw) or current_status_raw
        precheck_stage = str(ms.get("pre_check_status") or "").strip().lower()
        if current_status not in {
            ManuscriptStatus.MAJOR_REVISION.value,
            ManuscriptStatus.MINOR_REVISION.value,
            "revision_requested",
        }:
            return None

        decision_type = (
            "major"
            if current_status == ManuscriptStatus.MAJOR_REVISION.value
            else "minor"
        )
        comment = self._latest_revision_feedback_comment(manuscript_id) or (
            "Please revise the manuscript and resubmit."
        )
        now = datetime.now(timezone.utc).isoformat()

        try:
            self.client.table("revisions").insert(
                {
                    "manuscript_id": manuscript_id,
                    "round_number": self.get_next_round_number(manuscript_id),
                    "decision_type": decision_type,
                    "editor_comment": comment,
                    "status": "pending",
                    "created_at": now,
                }
            ).execute()
        except Exception as e:
            # 幂等容错：并发下可能已被其他请求创建，继续回读即可
            print(f"[RevisionService] ensure pending revision insert failed (ignored): {e}")

        pending = self.get_pending_revision(manuscript_id)
        if (
            pending
            and current_status == ManuscriptStatus.MINOR_REVISION.value
            and precheck_stage in {"intake", "technical"}
        ):
            # 中文注释:
            # - 仅对“本次自动补齐”返回一次性来源信息，供当前提交请求判定回流队列；
            # - 不写入数据库字段，避免引入迁移依赖。
            pending["__derived_precheck_stage"] = precheck_stage
        return pending

    def get_next_round_number(self, manuscript_id: str) -> int:
        """
        获取下一个修订轮次编号

        中文注释: 查询已有的最大 round_number，加 1 作为新轮次
        """
        try:
            response = (
                self.read_client.table("revisions")
                .select("round_number")
                .eq("manuscript_id", manuscript_id)
                .order("round_number", desc=True)
                .limit(1)
                .execute()
            )
            data = self._extract_data(response) or []
            if data:
                return data[0]["round_number"] + 1
            return 1
        except Exception as e:
            print(f"[RevisionService] get_next_round_number error: {e}")
            return 1

    def create_revision_request(
        self,
        manuscript_id: str,
        decision_type: Literal["major", "minor"],
        editor_comment: str,
    ) -> dict:
        """
        Editor 请求修订 (User Story 1)

        中文注释:
        1. 验证稿件状态是否允许请求修订（under_review / decision / resubmitted）
        2. 创建当前版本的快照（manuscript_version）
        3. 创建 revision 记录
        4. 更新稿件状态为 major_revision / minor_revision（Feature 028）

        Gate 2: 文件安全 - 此操作不修改任何文件，仅创建元数据记录
        """
        # 1. 获取稿件当前状态
        manuscript = self.get_manuscript(manuscript_id)
        if not manuscript:
            return {"success": False, "error": "Manuscript not found"}

        current_status_raw = manuscript.get("status", "")
        current_status = normalize_status(str(current_status_raw)) or str(current_status_raw or "")
        # 中文注释:
        # - resubmitted：作者修回后，Editor 可能仍需“再退回一轮小修/大修”，MVP 允许此操作。
        allowed_statuses = [
            ManuscriptStatus.UNDER_REVIEW.value,
            ManuscriptStatus.DECISION.value,
            "pending_decision",  # 兼容旧数据
            ManuscriptStatus.RESUBMITTED.value,
        ]
        if current_status not in allowed_statuses:
            return {
                "success": False,
                "error": f"Cannot request revision for manuscript with status '{current_status}'. Allowed: {allowed_statuses}",
            }

        # 2. 获取下一轮次编号
        round_number = self.get_next_round_number(manuscript_id)

        # 3. 创建当前版本快照（如果是第一次请求修订）
        current_version = manuscript.get("version", 1)
        if round_number == 1:
            # 首次修订请求，创建 v1 快照
            self._create_version_snapshot(manuscript, current_version)

        # 4. 创建 revision 记录
        now = datetime.now(timezone.utc).isoformat()
        revision_data = {
            "manuscript_id": manuscript_id,
            "round_number": round_number,
            "decision_type": decision_type,
            "editor_comment": editor_comment,
            "status": "pending",
            "created_at": now,
        }

        try:
            revision_response = (
                self.client.table("revisions").insert(revision_data).execute()
            )
            revision = (self._extract_data(revision_response) or [{}])[0]
        except Exception as e:
            print(f"[RevisionService] create revision error: {e}")
            return {"success": False, "error": f"Failed to create revision: {e}"}

        # 5. 更新稿件状态（Feature 028）
        try:
            new_status = (
                ManuscriptStatus.MAJOR_REVISION.value
                if decision_type == "major"
                else ManuscriptStatus.MINOR_REVISION.value
            )
            self.client.table("manuscripts").update(
                {
                    "status": new_status,
                    "updated_at": now,
                }
            ).eq("id", manuscript_id).execute()
        except Exception as e:
            print(f"[RevisionService] update manuscript status error: {e}")
            return {
                "success": False,
                "error": f"Failed to update manuscript status: {e}",
            }

        # 6. 取消未完成的审稿任务（避免 Reviewer 继续看到该稿件）
        # 中文注释:
        # - MVP 允许 Editor “不等所有 reviewer 回应就直接做决定/退修”。
        # - 一旦进入 major/minor revision，未完成的 review_assignments 应视为作废。
        try:
            self.client.table("review_assignments").update({"status": "cancelled"}).eq(
                "manuscript_id", manuscript_id
            ).eq("status", "pending").execute()
        except Exception as e:
            print(f"[RevisionService] cancel pending review_assignments failed (ignored): {e}")

        return {
            "success": True,
            "data": {
                "revision": revision,
                "manuscript_status": new_status,
                "round_number": round_number,
            },
        }

    def _create_version_snapshot(self, manuscript: dict, version_number: int):
        """
        创建稿件版本快照

        中文注释: 保存当前稿件的 title、abstract、file_path 作为历史记录
        """
        now = datetime.now(timezone.utc).isoformat()
        version_data = {
            "manuscript_id": manuscript["id"],
            "version_number": version_number,
            "file_path": manuscript.get("file_path", ""),
            "title": manuscript.get("title"),
            "abstract": manuscript.get("abstract"),
            "created_at": now,
        }

        try:
            self.client.table("manuscript_versions").insert(version_data).execute()
        except Exception as e:
            # 可能是唯一约束冲突（版本已存在），忽略
            print(f"[RevisionService] create version snapshot: {e}")

    def submit_revision(
        self,
        manuscript_id: str,
        author_id: str,
        new_file_path: str,
        response_letter: str,
        new_title: Optional[str] = None,
        new_abstract: Optional[str] = None,
        precheck_resubmit_stage: Optional[Literal["intake", "technical"]] = None,
    ) -> dict:
        """
        Author 提交修订稿 (User Story 2)

        中文注释:
        1. 验证稿件状态必须是 major_revision / minor_revision（兼容旧 revision_requested）
        2. 验证作者身份
        3. 创建新版本记录
        4. 更新 revision 记录（填充 response_letter, submitted_at）
        5. 更新稿件状态为 resubmitted，版本号 +1

        Gate 2: 文件安全 - 新文件使用 versioned path，不覆盖原文件
        """
        # 1. 获取稿件
        manuscript = self.get_manuscript(manuscript_id)
        if not manuscript:
            return {"success": False, "error": "Manuscript not found"}

        # 2. 验证状态
        current_status = normalize_status(str(manuscript.get("status") or "")) or str(manuscript.get("status") or "")
        if current_status not in {ManuscriptStatus.MAJOR_REVISION.value, ManuscriptStatus.MINOR_REVISION.value, "revision_requested"}:
            return {
                "success": False,
                "error": f"Cannot submit revision: manuscript status is '{manuscript.get('status')}', expected major/minor revision",
            }

        # 3. 验证作者身份
        if str(manuscript.get("author_id")) != str(author_id):
            return {
                "success": False,
                "error": "Only the manuscript author can submit revisions",
            }

        # 4. 获取待处理的 revision
        pending_revision = self.get_pending_revision(manuscript_id)
        if not pending_revision:
            return {"success": False, "error": "No pending revision request found"}

        # 5. 计算新版本号
        current_version = manuscript.get("version", 1)
        new_version = current_version + 1
        now = datetime.now(timezone.utc).isoformat()

        # 6. 创建新版本记录
        version_data = {
            "manuscript_id": manuscript_id,
            "version_number": new_version,
            "file_path": new_file_path,
            "title": new_title or manuscript.get("title"),
            "abstract": new_abstract or manuscript.get("abstract"),
            "created_at": now,
        }

        try:
            version_response = (
                self.client.table("manuscript_versions").insert(version_data).execute()
            )
            new_version_record = (self._extract_data(version_response) or [{}])[0]
        except Exception as e:
            print(f"[RevisionService] create version error: {e}")
            return {"success": False, "error": f"Failed to create version: {e}"}

        # 7. 更新 revision 记录
        try:
            self.client.table("revisions").update(
                {
                    "response_letter": response_letter,
                    "status": "submitted",
                    "submitted_at": now,
                }
            ).eq("id", pending_revision["id"]).execute()
        except Exception as e:
            print(f"[RevisionService] update revision error: {e}")
            return {"success": False, "error": f"Failed to update revision: {e}"}

        # 8. 更新稿件
        is_precheck_revision_flow = (
            current_status == ManuscriptStatus.MINOR_REVISION.value
            and (precheck_resubmit_stage in {"intake", "technical"})
        )
        manuscript_update: dict = {
            "status": "resubmitted",
            "version": new_version,
            "file_path": new_file_path,
            "updated_at": now,
        }
        if is_precheck_revision_flow:
            # 中文注释:
            # - ME/AE 技术退回后的作者修回应回到预审队列继续处理，而不是进入外审修回分支(resubmitted)。
            manuscript_update["status"] = ManuscriptStatus.PRE_CHECK.value
            manuscript_update["pre_check_status"] = precheck_resubmit_stage
            if precheck_resubmit_stage == "intake":
                # Intake 由 ME 重新看稿，清理 AE 绑定，避免误入 Technical 队列。
                manuscript_update["assistant_editor_id"] = None
        if new_title:
            manuscript_update["title"] = new_title
        if new_abstract:
            manuscript_update["abstract"] = new_abstract

        # 9. 若上一轮为大修：自动发起二审（复用上一轮已完成的 reviewer 列表）
        # 中文注释:
        # - MVP 规则：major revision 的修回默认进入 under_review，并自动生成新一轮 review_assignments（round=new_version）。
        # - minor revision 的修回保持 resubmitted，由 Editor 直接做终审即可。
        created_re_review = False
        try:
            decision_type = str(pending_revision.get("decision_type") or "").strip().lower()
        except Exception:
            decision_type = ""

        if decision_type == "major":
            try:
                prev = (
                    self.read_client.table("review_assignments")
                    .select("reviewer_id, status, round_number")
                    .eq("manuscript_id", manuscript_id)
                    .eq("round_number", current_version)
                    .execute()
                )
                prev_rows = self._extract_data(prev) or []
            except Exception as e:
                print(f"[RevisionService] load previous review_assignments failed: {e}")
                prev_rows = []

            prev_reviewer_ids = sorted(
                {
                    str(r.get("reviewer_id"))
                    for r in prev_rows
                    if r.get("reviewer_id")
                    and str(r.get("status") or "").lower() == "completed"
                }
            )

            if prev_reviewer_ids:
                due_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                for rid in prev_reviewer_ids:
                    try:
                        existing = (
                            self.client.table("review_assignments")
                            .select("id")
                            .eq("manuscript_id", manuscript_id)
                            .eq("reviewer_id", rid)
                            .eq("round_number", new_version)
                            .limit(1)
                            .execute()
                        )
                        if self._extract_data(existing):
                            continue
                    except Exception:
                        # 保守：查不到就尝试插入（由后端幂等/后续 UI 去重兜底）
                        pass

                    try:
                        self.client.table("review_assignments").insert(
                            {
                                "manuscript_id": manuscript_id,
                                "reviewer_id": rid,
                                "status": "pending",
                                "due_at": due_at,
                                "round_number": new_version,
                            }
                        ).execute()
                        created_re_review = True
                    except Exception as e:
                        print(f"[RevisionService] create re-review assignment failed: {e}")
                        continue

                    # 站内通知：提醒 reviewer 有新一轮复审
                    try:
                        title = str(manuscript.get("title") or "Manuscript")
                        NotificationService().create_notification(
                            user_id=str(rid),
                            manuscript_id=str(manuscript_id),
                            type="review_invite",
                            title="Re-review Invitation",
                            content=f"You have been invited to re-review '{title}'.",
                        )
                    except Exception as e:
                        print(f"[RevisionService] create reviewer notification failed (ignored): {e}")

                if created_re_review:
                    manuscript_update["status"] = "under_review"

        try:
            self.client.table("manuscripts").update(manuscript_update).eq(
                "id", manuscript_id
            ).execute()
        except Exception as e:
            print(f"[RevisionService] update manuscript error: {e}")
            return {"success": False, "error": f"Failed to update manuscript: {e}"}

        return {
            "success": True,
            "data": {
                "new_version": new_version_record,
                "revision_id": pending_revision["id"],
                "manuscript_status": manuscript_update.get("status") or "resubmitted",
                "pre_check_status": manuscript_update.get("pre_check_status"),
            },
        }

    def get_version_history(self, manuscript_id: str) -> dict:
        """
        获取稿件的版本历史

        中文注释: 返回所有版本快照和修订记录，用于 Editor 查看历史
        """
        try:
            # 获取所有版本
            versions_resp = (
                self.read_client.table("manuscript_versions")
                .select("*")
                .eq("manuscript_id", manuscript_id)
                .order("version_number", desc=False)
                .execute()
            )
            versions = self._extract_data(versions_resp) or []

            # 获取所有修订记录
            revisions_resp = (
                self.read_client.table("revisions")
                .select("*")
                .eq("manuscript_id", manuscript_id)
                .order("round_number", desc=False)
                .execute()
            )
            revisions = self._extract_data(revisions_resp) or []

            return {
                "success": True,
                "data": {
                    "versions": versions,
                    "revisions": revisions,
                },
            }
        except Exception as e:
            print(f"[RevisionService] get_version_history error: {e}")
            return {"success": False, "error": str(e)}

    def generate_versioned_file_path(
        self,
        manuscript_id: str,
        original_filename: str,
        version_number: int,
    ) -> str:
        """
        生成版本化的文件存储路径

        中文注释:
        - 格式: {manuscript_id}/v{version}_filename.pdf
        - 保证每个版本的文件路径唯一，不会覆盖

        Gate 2: 文件安全 - 使用版本前缀确保不覆盖
        """
        import os

        name, ext = os.path.splitext(original_filename)
        return f"{manuscript_id}/v{version_number}_{name}{ext}"
