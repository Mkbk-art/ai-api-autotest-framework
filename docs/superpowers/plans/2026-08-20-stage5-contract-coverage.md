# Stage 5 Contract & Coverage Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add normalized API Contract providers and deterministic API-to-test coverage/gap outputs without adding SUT-specific logic to Framework Core.

**Architecture:** Provider-specific acquisition ends at a shared immutable `ApiContract`. Coverage consumes only `ApiContract + CaseRegistry`, so OpenAPI and static-manifest projects follow the same path. Workflow multi-operation relationships become part of the generic CaseSpec contract.

**Tech Stack:** Python 3.11+, dataclasses, PyYAML, JSON, Pytest.

**Spec:** `docs/superpowers/specs/2026-08-20-stage5-contract-coverage-design.md`

## Global Constraints

- No Spring/Java source parser in production framework code.
- No Shortlink business token in `contracts/` or `coverage_engine/`.
- Do not change RequestClient/AssertionEngine semantics.
- OpenAPI and static manifest must normalize to the same model.
- `coverage_engine/` must not be named `coverage/`.
- TDD red -> green for each production behavior.

---

### Task 1: Normalized Contract Model

**Files:**
- Create: `contracts/__init__.py`
- Create: `contracts/model.py`
- Test: `tests/contracts/test_contract_model.py`

**Interfaces:**
- Produces: `SchemaField`, `Parameter`, `RequestBody`, `ResponseSpec`, `Operation`, `ApiContract`.

- [ ] Write failing model/validation/serialization tests.
- [ ] Run tests and confirm RED due to missing package.
- [ ] Implement minimal immutable model and JSON-safe `to_dict`/`write_json`.
- [ ] Run model tests GREEN.

### Task 2: Static Manifest Provider

**Files:**
- Create: `contracts/provider.py`
- Create: `contracts/manifest_provider.py`
- Test: `tests/contracts/test_manifest_provider.py`
- Create: `testcases/shortlink/contract/contract.yaml`
- Modify: `config/env.shortlink-local.yaml`

**Interfaces:**
- Produces: `ContractProvider`, `StaticManifestProvider`, `load_contract_from_config`.

- [ ] Write failing manifest/provider/config resolution tests using generic fixtures.
- [ ] Verify RED.
- [ ] Implement provider and strict manifest validation.
- [ ] Add reviewed Shortlink static contract as project asset.
- [ ] Run provider tests GREEN.

### Task 3: OpenAPI 3 Provider

**Files:**
- Create: `contracts/openapi_provider.py`
- Create: `tests/fixtures/contracts/sample_openapi.yaml`
- Test: `tests/contracts/test_openapi_provider.py`

**Interfaces:**
- Produces: `OpenAPIProvider` with OpenAPI YAML/JSON support and local `$ref` normalization.

- [ ] Write failing YAML/JSON/operationId/fallback/ref tests.
- [ ] Verify RED.
- [ ] Implement minimal OpenAPI 3 normalization.
- [ ] Run provider tests GREEN.

### Task 4: Generic Multi-operation Case Relations

**Files:**
- Modify: `core/case_spec.py`
- Modify: `core/case_registry.py`
- Modify: `testcases/shortlink/yaml/link.yaml`
- Test: `tests/unit/test_case_spec_v2.py`

**Interfaces:**
- Produces: `CaseSpec.operation_ids` and registry indexing of all bound operations.

- [ ] Write failing multi-operation parsing/index tests.
- [ ] Verify RED.
- [ ] Implement generic `operations` field and backward-safe primary relation.
- [ ] Migrate lifecycle Workflow metadata to top-level `operations`.
- [ ] Run Stage 4 tests GREEN.

### Task 5: Coverage Index and Gap

**Files:**
- Create: `coverage_engine/__init__.py`
- Create: `coverage_engine/index.py`
- Create: `coverage_engine/gap.py`
- Test: `tests/coverage_engine/test_coverage_index.py`
- Test: `tests/coverage_engine/test_coverage_gap.py`

**Interfaces:**
- Produces: `CoverageIndex.build(contract, registry)`, `CoverageGap.build(index)`, JSON outputs.

- [ ] Write failing operation/case/risk/workflow coverage tests.
- [ ] Verify RED.
- [ ] Implement index.
- [ ] Write failing deterministic gap tests.
- [ ] Implement gap and JSON output.
- [ ] Run coverage tests GREEN.

### Task 6: Architecture Guard + Real Static Contract Verification

**Files:**
- Create: `tests/integration/test_contract_coverage_architecture.py`
- Create: `docs/evidence/41_stage5_contract_coverage_offline_verification.md`

**Interfaces:**
- Verifies: no current-SUT token in generic packages; Shortlink manifest loads; current CaseRegistry bindings are valid; independent OpenAPI fixture loads.

- [ ] Add architecture and real-manifest tests.
- [ ] Run Stage 5 suite.
- [ ] Run full `python -m pytest tests -q`.
- [ ] Run Mock smoke/core/regression collection/execution as non-regression evidence.
- [ ] Write verification evidence and update plan status truthfully.
