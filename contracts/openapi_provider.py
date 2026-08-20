"""OpenAPI 3.x provider for the normalized framework contract model.

Only the stable subset required by coverage and future diff logic is normalized.
This module intentionally does not reimplement the complete OpenAPI standard.
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

_HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options", "trace")


def _as_mapping(value: Any, *, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{field_name} must be a mapping")
    return value


def _resolve_local_ref(document: Mapping[str, Any], value: Any) -> tuple[Mapping[str, Any], str | None]:
    """Resolve a local ``#/...`` reference and return the referenced model name."""
    data = _as_mapping(value, field_name="OpenAPI object")
    ref = data.get("$ref")
    if ref is None:
        return data, None
    if not isinstance(ref, str) or not ref.startswith("#/"):
        raise ContractError(f"only local OpenAPI refs are supported in Stage 5: {ref!r}")
    current: Any = document
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        current = _as_mapping(current, field_name=f"OpenAPI ref segment {token!r}").get(token)
        if current is None:
            raise ContractError(f"OpenAPI ref not found: {ref}")
    return _as_mapping(current, field_name=f"OpenAPI ref {ref}"), ref.rsplit("/", 1)[-1]


def _schema_fields(document: Mapping[str, Any], schema_value: Any) -> tuple[SchemaField, ...]:
    schema, _ = _resolve_local_ref(document, schema_value)
    required_raw = schema.get("required", [])
    required = set(required_raw if isinstance(required_raw, list) else [])
    properties = schema.get("properties", {})
    if not isinstance(properties, Mapping):
        return ()

    fields: list[SchemaField] = []
    for name, raw_value in properties.items():
        raw_schema, _ = _resolve_local_ref(document, raw_value)
        child_fields = _schema_fields(document, raw_value) if raw_schema.get("type") == "object" or "properties" in raw_schema else ()
        schema_type = raw_schema.get("type")
        if schema_type == "array":
            items = raw_schema.get("items")
            if isinstance(items, Mapping):
                item_schema, _ = _resolve_local_ref(document, items)
                if item_schema.get("type") == "object" or "properties" in item_schema:
                    child_fields = _schema_fields(document, items)
        fields.append(
            SchemaField(
                name=str(name),
                schema_type=str(schema_type) if schema_type is not None else None,
                required=name in required,
                format=raw_schema.get("format"),
                nullable=raw_schema.get("nullable"),
                description=raw_schema.get("description"),
                fields=child_fields,
            )
        )
    return tuple(fields)


def _content_schema(document: Mapping[str, Any], content_value: Any) -> tuple[str | None, Mapping[str, Any] | None, str | None]:
    if not isinstance(content_value, Mapping) or not content_value:
        return None, None, None
    content_type = "application/json" if "application/json" in content_value else next(iter(content_value))
    media = content_value.get(content_type)
    if not isinstance(media, Mapping):
        return str(content_type), None, None
    schema_value = media.get("schema")
    if not isinstance(schema_value, Mapping):
        return str(content_type), None, None
    schema, model = _resolve_local_ref(document, schema_value)
    return str(content_type), schema, model


def _parameter(document: Mapping[str, Any], raw: Any) -> Parameter:
    data, _ = _resolve_local_ref(document, raw)
    schema = data.get("schema", {})
    if not isinstance(schema, Mapping):
        schema = {}
    location = data.get("in")
    required = bool(data.get("required", False))
    if location == "path":
        required = True
    return Parameter(
        name=data.get("name"),
        location=location,
        required=required,
        schema_type=schema.get("type"),
        format=schema.get("format"),
        description=data.get("description"),
    )


def _request_body(document: Mapping[str, Any], raw: Any) -> RequestBody | None:
    if raw is None:
        return None
    data, _ = _resolve_local_ref(document, raw)
    content_type, schema, model = _content_schema(document, data.get("content"))
    fields = _schema_fields(document, data.get("content", {}).get(content_type, {}).get("schema")) if content_type and schema is not None else ()
    return RequestBody(
        required=bool(data.get("required", False)),
        content_type=content_type,
        model=model,
        fields=fields,
    )


def _responses(document: Mapping[str, Any], raw: Any) -> tuple[ResponseSpec, ...]:
    if not isinstance(raw, Mapping):
        return ()
    result: list[ResponseSpec] = []
    for status, response_value in raw.items():
        data, _ = _resolve_local_ref(document, response_value)
        content_type, schema, model = _content_schema(document, data.get("content"))
        fields: tuple[SchemaField, ...] = ()
        if content_type and schema is not None:
            media = data.get("content", {}).get(content_type, {})
            if isinstance(media, Mapping) and isinstance(media.get("schema"), Mapping):
                fields = _schema_fields(document, media["schema"])
        result.append(
            ResponseSpec(
                status_code=str(status),
                content_type=content_type,
                model=model,
                fields=fields,
                description=data.get("description"),
            )
        )
    return tuple(result)


def _merge_parameters(
    document: Mapping[str, Any],
    path_parameters: Any,
    operation_parameters: Any,
) -> tuple[Parameter, ...]:
    """Merge path-level and operation-level parameters by (name, in)."""
    merged: dict[tuple[str, str], Parameter] = {}
    order: list[tuple[str, str]] = []
    for collection in (path_parameters, operation_parameters):
        if collection is None:
            continue
        if not isinstance(collection, list):
            raise ContractError("OpenAPI parameters must be a list")
        for item in collection:
            parameter = _parameter(document, item)
            key = (parameter.name, parameter.location)
            if key not in merged:
                order.append(key)
            merged[key] = parameter
    return tuple(merged[key] for key in order)


class OpenAPIProvider:
    """Normalize OpenAPI 3.x YAML/JSON documents into ``ApiContract``."""

    def load(self, source: str | Path) -> ApiContract:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Contract file not found: {path}")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError as exc:
            raise ContractError(f"OpenAPI document must be UTF-8: {path}") from exc
        except yaml.YAMLError as exc:
            raise ContractError(f"invalid OpenAPI YAML/JSON: {path}: {exc}") from exc

        document = _as_mapping(raw, field_name="OpenAPI root")
        openapi_version = document.get("openapi")
        if not isinstance(openapi_version, str) or not openapi_version.startswith("3."):
            raise ContractError("OpenAPI 3.x document required")
        info = _as_mapping(document.get("info"), field_name="OpenAPI info")
        title = info.get("title")
        version = info.get("version")
        paths = _as_mapping(document.get("paths"), field_name="OpenAPI paths")

        operations: list[Operation] = []
        for route, path_item_value in paths.items():
            if not isinstance(route, str) or not route.startswith("/"):
                continue
            path_item = _as_mapping(path_item_value, field_name=f"OpenAPI path {route}")
            path_parameters = path_item.get("parameters")
            for method in _HTTP_METHODS:
                operation_value = path_item.get(method)
                if operation_value is None:
                    continue
                data = _as_mapping(operation_value, field_name=f"OpenAPI operation {method.upper()} {route}")
                explicit_id = data.get("operationId")
                if isinstance(explicit_id, str) and explicit_id.strip():
                    operation_id = explicit_id.strip()
                    id_source = "operationId"
                else:
                    operation_id = f"{method}:{route}"
                    id_source = "method_path_fallback"

                metadata = {
                    "id_source": id_source,
                }
                operations.append(
                    Operation(
                        operation_id=operation_id,
                        method=method,
                        path=route,
                        service=data.get("x-service"),
                        visibility=data.get("x-visibility", "external"),
                        summary=data.get("summary"),
                        parameters=_merge_parameters(
                            document,
                            path_parameters,
                            data.get("parameters"),
                        ),
                        request_body=_request_body(document, data.get("requestBody")),
                        responses=_responses(document, data.get("responses")),
                        metadata=metadata,
                    )
                )

        if not operations:
            raise ContractError("OpenAPI document contains no operations")
        return ApiContract(
            project=title,
            source_kind="openapi",
            version=str(version),
            operations=tuple(operations),
            metadata={
                "openapi_version": openapi_version,
                "source_path": str(path.resolve()),
            },
        )
