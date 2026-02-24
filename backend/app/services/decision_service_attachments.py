from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException


def _safe_file_name(filename: str) -> str:
    return filename.replace("/", "_").replace("\\", "_")


def _encode_attachment_ref(attachment_id: str, object_path: str) -> str:
    return f"{attachment_id}|{object_path}"


def _decode_attachment_ref(raw: str) -> tuple[str, str]:
    text = str(raw or "").strip()
    if "|" in text:
        attachment_id, path = text.split("|", 1)
        return attachment_id.strip(), path.strip()
    return text, text


class DecisionServiceAttachmentMixin:
    def upload_attachment(
        self,
        *,
        manuscript_id: str,
        user_id: str,
        profile_roles: list[str] | None,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> dict[str, str]:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        self._ensure_internal_decision_access(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            user_id=user_id,
            roles=roles,
            action="decision:record_first",
        )

        if not content:
            raise HTTPException(status_code=400, detail="Attachment cannot be empty")
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Attachment too large (max 25MB)")

        self._ensure_bucket("decision-attachments", public=False)
        attachment_id = str(uuid4())
        safe_name = _safe_file_name(filename or "decision-attachment")
        object_path = f"decision_letters/{manuscript_id}/{attachment_id}_{safe_name}"

        try:
            self.client.storage.from_("decision-attachments").upload(
                object_path,
                content,
                {"content-type": content_type or "application/octet-stream"},
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload attachment: {e}") from e

        return {
            "attachment_id": attachment_id,
            "path": object_path,
            "ref": _encode_attachment_ref(attachment_id, object_path),
        }

    def _find_attachment(
        self, *, manuscript_id: str, attachment_id: str
    ) -> dict[str, Any] | None:
        try:
            resp = (
                self.client.table("decision_letters")
                .select("id,status,editor_id,attachment_paths")
                .eq("manuscript_id", manuscript_id)
                .execute()
            )
        except Exception as e:
            if "decision_letters" in str(e).lower() and "does not exist" in str(e).lower():
                raise HTTPException(
                    status_code=500, detail="DB not migrated: decision_letters table missing"
                ) from e
            raise

        rows = getattr(resp, "data", None) or []
        for row in rows:
            for ref in list(row.get("attachment_paths") or []):
                ref_id, path = _decode_attachment_ref(str(ref))
                if ref_id == attachment_id:
                    return {
                        "decision_letter_id": row.get("id"),
                        "status": row.get("status"),
                        "editor_id": row.get("editor_id"),
                        "path": path,
                    }
        return None

    def get_attachment_signed_url_for_editor(
        self,
        *,
        manuscript_id: str,
        attachment_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> str:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        self._ensure_internal_decision_access(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            user_id=user_id,
            roles=roles,
            action="decision:record_first",
        )
        found = self._find_attachment(manuscript_id=manuscript_id, attachment_id=attachment_id)
        if not found:
            raise HTTPException(status_code=404, detail="Attachment not found")
        signed = self._signed_url("decision-attachments", found["path"])
        if not signed:
            raise HTTPException(status_code=500, detail="Failed to sign attachment URL")
        return signed

    def get_attachment_signed_url_for_author(
        self,
        *,
        manuscript_id: str,
        attachment_id: str,
        user_id: str,
        profile_roles: list[str] | None,
    ) -> str:
        manuscript = self._get_manuscript(manuscript_id)
        roles = self._roles(profile_roles)
        is_internal = self._ensure_author_or_internal_access(
            manuscript=manuscript,
            user_id=user_id,
            roles=roles,
        )
        found = self._find_attachment(manuscript_id=manuscript_id, attachment_id=attachment_id)
        if not found:
            raise HTTPException(status_code=404, detail="Attachment not found")
        if not is_internal and str(found.get("status") or "").lower() != "final":
            raise HTTPException(status_code=403, detail="Attachment is not visible before final decision")
        signed = self._signed_url("decision-attachments", found["path"])
        if not signed:
            raise HTTPException(status_code=500, detail="Failed to sign attachment URL")
        return signed
