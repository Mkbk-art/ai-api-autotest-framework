"""Static Contract Manifest provider tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from contracts.manifest_provider import StaticManifestProvider
from contracts.model import ContractError
from contracts.provider import load_contract_from_config


def _write_manifest(path: Path) -> None:
    path.write_text(
        """
version: 1
project: example
operations:
  - id: getItem
    service: catalog
    visibility: external_gateway
    method: GET
    path: /api/items/{itemId}
    summary: Query one item
    parameters:
      - name: itemId
        in: path
        required: true
        type: string
    responses:
      - status: 200
        content_type: application/json
        model: ItemResponse
        fields:
          - name: id
            type: string
            required: true

  - id: createItem
    service: catalog
    visibility: external_gateway
    method: POST
    path: /api/items
    request_body:
      required: true
      content_type: application/json
      model: CreateItemRequest
      fields:
        - name: name
          type: string
          required: true
        - name: count
          type: integer
          required: false
    responses:
      - status: 200
        model: ItemResponse
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_static_manifest_provider_normalizes_manifest(tmp_path):
    source = tmp_path / "contract.yaml"
    _write_manifest(source)

    contract = StaticManifestProvider().load(source)

    assert contract.project == "example"
    assert contract.source_kind == "static_manifest"
    assert contract.operation_ids == ("getItem", "createItem")
    assert contract.metadata["source_path"] == str(source.resolve())

    get_item = contract.get_operation("getItem")
    assert get_item.parameters[0].name == "itemId"
    assert get_item.parameters[0].location == "path"
    assert get_item.responses[0].fields[0].name == "id"

    create_item = contract.get_operation("createItem")
    assert create_item.request_body is not None
    assert create_item.request_body.model == "CreateItemRequest"
    assert [field.name for field in create_item.request_body.fields] == ["name", "count"]


def test_static_manifest_provider_rejects_invalid_operation_shape(tmp_path):
    source = tmp_path / "broken.yaml"
    source.write_text(
        "version: 1\nproject: example\noperations:\n  - id: missingPath\n    method: GET\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="operation.path"):
        StaticManifestProvider().load(source)


def test_load_contract_from_config_resolves_source_relative_to_project_root(tmp_path):
    contract_dir = tmp_path / "contracts-data"
    contract_dir.mkdir()
    source = contract_dir / "manifest.yaml"
    _write_manifest(source)

    runtime_config = {
        "contract": {
            "provider": "static_manifest",
            "source": "contracts-data/manifest.yaml",
        }
    }

    contract = load_contract_from_config(runtime_config, project_root=tmp_path)

    assert contract.get_operation("createItem").method == "POST"


def test_load_contract_from_config_rejects_unknown_provider(tmp_path):
    runtime_config = {"contract": {"provider": "spring_magic", "source": "contract.yaml"}}

    with pytest.raises(ContractError, match="unsupported contract provider"):
        load_contract_from_config(runtime_config, project_root=tmp_path)
