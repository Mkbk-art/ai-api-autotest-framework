"""Stage 6 architecture guards keep smart regression generic and optional."""
from __future__ import annotations

import ast
from pathlib import Path

from utils.project_paths import PROJECT_ROOT


REGRESSION_ROOT = PROJECT_ROOT / "regression_engine"
RUNNER_PATH = PROJECT_ROOT / "run.py"
_FORBIDDEN_SUT_TOKENS = (
    "shortlink",
    "nurl.ink",
    "t_link_",
    "short-link:goto",
    "short-link:login",
)


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts))


def test_regression_engine_has_no_current_sut_hardcoding():
    assert REGRESSION_ROOT.is_dir()
    combined = "\n".join(path.read_text(encoding="utf-8") for path in _python_files(REGRESSION_ROOT)).lower()
    for token in _FORBIDDEN_SUT_TOKENS:
        assert token.lower() not in combined, f"Stage 6 hardcodes current SUT token: {token}"


def test_regression_engine_does_not_depend_on_ai_or_git_runtime():
    """V1 is deterministic and Contract-driven; AI/Git integration must remain optional later layers."""
    imported_roots: set[str] = set()
    for path in _python_files(REGRESSION_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
    assert "ai" not in imported_roots
    assert "git" not in imported_roots
    assert "gitpython" not in imported_roots


def test_default_runner_keeps_stage6_import_lazy():
    """Importing run.py must not make legacy FULL runs depend on Stage 6 analysis."""
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"), filename=str(RUNNER_PATH))
    top_level_roots: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level_roots.add(node.module.split(".", 1)[0])
    assert "regression_engine" not in top_level_roots


def test_normal_ci_never_accepts_or_initializes_baseline():
    combined = (
        (PROJECT_ROOT / "Jenkinsfile").read_text(encoding="utf-8")
        + "\n"
        + (PROJECT_ROOT / ".github" / "workflows" / "api-test.yml").read_text(encoding="utf-8")
    ).lower()
    assert "baseline init" not in combined
    assert "baseline accept" not in combined


def _all_project_yaml_cases():
    """Yield every parsed YAML case from every project suite, without hard-coded SUT names."""
    from core.case_spec import load_case_specs

    yaml_files = sorted((PROJECT_ROOT / "testcases").glob("*/yaml/*.yaml"))
    assert yaml_files, "no project YAML cases discovered"
    for yaml_path in yaml_files:
        for case in load_case_specs(yaml_path):
            yield yaml_path, case


def test_contract_bound_project_cases_do_not_duplicate_any_endpoint_identity():
    """Every operation-bound YAML case gets method/path/host identity from Contract + environment."""
    for yaml_path, case in _all_project_yaml_cases():
        if not case.operation_ids:
            continue
        for field in ("method", "path", "url"):
            assert field not in case.request, f"duplicate {field} in {yaml_path}:{case.case_id}"
