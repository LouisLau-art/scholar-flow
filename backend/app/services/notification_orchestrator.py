from __future__ import annotations

from typing import Any

from app.core.email_normalization import normalize_email
from app.services.email_recipient_resolver import EmailRecipientResolver


class NotificationOrchestrator:
    """
    通知编排入口的最小骨架。

    中文注释:
    - 本阶段先把“收件人解析”统一收口；
    - 后续再继续承接渠道策略、发送模式和模板解析。
    """

    def __init__(self, recipient_resolver: EmailRecipientResolver | None = None) -> None:
        self.recipient_resolver = recipient_resolver or EmailRecipientResolver()

    def resolve_author_notification_target(
        self,
        *,
        manuscript: dict[str, Any] | None,
        manuscript_id: str | None = None,
        supabase_client: Any | None = None,
        author_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target = self.recipient_resolver.resolve_author_email_targets(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            supabase_client=supabase_client,
            author_profile=author_profile,
        )
        submission_email = normalize_email((manuscript or {}).get("submission_email"))
        corresponding_authors = target.get("corresponding_authors") or []
        if (
            not submission_email
            or corresponding_authors
            or target.get("source") not in {"author_contact_email", "author_profile_email"}
        ):
            return target

        cc_recipients: list[str] = []
        seen = {submission_email}
        submission_contact_name = ""
        raw_contacts = (manuscript or {}).get("author_contacts")
        if isinstance(raw_contacts, list):
            for item in raw_contacts:
                if not isinstance(item, dict):
                    continue
                email = normalize_email(item.get("email"))
                name = str(item.get("name") or "").strip()
                if email == submission_email and name:
                    submission_contact_name = name
                if email and email not in seen:
                    seen.add(email)
                    cc_recipients.append(email)

        for bucket in (target.get("to_recipients") or [], target.get("cc_recipients") or []):
            for email in bucket:
                normalized_email = normalize_email(email)
                if normalized_email and normalized_email not in seen:
                    seen.add(normalized_email)
                    cc_recipients.append(normalized_email)

        target["recipient_email"] = submission_email
        target["recipient_name"] = submission_contact_name or str(target.get("recipient_name") or "").strip() or "Author"
        target["source"] = "submission_email"
        target["to_recipients"] = [submission_email]
        target["cc_recipients"] = cc_recipients
        return target
