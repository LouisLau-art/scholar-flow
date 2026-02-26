from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.models.manuscript import ManuscriptStatus, normalize_status


class DecisionServiceTransitionsMixin:
    def _transition_for_final_decision(
        self,
        *,
        manuscript_id: str,
        current_status: str,
        decision: str,
        changed_by: str,
        transition_payload: dict[str, Any],
    ) -> str:
        norm = normalize_status(current_status) or ManuscriptStatus.PRE_CHECK.value
        comment = f"final_decision:{decision}"
        target_status = (
            ManuscriptStatus.REJECTED.value
            if decision == "reject"
            else ManuscriptStatus.APPROVED.value
            if decision == "accept"
            else ManuscriptStatus.MAJOR_REVISION.value
            if decision == "major_revision"
            else ManuscriptStatus.MINOR_REVISION.value
        )
        audit_payload = dict(transition_payload or {})
        audit_payload.setdefault("source", "decision_workspace")
        audit_payload.setdefault("reason", "editor_submit_final_decision")
        audit_payload["decision_stage"] = "final"
        audit_payload["before"] = {"status": norm}
        audit_payload["after"] = {"status": target_status}

        if decision == "reject":
            if norm == ManuscriptStatus.RESUBMITTED.value:
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION_DONE.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
            elif norm == ManuscriptStatus.DECISION.value:
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION_DONE.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
            elif norm != ManuscriptStatus.DECISION_DONE.value:
                raise HTTPException(
                    status_code=422,
                    detail="Final reject only allowed in resubmitted/decision/decision_done stage",
                )
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status=ManuscriptStatus.REJECTED.value,
                changed_by=changed_by,
                comment=comment,
                allow_skip=False,
                payload=audit_payload,
            )
            return str(updated.get("status") or ManuscriptStatus.REJECTED.value)

        if decision == "accept":
            if norm == ManuscriptStatus.RESUBMITTED.value:
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION_DONE.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
            elif norm == ManuscriptStatus.DECISION.value:
                self.editorial.update_status(
                    manuscript_id=manuscript_id,
                    to_status=ManuscriptStatus.DECISION_DONE.value,
                    changed_by=changed_by,
                    comment="decision workspace auto step",
                    allow_skip=False,
                )
            elif norm != ManuscriptStatus.DECISION_DONE.value:
                raise HTTPException(
                    status_code=422,
                    detail="Final accept only allowed in resubmitted/decision/decision_done stage",
                )
            updated = self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status=ManuscriptStatus.APPROVED.value,
                changed_by=changed_by,
                comment=comment,
                allow_skip=False,
                payload=audit_payload,
            )
            return str(updated.get("status") or ManuscriptStatus.APPROVED.value)

        to_status = (
            ManuscriptStatus.MAJOR_REVISION.value
            if decision == "major_revision"
            else ManuscriptStatus.MINOR_REVISION.value
        )
        if norm not in {
            ManuscriptStatus.UNDER_REVIEW.value,
            ManuscriptStatus.RESUBMITTED.value,
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
        }:
            raise HTTPException(
                status_code=422,
                detail="Final revision decision only allowed in under_review/resubmitted/decision/decision_done stage",
            )
        updated = self.editorial.update_status(
            manuscript_id=manuscript_id,
            to_status=to_status,
            changed_by=changed_by,
            comment=comment,
            allow_skip=False,
            payload=audit_payload,
        )
        return str(updated.get("status") or to_status)

    def _notify_author(self, *, manuscript: dict[str, Any], manuscript_id: str, decision: str) -> None:
        author_id = str(manuscript.get("author_id") or "").strip()
        if not author_id:
            return
        title = str(manuscript.get("title") or "Manuscript")
        decision_label = {
            "accept": "Accepted",
            "reject": "Rejected",
            "major_revision": "Major Revision Requested",
            "minor_revision": "Minor Revision Requested",
        }.get(decision, "Updated")
        self.notification.create_notification(
            user_id=author_id,
            manuscript_id=manuscript_id,
            type="decision",
            title="Final Decision Updated",
            content=f"Decision for '{title}': {decision_label}.",
        )
