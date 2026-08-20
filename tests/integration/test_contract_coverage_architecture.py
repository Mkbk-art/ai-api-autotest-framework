"""Stage 5 architecture guards and real-project offline verification."""
from __future__ import annotations

from contracts.manifest_provider import StaticManifestProvider
from contracts.openapi_provider import OpenAPIProvider
from core.case_registry import CaseRegistry
from core.config_manager import ConfigManager
from coverage_engine.gap import CoverageGap
from coverage_engine.index import CoverageIndex
from utils.project_paths import PROJECT_ROOT


GENERIC_DIRS = (PROJECT_ROOT / "contracts", PROJECT_ROOT / "coverage_engine")
FORBIDDEN_SUT_TOKENS = (
    "shortlink",
    "short-uri",
    "nurl.ink",
    "b100000",
    "t_link",
    "pv/uv/uip",
)


def _shortlink_registry() -> CaseRegistry:
    paths = sorted((PROJECT_ROOT / "testcases" / "shortlink" / "yaml").glob("*.yaml"))
    return CaseRegistry.from_paths(paths)


def test_generic_contract_and_coverage_packages_have_no_current_sut_hardcoding():
    for directory in GENERIC_DIRS:
        for path in directory.glob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for token in FORBIDDEN_SUT_TOKENS:
                assert token not in text, f"{token!r} leaked into generic module {path}"


def test_coverage_engine_package_name_does_not_shadow_third_party_coverage_library():
    # The framework deliberately uses ``coverage_engine`` instead of creating a
    # top-level ``coverage`` package/module.  This structural assertion protects
    # third-party tools such as pytest-cov without requiring that optional
    # development dependency to be installed merely to collect this test file.
    assert (PROJECT_ROOT / "coverage_engine").is_dir()
    assert not (PROJECT_ROOT / "coverage").exists()
    assert not (PROJECT_ROOT / "coverage.py").exists()


def test_shortlink_static_contract_and_current_cases_build_clean_coverage_index():
    contract = StaticManifestProvider().load(
        PROJECT_ROOT / "testcases" / "shortlink" / "contract" / "contract.yaml"
    )
    index = CoverageIndex.build(contract, _shortlink_registry())
    gap = CoverageGap.build(index)

    assert len(contract.operations) == 43
    assert len(contract.external_operations()) == 27
    assert len(_shortlink_registry().all_cases()) == 18
    assert index.unknown_bindings == ()
    assert index.unbound_case_ids == ()
    assert gap.total_operations == 27
    assert gap.covered_operations == 8
    assert gap.coverage_percent == 29.63
    assert len(gap.untested_operation_ids) == 19


def test_shortlink_environment_selects_static_manifest_without_core_changes():
    runtime = ConfigManager(PROJECT_ROOT).load("shortlink-local")

    assert runtime["contract"] == {
        "provider": "static_manifest",
        "source": "testcases/shortlink/contract/contract.yaml",
    }


def test_independent_openapi_fixture_normalizes_without_shortlink_assets():
    contract = OpenAPIProvider().load(PROJECT_ROOT / "tests" / "fixtures" / "contracts" / "sample_openapi.yaml")

    assert contract.project == "inventory-service"
    assert contract.operation_ids == ("getItem", "post:/api/items")
