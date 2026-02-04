from __future__ import annotations

from enum import Enum


class ManuscriptStatus(str, Enum):
    """
    Feature 028：统一稿件生命周期状态枚举。

    中文注释:
    - 这里保留较少的“显性状态”，由后端服务统一校验流转。
    - 数据库存储为字符串/enum 都可；服务层会 normalize 后再写入。
    """

    PRE_CHECK = "pre_check"
    UNDER_REVIEW = "under_review"
    MAJOR_REVISION = "major_revision"
    MINOR_REVISION = "minor_revision"
    RESUBMITTED = "resubmitted"
    DECISION = "decision"
    DECISION_DONE = "decision_done"
    APPROVED = "approved"
    LAYOUT = "layout"
    ENGLISH_EDITING = "english_editing"
    PROOFREADING = "proofreading"
    PUBLISHED = "published"
    REJECTED = "rejected"

    @classmethod
    def allowed_next(cls, current: str) -> set[str]:
        """
        章程要求：状态机规则必须显性可见。

        MVP 规则（editor 视角）：
        - pre_check -> under_review / minor_revision / rejected
        - under_review -> decision / major_revision / minor_revision / rejected
        - major_revision/minor_revision -> resubmitted
        - resubmitted -> under_review / decision / major_revision / minor_revision / rejected
        - decision -> decision_done
        - decision_done -> approved / rejected
        - approved -> layout
        - layout -> english_editing / proofreading
        - english_editing -> proofreading
        - proofreading -> published
        """
        c = (current or "").strip().lower()
        if c == cls.PRE_CHECK.value:
            return {cls.UNDER_REVIEW.value, cls.MINOR_REVISION.value, cls.REJECTED.value}
        if c == cls.UNDER_REVIEW.value:
            return {cls.DECISION.value, cls.MAJOR_REVISION.value, cls.MINOR_REVISION.value, cls.REJECTED.value}
        if c in {cls.MAJOR_REVISION.value, cls.MINOR_REVISION.value}:
            return {cls.RESUBMITTED.value}
        if c == cls.RESUBMITTED.value:
            return {cls.UNDER_REVIEW.value, cls.DECISION.value, cls.MAJOR_REVISION.value, cls.MINOR_REVISION.value, cls.REJECTED.value}
        if c == cls.DECISION.value:
            return {cls.DECISION_DONE.value}
        if c == cls.DECISION_DONE.value:
            return {cls.APPROVED.value, cls.REJECTED.value}
        if c == cls.APPROVED.value:
            return {cls.LAYOUT.value}
        if c == cls.LAYOUT.value:
            return {cls.ENGLISH_EDITING.value, cls.PROOFREADING.value}
        if c == cls.ENGLISH_EDITING.value:
            return {cls.PROOFREADING.value}
        if c == cls.PROOFREADING.value:
            return {cls.PUBLISHED.value}
        return set()


def normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    v = str(value).strip().lower()
    if not v:
        return None
    # 兼容旧状态（迁移未跑/历史数据）
    legacy_map = {
        "submitted": ManuscriptStatus.PRE_CHECK.value,
        "pending_quality": ManuscriptStatus.PRE_CHECK.value,
        "pending_decision": ManuscriptStatus.DECISION.value,
        "revision_requested": ManuscriptStatus.MINOR_REVISION.value,
        "returned_for_revision": ManuscriptStatus.MINOR_REVISION.value,
    }
    v = legacy_map.get(v, v)

    try:
        return ManuscriptStatus(v).value
    except Exception:
        return None

