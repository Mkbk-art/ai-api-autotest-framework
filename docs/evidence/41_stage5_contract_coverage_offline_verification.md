# Stage 5 Contract & Coverage Offline Verification

Date: 2026-08-20

## Scope

- normalized ApiContract model
- StaticManifestProvider
- OpenAPIProvider (YAML/JSON/local refs)
- generic multi-operation Workflow relation
- CoverageIndex / CoverageGap
- standalone coverage analysis CLI
- Shortlink reviewed Static Manifest
- architecture hardcoding guard

## TDD / Stage 5 focused suite

```text
34 passed
```

## Full framework regression

```text
211 passed
```

## Existing Mock runtime regression

```text
smoke      2 passed, 4 deselected
core       2 passed, 4 deselected
regression 2 passed, 4 deselected
```

## Shortlink Contract/Coverage offline analysis

Command:

```bash
python -m coverage_engine.cli --env shortlink-local
```

Result:

```text
project=shortlink coverage=8/27 (29.63%) untested=19 unknown_bindings=0
```

Contract inventory:

```text
total mappings        43
external operations   27
current test cases     18
covered operations     8
unknown bindings       0
unbound cases          0
```

## Architecture evidence

- `contracts/` contains no current SUT business token.
- `coverage_engine/` contains no current SUT business token.
- package name is `coverage_engine`, therefore it does not shadow third-party `coverage` used by pytest-cov.
- OpenAPI provider is verified with an independent inventory-service fixture.
- Shortlink uses Static Manifest only as project-owned contract data.
- RequestClient and AssertionEngine behavior were not changed by Stage 5.

## Generic issue found during Stage 5

Adding `testcases/<suite>/contract/contract.yaml` exposed that root `conftest.py` previously scanned every `testcases/**/*.yaml` when registering markers. This caused Contract YAML to be parsed as a Test Specification.

Fix:

```text
old: testcases/**/*.yaml
new: testcases/<suite>/yaml/*.yaml
```

This is a generic project-asset isolation fix; it allows projects to contain contract/fixtures/config YAML without changing framework test collection semantics.

## Status boundary

Code and offline verification are complete. Stage 5 should be marked fully complete only after the user re-runs the focused local verification on the working repository and then publishes through the normal Git/CI review flow.
