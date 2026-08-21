"""Stage 6 Runner selection controls without changing existing FULL semantics."""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import run as run_module


def _config(tmp_path: Path) -> dict:
    return {
        "api": {
            "host": "http://127.0.0.1:1",
            "timeout": 1,
            "verify_ssl": False,
            "use_mock": False,
        },
        "report": {"root_dir": str(tmp_path / "runs")},
    }


def test_level_all_is_additive_and_does_not_create_pytest_marker_filter(tmp_path):
    args = run_module.build_pytest_args(
        level="all",
        test_path="testcases",
        results_dir=tmp_path / "allure-results",
        junit_path=tmp_path / "junit.xml",
        allure_enabled=False,
    )

    assert "-m" not in args
    assert run_module._parser().parse_args(["--level", "all"]).level == "all"


def test_parser_exposes_explicit_selection_controls():
    args = run_module._parser().parse_args(
        [
            "--level",
            "all",
            "--selection",
            "auto",
            "--selection-only",
            "--include-case",
            "case.a",
            "--include-case",
            "case.b",
            "--include-tag",
            "security",
        ]
    )

    assert args.selection == "auto"
    assert args.selection_only is True
    assert args.include_case == ["case.a", "case.b"]
    assert args.include_tag == ["security"]


def test_default_full_run_never_invokes_regression_analysis(monkeypatch, tmp_path):
    monkeypatch.setattr(run_module.ConfigManager, "load", lambda *a, **k: _config(tmp_path))
    monkeypatch.setattr(run_module.pytest, "main", lambda args: 0)
    monkeypatch.setattr(run_module, "_allure_plugin_available", lambda: False)
    monkeypatch.setattr(
        run_module,
        "_analyze_regression_selection",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("FULL must not analyze Contract")),
    )

    assert run_module.run_tests(env_name="test", level="smoke", run_id="full-default") == 0


def test_auto_run_builds_selection_before_pytest_and_exposes_only_plan_path(monkeypatch, tmp_path):
    monkeypatch.setattr(run_module.ConfigManager, "load", lambda *a, **k: _config(tmp_path))
    monkeypatch.setattr(run_module, "_allure_plugin_available", lambda: False)
    observed = {}
    selection_json = tmp_path / "selection.json"
    selection_json.write_text('{"selected_case_ids":["case.a"]}\n', encoding="utf-8")

    fake_plan = SimpleNamespace(
        mode="auto",
        selected_cases=(object(),),
        eligible_case_ids=("case.a", "case.b"),
    )
    fake_result = SimpleNamespace(
        plan=fake_plan,
        selection_json=selection_json,
        console_summary=lambda: "selection summary",
    )

    def fake_analysis(**kwargs):
        observed["analysis"] = kwargs
        return fake_result

    def fake_pytest(args):
        observed["selection_file_during_pytest"] = os.environ.get("API_TEST_SELECTION_FILE")
        observed["pytest_args"] = list(args)
        return 0

    monkeypatch.setattr(run_module, "_analyze_regression_selection", fake_analysis)
    monkeypatch.setattr(run_module.pytest, "main", fake_pytest)
    monkeypatch.delenv("API_TEST_SELECTION_FILE", raising=False)

    exit_code = run_module.run_tests(
        env_name="test",
        level="all",
        selection="auto",
        include_case_ids=("case.a",),
        include_tags=("security",),
        run_id="auto-run",
    )

    assert exit_code == 0
    assert observed["analysis"]["level"] == "all"
    assert observed["analysis"]["include_case_ids"] == ("case.a",)
    assert observed["selection_file_during_pytest"] == str(selection_json.resolve())
    assert "API_TEST_SELECTION_FILE" not in os.environ


def test_selection_only_auto_writes_run_metadata_without_executing_pytest(monkeypatch, tmp_path):
    monkeypatch.setattr(run_module.ConfigManager, "load", lambda *a, **k: _config(tmp_path))
    monkeypatch.setattr(run_module, "_allure_plugin_available", lambda: False)
    selection_json = tmp_path / "selection.json"
    selection_json.write_text('{"selected_case_ids":[]}\n', encoding="utf-8")
    fake_plan = SimpleNamespace(mode="auto", selected_cases=(), eligible_case_ids=("case.a",))
    fake_result = SimpleNamespace(
        plan=fake_plan,
        selection_json=selection_json,
        console_summary=lambda: "preview",
    )
    monkeypatch.setattr(run_module, "_analyze_regression_selection", lambda **kwargs: fake_result)
    monkeypatch.setattr(
        run_module.pytest,
        "main",
        lambda args: (_ for _ in ()).throw(AssertionError("selection-only must not execute Pytest")),
    )

    exit_code = run_module.run_tests(
        env_name="test",
        level="all",
        selection="auto",
        selection_only=True,
        run_id="preview-run",
    )

    assert exit_code == 0
    metadata = json.loads(
        (tmp_path / "runs" / "preview-run" / "run.json").read_text(encoding="utf-8")
    )
    assert metadata["selection_only"] is True
    assert metadata["selection_mode"] == "auto"
    assert metadata["pytest_exit_code"] is None
    assert metadata["selected_case_count"] == 0


def test_run_tests_restores_runtime_api_environment(monkeypatch, tmp_path):
    """一次 Runner 调用不得把 API_* 运行态泄漏给同进程的下一次运行。"""
    monkeypatch.setattr(run_module.ConfigManager, "load", lambda *a, **k: _config(tmp_path))
    monkeypatch.setattr(run_module.pytest, "main", lambda args: 0)
    monkeypatch.setattr(run_module, "_allure_plugin_available", lambda: False)
    monkeypatch.setenv("API_HOST", "http://before.example")
    monkeypatch.delenv("API_TIMEOUT", raising=False)

    assert run_module.run_tests(env_name="test", level="smoke", run_id="runtime-env") == 0

    assert os.environ["API_HOST"] == "http://before.example"
    assert "API_TIMEOUT" not in os.environ
