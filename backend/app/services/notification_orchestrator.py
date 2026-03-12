from __future__ import annotations

from typing import Any

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
        return self.recipient_resolver.resolve_author_email_targets(
            manuscript=manuscript,
            manuscript_id=manuscript_id,
            supabase_client=supabase_client,
            author_profile=author_profile,
        )
