"""CaseSpec V2 与 CaseRegistry 的框架级行为测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from contracts.model import Operation
from core.case_registry import CaseRegistry
from core.case_spec import CaseSpecError, load_case_specs


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_v2_case_spec_preserves_structured_metadata(tmp_path):
    path = _write(
        tmp_path / "auth.yaml",
        """
version: 2
cases:
  - id: auth.login.success
    name: login success
    operation_id: userLogin
    level: smoke
    tags: [auth, real]
    risks: [authentication]
    requires: [project.static]
    execution: declarative
    request:
      api_name: login
      headers:
        Content-Type: application/json
      json:
        username: demo
    extract:
      token: $.data.token
    assertions:
      - status_code: 200
""",
    )

    cases = load_case_specs(path)

    assert len(cases) == 1
    case = cases[0]
    assert case.case_id == "auth.login.success"
    assert case.operation_id == "userLogin"
    assert case.level == "smoke"
    assert case.tags == ("auth", "real")
    assert case.risks == ("authentication",)
    assert case.requires == ("project.static",)
    assert case.execution == "declarative"
    base_info, test_case = case.to_runner_parts(Operation(operation_id="userLogin", method="POST", path="/api/login"))
    assert base_info == {
        "api_name": "login",
        "url": "/api/login",
        "method": "POST",
        "header": {"Content-Type": "application/json"},
    }
    assert test_case["case_name"] == "login success"
    assert test_case["json"] == {"username": "demo"}
    assert test_case["extract"] == {"token": "$.data.token"}
    assert test_case["validation"] == [{"status_code": 200}]


def test_case_registry_rejects_duplicate_case_ids(tmp_path):
    first = _write(
        tmp_path / "a.yaml",
        """
version: 2
cases:
  - id: duplicate.case
    name: a
    level: smoke
    request: {method: GET, path: /a}
    assertions: [{status_code: 200}]
""",
    )
    second = _write(
        tmp_path / "b.yaml",
        """
version: 2
cases:
  - id: duplicate.case
    name: b
    level: core
    request: {method: GET, path: /b}
    assertions: [{status_code: 200}]
""",
    )

    with pytest.raises(CaseSpecError, match="duplicate case id"):
        CaseRegistry.from_paths([first, second])


def test_case_registry_exposes_only_declarative_cases_for_auto_collection(tmp_path):
    path = _write(
        tmp_path / "cases.yaml",
        """
version: 2
cases:
  - id: simple.case
    name: simple
    level: smoke
    request: {method: GET, path: /simple}
    assertions: [{status_code: 200}]
  - id: lifecycle.case
    name: lifecycle
    level: regression
    execution: workflow
    workflow:
      handler: project.lifecycle
    request: {}
    assertions: [{status_code: 200}]
""",
    )

    registry = CaseRegistry.from_paths([path])

    assert [case.case_id for case in registry.declarative_cases()] == ["simple.case"]
    assert registry.get("lifecycle.case").execution == "workflow"


def test_v2_case_requires_stable_id_name_level_request_and_assertions(tmp_path):
    path = _write(
        tmp_path / "invalid.yaml",
        """
version: 2
cases:
  - id: " "
    name: broken
    level: smoke
    request: {method: GET, path: /broken}
    assertions: []
""",
    )

    with pytest.raises(CaseSpecError, match="id"):
        load_case_specs(path)


def test_v2_case_rejects_control_flow_keys_in_yaml(tmp_path):
    path = _write(
        tmp_path / "invalid-flow.yaml",
        """
version: 2
cases:
  - id: bad.flow
    name: bad flow
    level: core
    request: {method: GET, path: /x}
    assertions: [{status_code: 200}]
    if: something
""",
    )

    with pytest.raises(CaseSpecError, match="control flow"):
        load_case_specs(path)


def test_workflow_can_bind_multiple_operations_as_first_class_metadata(tmp_path):
    path = _write(
        tmp_path / "workflow.yaml",
        """
version: 2
cases:
  - id: resource.lifecycle
    name: lifecycle
    level: regression
    execution: workflow
    operations:
      - createResource
      - recycleResource
      - removeResource
    workflow:
      handler: project.lifecycle
    request: {}
    assertions: []
""",
    )

    registry = CaseRegistry.from_paths([path])
    case = registry.get("resource.lifecycle")

    assert case.operation_id is None
    assert case.operation_ids == ("createResource", "recycleResource", "removeResource")
    assert registry.cases_for_operation("createResource") == (case,)
    assert registry.cases_for_operation("removeResource") == (case,)


def test_operation_ids_merge_primary_and_additional_relations_without_duplicates(tmp_path):
    path = _write(
        tmp_path / "relations.yaml",
        """
version: 2
cases:
  - id: composite.case
    name: composite
    operation_id: primaryOperation
    operations: [primaryOperation, secondaryOperation]
    level: core
    request: {}
    assertions: [{status_code: 200}]
""",
    )

    case = load_case_specs(path)[0]

    assert case.operation_ids == ("primaryOperation", "secondaryOperation")
    _, runner_case = case.to_runner_parts(Operation(operation_id="primaryOperation", method="GET", path="/api/composite"))
    assert runner_case["operations"] == ["primaryOperation", "secondaryOperation"]


def test_operations_relation_must_be_a_list_of_strings(tmp_path):
    path = _write(
        tmp_path / "invalid-operations.yaml",
        """
version: 2
cases:
  - id: bad.operations
    name: bad
    level: core
    operations: createResource
    request: {method: GET, path: /api/resource}
    assertions: [{status_code: 200}]
""",
    )

    with pytest.raises(CaseSpecError, match="operations must be a list of strings"):
        load_case_specs(path)
