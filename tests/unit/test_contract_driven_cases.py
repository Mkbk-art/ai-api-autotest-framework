"""Stage 6.5 contract-driven Case execution behavior."""
from __future__ import annotations

from pathlib import Path

import pytest

from contracts.model import ApiContract, Operation
from core.case_executor import CaseExecutor
from core.case_registry import CaseRegistry
from core.case_spec import CaseSpecError, load_case_specs


class _Response:
    status_code = 200


class _Runner:
    def __init__(self):
        from core.variable_context import VariableContext

        self.context = VariableContext()
        self.calls: list[tuple[dict, dict]] = []

    def run(self, base_info, test_case):
        self.calls.append((base_info, test_case))
        return _Response()

    def run_polling(self, base_info, test_case):
        self.calls.append((base_info, {**test_case, "_polling": True}))
        return _Response()


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "cases.yaml"
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def _contract(*operations: Operation) -> ApiContract:
    return ApiContract(
        project="example",
        source_kind="fixture",
        version="1",
        operations=tuple(operations),
    )


def test_contract_bound_case_can_omit_method_and_path(tmp_path):
    path = _write(
        tmp_path,
        """
version: 2
cases:
  - id: user.query.success
    name: query user
    operation_id: userQuery
    level: smoke
    request:
      headers:
        Authorization: Bearer ${token}
      params:
        verbose: true
    assertions:
      - status_code: 200
""",
    )

    case = load_case_specs(path)[0]

    assert case.operation_id == "userQuery"
    assert "method" not in case.request
    assert "path" not in case.request


def test_contract_bound_case_rejects_duplicate_relative_endpoint(tmp_path):
    path = _write(
        tmp_path,
        """
version: 2
cases:
  - id: user.query.duplicated
    name: duplicated endpoint
    operation_id: userQuery
    level: smoke
    request:
      method: GET
      path: /api/users
    assertions:
      - status_code: 200
""",
    )

    with pytest.raises(CaseSpecError, match="Contract-bound case must not declare request.method/path"):
        load_case_specs(path)


def test_contract_bound_case_rejects_duplicate_absolute_url_endpoint(tmp_path):
    path = _write(
        tmp_path,
        """
version: 2
cases:
  - id: redirect.success
    name: redirect
    operation_id: redirect
    level: smoke
    request:
      url: http://service.test/${resource_id}
    assertions:
      - status_code: 302
""",
    )

    with pytest.raises(CaseSpecError, match="must not declare request.method/path/url"):
        load_case_specs(path)


def test_standalone_case_still_requires_explicit_method_and_endpoint(tmp_path):
    path = _write(
        tmp_path,
        """
version: 2
cases:
  - id: adhoc.health
    name: adhoc health
    level: core
    request:
      method: GET
      path: /health
    assertions:
      - status_code: 200
""",
    )

    case = load_case_specs(path)[0]
    base_info, _ = case.to_runner_parts()

    assert base_info["method"] == "GET"
    assert base_info["url"] == "/health"


def test_workflow_case_can_omit_dummy_request_endpoint(tmp_path):
    path = _write(
        tmp_path,
        """
version: 2
cases:
  - id: resource.lifecycle
    name: lifecycle
    level: regression
    execution: workflow
    operations: [createResource, removeResource]
    workflow:
      handler: resource.lifecycle
    assertions: []
""",
    )

    case = load_case_specs(path)[0]

    assert case.execution == "workflow"
    assert case.request == {}


def test_case_executor_resolves_contract_method_and_path(tmp_path):
    path = _write(
        tmp_path,
        """
version: 2
cases:
  - id: user.query.success
    name: query user
    operation_id: userQuery
    level: smoke
    request:
      headers:
        X-Test: "yes"
      params:
        verbose: true
    assertions:
      - status_code: 200
""",
    )
    registry = CaseRegistry.from_paths([path])
    runner = _Runner()
    contract = _contract(Operation(operation_id="userQuery", method="GET", path="/api/users"))

    with CaseExecutor(runner=runner, registry=registry, contract=contract) as executor:
        executor.execute("user.query.success")

    base_info, test_case = runner.calls[0]
    assert base_info == {
        "api_name": "query user",
        "url": "/api/users",
        "method": "GET",
        "header": {"X-Test": "yes"},
    }
    assert test_case["params"] == {"verbose": True}


def test_case_executor_passes_contract_service_and_resolved_path(tmp_path):
    path = _write(
        tmp_path,
        """
version: 2
cases:
  - id: redirect.success
    name: redirect
    operation_id: redirect
    level: smoke
    request:
      path_params:
        resource_id: ${resource_id}
      request_options:
        allow_redirects: false
    assertions:
      - status_code: 302
""",
    )
    registry = CaseRegistry.from_paths([path])
    runner = _Runner()
    contract = _contract(
        Operation(operation_id="redirect", service="project", method="GET", path="/{resource_id}")
    )

    with CaseExecutor(runner=runner, registry=registry, contract=contract) as executor:
        executor.execute("redirect.success")

    base_info, _ = runner.calls[0]
    assert base_info["method"] == "GET"
    assert base_info["url"] == "/${resource_id}"
    assert base_info["service"] == "project"


def test_contract_path_params_are_substituted_before_api_runner_dynamic_resolution(tmp_path):
    path = _write(
        tmp_path,
        """
version: 2
cases:
  - id: user.detail
    name: detail
    operation_id: userDetail
    level: core
    request:
      path_params:
        user_id: ${user_id}
    assertions:
      - status_code: 200
""",
    )
    registry = CaseRegistry.from_paths([path])
    runner = _Runner()
    contract = _contract(Operation(operation_id="userDetail", method="GET", path="/api/users/{user_id}"))

    with CaseExecutor(runner=runner, registry=registry, contract=contract) as executor:
        executor.execute("user.detail")

    base_info, test_case = runner.calls[0]
    assert base_info["url"] == "/api/users/${user_id}"
    assert "path_params" not in test_case


def test_contract_bound_case_fails_before_http_when_contract_missing(tmp_path):
    path = _write(
        tmp_path,
        """
version: 2
cases:
  - id: user.query.success
    name: query user
    operation_id: userQuery
    level: smoke
    request: {}
    assertions:
      - status_code: 200
""",
    )
    registry = CaseRegistry.from_paths([path])
    runner = _Runner()

    with CaseExecutor(runner=runner, registry=registry) as executor:
        with pytest.raises(RuntimeError, match="requires an ApiContract"):
            executor.execute("user.query.success")

    assert runner.calls == []
