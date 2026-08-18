# Stage 1 P0 Repair Design

## Scope

Use the approved V2.0 project plan as the design authority. Repair the inspected
baseline without performing the later large directory migration.

## Architecture

- Strict YAML loading fails fast on missing or malformed required files.
- Request payloads use Requests-compatible names (`json`, `data`, `params`, `files`).
- Case headers overlay base headers; `null` deletes inherited values.
- Session/scenario fixtures create prerequisites, so marker groups run alone.
- Configuration resolves CLI > environment > named YAML > defaults.
- Runner separates Allure results, HTML report, and JUnit XML and rejects zero tests.
- A local HTTP mock server provides deterministic verification before real SaaS integration.

## Out of scope

Real short-link SaaS integration, MySQL/Redis, AI functionality, UI automation,
and the final target-directory migration.
