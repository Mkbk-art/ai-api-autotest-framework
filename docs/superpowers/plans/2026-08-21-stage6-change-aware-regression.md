# Stage 6 Change-aware Smart Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a deterministic, user-controlled, Local-first regression selection pipeline based on accepted normalized Contract snapshots, explicit test dependencies, safe FULL fallback, and stable Pytest case IDs.

**Architecture:** `regression_engine` reads the same Stage 5 `ApiContract` and `CaseRegistry`, compares an explicit accepted baseline to the current normalized contract, expands only explicit Workflow/Context dependencies, builds a machine-readable `SelectionPlan`, and hands stable case IDs to normal Pytest collection. Existing smoke/core/regression FULL behavior remains unchanged; `level=all` and `selection=auto` are additive. CI integration is deliberately deferred until Local closure is verified; after Local closure, only a thin parameter/artifact layer is added.

**Tech Stack:** Python 3.11+, Pytest, YAML/JSON, existing `ConfigManager`, `ApiContract`, `CaseRegistry`, Allure/JUnit pipeline.

**Spec:** `AI_API_Autotest_Framework_Project_Plan_Latest.md` Stage 6.

## Global Constraints

- Framework Core and `regression_engine/` contain zero Shortlink business hardcoding.
- No Java/Spring/source-code impact analyzer.
- No AI in Stage 6 V1 selection.
- Normal test runs never mutate accepted baseline snapshots.
- AUTO uncertainty falls back to FULL; it never silently reduces required tests.
- `smoke/core/regression` semantics remain unchanged; `all` is additive.
- Pytest remains the executor; selection is a collection filter by stable `case_id`.
- No giant `pytest -k`, no YAML mutation, no direct CaseExecutor loop as test runner.
- Local workflow closes before thin GitHub Actions/Jenkins integration.

---

### Task 1: Normalized snapshot round-trip and explicit baseline lifecycle

**Files:**
- Modify: `contracts/model.py`
- Create: `regression_engine/__init__.py`
- Create: `regression_engine/snapshot.py`
- Test: `tests/regression_engine/test_snapshot.py`

**Interfaces:**
- Produces: `ApiContract.from_dict(data)`, `ContractSnapshot`, `load_baseline_path(runtime_config, project_root)`, `write_baseline(contract, path, mode)`.
- Baseline modes: `init` refuses overwrite; `accept` explicitly replaces.

- [ ] Write failing tests for normalized round-trip, init refusal, accept overwrite, missing/invalid/project-mismatch baseline.
- [ ] Run `python -m pytest tests/regression_engine/test_snapshot.py -q` and verify RED.
- [ ] Implement minimal normalized deserialization and snapshot lifecycle.
- [ ] Re-run target tests and verify GREEN.

### Task 2: Deterministic Contract Diff

**Files:**
- Create: `regression_engine/diff.py`
- Test: `tests/regression_engine/test_contract_diff.py`

**Interfaces:**
- Produces: `ChangeSeverity`, `ContractChange`, `OperationDiff`, `ContractDiff`, `diff_contracts(baseline, current)`.
- Ignores summary/description/metadata-only differences.

- [ ] Write failing tests for added/removed operations, method/path, parameters, request fields/body, response statuses/fields, and docs-only no-op.
- [ ] Verify RED.
- [ ] Implement deterministic comparison over existing normalized model fields only.
- [ ] Verify GREEN.

### Task 3: Context Provider dependency metadata and graph validation

**Files:**
- Modify: `core/context_provider.py`
- Modify: `core/case_executor.py`
- Create: `core/project_extensions.py`
- Modify: `conftest.py`
- Modify: `testcases/shortlink/context.py`
- Test: `tests/unit/test_context_provider_dependencies.py`
- Test: `tests/unit/test_case_executor.py`

**Interfaces:**
- `ContextProviderRegistry.register(name, provider, *, requires=(), operations=())`.
- Registry exposes immutable provider specs and validates duplicate/unknown/cycle metadata.
- Runtime dependency resolution uses declared `requires`; provider code may retain defensive `ensure_context` calls without changing behavior.

- [ ] Write failing tests for explicit empty metadata, transitive requires, unknown provider, cycle, and declared runtime dependency order.
- [ ] Verify RED.
- [ ] Implement provider specs and shared project extension loader.
- [ ] Update Shortlink registrations with explicit generic metadata.
- [ ] Verify GREEN plus existing CaseExecutor tests.

### Task 4: Dependency expansion and Case–Contract drift

**Files:**
- Create: `regression_engine/dependency.py`
- Test: `tests/regression_engine/test_dependency.py`

**Interfaces:**
- Produces a validated graph from `CaseRegistry + ContextProviderRegistry + ApiContract`.
- Provides impacted cases with evidence paths for changed operation IDs.
- Drift compares declarative relative path/method only.

- [ ] Write failing tests for direct case, workflow multi-operation, transitive context dependency, multiple reasons, drift, unknown operation/provider/cycle unsafe state.
- [ ] Verify RED.
- [ ] Implement minimal graph traversal and drift detector.
- [ ] Verify GREEN.

### Task 5: SelectionPlan, level scope, user includes, smoke safety, FULL fallback

**Files:**
- Create: `regression_engine/selection.py`
- Test: `tests/regression_engine/test_selection.py`

**Interfaces:**
- Produces `SelectionReason`, `SelectedCase`, `SelectionPlan`, `build_selection_plan(...)`.
- Modes: `full`, `auto`, `fallback_full`.
- Level scopes: `smoke`, `core`, `regression`, `all`.

- [ ] Write failing tests for FULL, AUTO, level boundary, include-case/include-tag, include out-of-scope error, smoke safety only for `all`, added-op gap, removed-op old binding, and invalid dependency fallback FULL.
- [ ] Verify RED.
- [ ] Implement selection union and evidence serialization.
- [ ] Verify GREEN.

### Task 6: Run artifact orchestration and human-readable selection report

**Files:**
- Create: `regression_engine/analyzer.py`
- Test: `tests/regression_engine/test_regression_analyzer.py`

**Interfaces:**
- Inputs: env/config, run directory, level, selection mode, user includes.
- Outputs: `contract/baseline.json`, `contract/current.json`, `contract/diff.json`, `selection/selection.json`, `selection/selection.md`.
- AUTO missing/invalid baseline produces `fallback_full` plan rather than modifying baseline.

- [ ] Write failing artifact and fallback tests.
- [ ] Verify RED.
- [ ] Implement orchestration and concise Markdown/console summary data.
- [ ] Verify GREEN.

### Task 7: Baseline CLI

**Files:**
- Create: `regression_engine/cli.py`
- Test: `tests/regression_engine/test_regression_cli.py`

**Interfaces:**
- `python -m regression_engine.cli baseline init --env <env>`.
- `python -m regression_engine.cli baseline accept --env <env>`.

- [ ] Write failing parser/lifecycle tests proving normal analysis never writes baseline.
- [ ] Verify RED.
- [ ] Implement baseline subcommands without Git dependency.
- [ ] Verify GREEN.

### Task 8: Integrate selection into run.py and Pytest collection

**Files:**
- Modify: `run.py`
- Modify: `conftest.py`
- Test: `tests/unit/test_config_and_runner.py`
- Create: `tests/integration/test_regression_selection_runtime.py`

**Interfaces:**
- Add `--level all`, `--selection full|auto` default full, `--selection-only`, repeatable `--include-case`, repeatable `--include-tag`.
- `run.py` writes SelectionPlan before Pytest and exposes only its file path for collection filtering.
- `pytest_collection_modifyitems` identifies stable `case_id` from parametrized CaseSpec and deselects unselected structured cases.

- [ ] Write failing CLI/args/collection tests.
- [ ] Verify RED.
- [ ] Implement without changing existing default FULL paths.
- [ ] Verify GREEN and existing smoke/core/regression runner tests.

### Task 9: Shortlink initial accepted baseline and Local real selection proof

**Files:**
- Modify: `config/env.shortlink-local.yaml`
- Create: `testcases/shortlink/contract/baseline.json`
- Create: `tests/integration/test_stage6_shortlink_selection.py`
- Modify: `README.md`
- Modify: `AI_API_Autotest_Framework_Project_Plan_Latest.md` only for actual implementation findings/status, not a new historical copy.

**Interfaces:**
- Shortlink uses generic `contract.baseline` configuration.
- Production Stage 6 packages contain no current-SUT tokens.

- [ ] Generate initial baseline explicitly from accepted Stage 5 Shortlink contract.
- [ ] Test no-change AUTO, synthetic changed-contract selection, dependency expansion, and architecture guard.
- [ ] Verify Stage 6 target suite.
- [ ] Run framework regression and Mock FULL smoke/core/regression.
- [ ] Keep CI code unchanged until Local closure is accepted by the user.



### Task 10: Thin CI integration after Local closure

**Files:**
- Modify: `Jenkinsfile`
- Modify: `.github/workflows/api-test.yml`
- Modify: `tests/integration/test_ci_contract.py`
- Create: `tests/integration/test_stage6_architecture_contract.py`

**Interfaces:**
- Jenkins only forwards `LEVEL`, `SELECTION`, and optional `SELECTION_ONLY` to `run.py`; it does not implement Contract Diff or Selection.
- GitHub Actions keeps the existing FULL Mock smoke and adds one controlled Demo AUTO preview.
- CI never runs `baseline init` or `baseline accept`.
- Existing per-run report directories automatically archive `selection.json/md` with the same run ID.

- [x] Write a failing CI contract test for `LEVEL=all`, `SELECTION=full|auto`, Preview, and Stage 6 artifact upload.
- [x] Verify RED against the pre-Stage-6 CI files.
- [x] Add thin Jenkins parameters and one GitHub Actions Demo AUTO preview without copying selector logic.
- [x] Add architecture guards for SUT hardcoding, AI/Git coupling, baseline mutation, and lazy Stage 6 runner loading.
- [x] Run Stage 6 target tests, full framework regression, existing FULL smoke/core/regression, AUTO preview/execution, and compileall.
