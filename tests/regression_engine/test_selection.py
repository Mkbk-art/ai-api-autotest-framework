"""Safe, user-controlled regression SelectionPlan tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from contracts.model import ApiContract, Operation, RequestBody, SchemaField
from core.case_registry import CaseRegistry
from core.context_provider import ContextProviderRegistry
from regression_engine.diff import diff_contracts
from regression_engine.selection import SelectionInputError, build_selection_plan


def _contract(*, create_path: str = "/create", include_remove: bool = True, add_refund: bool = False) -> ApiContract:
    operations = [
        Operation(operation_id="login", method="POST", path="/login"),
        Operation(operation_id="create", method="POST", path=create_path),
        Operation(operation_id="query", method="GET", path="/query"),
    ]
    if include_remove:
        operations.append(Operation(operation_id="remove", method="DELETE", path="/remove"))
    if add_refund:
        operations.append(Operation(operation_id="refund", method="POST", path="/refund"))
    return ApiContract(project="example", source_kind="fixture", version="1", operations=tuple(operations))


def _registry(tmp_path: Path) -> CaseRegistry:
    path = tmp_path / "cases.yaml"
    path.write_text(
        """
version: 2
cases:
  - id: auth.login.success
    name: login
    operation_id: login
    level: smoke
    tags: [auth]
    request: {}
    assertions: []

  - id: create.success
    name: create
    operation_id: create
    level: core
    tags: [write]
    request: {}
    assertions: []

  - id: query.after.created
    name: query
    operation_id: query
    level: regression
    tags: [read]
    requires: [created]
    request: {}
    assertions: []

  - id: remove.lifecycle
    name: remove flow
    execution: workflow
    operations: [create, remove]
    level: regression
    tags: [lifecycle]
    request: {}
    assertions: []
    workflow: {handler: demo.remove}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return CaseRegistry.from_paths([path])


def _providers(*, valid: bool = True) -> ContextProviderRegistry:
    providers = ContextProviderRegistry()
    if valid:
        providers.register("auth", lambda executor: None, requires=(), operations=("login",))
        providers.register("created", lambda executor: None, requires=("auth",), operations=("create",))
    else:
        providers.register("created", lambda executor: None)  # incomplete -> AUTO unsafe
    return providers


def _selected(plan):
    return [item.case_id for item in plan.selected_cases]


def test_full_mode_keeps_all_cases_in_requested_level_without_diff_dependency(tmp_path):
    plan = build_selection_plan(
        baseline=None,
        current=_contract(),
        registry=_registry(tmp_path),
        providers=_providers(valid=False),
        level="regression",
        selection="full",
    )

    assert plan.mode == "full"
    assert _selected(plan) == ["query.after.created", "remove.lifecycle"]
    assert all(item.reasons[0].code == "FULL_MODE" for item in plan.selected_cases)


def test_auto_selects_direct_and_context_impacts_only_inside_level(tmp_path):
    baseline = _contract()
    current = _contract(create_path="/v2/create")

    plan = build_selection_plan(
        baseline=baseline,
        current=current,
        registry=_registry(tmp_path),
        providers=_providers(),
        level="regression",
        selection="auto",
    )

    assert plan.mode == "auto"
    assert _selected(plan) == ["query.after.created", "remove.lifecycle"]
    query = next(item for item in plan.selected_cases if item.case_id == "query.after.created")
    assert any(reason.code == "CONTEXT_OPERATION_DEPENDENCY" for reason in query.reasons)
    assert "create.success" not in _selected(plan)  # core is outside the requested level


def test_auto_level_all_adds_smoke_safety_set_but_level_regression_does_not(tmp_path):
    baseline = _contract()
    current = _contract()  # no Contract change
    registry = _registry(tmp_path)

    all_plan = build_selection_plan(
        baseline=baseline,
        current=current,
        registry=registry,
        providers=_providers(),
        level="all",
        selection="auto",
    )
    regression_plan = build_selection_plan(
        baseline=baseline,
        current=current,
        registry=registry,
        providers=_providers(),
        level="regression",
        selection="auto",
    )

    assert _selected(all_plan) == ["auth.login.success"]
    assert all_plan.selected_cases[0].reasons[0].code == "SMOKE_SAFETY_SET"
    assert _selected(regression_plan) == []


def test_user_includes_only_add_within_level_and_support_case_and_tag(tmp_path):
    registry = _registry(tmp_path)
    plan = build_selection_plan(
        baseline=_contract(),
        current=_contract(),
        registry=registry,
        providers=_providers(),
        level="regression",
        selection="auto",
        include_case_ids=("query.after.created",),
        include_tags=("lifecycle",),
    )

    assert _selected(plan) == ["query.after.created", "remove.lifecycle"]
    assert all(any(reason.code == "USER_INCLUDE" for reason in item.reasons) for item in plan.selected_cases)

    with pytest.raises(SelectionInputError, match="outside selected level"):
        build_selection_plan(
            baseline=_contract(),
            current=_contract(),
            registry=registry,
            providers=_providers(),
            level="regression",
            selection="auto",
            include_case_ids=("create.success",),
        )


def test_removed_operation_still_selects_cases_bound_to_old_operation(tmp_path):
    baseline = _contract(include_remove=True)
    current = _contract(include_remove=False)

    plan = build_selection_plan(
        baseline=baseline,
        current=current,
        registry=_registry(tmp_path),
        providers=_providers(),
        level="all",
        selection="auto",
    )

    lifecycle = next(item for item in plan.selected_cases if item.case_id == "remove.lifecycle")
    assert any(
        reason.code == "WORKFLOW_OPERATION_CHANGE" and reason.operation_id == "remove"
        for reason in lifecycle.reasons
    )


def test_added_operation_without_case_is_reported_as_changed_coverage_gap(tmp_path):
    plan = build_selection_plan(
        baseline=_contract(),
        current=_contract(add_refund=True),
        registry=_registry(tmp_path),
        providers=_providers(),
        level="all",
        selection="auto",
    )

    assert plan.uncovered_changed_operation_ids == ("refund",)
    assert "refund" in plan.changed_operation_ids


def test_invalid_dependency_metadata_falls_back_to_full_candidate_scope(tmp_path):
    baseline = _contract()
    current = _contract(create_path="/v2/create")

    plan = build_selection_plan(
        baseline=baseline,
        current=current,
        registry=_registry(tmp_path),
        providers=_providers(valid=False),
        level="regression",
        selection="auto",
    )

    assert plan.mode == "fallback_full"
    assert plan.fallback_reason is not None
    assert _selected(plan) == ["query.after.created", "remove.lifecycle"]
    assert all(item.reasons[0].code == "AUTO_FALLBACK_FULL" for item in plan.selected_cases)
