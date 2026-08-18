# External Environment Override Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a framework-generic external environment YAML override that lets Jenkins run real SUTs without storing private credentials in the public repository.

**Architecture:** Keep public named environment YAML as the reusable project definition, then merge an optional external YAML override above it. `run.py` and `ConfigManager` own the capability; Jenkins only supplies a generic file path and never copies or archives private YAML.

**Tech Stack:** Python 3.11+, Pytest, PyYAML, Jenkins Declarative Pipeline, GitHub Actions contract tests.

**Spec:** `docs/superpowers/specs/2026-08-18-external-env-override-design.md`

## Global Constraints

- Framework core and CI must not hard-code the current short-link SUT.
- Existing `ENV_NAME=test, LEVEL=smoke` Jenkins flow must stay backward compatible.
- Public `config/env.<project>.yaml` remains uploadable as an example with placeholder secrets.
- External YAML is optional and may contain only private override fields.
- External file contents must not be copied into Jenkins Workspace or archived.
- Modified Python files require dense Chinese comments/docstrings.

---

### Task 1: ConfigManager external override layer

**Files:**
- Modify: `tests/unit/test_config_and_runner.py`
- Modify: `core/config_manager.py`

**Interfaces:**
- Consumes: existing `ConfigManager.load(env_name, cli_overrides=...)`
- Produces: `ConfigManager.load(env_name, env_file=None, cli_overrides=...)`

- [ ] Add failing tests proving external YAML overrides the named file but is still overridden by env vars and CLI.
- [ ] Add a failing test proving an explicitly configured missing external file raises `FileNotFoundError`.
- [ ] Run the focused tests and confirm RED for the missing feature.
- [ ] Implement the external merge layer and `API_TEST_ENV_FILE` fallback.
- [ ] Re-run the focused tests and confirm GREEN.

### Task 2: Unified runner CLI support

**Files:**
- Modify: `tests/unit/test_config_and_runner.py`
- Modify: `run.py`

**Interfaces:**
- Consumes: `ConfigManager.load(..., env_file=...)`
- Produces: optional `--env-file` CLI argument and `run_tests(..., env_file=...)`

- [ ] Add failing tests for parser support and propagation into ConfigManager/Pytest runtime.
- [ ] Run focused tests and confirm RED.
- [ ] Implement `--env-file`, temporary `API_TEST_ENV_FILE` propagation during Pytest, and restoration after the run.
- [ ] Re-run focused tests and confirm GREEN.

### Task 3: Generic Jenkins parameter contract

**Files:**
- Modify: `tests/integration/test_ci_contract.py`
- Modify: `Jenkinsfile`

**Interfaces:**
- Consumes: framework `API_TEST_ENV_FILE` capability.
- Produces: optional Jenkins string parameter `ENV_FILE`.

- [ ] Extend CI contract tests to require `ENV_FILE`, generic runtime injection, and continued absence of SUT tokens.
- [ ] Run the CI contract test and confirm RED.
- [ ] Add `ENV_FILE` parameter and inject it only for the test process; do not copy file contents into Workspace.
- [ ] Re-run CI contract tests and confirm GREEN.

### Task 4: Documentation and canonical plan

**Files:**
- Modify: `docs/10_CI-CD接入说明.md`
- Modify: `README.md`
- Modify: `AI_API_Autotest_Framework_Project_Plan_Latest.md`
- Modify: `docs/00_项目计划书_Latest.md`

**Interfaces:**
- Documents the same `ENV_NAME + ENV_FILE + LEVEL` contract implemented above.

- [ ] Document public project YAML vs private override YAML responsibilities.
- [ ] Document local and Jenkins examples without real secrets or SUT hard-coding in framework sections.
- [ ] Record Stage 6 status as “private-config mechanism implemented; real SUT Jenkins smoke pending user execution”.

### Task 5: Full verification and packaging

**Files:**
- Verify all modified files and existing framework suites.

- [ ] Run focused ConfigManager/runner tests.
- [ ] Run CI contract tests.
- [ ] Run all framework tests under `tests/`.
- [ ] Run Mock smoke through the supported `run.py` entrypoint.
- [ ] Run `compileall`.
- [ ] Scan public core/CI files for current SUT tokens.
- [ ] Package a complete ZIP because this change touches multiple framework/CI/docs files.
