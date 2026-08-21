"""Controlled Demo proves Stage 6 AUTO can run without any real SUT."""
from __future__ import annotations

from core.config_manager import ConfigManager
from core.project_extensions import load_project_extensions
from regression_engine.analyzer import analyze_selection
from regression_engine.snapshot import load_baseline_path


def test_demo_environment_has_accepted_contract_and_safe_provider_metadata(tmp_path):
    runtime = ConfigManager().load("test")
    assert runtime["contract"]["provider"] == "static_manifest"
    assert load_baseline_path(runtime, project_root=".").is_file()

    providers, _ = load_project_extensions(("demo",))
    providers.validate_dependencies({"demoLogin", "demoPublishInterface", "demoCallInterface"})
    assert providers.get_spec("demo.authenticated").operations == ("demoLogin",)
    assert providers.get_spec("demo.published_interface").requires == ("demo.authenticated",)


def test_demo_unchanged_contract_auto_preview_selects_only_smoke_safety(tmp_path):
    result = analyze_selection(
        "test",
        output_dir=tmp_path / "run",
        level="all",
        selection="auto",
    )

    assert result.plan.mode == "auto"
    assert result.plan.changed_operation_ids == ()
    assert len(result.plan.eligible_case_ids) == 6
    assert result.plan.selected_case_ids == (
        "demo.auth.login.success",
        "demo.auth.login.invalid_password",
    )
    assert all(
        reason.code == "SMOKE_SAFETY_SET"
        for selected in result.plan.selected_cases
        for reason in selected.reasons
    )


def test_demo_changed_contract_selects_changed_operation_plus_smoke_safety(tmp_path):
    import yaml
    from pathlib import Path

    source = Path("testcases/demo/contract/contract.yaml")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    call = next(item for item in data["operations"] if item["id"] == "demoCallInterface")
    response_200 = next(item for item in call["responses"] if item["status"] == "200")
    response_200["fields"] = [
        {"name": "call_status", "type": "string", "required": False}
    ]
    changed = tmp_path / "changed-contract.yaml"
    changed.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    override = tmp_path / "override.yaml"
    override.write_text(
        yaml.safe_dump(
            {
                "contract": {
                    "source": str(changed),
                    "baseline": str(Path("testcases/demo/contract/baseline.json").resolve()),
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = analyze_selection(
        "test",
        env_file=override,
        output_dir=tmp_path / "run",
        level="all",
        selection="auto",
    )

    assert result.plan.changed_operation_ids == ("demoCallInterface",)
    assert set(result.plan.selected_case_ids) == {
        "demo.auth.login.success",
        "demo.auth.login.invalid_password",
        "demo.interface.call.success",
        "demo.interface.call.unauthorized",
    }
    call_cases = [item for item in result.plan.selected_cases if item.case_id.startswith("demo.interface.call")]
    assert all(
        any(reason.code == "DIRECT_OPERATION_CHANGE" for reason in item.reasons)
        for item in call_cases
    )
