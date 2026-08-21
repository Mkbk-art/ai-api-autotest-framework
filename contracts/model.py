"""Provider-neutral normalized API Contract model.

The model intentionally captures only information required by coverage and future
contract-diff logic. It does not mirror the full OpenAPI specification and does
not contain knowledge about any concrete SUT.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping


class ContractError(ValueError):
    """Raised when a contract cannot satisfy the framework's stable model."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractError("optional text value must be non-empty when provided")
    return value.strip()


@dataclass(frozen=True)
class SchemaField:
    """One normalized request/response schema field."""

    name: str
    schema_type: str | None = None
    required: bool = False
    format: str | None = None
    nullable: bool | None = None
    description: str | None = None
    fields: tuple["SchemaField", ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "field.name"))
        object.__setattr__(self, "schema_type", _optional_text(self.schema_type))
        object.__setattr__(self, "format", _optional_text(self.format))
        object.__setattr__(self, "description", _optional_text(self.description))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"name": self.name}
        if self.schema_type is not None:
            data["type"] = self.schema_type
        data["required"] = self.required
        if self.format is not None:
            data["format"] = self.format
        if self.nullable is not None:
            data["nullable"] = self.nullable
        if self.description is not None:
            data["description"] = self.description
        if self.fields:
            data["fields"] = [item.to_dict() for item in self.fields]
        return data


@dataclass(frozen=True)
class Parameter:
    """One path/query/header/cookie parameter."""

    name: str
    location: str
    required: bool = False
    schema_type: str | None = None
    format: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "parameter.name"))
        location = _required_text(self.location, "parameter.location").lower()
        if location not in {"path", "query", "header", "cookie"}:
            raise ContractError(f"unsupported parameter location: {location}")
        object.__setattr__(self, "location", location)
        object.__setattr__(self, "schema_type", _optional_text(self.schema_type))
        object.__setattr__(self, "format", _optional_text(self.format))
        object.__setattr__(self, "description", _optional_text(self.description))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "in": self.location,
            "required": self.required,
        }
        if self.schema_type is not None:
            data["type"] = self.schema_type
        if self.format is not None:
            data["format"] = self.format
        if self.description is not None:
            data["description"] = self.description
        return data


@dataclass(frozen=True)
class RequestBody:
    """Normalized request body metadata."""

    required: bool = False
    content_type: str | None = None
    model: str | None = None
    fields: tuple[SchemaField, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "content_type", _optional_text(self.content_type))
        object.__setattr__(self, "model", _optional_text(self.model))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"required": self.required}
        if self.content_type is not None:
            data["content_type"] = self.content_type
        if self.model is not None:
            data["model"] = self.model
        if self.fields:
            data["fields"] = [item.to_dict() for item in self.fields]
        return data


@dataclass(frozen=True)
class ResponseSpec:
    """Normalized HTTP response metadata."""

    status_code: str
    content_type: str | None = None
    model: str | None = None
    fields: tuple[SchemaField, ...] = ()
    description: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status_code", _required_text(str(self.status_code), "response.status"))
        object.__setattr__(self, "content_type", _optional_text(self.content_type))
        object.__setattr__(self, "model", _optional_text(self.model))
        object.__setattr__(self, "description", _optional_text(self.description))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"status": self.status_code}
        if self.content_type is not None:
            data["content_type"] = self.content_type
        if self.model is not None:
            data["model"] = self.model
        if self.fields:
            data["fields"] = [item.to_dict() for item in self.fields]
        if self.description is not None:
            data["description"] = self.description
        return data


@dataclass(frozen=True)
class Operation:
    """One normalized API operation independent of its source format."""

    operation_id: str
    method: str
    path: str
    service: str | None = None
    visibility: str = "external"
    summary: str | None = None
    parameters: tuple[Parameter, ...] = ()
    request_body: RequestBody | None = None
    responses: tuple[ResponseSpec, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_id", _required_text(self.operation_id, "operation.id"))
        object.__setattr__(self, "method", _required_text(self.method, "operation.method").upper())
        path = _required_text(self.path, "operation.path")
        if not path.startswith("/"):
            raise ContractError(f"operation.path must start with '/': {path}")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "service", _optional_text(self.service))
        object.__setattr__(self, "visibility", _required_text(self.visibility, "operation.visibility"))
        object.__setattr__(self, "summary", _optional_text(self.summary))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.operation_id,
            "method": self.method,
            "path": self.path,
            "visibility": self.visibility,
        }
        if self.service is not None:
            data["service"] = self.service
        if self.summary is not None:
            data["summary"] = self.summary
        if self.parameters:
            data["parameters"] = [item.to_dict() for item in self.parameters]
        if self.request_body is not None:
            data["request_body"] = self.request_body.to_dict()
        if self.responses:
            data["responses"] = [item.to_dict() for item in self.responses]
        if self.metadata:
            data["metadata"] = dict(self.metadata)
        return data



def _field_from_dict(data: Mapping[str, Any]) -> SchemaField:
    if not isinstance(data, Mapping):
        raise ContractError("schema field must be a mapping")
    return SchemaField(
        name=data.get("name"),
        schema_type=data.get("type"),
        required=bool(data.get("required", False)),
        format=data.get("format"),
        nullable=data.get("nullable"),
        description=data.get("description"),
        fields=tuple(_field_from_dict(item) for item in data.get("fields", ()) or ()),
    )


def _parameter_from_dict(data: Mapping[str, Any]) -> Parameter:
    if not isinstance(data, Mapping):
        raise ContractError("parameter must be a mapping")
    return Parameter(
        name=data.get("name"),
        location=data.get("in"),
        required=bool(data.get("required", False)),
        schema_type=data.get("type"),
        format=data.get("format"),
        description=data.get("description"),
    )


def _request_body_from_dict(data: Mapping[str, Any] | None) -> RequestBody | None:
    if data is None:
        return None
    if not isinstance(data, Mapping):
        raise ContractError("request_body must be a mapping")
    return RequestBody(
        required=bool(data.get("required", False)),
        content_type=data.get("content_type"),
        model=data.get("model"),
        fields=tuple(_field_from_dict(item) for item in data.get("fields", ()) or ()),
    )


def _response_from_dict(data: Mapping[str, Any]) -> ResponseSpec:
    if not isinstance(data, Mapping):
        raise ContractError("response must be a mapping")
    return ResponseSpec(
        status_code=str(data.get("status")),
        content_type=data.get("content_type"),
        model=data.get("model"),
        fields=tuple(_field_from_dict(item) for item in data.get("fields", ()) or ()),
        description=data.get("description"),
    )


def _operation_from_dict(data: Mapping[str, Any]) -> Operation:
    if not isinstance(data, Mapping):
        raise ContractError("operation must be a mapping")
    return Operation(
        operation_id=data.get("id"),
        method=data.get("method"),
        path=data.get("path"),
        service=data.get("service"),
        visibility=data.get("visibility", "external"),
        summary=data.get("summary"),
        parameters=tuple(_parameter_from_dict(item) for item in data.get("parameters", ()) or ()),
        request_body=_request_body_from_dict(data.get("request_body")),
        responses=tuple(_response_from_dict(item) for item in data.get("responses", ()) or ()),
        metadata=dict(data.get("metadata", {}) or {}),
    )

_EXTERNAL_VISIBILITIES = frozenset({"external", "external_gateway", "external_direct"})


@dataclass(frozen=True)
class ApiContract:
    """Normalized contract consumed by coverage and future diff logic."""

    project: str
    source_kind: str
    version: str
    operations: tuple[Operation, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "project", _required_text(self.project, "contract.project"))
        object.__setattr__(self, "source_kind", _required_text(self.source_kind, "contract.source_kind"))
        object.__setattr__(self, "version", _required_text(str(self.version), "contract.version"))
        if not self.operations:
            raise ContractError("contract.operations must not be empty")
        seen: set[str] = set()
        for operation in self.operations:
            if operation.operation_id in seen:
                raise ContractError(f"duplicate operation id: {operation.operation_id}")
            seen.add(operation.operation_id)
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def operation_ids(self) -> tuple[str, ...]:
        """Return operation IDs in source order."""
        return tuple(item.operation_id for item in self.operations)

    def get_operation(self, operation_id: str) -> Operation:
        """Return one operation by stable ID or fail explicitly."""
        for operation in self.operations:
            if operation.operation_id == operation_id:
                return operation
        raise KeyError(f"unknown operation id: {operation_id}")

    def external_operations(self) -> tuple[Operation, ...]:
        """Return operations included in the default API coverage denominator."""
        return tuple(item for item in self.operations if item.visibility in _EXTERNAL_VISIBILITIES)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "project": self.project,
            "source_kind": self.source_kind,
            "version": self.version,
            "operations": [item.to_dict() for item in self.operations],
        }
        if self.metadata:
            data["metadata"] = dict(self.metadata)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ApiContract":
        """Restore one normalized contract snapshot produced by :meth:`to_dict`."""
        if not isinstance(data, Mapping):
            raise ContractError("contract snapshot must be a mapping")
        operations = data.get("operations")
        if not isinstance(operations, list):
            raise ContractError("contract.operations must be a list")
        metadata = data.get("metadata", {}) or {}
        if not isinstance(metadata, Mapping):
            raise ContractError("contract.metadata must be a mapping")
        return cls(
            project=data.get("project"),
            source_kind=data.get("source_kind"),
            version=str(data.get("version")),
            operations=tuple(_operation_from_dict(item) for item in operations),
            metadata=dict(metadata),
        )

    def write_json(self, path: str | Path) -> Path:
        """Write a deterministic UTF-8 JSON snapshot and return its path."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target
