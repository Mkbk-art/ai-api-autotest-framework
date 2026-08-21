"""Deterministic Contract-to-test Coverage Index tests."""
from __future__ import annotations

import json

from contracts.model import ApiContract, Operation
from core.case_registry import CaseRegistry
from coverage_engine.index import CoverageIndex


def _registry(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text(
        """
version: 2
cases:
  - id: item.create.success
    name: create success
    operation_id: createItem
    level: smoke
    risks: [persistence]
    request: {}
    assertions: [{status_code: 200}]

  - id: item.lifecycle
    name: lifecycle
    level: regression
    execution: workflow
    operations: [createItem, syncItem]
    risks: [state_transition, eventual_consistency]
    workflow: {handler: project.lifecycle}
    request: {}
    assertions: []

  - id: typo.case
    name: typo
    operation_id: missingOperation
    level: core
    request: {}
    assertions: [{status_code: 200}]

  - id: utility.health
    name: health
    level: smoke
    request: {method: GET, path: /health}
    assertions: [{status_code: 200}]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return CaseRegistry.from_paths([path])


def _contract():
    return ApiContract(
        project="example",
        source_kind="fixture",
        version="1",
        operations=(
            Operation(operation_id="createItem", method="POST", path="/api/items", visibility="external_gateway"),
            Operation(operation_id="getItem", method="GET", path="/api/items/{id}", visibility="external_gateway"),
            Operation(operation_id="syncItem", method="POST", path="/internal/items/sync", visibility="internal_service"),
        ),
    )


def test_coverage_index_maps_declarative_and_workflow_cases_to_operations(tmp_path):
    index = CoverageIndex.build(_contract(), _registry(tmp_path))

    create = index.get_operation("createItem")
    assert create.case_ids == ("item.create.success", "item.lifecycle")
    assert create.workflow_case_ids == ("item.lifecycle",)
    assert create.risks == ("persistence", "state_transition", "eventual_consistency")
    assert create.levels == ("smoke", "regression")

    internal = index.get_operation("syncItem")
    assert internal.case_ids == ("item.lifecycle",)
    assert internal.workflow_case_ids == ("item.lifecycle",)


def test_coverage_index_records_unknown_bindings_and_unbound_cases(tmp_path):
    index = CoverageIndex.build(_contract(), _registry(tmp_path))

    assert [(item.case_id, item.operation_id) for item in index.unknown_bindings] == [
        ("typo.case", "missingOperation")
    ]
    assert index.unbound_case_ids == ("utility.health",)


def test_coverage_index_writes_machine_readable_json(tmp_path):
    index = CoverageIndex.build(_contract(), _registry(tmp_path))
    output = tmp_path / "coverage-index.json"

    index.write_json(output)
    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["project"] == "example"
    assert data["operations"][0]["operation_id"] == "createItem"
    assert data["operations"][0]["cases"] == ["item.create.success", "item.lifecycle"]
    assert data["unknown_operation_bindings"] == [
        {
            "case_id": "typo.case",
            "execution": "declarative",
            "operation_id": "missingOperation",
        }
    ]
