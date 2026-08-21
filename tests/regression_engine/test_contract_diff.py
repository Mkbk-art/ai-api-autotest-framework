"""Deterministic normalized Contract Diff tests."""
from __future__ import annotations

from contracts.model import ApiContract, Operation, Parameter, RequestBody, ResponseSpec, SchemaField
from regression_engine.diff import ChangeSeverity, diff_contracts


def _contract(*operations: Operation) -> ApiContract:
    return ApiContract(project="shop", source_kind="fixture", version="1", operations=operations)


def _operation(
    *,
    operation_id: str = "createOrder",
    method: str = "POST",
    path: str = "/orders",
    summary: str | None = None,
    parameters=(),
    request_fields=(),
    response_fields=(),
    statuses=("200",),
) -> Operation:
    return Operation(
        operation_id=operation_id,
        method=method,
        path=path,
        summary=summary,
        parameters=tuple(parameters),
        request_body=RequestBody(
            required=True,
            content_type="application/json",
            fields=tuple(request_fields),
        ),
        responses=tuple(
            ResponseSpec(status_code=status, fields=tuple(response_fields)) for status in statuses
        ),
    )


def _types(diff):
    return [change.change_type for change in diff.changes]


def test_diff_detects_added_and_removed_operations():
    baseline = _contract(
        _operation(operation_id="createOrder"),
        _operation(operation_id="deleteOrder", method="DELETE", path="/orders/{id}"),
    )
    current = _contract(
        _operation(operation_id="createOrder"),
        _operation(operation_id="refundOrder", path="/refunds"),
    )

    diff = diff_contracts(baseline, current)

    assert diff.changed_operation_ids == ("deleteOrder", "refundOrder")
    assert [(item.change_type, item.severity) for item in diff.changes] == [
        ("OPERATION_REMOVED", ChangeSeverity.BREAKING),
        ("OPERATION_ADDED", ChangeSeverity.NON_BREAKING),
    ]


def test_diff_tracks_method_and_path_under_stable_operation_id():
    baseline = _contract(_operation(method="PUT", path="/orders/{id}"))
    current = _contract(_operation(method="PATCH", path="/v2/orders/{id}"))

    diff = diff_contracts(baseline, current)

    assert _types(diff) == ["METHOD_CHANGED", "PATH_CHANGED"]
    assert all(change.severity is ChangeSeverity.BREAKING for change in diff.changes)
    assert diff.changed_operation_ids == ("createOrder",)


def test_diff_compares_parameters_and_request_fields_without_docs_noise():
    baseline = _contract(
        _operation(
            summary="old docs",
            parameters=(Parameter(name="page", location="query", required=False, schema_type="integer"),),
            request_fields=(SchemaField(name="address", schema_type="string", required=False),),
        )
    )
    current = _contract(
        _operation(
            summary="new docs only",
            parameters=(Parameter(name="page", location="query", required=True, schema_type="integer"),),
            request_fields=(
                SchemaField(name="address", schema_type="string", required=True),
                SchemaField(name="coupon", schema_type="string", required=False),
            ),
        )
    )

    diff = diff_contracts(baseline, current)

    assert _types(diff) == [
        "PARAMETER_REQUIRED_CHANGED",
        "REQUEST_FIELD_REQUIRED_CHANGED",
        "REQUEST_FIELD_ADDED",
    ]
    assert [item.severity for item in diff.changes] == [
        ChangeSeverity.BREAKING,
        ChangeSeverity.BREAKING,
        ChangeSeverity.NON_BREAKING,
    ]


def test_diff_detects_removed_request_field_and_type_change():
    baseline = _contract(
        _operation(
            request_fields=(
                SchemaField(name="sku", schema_type="string", required=True),
                SchemaField(name="quantity", schema_type="integer", required=True),
            )
        )
    )
    current = _contract(
        _operation(request_fields=(SchemaField(name="sku", schema_type="integer", required=True),))
    )

    diff = diff_contracts(baseline, current)

    assert _types(diff) == ["REQUEST_FIELD_TYPE_CHANGED", "REQUEST_FIELD_REMOVED"]
    assert all(item.severity is ChangeSeverity.BREAKING for item in diff.changes)


def test_diff_detects_response_status_and_field_changes():
    baseline = _contract(
        _operation(
            statuses=("200", "400"),
            response_fields=(SchemaField(name="token", schema_type="string", required=True),),
        )
    )
    current = _contract(
        _operation(
            statuses=("201", "400"),
            response_fields=(SchemaField(name="accessToken", schema_type="string", required=True),),
        )
    )

    diff = diff_contracts(baseline, current)

    assert _types(diff) == [
        "RESPONSE_STATUS_REMOVED",
        "RESPONSE_STATUS_ADDED",
        "RESPONSE_FIELD_REMOVED",
        "RESPONSE_FIELD_ADDED",
    ]
    assert diff.changes[0].severity is ChangeSeverity.BREAKING
    assert diff.changes[1].severity is ChangeSeverity.NON_BREAKING
    assert diff.changes[2].severity is ChangeSeverity.BREAKING


def test_diff_ignores_summary_description_and_metadata_only_changes():
    baseline = _contract(
        Operation(
            operation_id="queryOrder",
            method="GET",
            path="/orders/{id}",
            summary="old",
            metadata={"source_controller": "Old"},
            parameters=(Parameter(name="id", location="path", required=True, schema_type="string", description="old"),),
            responses=(ResponseSpec(status_code="200", description="old"),),
        )
    )
    current = _contract(
        Operation(
            operation_id="queryOrder",
            method="GET",
            path="/orders/{id}",
            summary="new",
            metadata={"source_controller": "New"},
            parameters=(Parameter(name="id", location="path", required=True, schema_type="string", description="new"),),
            responses=(ResponseSpec(status_code="200", description="new"),),
        )
    )

    diff = diff_contracts(baseline, current)

    assert diff.changes == ()
    assert diff.changed_operation_ids == ()
