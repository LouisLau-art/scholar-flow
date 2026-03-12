from __future__ import annotations

from typing import Any

from app.core.email_normalization import normalize_email


def _titleize_email_local_part(email: str | None) -> str:
    local = str(email or "").split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    return local.title() if local else "Author"


def _normalize_author_contact(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    email = normalize_email(raw.get("email"))
    affiliation = str(raw.get("affiliation") or "").strip()
    city = str(raw.get("city") or "").strip()
    country_or_region = str(raw.get("country_or_region") or "").strip()
    return {
        "name": name,
        "email": email,
        "affiliation": affiliation,
        "city": city,
        "country_or_region": country_or_region,
        "is_corresponding": bool(raw.get("is_corresponding")),
    }


def _append_unique_email(target: list[str], seen: set[str], email: str | None) -> None:
    value = normalize_email(email)
    if not value:
        return
    if value in seen:
        return
    seen.add(value)
    target.append(value)


class EmailRecipientResolver:
    """
    统一解析外发邮件收件人。

    中文注释:
    - 作者类邮件默认主送通讯作者，而不是 submission_email。
    - 其他作者进入 CC；期刊公开编辑部邮箱同时进入 CC 与 Reply-To。
    - submission_email 只作为兜底。
    """

    def resolve_author_email_targets(
        self,
        *,
        manuscript: dict[str, Any] | None,
        manuscript_id: str | None = None,
        supabase_client: Any | None = None,
        author_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        manuscript_data = dict(manuscript or {})
        author_id = str(manuscript_data.get("author_id") or "").strip()

        need_fetch = bool(
            supabase_client
            and manuscript_id
            and (
                not isinstance(manuscript_data.get("author_contacts"), list)
                or not manuscript_data.get("journal_id")
                or not author_id
            )
        )
        if need_fetch:
            try:
                fetched = (
                    supabase_client.table("manuscripts")
                    .select("author_id, submission_email, author_contacts, journal_id")
                    .eq("id", str(manuscript_id))
                    .single()
                    .execute()
                )
                fetched_data = getattr(fetched, "data", None) or {}
                if isinstance(fetched_data, dict):
                    for key in ("author_id", "submission_email", "author_contacts", "journal_id"):
                        if manuscript_data.get(key) in (None, "", []):
                            manuscript_data[key] = fetched_data.get(key)
                    author_id = str(manuscript_data.get("author_id") or "").strip()
            except Exception:
                pass

        contacts: list[dict[str, Any]] = []
        raw_contacts = manuscript_data.get("author_contacts")
        if isinstance(raw_contacts, list):
            for item in raw_contacts:
                normalized = _normalize_author_contact(item)
                if normalized is not None:
                    contacts.append(normalized)

        corresponding_contacts = [
            item for item in contacts if item.get("is_corresponding") and item.get("email")
        ]
        first_contact_with_email = next((item for item in contacts if item.get("email")), None)
        first_contact = contacts[0] if contacts else None

        profile_data = dict(author_profile or {})
        need_profile = bool(
            supabase_client and author_id and (not profile_data or not normalize_email(profile_data.get("email")))
        )
        if need_profile:
            try:
                prof = (
                    supabase_client.table("user_profiles")
                    .select("email, full_name")
                    .eq("id", author_id)
                    .single()
                    .execute()
                )
                pdata = getattr(prof, "data", None) or {}
                if isinstance(pdata, dict):
                    profile_data.update({k: v for k, v in pdata.items() if v not in (None, "")})
            except Exception:
                pass

        journal_public_editorial_email = None
        journal_id = str(manuscript_data.get("journal_id") or "").strip()
        if supabase_client and journal_id:
            try:
                journal = (
                    supabase_client.table("journals")
                    .select("public_editorial_email")
                    .eq("id", journal_id)
                    .single()
                    .execute()
                )
                journal_data = getattr(journal, "data", None) or {}
                if isinstance(journal_data, dict):
                    journal_public_editorial_email = normalize_email(journal_data.get("public_editorial_email"))
            except Exception:
                journal_public_editorial_email = None

        submission_email = normalize_email(manuscript_data.get("submission_email"))
        profile_email = normalize_email(profile_data.get("email"))

        to_recipients: list[str] = []
        cc_recipients: list[str] = []
        seen: set[str] = set()
        source = "none"

        if corresponding_contacts:
            source = "corresponding_author_email"
            for item in corresponding_contacts:
                _append_unique_email(to_recipients, seen, item.get("email"))
        elif first_contact_with_email:
            source = "author_contact_email"
            _append_unique_email(to_recipients, seen, first_contact_with_email.get("email"))
        elif profile_email:
            source = "author_profile_email"
            _append_unique_email(to_recipients, seen, profile_email)
        elif submission_email:
            source = "submission_email"
            _append_unique_email(to_recipients, seen, submission_email)

        if source == "corresponding_author_email":
            for item in contacts:
                if item in corresponding_contacts:
                    continue
                _append_unique_email(cc_recipients, seen, item.get("email"))
        elif source == "author_contact_email":
            for item in contacts:
                if item is first_contact_with_email:
                    continue
                _append_unique_email(cc_recipients, seen, item.get("email"))

        if journal_public_editorial_email:
            _append_unique_email(cc_recipients, seen, journal_public_editorial_email)

        reply_to_recipients: list[str] = []
        reply_seen: set[str] = set()
        if journal_public_editorial_email:
            _append_unique_email(reply_to_recipients, reply_seen, journal_public_editorial_email)

        primary_contact = corresponding_contacts[0] if corresponding_contacts else (first_contact_with_email or first_contact)
        primary_email = to_recipients[0] if to_recipients else None
        recipient_name = (
            str((primary_contact or {}).get("name") or "").strip()
            or str(profile_data.get("full_name") or "").strip()
            or _titleize_email_local_part(primary_email)
        )

        return {
            "recipient_email": primary_email,
            "recipient_name": recipient_name or "Author",
            "corresponding_author": corresponding_contacts[0] if corresponding_contacts else None,
            "corresponding_authors": corresponding_contacts,
            "source": source,
            "author_profile": profile_data or None,
            "to_recipients": to_recipients,
            "cc_recipients": cc_recipients,
            "bcc_recipients": [],
            "reply_to_recipients": reply_to_recipients,
            "journal_public_editorial_email": journal_public_editorial_email,
        }
