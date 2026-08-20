"""Static Contract Manifest provider.

Static manifests are the reviewed contract source for projects that do not expose
OpenAPI. How the manifest was acquired (source review, API documentation, Postman,
etc.) is deliberately outside Framework Core.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from contracts.model import (
    ApiContract,
    ContractError,
    Operation,
    Parameter,
    RequestBody,
    ResponseSpec,
    SchemaField,
)


def _mapping(value: Any, *, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{field_name} must be a mapping")
    return value


def _list(value: Any, *, field_name: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ContractError(f"{field_name} must be a list")
    return value


def _field(raw: Any) -> SchemaField:
    data = _mapping(raw, field_name="schema field")
    children = tuple(_field(item) for item in _list(data.get("fields"), field_name="schema field.fields"))
    return SchemaField(
        name=data.get("name"),
        schema_type=data.get("type"),
        required=bool(data.get("required", False)),
        format=data.get("format"),
        nullable=data.get("nullable"),
        description=data.get("description"),
        fields=children,
    )


def _parameter(raw: Any) -> Parameter:
    data = _mapping(raw, field_name="parameter")
    return Parameter(
        name=data.get("name"),
        location=data.get("in"),
        required=bool(data.get("required", False)),
        schema_type=data.get("type"),
        format=data.get("format"),
        description=data.get("description"),
    )


def _request_body(raw: Any) -> RequestBody | None:
    if raw is None:
        return None
    data = _mapping(raw, field_name="request_body")
    return RequestBody(
        required=bool(data.get("required", False)),
        content_type=data.get("content_type"),
        model=data.get("model"),
        fields=tuple(_field(item) for item in _list(data.get("fields"), field_name="request_body.fields")),
    )


def _response(raw: Any) -> ResponseSpec:
    data = _mapping(raw, field_name="response")
    status = data.get("status")
    if status is None:
        raise ContractError("response.status must be provided")
    return ResponseSpec(
        status_code=str(status),
        content_type=data.get("content_type"),
        model=data.get("model"),
        description=data.get("description"),
        fields=tuple(_field(item) for item in _list(data.get("fields"), field_name="response.fields")),
    )


def _operation(raw: Any) -> Operation:
    data = _mapping(raw, field_name="operation")
    path = data.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ContractError("operation.path must be non-empty text")
    metadata = data.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, Mapping):
        raise ContractError("operation.metadata must be a mapping")
    return Operation(
        operation_id=data.get("id"),
        method=data.get("method"),
        path=path,
        service=data.get("service"),
        visibility=data.get("visibility", "external"),
        summary=data.get("summary"),
        parameters=tuple(_parameter(item) for item in _list(data.get("parameters"), field_name="operation.parameters")),
        request_body=_request_body(data.get("request_body")),
        responses=tuple(_response(item) for item in _list(data.get("responses"), field_name="operation.responses")),
        metadata=dict(metadata),
    )


class StaticManifestProvider:
    """Load the framework-defined, language-neutral static contract manifest."""

    def load(self, source: str | Path) -> ApiContract:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Contract file not found: {path}")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError as exc:
            raise ContractError(f"contract manifest must be UTF-8: {path}") from exc
        except yaml.YAMLError as exc:
            raise ContractError(f"invalid contract manifest YAML: {path}: {exc}") from exc

        data = _mapping(raw, field_name="contract manifest root")
        if data.get("version") != 1:
            raise ContractError(f"static contract manifest version must be 1: {path}")
        operations = tuple(
            _operation(item)
            for item in _list(data.get("operations"), field_name="contract.operations")
        )
        metadata = data.get("metadata", {}) or {}
        if not isinstance(metadata, Mapping):
            raise ContractError("contract.metadata must be a mapping")
        normalized_metadata = dict(metadata)
        normalized_metadata["source_path"] = str(path.resolve())
        return ApiContract(
            project=data.get("project"),
            source_kind="static_manifest",
            version=str(data.get("version")),
            operations=operations,
            metadata=normalized_metadata,
        )
