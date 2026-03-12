from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.api.v1.editor_common import resolve_author_notification_target
from app.core.mail import email_service
from app.models.decision import get_workflow_decision_bucket
from app.models.manuscript import ManuscriptStatus, normalize_status


_AUTHOR_DECISION_EMAIL_METADATA: dict[str, dict[str, str]] = {
    "accept": {
        "template_key": "decision_accept",
        "decision_label": "Accept",
        "headline": "We are pleased to inform you that your manuscript has been accepted.",
        "next_step": "Our editorial team will contact you if any production-stage follow-up is needed.",
    },
    "accept_after_minor_revision": {
        "template_key": "decision_accept_after_minor_revision",
        "decision_label": "Accept After Minor Revision",
        "headline": "Your manuscript is conditionally accepted after minor revision.",
        "next_step": "Please submit a polished minor revision so the editorial team can finalize acceptance.",
    },
    "major_revision": {
        "template_key": "decision_major_revision",
        "decision_label": "Major Revision",
        "headline": "Your manuscript requires major revision before it can be reconsidered.",
        "next_step": "Please address the editorial and reviewer comments carefully before resubmission.",
    },
    "minor_revision": {
        "template_key": "decision_minor_revision",
        "decision_label": "Minor Revision",
        "headline": "Your manuscript requires minor revision before it can move forward.",
        "next_step": "Please submit a revised version after addressing the requested changes.",
    },
    "reject": {
        "template_key": "decision_reject",
        "decision_label": "Reject",
        "headline": "After editorial evaluation, your manuscript cannot be accepted in its current form.",
        "next_step": "Thank you for considering this journal for your work.",
    },
    "reject_resubmit": {
        "template_key": "decision_reject_resubmit",
        "decision_label": "Reject and Encourage Resubmitting after Revision",
        "headline": "After editorial evaluation, the current submission will not be accepted in its present form.",
        "next_step": "The topic remains of interest, and you are encouraged to prepare a substantially revised manuscript and resubmit it as a new submission.",
    },
    "reject_decline": {
        "template_key": "decision_reject_decline",
        "decision_label": "Reject and Decline Resubmitting",
        "headline": "After editorial evaluation, your manuscript will not be accepted for publication.",
        "next_step": "Thank you for considering this journal for your work.",
    },
}


def build_author_decision_email_payload(
    *,
    decision: str,
    manuscript_title: str,
    recipient_name: str,
) -> dict[str, Any]:
    normalized = str(decision or "").strip().lower()
    metadata = _AUTHOR_DECISION_EMAIL_METADATA.get(normalized) or _AUTHOR_DECISION_EMAIL_METADATA["reject"]
    context = {
        "recipient_name": str(recipient_name or "Author").strip() or "Author",
        "manuscript_title": str(manuscript_title or "Manuscript").strip() or "Manuscript",
        "decision_label": metadata["decision_label"],
        "decision_headline": metadata["headline"],
        "next_step": metadata["next_step"],
    }
    return {
        "template_key": metadata["template_key"],
        "subject_template": "[{{ manuscript_title }}] {{ decision_label }}",
        "body_html_template": (
            "<p>Dear {{ recipient_name }},</p>"
            f"<p>{metadata['headline']}</p>"
            f"<p>{metadata['next_step']}</p>"
            "<p>Manuscript: <strong>{{ manuscript_title }}</strong></p>"
        ),
        "body_text_template": (
            f"Dear {{{{ recipient_name }}}}, {metadata['headline']} "
            f"{metadata['next_step']} Manuscript: {{{{ manuscript_title }}}}."
        ),
        "context": context,
    }


class DecisionServiceTransitionsMixin:
    def _transition_for_first_decision(
        self,
        *,
        manuscript_id: str,
        current_status: str,
        decision: str,
        changed_by: str,
        transition_payload: dict[str, Any],
    ) -> str:
        norm = normalize_status(current_status) or ManuscriptStatus.PRE_CHECK.value
        if norm != ManuscriptStatus.DECISION.value:
            raise HTTPException(
                status_code=422,
                detail="First decision submission is only allowed in decision stage",
            )

        target_status = (
            ManuscriptStatus.UNDER_REVIEW.value
            if decision == "add_reviewer"
            else ManuscriptStatus.REJECTED.value
            if decision == "reject"
            else ManuscriptStatus.MAJOR_REVISION.value
            if decision == "major_revision"
            else ManuscriptStatus.MINOR_REVISION.value
        )
        audit_payload = dict(transition_payload or {})
        audit_payload.setdefault("source", "decision_workspace")
        audit_payload.setdefault("reason", "editor_submit_first_decision")
        audit_payload["decision_stage"] = "first"
        audit_payload["before"] = {"status": norm}
        audit_payload["after"] = {"status": target_status}

        if decision == "reject":
            self.editorial.update_status(
                manuscript_id=manuscript_id,
                to_status=ManuscriptStatus.DECISION_DONE.value,
                changed_by=changed_by,
                comment="first decision auto step",
                allow_skip=False,
            )

        updated = self.editorial.update_status(
            manuscript_id=manuscript_id,
            to_status=target_status,
            changed_by=changed_by,
            comment=f"first_decision:{decision}",
            allow_skip=False,
            payload=audit_payload,
        )
        return str(updated.get("status") or target_status)

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
            if norm == ManuscriptStatus.DECISION.value:
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
                    detail="Final reject only allowed in decision/decision_done stage",
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
            if norm != ManuscriptStatus.DECISION_DONE.value:
                raise HTTPException(
                    status_code=422,
                    detail="Final accept only allowed in decision_done stage",
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
            ManuscriptStatus.DECISION.value,
            ManuscriptStatus.DECISION_DONE.value,
        }:
            raise HTTPException(
                status_code=422,
                detail="Final revision decision only allowed in decision/decision_done stage",
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

    def _resolve_author_email_decision(self, *, manuscript_id: str, decision: str) -> str:
        normalized = str(decision or "").strip().lower()
        latest_loader = getattr(self, "_get_latest_decision_recommendation", None)
        if not callable(latest_loader):
            return normalized
        try:
            latest = latest_loader(manuscript_id)
        except Exception:
            return normalized
        latest_decision = str((latest or {}).get("decision") or "").strip().lower()
        if not latest_decision:
            return normalized
        try:
            if get_workflow_decision_bucket(latest_decision) == get_workflow_decision_bucket(normalized):
                return latest_decision
        except Exception:
            return normalized
        return normalized

    def _notify_author(self, *, manuscript: dict[str, Any], manuscript_id: str, decision: str) -> None:
        author_id = str(manuscript.get("author_id") or "").strip()
        if not author_id:
            return
        title = str(manuscript.get("title") or "Manuscript")
        effective_decision = self._resolve_author_email_decision(
            manuscript_id=manuscript_id,
            decision=decision,
        )
        decision_payload = build_author_decision_email_payload(
            decision=effective_decision,
            manuscript_title=title,
            recipient_name="Author",
        )
        target = resolve_author_notification_target(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            supabase_client=self.client,
        )
        recipient_email = str(target.get("recipient_email") or "").strip().lower()
        recipient_name = str(target.get("recipient_name") or "Author").strip() or "Author"
        decision_payload["context"]["recipient_name"] = recipient_name
        decision_label = str(decision_payload["context"]["decision_label"] or "Updated")
        if recipient_email:
            email_service.send_inline_email(
                to_email=recipient_email,
                template_key=str(decision_payload["template_key"]),
                subject_template=str(decision_payload["subject_template"]),
                body_html_template=str(decision_payload["body_html_template"]),
                body_text_template=str(decision_payload["body_text_template"]),
                context=dict(decision_payload["context"]),
                idempotency_key=f"author-decision/{manuscript_id}/{effective_decision}/{recipient_email}",
                tags=[
                    {"name": "scene", "value": "decision_workflow"},
                    {"name": "event", "value": "author_decision_notification"},
                    {"name": "manuscript_id", "value": manuscript_id},
                    {"name": "decision", "value": effective_decision or "updated"},
                ],
                headers={
                    "X-SF-Manuscript-ID": manuscript_id,
                    "X-SF-Event-Type": "author_decision_notification",
                },
                audit_context={
                    "manuscript_id": manuscript_id,
                    "author_user_id": author_id,
                    "scene": "decision_workflow",
                    "event_type": "author_decision_notification",
                },
            )
        self.notification.create_notification(
            user_id=author_id,
            manuscript_id=manuscript_id,
            type="decision",
            title="Final Decision Updated",
            content=f"Decision for '{title}': {decision_label}.",
        )
