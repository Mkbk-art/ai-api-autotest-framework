# Third-Party Notices

## Upstream baseline

This project was initially based on ideas and code structure from:

- Repository: `zed123214/api-autotest-framework`
- Reviewed commit: `e0ac76720265609d63249fed630016821659b679`
- License: MIT

The upstream MIT license is preserved in the repository `LICENSE` file.

## What was inherited as a learning baseline

The baseline provided a small teaching/demo skeleton around Pytest, Requests, YAML,
Allure, request execution, response extraction, assertions, logging and Jenkins ideas.
It was not treated as a mature production framework and was not represented as wholly
original work.

## Major work added or substantially reworked in this project

The current project includes independently reviewed, repaired or redesigned work such as:

- strict YAML case loading and reliable project-path handling;
- Requests JSON/form/params/files forwarding fixes;
- case-level Header override/delete semantics;
- environment configuration precedence and unified CLI runner;
- smoke/core/regression independence from test-file execution order;
- deterministic local Mock API and framework unit/integration tests;
- in-memory scoped `VariableContext` replacing shared runtime `extract.yaml` state;
- expanded assertion engine and explicit unsupported-assertion failures;
- timeout/connection/non-JSON regression coverage;
- sensitive-data redaction for logs and Allure attachments;
- Stage 3 architecture migration from `base/common/testcase` to
  `core/utils/testcases` with clearer module responsibilities;
- documentation, evidence, reproducibility and interview-oriented project materials.

Future MySQL, Redis, real short-link SaaS, CI/CD and AI capabilities are intentionally
not claimed here until they are implemented and verified.
