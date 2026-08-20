"""Coverage Gap tests: only deterministic gaps are reported in Stage 5."""
from __future__ import annotations

import json

from contracts.model import ApiContract, Operation
from core.case_registry import CaseRegistry
from coverage_engine.gap import CoverageGap
from coverage_engine.index import CoverageIndex


def _build(tmp_path):
    source = tmp_path / "cases.yaml"
    source.write_text(
        """
version: 2
cases:
  - id: public.covered
    name: covered
    operation_id: publicCovered
    level: smoke
    risks: [authentication]
    request: {method: GET, path: /covered}
    assertions: [{status_code: 200}]
  - id: unknown.binding
    name: unknown
    operation_id: doesNotExist
    level: core
    request: {method: GET, path: /unknown}
    assertions: [{status_code: 200}]
  - id: no.binding
    name: helper
    level: regression
    request: {method: GET, path: /helper}
    assertions: [{status_code: 200}]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    registry = CaseRegistry.from_paths([source])
    contract = ApiContract(
        project="example",
        source_kind="fixture",
        version="1",
        operations=(
            Operation(operation_id="publicCovered", method="GET", path="/covered", visibility="external_gateway"),
            Operation(operation_id="publicMissing", method="POST", path="/missing", visibility="external_direct"),
            Operation(operation_id="internalMissing", method="POST", path="/internal", visibility="internal_service"),
        ),
    )
    return CoverageIndex.build(contract, registry)


def test_default_gap_uses_external_api_scope_and_reports_deterministic_gaps(tmp_path):
    gap = CoverageGap.build(_build(tmp_path))

    assert gap.scope_visibilities == ("external", "external_gateway", "external_direct")
    assert gap.total_operations == 2
    assert gap.covered_operations == 1
    assert gap.coverage_percent == 50.0
    assert gap.untested_operation_ids == ("publicMissing",)
    assert [(item.case_id, item.operation_id) for item in gap.unknown_bindings] == [
        ("unknown.binding", "doesNotExist")
    ]
    assert gap.unbound_case_ids == ("no.binding",)


def test_gap_can_include_internal_service_scope_explicitly(tmp_path):
    gap = CoverageGap.build(
        _build(tmp_path),
        visibilities=("external_gateway", "external_direct", "internal_service"),
    )

    assert gap.total_operations == 3
    assert gap.untested_operation_ids == ("publicMissing", "internalMissing")


def test_gap_writes_json_without_inventing_missing_risks(tmp_path):
    gap = CoverageGap.build(_build(tmp_path))
    output = tmp_path / "coverage-gap.json"

    gap.write_json(output)
    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["untested_operations"] == ["publicMissing"]
    assert "missing_risks" not in data
    assert data["summary"] == {
        "coverage_percent": 50.0,
        "covered_operations": 1,
        "total_operations": 2,
    }
