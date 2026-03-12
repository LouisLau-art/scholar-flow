from __future__ import annotations

from app.models.decision import (
    DecisionSubmitRequest,
    get_workflow_decision_bucket,
)


def test_decision_submit_request_accepts_new_academic_recommendation_values() -> None:
    request = DecisionSubmitRequest(
        content="Needs another round of revision before acceptance.",
        decision="accept_after_minor_revision",
        is_final=True,
        decision_stage="final",
        attachment_paths=[],
        last_updated_at=None,
    )

    assert request.decision == "accept_after_minor_revision"


def test_workflow_decision_bucket_maps_new_recommendations_to_legacy_workflow_values() -> None:
    assert get_workflow_decision_bucket("accept") == "accept"
    assert get_workflow_decision_bucket("accept_after_minor_revision") == "minor_revision"
    assert get_workflow_decision_bucket("major_revision") == "major_revision"
    assert get_workflow_decision_bucket("reject_resubmit") == "reject"
    assert get_workflow_decision_bucket("reject_decline") == "reject"
