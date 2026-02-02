"""
Revision Service: 处理稿件修订工作流的核心业务逻辑

中文注释:
1. 遵循章程: 所有核心业务逻辑在 Service 层实现，API 层仅做请求验证和路由。
2. 状态机保证: 所有状态变更通过 Service 统一管理，避免客户端直接修改。
3. 文件安全: 从不覆盖原始文件，始终创建新版本。
"""

from datetime import datetime, timezone
from typing import Optional, Literal
from uuid import UUID
from app.lib.api_client import supabase, supabase_admin


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
        1. 验证稿件状态是否允许请求修订（under_review / pending_decision）
        2. 创建当前版本的快照（manuscript_version）
        3. 创建 revision 记录
        4. 更新稿件状态为 revision_requested

        Gate 2: 文件安全 - 此操作不修改任何文件，仅创建元数据记录
        """
        # 1. 获取稿件当前状态
        manuscript = self.get_manuscript(manuscript_id)
        if not manuscript:
            return {"success": False, "error": "Manuscript not found"}

        current_status = manuscript.get("status", "")
        allowed_statuses = ["under_review", "pending_decision"]
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

        # 5. 更新稿件状态
        try:
            self.client.table("manuscripts").update(
                {
                    "status": "revision_requested",
                    "updated_at": now,
                }
            ).eq("id", manuscript_id).execute()
        except Exception as e:
            print(f"[RevisionService] update manuscript status error: {e}")
            return {
                "success": False,
                "error": f"Failed to update manuscript status: {e}",
            }

        return {
            "success": True,
            "data": {
                "revision": revision,
                "manuscript_status": "revision_requested",
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
    ) -> dict:
        """
        Author 提交修订稿 (User Story 2)

        中文注释:
        1. 验证稿件状态必须是 revision_requested
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
        if manuscript.get("status") != "revision_requested":
            return {
                "success": False,
                "error": f"Cannot submit revision: manuscript status is '{manuscript.get('status')}', expected 'revision_requested'",
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
        manuscript_update = {
            "status": "resubmitted",
            "version": new_version,
            "file_path": new_file_path,
            "updated_at": now,
        }
        if new_title:
            manuscript_update["title"] = new_title
        if new_abstract:
            manuscript_update["abstract"] = new_abstract

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
                "manuscript_status": "resubmitted",
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
