"""Explicit dependency expansion and Case–Contract drift tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from contracts.model import ApiContract, Operation
from core.case_registry import CaseRegistry
from core.context_provider import ContextProviderRegistry
from regression_engine.dependency import DependencyGraphError, analyze_dependencies


def _contract(*operation_ids: str, create_path: str = "/create") -> ApiContract:
    operations = []
    for operation_id in operation_ids:
        path = create_path if operation_id == "create" else f"/{operation_id}"
        method = "POST" if operation_id in {"create", "save", "remove"} else "GET"
        operations.append(Operation(operation_id=operation_id, method=method, path=path))
    return ApiContract(
        project="example",
        source_kind="fixture",
        version="1",
        operations=tuple(operations),
    )


def _registry(tmp_path: Path) -> CaseRegistry:
    path = tmp_path / "cases.yaml"
    path.write_text(
        """
version: 2
cases:
  - id: create.success
    name: create
    operation_id: create
    level: smoke
    request: {}
    assertions: []

  - id: lifecycle
    name: lifecycle
    execution: workflow
    operations: [create, save, remove]
    level: regression
    request: {}
    assertions: []
    workflow: {handler: demo.lifecycle}

  - id: query.after.created
    name: query
    operation_id: query
    level: core
    requires: [visited]
    request: {}
    assertions: []

  - id: second.create.case
    name: second create
    operation_id: create
    level: regression
    request: {}
    assertions: []
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return CaseRegistry.from_paths([path])


def _providers() -> ContextProviderRegistry:
    providers = ContextProviderRegistry()
    providers.register("auth", lambda executor: None, requires=(), operations=("login",))
    providers.register("created", lambda executor: None, requires=("auth",), operations=("create",))
    providers.register("visited", lambda executor: None, requires=("created",), operations=("redirect",))
    return providers


def test_dependency_analysis_maps_direct_and_workflow_operation_changes(tmp_path):
    analysis = analyze_dependencies(
        contract=_contract("login", "create", "save", "remove", "query", "redirect"),
        registry=_registry(tmp_path),
        providers=_providers(),
        changed_operation_ids=("save", "create"),
    )

    lifecycle = [item for item in analysis.impacts if item.case_id == "lifecycle"]
    assert {(item.reason_code, item.operation_id) for item in lifecycle} == {
        ("WORKFLOW_OPERATION_CHANGE", "save"),
        ("WORKFLOW_OPERATION_CHANGE", "create"),
    }
    direct = [item for item in analysis.impacts if item.case_id == "create.success"]
    assert [(item.reason_code, item.operation_id) for item in direct] == [
        ("DIRECT_OPERATION_CHANGE", "create")
    ]


def test_dependency_analysis_expands_transitive_context_provider_path(tmp_path):
    analysis = analyze_dependencies(
        contract=_contract("login", "create", "save", "remove", "query", "redirect"),
        registry=_registry(tmp_path),
        providers=_providers(),
        changed_operation_ids=("login",),
    )

    impact = next(item for item in analysis.impacts if item.case_id == "query.after.created")
    assert impact.reason_code == "CONTEXT_OPERATION_DEPENDENCY"
    assert impact.operation_id == "login"
    assert impact.dependency_path == (
        "case:query.after.created",
        "provider:visited",
        "provider:created",
        "provider:auth",
        "operation:login",
    )


def test_dependency_analysis_keeps_multiple_reasons_for_one_case(tmp_path):
    analysis = analyze_dependencies(
        contract=_contract("login", "create", "save", "remove", "query", "redirect"),
        registry=_registry(tmp_path),
        providers=_providers(),
        changed_operation_ids=("query", "create"),
    )

    impacts = [item for item in analysis.impacts if item.case_id == "query.after.created"]
    assert {(item.reason_code, item.operation_id) for item in impacts} == {
        ("DIRECT_OPERATION_CHANGE", "query"),
        ("CONTEXT_OPERATION_DEPENDENCY", "create"),
    }


def test_dependency_analysis_does_not_invent_drift_for_contract_bound_cases(tmp_path):
    analysis = analyze_dependencies(
        contract=_contract("login", "create", "save", "remove", "query", "redirect"),
        registry=_registry(tmp_path),
        providers=_providers(),
        changed_operation_ids=(),
    )

    assert all(item.reason_code != "CASE_CONTRACT_DRIFT" for item in analysis.impacts)


def test_dependency_analysis_rejects_undeclared_unknown_and_cyclic_metadata(tmp_path):
    contract = _contract("login", "create", "save", "remove", "query", "redirect")
    registry = _registry(tmp_path)

    providers = ContextProviderRegistry()
    providers.register("visited", lambda executor: None)  # legacy metadata is unsafe for AUTO
    with pytest.raises(DependencyGraphError, match="metadata not declared"):
        analyze_dependencies(
            contract=contract,
            registry=registry,
            providers=providers,
            changed_operation_ids=("create",),
        )

    providers = ContextProviderRegistry()
    providers.register("visited", lambda executor: None, requires=("missing",), operations=())
    with pytest.raises(DependencyGraphError, match="unknown context provider dependency"):
        analyze_dependencies(
            contract=contract,
            registry=registry,
            providers=providers,
            changed_operation_ids=("create",),
        )

    providers = ContextProviderRegistry()
    providers.register("visited", lambda executor: None, requires=("created",), operations=())
    providers.register("created", lambda executor: None, requires=("visited",), operations=("create",))
    with pytest.raises(DependencyGraphError, match="cycle"):
        analyze_dependencies(
            contract=contract,
            registry=registry,
            providers=providers,
            changed_operation_ids=("create",),
        )
