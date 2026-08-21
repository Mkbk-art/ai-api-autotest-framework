"""Accepted normalized Contract snapshot lifecycle tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.model import ApiContract, ContractError, Operation, Parameter, RequestBody, ResponseSpec, SchemaField
from regression_engine.snapshot import (
    BaselineSnapshotError,
    ContractSnapshot,
    load_baseline_path,
    load_contract_snapshot,
    write_baseline,
)


def _contract(*, project: str = "example", path: str = "/api/items") -> ApiContract:
    return ApiContract(
        project=project,
        source_kind="fixture",
        version="1",
        operations=(
            Operation(
                operation_id="createItem",
                method="POST",
                path=path,
                parameters=(Parameter(name="traceId", location="header", schema_type="string"),),
                request_body=RequestBody(
                    required=True,
                    content_type="application/json",
                    fields=(SchemaField(name="name", schema_type="string", required=True),),
                ),
                responses=(
                    ResponseSpec(
                        status_code="200",
                        fields=(SchemaField(name="id", schema_type="string", required=True),),
                    ),
                ),
            ),
        ),
    )


def test_api_contract_from_dict_round_trips_normalized_snapshot():
    original = _contract()

    restored = ApiContract.from_dict(original.to_dict())

    assert restored.to_dict() == original.to_dict()


def test_load_baseline_path_prefers_explicit_config_and_resolves_from_project_root(tmp_path):
    runtime = {
        "contract": {
            "provider": "static_manifest",
            "source": "project/contract.yaml",
            "baseline": "accepted/baseline.json",
        }
    }

    assert load_baseline_path(runtime, project_root=tmp_path) == (tmp_path / "accepted/baseline.json").resolve()


def test_load_baseline_path_defaults_next_to_contract_source(tmp_path):
    runtime = {
        "contract": {
            "provider": "static_manifest",
            "source": "project/contract/contract.yaml",
        }
    }

    assert load_baseline_path(runtime, project_root=tmp_path) == (tmp_path / "project/contract/baseline.json").resolve()


def test_baseline_init_refuses_to_overwrite_existing_snapshot(tmp_path):
    path = tmp_path / "baseline.json"
    first = write_baseline(_contract(), path, mode="init")

    with pytest.raises(BaselineSnapshotError, match="already exists"):
        write_baseline(_contract(path="/api/v2/items"), path, mode="init")

    assert load_contract_snapshot(path).contract.to_dict() == first.contract.to_dict()


def test_baseline_accept_explicitly_replaces_snapshot(tmp_path):
    path = tmp_path / "baseline.json"
    write_baseline(_contract(), path, mode="init")

    accepted = write_baseline(_contract(path="/api/v2/items"), path, mode="accept")

    assert accepted.contract.get_operation("createItem").path == "/api/v2/items"
    assert load_contract_snapshot(path).contract.to_dict() == accepted.contract.to_dict()


def test_snapshot_loader_rejects_missing_invalid_and_project_mismatch(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(BaselineSnapshotError, match="not found"):
        load_contract_snapshot(missing)

    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json", encoding="utf-8")
    with pytest.raises(BaselineSnapshotError, match="invalid JSON"):
        load_contract_snapshot(invalid)

    path = tmp_path / "baseline.json"
    write_baseline(_contract(project="service-a"), path, mode="init")
    with pytest.raises(BaselineSnapshotError, match="project mismatch"):
        load_contract_snapshot(path, expected_project="service-b")


def test_snapshot_schema_version_is_validated(tmp_path):
    path = tmp_path / "baseline.json"
    data = ContractSnapshot.create(_contract()).to_dict()
    data["snapshot_schema_version"] = 999
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(BaselineSnapshotError, match="schema version"):
        load_contract_snapshot(path)


def test_baseline_accept_requires_an_existing_accepted_baseline(tmp_path):
    with pytest.raises(BaselineSnapshotError, match="does not exist"):
        write_baseline(_contract(), tmp_path / "baseline.json", mode="accept")


def test_snapshot_strips_runtime_source_path_but_preserves_portable_metadata(tmp_path):
    contract = ApiContract(
        project="portable-service",
        source_kind="static_manifest",
        version="1",
        operations=(Operation(operation_id="ping", method="GET", path="/ping"),),
        metadata={
            "source_path": str((tmp_path / "machine-specific" / "contract.yaml").resolve()),
            "source_note": "reviewed contract",
        },
    )

    snapshot = ContractSnapshot.create(contract)
    data = snapshot.to_dict()

    assert "source_path" not in data["contract"]["metadata"]
    assert data["contract"]["metadata"]["source_note"] == "reviewed contract"
    assert str(tmp_path) not in json.dumps(data, ensure_ascii=False)
