"""Stage 6 Pytest collection filter stays generic and case-id based."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import conftest as framework_conftest
from core.case_spec import CaseSpec


def _case(case_id: str, *, execution: str = "declarative") -> CaseSpec:
    return CaseSpec(
        case_id=case_id,
        name=case_id,
        level="regression",
        operation_id="demoOperation",
        execution=execution,
        request={"method": "GET", "path": "/demo"},
        assertions=(),
    )


class _Hook:
    def __init__(self) -> None:
        self.deselected = []

    def pytest_deselected(self, *, items):
        self.deselected.extend(items)


class _Config:
    def __init__(self) -> None:
        self.hook = _Hook()


class _Item:
    def __init__(self, case: CaseSpec | None) -> None:
        if case is not None:
            self.callspec = SimpleNamespace(params={"case": case})


def _write_plan(path: Path, selected: list[str]) -> Path:
    path.write_text(json.dumps({"selected_case_ids": selected}), encoding="utf-8")
    return path


def test_selection_filter_deselects_unselected_declarative_and_workflow_cases(monkeypatch, tmp_path):
    selected = _case("case.selected")
    workflow = _case("case.workflow", execution="workflow")
    rejected = _case("case.rejected")
    items = [_Item(selected), _Item(workflow), _Item(rejected), _Item(None)]
    config = _Config()
    plan = _write_plan(tmp_path / "selection.json", ["case.selected", "case.workflow"])
    monkeypatch.setenv("API_TEST_SELECTION_FILE", str(plan))

    framework_conftest.pytest_collection_modifyitems(config, items)

    assert [item.callspec.params["case"].case_id for item in items[:2]] == [
        "case.selected",
        "case.workflow",
    ]
    assert len(items) == 3  # selected structured cases + unrelated framework item
    assert config.hook.deselected[0].callspec.params["case"].case_id == "case.rejected"


def test_full_collection_without_selection_file_is_unchanged(monkeypatch):
    monkeypatch.delenv("API_TEST_SELECTION_FILE", raising=False)
    items = [_Item(_case("case.a")), _Item(_case("case.b"))]
    config = _Config()

    framework_conftest.pytest_collection_modifyitems(config, items)

    assert len(items) == 2
    assert config.hook.deselected == []


def test_selection_filter_rejects_invalid_or_missing_plan(monkeypatch, tmp_path):
    config = _Config()
    items = [_Item(_case("case.a"))]
    missing = tmp_path / "missing.json"
    monkeypatch.setenv("API_TEST_SELECTION_FILE", str(missing))

    with pytest.raises(pytest.UsageError, match="SelectionPlan"):
        framework_conftest.pytest_collection_modifyitems(config, items)


def test_selection_filter_fails_if_selected_case_was_not_collected(monkeypatch, tmp_path):
    config = _Config()
    items = [_Item(_case("case.a"))]
    plan = _write_plan(tmp_path / "selection.json", ["case.a", "case.missing"])
    monkeypatch.setenv("API_TEST_SELECTION_FILE", str(plan))

    with pytest.raises(pytest.UsageError, match="case.missing"):
        framework_conftest.pytest_collection_modifyitems(config, items)


def test_auto_selected_case_attaches_selection_evidence_to_allure(monkeypatch, tmp_path):
    case = _case("case.a")
    item = _Item(case)
    item.config = _Config()
    plan = {
        "selected_case_ids": ["case.a"],
        "selected_cases": [
            {
                "case_id": "case.a",
                "level": "regression",
                "execution": "declarative",
                "reasons": [
                    {"code": "DIRECT_OPERATION_CHANGE", "operation_id": "demoOperation"}
                ],
            }
        ],
    }
    plan_path = tmp_path / "selection.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.setenv("API_TEST_SELECTION_FILE", str(plan_path))
    attached = {}
    monkeypatch.setattr(
        framework_conftest.allure_compat,
        "attach",
        lambda body, name, attachment_type=None: attached.update(
            body=body, name=name, attachment_type=attachment_type
        ),
    )

    framework_conftest.pytest_runtest_setup(item)

    payload = json.loads(attached["body"])
    assert attached["name"] == "Regression Selection Evidence"
    assert payload["case_id"] == "case.a"
    assert payload["reasons"][0]["code"] == "DIRECT_OPERATION_CHANGE"


def test_full_case_has_no_selection_evidence_attachment(monkeypatch):
    case = _case("case.a")
    item = _Item(case)
    item.config = _Config()
    monkeypatch.delenv("API_TEST_SELECTION_FILE", raising=False)
    monkeypatch.setattr(
        framework_conftest.allure_compat,
        "attach",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("FULL mode must not attach AUTO selection evidence")
        ),
    )

    framework_conftest.pytest_runtest_setup(item)
