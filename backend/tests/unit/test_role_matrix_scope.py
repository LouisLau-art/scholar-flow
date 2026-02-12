from app.core.role_matrix import can_perform_action, list_allowed_actions, normalize_roles


def test_normalize_roles_keeps_current_roles_only() -> None:
    roles = normalize_roles(["managing_editor", " Admin ", "", None])
    assert "managing_editor" in roles
    assert "admin" in roles


def test_admin_has_global_action_access() -> None:
    assert can_perform_action(action="decision:submit_final", roles=["admin"]) is True
    assert can_perform_action(action="unknown:anything", roles=["admin"]) is True


def test_managing_editor_can_record_first_but_not_submit_final() -> None:
    assert can_perform_action(action="decision:record_first", roles=["managing_editor"]) is True
    assert can_perform_action(action="decision:submit_final", roles=["managing_editor"]) is False


def test_eic_can_submit_final_decision() -> None:
    assert can_perform_action(action="decision:submit_final", roles=["editor_in_chief"]) is True


def test_list_allowed_actions_unions_roles() -> None:
    actions = list_allowed_actions(["assistant_editor", "managing_editor"])
    assert "precheck:technical_check" in actions
    assert "manuscript:bind_owner" in actions


def test_assistant_editor_can_record_first_but_not_submit_final() -> None:
    assert can_perform_action(action="decision:record_first", roles=["assistant_editor"]) is True
    assert can_perform_action(action="decision:submit_final", roles=["assistant_editor"]) is False
