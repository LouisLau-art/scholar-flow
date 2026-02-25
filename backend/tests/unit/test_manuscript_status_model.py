from __future__ import annotations

from app.models.manuscript import ManuscriptStatus


def test_allowed_next_decision_includes_revision_paths() -> None:
    allowed = ManuscriptStatus.allowed_next(ManuscriptStatus.DECISION.value)
    assert ManuscriptStatus.DECISION_DONE.value in allowed
    assert ManuscriptStatus.MAJOR_REVISION.value in allowed
    assert ManuscriptStatus.MINOR_REVISION.value in allowed


def test_allowed_next_decision_done_includes_terminal_and_revision_paths() -> None:
    allowed = ManuscriptStatus.allowed_next(ManuscriptStatus.DECISION_DONE.value)
    assert ManuscriptStatus.APPROVED.value in allowed
    assert ManuscriptStatus.REJECTED.value in allowed
    assert ManuscriptStatus.MAJOR_REVISION.value in allowed
    assert ManuscriptStatus.MINOR_REVISION.value in allowed
