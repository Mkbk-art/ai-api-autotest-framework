"""Stage 5 normalized Contract model tests."""
from __future__ import annotations

import json

import pytest

from contracts.model import (
    ApiContract,
    ContractError,
    Operation,
    Parameter,
    RequestBody,
    ResponseSpec,
    SchemaField,
)


def test_api_contract_serializes_normalized_operation_tree(tmp_path):
    contract = ApiContract(
        project="example",
        source_kind="static_manifest",
        version="1",
        operations=(
            Operation(
                operation_id="createItem",
                method="post",
                path="/api/items",
                service="catalog",
                visibility="external",
                summary="Create item",
                parameters=(
                    Parameter(name="tenant", location="header", required=True, schema_type="string"),
                ),
                request_body=RequestBody(
                    required=True,
                    content_type="application/json",
                    model="CreateItemRequest",
                    fields=(
                        SchemaField(name="name", schema_type="string", required=True),
                        SchemaField(name="count", schema_type="integer", required=False),
                    ),
                ),
                responses=(
                    ResponseSpec(
                        status_code="200",
                        content_type="application/json",
                        model="CreateItemResponse",
                        fields=(SchemaField(name="id", schema_type="string", required=True),),
                    ),
                ),
                metadata={"source": "fixture"},
            ),
        ),
    )

    assert contract.operation_ids == ("createItem",)
    operation = contract.get_operation("createItem")
    assert operation.method == "POST"
    assert operation.request_body is not None
    assert operation.request_body.fields[0].required is True

    output = tmp_path / "contract.json"
    contract.write_json(output)
    loaded = json.loads(output.read_text(encoding="utf-8"))

    assert loaded["project"] == "example"
    assert loaded["operations"][0]["id"] == "createItem"
    assert loaded["operations"][0]["request_body"]["fields"][0] == {
        "name": "name",
        "type": "string",
        "required": True,
    }


def test_api_contract_rejects_duplicate_operation_ids():
    first = Operation(operation_id="same", method="GET", path="/a")
    second = Operation(operation_id="same", method="POST", path="/b")

    with pytest.raises(ContractError, match="duplicate operation id: same"):
        ApiContract(project="example", source_kind="fixture", version="1", operations=(first, second))


def test_external_operations_exclude_internal_and_page_routes_by_default():
    contract = ApiContract(
        project="example",
        source_kind="fixture",
        version="1",
        operations=(
            Operation(operation_id="publicA", method="GET", path="/a", visibility="external_gateway"),
            Operation(operation_id="publicB", method="GET", path="/b", visibility="external_direct"),
            Operation(operation_id="internal", method="GET", path="/internal", visibility="internal_service"),
            Operation(operation_id="page", method="GET", path="/page", visibility="page_internal"),
        ),
    )

    assert tuple(item.operation_id for item in contract.external_operations()) == ("publicA", "publicB")


def test_get_operation_rejects_unknown_id_with_clear_error():
    contract = ApiContract(
        project="example",
        source_kind="fixture",
        version="1",
        operations=(Operation(operation_id="known", method="GET", path="/known"),),
    )

    with pytest.raises(KeyError, match="unknown operation id: missing"):
        contract.get_operation("missing")
