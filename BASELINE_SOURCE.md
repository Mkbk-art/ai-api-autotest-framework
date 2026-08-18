# Baseline source and reconstruction note

- Upstream: `zed123214/api-autotest-framework`
- Reviewed commit: `e0ac76720265609d63249fed630016821659b679`
- Review date: `2026-08-04`
- License: MIT

The Stage 1 sandbox could not directly clone GitHub because outbound DNS was unavailable,
so the inspected baseline modules required for the repair work were reconstructed locally.
This project is therefore not described as a byte-for-byte clone.

Stage 1 repaired blocking defects, Stage 2 added controlled Mock verification, scoped
runtime context and stronger regression protection, and Stage 3 migrated the stable code
into the project-owned `core/`, `utils/` and `testcases/` structure. See
`THIRD_PARTY_NOTICES.md` for the attribution and contribution boundary.
