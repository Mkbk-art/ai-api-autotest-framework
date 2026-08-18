# Stage 2 Framework Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Stage 2 with isolated in-memory context, stronger assertions, network-error coverage, and trustworthy report evidence while preserving current business-test commands.

**Architecture:** `VariableContext` becomes the runtime state source and is injected into `RequestBase`, `DebugTalk`, and `Extractor`. Assertions are centralized in `Assertions` with backward-compatible rules and selector-based rules. Mock Server exposes deterministic endpoints for non-JSON and timeout testing.

**Tech Stack:** Python 3.11+, Pytest, Requests, YAML, Allure compatibility layer, standard-library HTTP mock server.

## Global Constraints
- Preserve `python run.py --env test --level smoke|core|regression`.
- Do not introduce MySQL/Redis real behavior, CI/CD, AI, or final directory migration in this stage.
- No shared file is allowed as runtime context truth.
- Existing YAML cases remain valid.
- All behavior changes require failing tests first.

---

### Task 1: In-memory VariableContext

**Files:**
- Create: `common/variable_context.py`
- Test: `tests/unit/test_variable_context.py`

**Interfaces:**
- Produces: `VariableContext`, `VariableNotFoundError`, `set`, `get`, `clear`, `replace_variables`, `export_debug_snapshot`.

- [ ] Write tests for scope precedence, type-preserving replacement, recursive data replacement, missing-variable failure, clear, and instance isolation.
- [ ] Run the new test module and verify it fails because `common.variable_context` does not exist.
- [ ] Implement the minimal class and exception.
- [ ] Run the test module and verify all tests pass.
- [ ] Commit the task.

### Task 2: Replace extract.yaml runtime state

**Files:**
- Modify: `common/yaml_loader.py`
- Modify: `common/extractor.py`
- Modify: `base/debugtalk.py`
- Modify: `base/apiutil.py`
- Modify: `testcase/conftest.py`
- Test: `tests/unit/test_context_integration.py`

**Interfaces:**
- Consumes: `VariableContext`.
- Produces: request execution where extraction and later `${get_extract_data(...)}` replacement use the injected in-memory context.

- [ ] Write tests proving extractor writes to an injected context and RequestBase/DebugTalk read from the same context without creating `extract.yaml`.
- [ ] Run the tests and verify failure against the current file-backed integration.
- [ ] Inject context into Extractor, DebugTalk, RequestBase, and pytest fixtures.
- [ ] Keep `common.yaml_loader.context` as an in-memory compatibility object only.
- [ ] Run context tests and existing business tests.
- [ ] Commit the task.

### Task 3: AssertionEngine expansion

**Files:**
- Modify: `common/assertion.py`
- Modify: `base/apiutil.py`
- Test: `tests/unit/test_assertion_engine.py`

**Interfaces:**
- Produces: `Assertions.assert_all(validations, response_body, status_code, headers=None, elapsed_seconds=None)`.

- [ ] Write failing tests for legacy `contains/eq/ne`, selector `status_code`, exists/not_exists, in/not_in, numeric comparisons, header equality, response-time threshold, and unsupported assertion failure.
- [ ] Run the tests and verify the new rules fail.
- [ ] Implement selector resolution and readable aggregated failures.
- [ ] Pass response headers and elapsed time from RequestBase.
- [ ] Run assertion and business regression tests.
- [ ] Commit the task.

### Task 4: Network errors, non-JSON and Allure evidence

**Files:**
- Modify: `mock_server/server.py`
- Modify: `tests/unit/test_request_and_headers.py`
- Create: `tests/integration/test_error_paths.py`
- Modify: `tests/integration/test_runner_evidence.py`

**Interfaces:**
- Mock endpoints: `GET /api/v1/plain`, `GET /api/v1/slow?delay=<seconds>`.

- [ ] Write failing tests for timeout, connection failure, non-JSON RequestClient handling, sanitized Allure headers, and environment-independent Allure runner metadata.
- [ ] Run those tests and confirm the intended failures.
- [ ] Add deterministic Mock endpoints and make the runner evidence assertion conditional on actual plugin availability.
- [ ] Run the error-path tests and full suite.
- [ ] Commit the task.

### Task 5: Stage 2 evidence and delivery docs

**Files:**
- Create: `docs/05_上下文变量机制.md`
- Create: `docs/06_断言引擎设计.md`
- Update: `README.md`
- Create/update: `docs/evidence/05_stage2_full_test.txt`
- Create/update: `reports/coverage.xml` when coverage tooling is available.

**Interfaces:**
- Documents only verified behavior from Tasks 1-4.

- [ ] Run unit, integration, business-level, and full regression commands.
- [ ] Capture exact outputs in evidence.
- [ ] Update README and design docs with verified behavior and remaining limitations.
- [ ] Run `compileall` and full tests again from final tree.
- [ ] Commit the task.
