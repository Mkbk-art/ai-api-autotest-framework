"""OpenAPI 3 provider normalization tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from contracts.model import ContractError
from contracts.openapi_provider import OpenAPIProvider
from contracts.provider import load_contract_from_config


FIXTURE = Path("tests/fixtures/contracts/sample_openapi.yaml")


def test_openapi_yaml_normalizes_operation_parameters_and_local_schema_refs():
    contract = OpenAPIProvider().load(FIXTURE)

    assert contract.project == "inventory-service"
    assert contract.source_kind == "openapi"
    assert contract.version == "1.2.0"
    assert contract.metadata["openapi_version"] == "3.0.3"

    operation = contract.get_operation("getItem")
    assert operation.method == "GET"
    assert operation.service == "catalog"
    assert operation.visibility == "external_gateway"
    assert [(p.name, p.location) for p in operation.parameters] == [
        ("itemId", "path"),
        ("verbose", "query"),
    ]
    assert operation.responses[0].model == "Item"
    assert [field.name for field in operation.responses[0].fields] == ["id", "name", "tags"]
    assert operation.responses[0].fields[0].required is True


def test_openapi_without_operation_id_gets_deterministic_fallback_id():
    contract = OpenAPIProvider().load(FIXTURE)

    operation = contract.get_operation("post:/api/items")

    assert operation.method == "POST"
    assert operation.metadata["id_source"] == "method_path_fallback"
    assert operation.request_body is not None
    assert operation.request_body.model == "CreateItemRequest"
    assert [(f.name, f.required) for f in operation.request_body.fields] == [
        ("name", True),
        ("count", False),
    ]


def test_openapi_json_and_yaml_normalize_to_same_contract(tmp_path):
    raw = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    json_path = tmp_path / "openapi.json"
    json_path.write_text(json.dumps(raw), encoding="utf-8")

    yaml_contract = OpenAPIProvider().load(FIXTURE)
    json_contract = OpenAPIProvider().load(json_path)

    yaml_dict = yaml_contract.to_dict()
    json_dict = json_contract.to_dict()
    yaml_dict["metadata"].pop("source_path")
    json_dict["metadata"].pop("source_path")
    assert yaml_dict == json_dict


def test_openapi_provider_rejects_non_openapi3_document(tmp_path):
    source = tmp_path / "swagger.yaml"
    source.write_text("swagger: '2.0'\ninfo: {title: old, version: '1'}\npaths: {}\n", encoding="utf-8")

    with pytest.raises(ContractError, match="OpenAPI 3"):
        OpenAPIProvider().load(source)


def test_config_loader_can_select_openapi_provider(tmp_path):
    source = tmp_path / "api.yaml"
    source.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    contract = load_contract_from_config(
        {"contract": {"provider": "openapi", "source": "api.yaml"}},
        project_root=tmp_path,
    )

    assert "getItem" in contract.operation_ids
