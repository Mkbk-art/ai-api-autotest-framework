# Stage 2 Framework Hardening Design

## Goal
Complete Stage 2 so the framework no longer relies on shared `extract.yaml` state, has a practical response assertion engine, verifies non-JSON/timeout/connection failure behavior, and records trustworthy Allure/JUnit evidence without changing the public business-test workflow.

## Scope
- Replace runtime file-backed context with an in-memory `VariableContext`.
- Keep `session`, `scenario`, and `case` namespaces; each `VariableContext` instance is isolated.
- Make each pytest business test receive its own context instance through fixtures.
- Preserve existing YAML expressions such as `${get_extract_data(access_token)}` for backward compatibility.
- Expand assertions while preserving existing `contains`, `eq`, and `ne` YAML syntax.
- Add explicit selector-based assertions for status code, field existence, membership, numeric comparison, response headers, and response time.
- Verify non-JSON responses, timeouts, connection failures, and Allure attachment sanitization.
- Fix runner evidence tests so they work whether Allure is installed or absent.
- Do not add MySQL/Redis real integration, CI/CD, AI, or migrate to the final `core/` directory yet.

## VariableContext
`VariableContext` owns three dictionaries: `session`, `scenario`, and `case`. Lookup order is `case -> scenario -> session` when no explicit scope is supplied. `set`, `get`, `clear`, `replace_variables`, and `export_debug_snapshot` are provided. Missing variables raise `VariableNotFoundError` rather than silently returning empty strings.

If a string is exactly `${name}`, replacement preserves the original value type. If a variable is embedded inside a larger string, the replacement is converted to text. Dictionaries, lists, and tuples are replaced recursively.

Dynamic function expressions such as `${random_string(6)}` remain handled by `DebugTalk`; `${get_extract_data(name)}` reads the current `VariableContext`.

## Runtime Integration
`RequestBase` receives a `VariableContext` instance. It passes that instance to `DebugTalk` and `extract_from_response`. Test fixtures create a function-scoped context, so parallel tests do not share state through a file. Authentication and published-resource fixtures write their values into the same context used by the test's `RequestBase`.

## Assertion Engine
Existing YAML remains valid:

```yaml
- contains:
    status_code: 200
    msg: 登录成功
- eq:
    success: true
```

New selector syntax is also supported:

```yaml
- status_code: 200
- exists: $.data.access_token
- not_exists: $.error
- eq: [$.data.userId, 1]
- ne: [$.data.status, disabled]
- in: [$.data.role, [admin, owner]]
- gt: [$.data.count, 0]
- response_time_lt: 1.0
- header_eq: [Content-Type, application/json]
```

Every failed rule contributes a readable detail. Unsupported assertion types fail explicitly. Database/Redis assertions are not implemented in Stage 2 and therefore fail explicitly if used.

## Error and Report Behavior
`RequestClient` continues to re-raise `requests.Timeout` and `requests.ConnectionError`. Tests verify both branches. Mock Server adds a plain-text endpoint and delayed endpoint for real integration coverage. Allure attachments are verified through the compatibility API and must contain sanitized headers.

## Acceptance
- Existing six business Mock tests still pass.
- smoke/core/regression still execute independently.
- No runtime dependency on `extract.yaml`.
- Context tests prove type-preserving replacement, recursive replacement, scope precedence, isolation, clearing, and missing-variable failure.
- Assertion tests cover old and new syntax plus unsupported rules.
- Timeout, connection failure, and non-JSON paths are tested.
- Runner evidence test passes with or without Allure plugin installed.
- Full suite passes from a clean extracted delivery archive.
