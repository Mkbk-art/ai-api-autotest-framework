"""Shortlink real assets prove Stage 6 analysis without contacting the real SUT."""
from __future__ import annotations

from regression_engine.analyzer import analyze_selection


def test_shortlink_accepted_contract_auto_preview_selects_only_six_smoke_safety_cases(tmp_path):
    result = analyze_selection(
        "shortlink-local",
        output_dir=tmp_path / "run",
        level="all",
        selection="auto",
    )

    assert result.plan.project == "shortlink"
    assert result.plan.mode == "auto"
    assert result.plan.fallback_reason is None
    assert result.plan.changed_operation_ids == ()
    assert len(result.plan.eligible_case_ids) == 18
    assert result.plan.selected_case_ids == (
        "shortlink.auth.login.success",
        "shortlink.group.query.success",
        "shortlink.link.create.success",
        "shortlink.link.page.contains_created",
        "shortlink.redirect.success",
        "shortlink.statistics.query.success",
    )
    assert all(
        selected.reasons and all(reason.code == "SMOKE_SAFETY_SET" for reason in selected.reasons)
        for selected in result.plan.selected_cases
    )
