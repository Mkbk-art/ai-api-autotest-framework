# Stage 1 P0 Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible baseline where YAML-driven smoke, core, and regression tests run independently against a deterministic local mock API.

**Architecture:** Preserve the baseline directory shape during repair. Introduce only focused helpers for project paths, configuration, header merging, the local mock server, and runner result handling. Every behavior change is protected by a failing test first.

**Tech Stack:** Python 3.11, Pytest, Requests, PyYAML, jsonpath-ng, Allure Pytest.

## Global Constraints

- Do not integrate the real short-link SaaS without its repository and API contract.
- Do not claim MySQL, Redis, CI, or AI capabilities as implemented.
- Preserve the upstream MIT license and source attribution.
- Use test-first red/green verification for each P0 behavior.

---

### Task 1: Strict paths and YAML loader
- [ ] Add failing tests for repository-root paths, missing files, malformed YAML, and case counts.
- [ ] Implement project path helpers and strict YAML validation.
- [ ] Correct test module YAML paths.

### Task 2: Request payload and case headers
- [ ] Add failing tests for JSON forwarding and header overlay/delete behavior.
- [ ] Standardize RequestClient on `json` and implement header merging.
- [ ] Sanitize authorization values before logging/reporting.

### Task 3: Configuration and runner
- [ ] Add failing tests for configuration precedence and runner argument construction.
- [ ] Implement ConfigManager and `--env/--level` runner arguments.
- [ ] Separate Allure result/report directories, generate JUnit XML, and reject zero tests.

### Task 4: Independent marker flows
- [ ] Add a deterministic local mock API server.
- [ ] Add scenario fixtures for authentication and published-resource prerequisites.
- [ ] Make smoke, core, and regression groups independently executable.

### Task 5: Verification and documentation
- [ ] Run unit tests and all three marker commands.
- [ ] Save JUnit/Allure result evidence and source-review documentation.
- [ ] Package the isolated project for handoff.
