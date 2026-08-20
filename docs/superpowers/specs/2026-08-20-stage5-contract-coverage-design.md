# Stage 5 Contract & Coverage Intelligence Design

## Goal

Build a SUT-neutral contract and coverage layer that answers three deterministic questions:
1. What API operations does the project expose?
2. Which Case/Workflow assets cover each operation?
3. Which contract operations are untested or referenced incorrectly?

## Contract acquisition boundary

The framework consumes contracts; it does not become a source-code parser.

- OpenAPI 3.x -> `OpenAPIProvider` -> `ApiContract`
- Reviewed static manifest -> `StaticManifestProvider` -> `ApiContract`
- Backend source without OpenAPI is a one-time acquisition input used to author the static manifest.
- Framework production code must not parse Spring annotations or contain Shortlink business knowledge.

## Normalized model

`ApiContract` contains stable `Operation` records. Each operation has:
- `operation_id`
- HTTP `method`
- `path`
- optional `service`, `visibility`, `summary`
- normalized parameters/request/response field metadata
- provider/source metadata

Coverage defaults to externally visible operations. Internal service and page routes stay in the contract but do not inflate the default gap denominator.

## Test asset relation

- Declarative Case: one primary `operation_id`, optional additional `operations` only when needed.
- Workflow Case: `operations` is a first-class multi-operation relation.
- `CaseRegistry` indexes all operation relations; it does not know project-specific workflow names.

## Coverage outputs

- `contract.json`
- `coverage-index.json`
- `coverage-gap.json`

`CoverageGap` reports only deterministic facts in Stage 5:
- untested operations in the selected scope;
- case/workflow references to unknown operation IDs;
- cases without any operation binding.

Risk labels are aggregated as observed coverage metadata. Stage 5 does not invent expected/missing risks without an explicit future policy.

## Naming constraint

Use package `coverage_engine/`, not `coverage/`, to avoid shadowing the third-party `coverage` package used by pytest-cov.

## Non-goals

Stage 5 does not implement Contract Diff, smart regression selection, AI impact analysis, source-code parsers, or automatic risk-gap invention.
