# v0.1.0 release-candidate rehearsal — 2026-09-08

## Outcome

The clean-checkout release rehearsal passed at source commit
`973701ee56b9da025b08f456ff2d86642ceb8c97`. It used the repository's guarded
rehearsal script and an isolated offline uv environment after the exact locked
dependencies were cached.

The rehearsal performed no cloud or model call and used only checked-in
synthetic quickstart data.

## Verified gates

| Gate | Result |
|---|---|
| Locked clean-checkout install | Passed under CPython 3.12.13 |
| Release-tree and generated matrix | Passed; 72 controls remained current |
| Compile and narrow Ruff checks | Passed |
| Full Python suite | 746 passed in 36.80 seconds |
| Wheel and source distribution | Built, content-inspected, and checksummed |
| Complete-history secret scan | Gitleaks scanned 207 commits; zero findings |
| PostgreSQL quickstart | Passed in 15 seconds with synthetic data and no cloud/model credentials |
| Container build | Passed from digest/checksum-pinned inputs |
| CycloneDX SBOM | 370 components |
| OCI provenance | Present |
| Fixed high/critical vulnerability scan | Trivy 0.70.0 reported zero findings across Debian, Python, and Terraform/Go results |

The local rehearsal OCI digest was
`sha256:876f27679510813bb8e0dae542567735f266b7faf7a22fd9fb793db05ea2b955`.
This is local candidate evidence, not the final multi-architecture release
digest. The protected GitHub release workflow rebuilds and attests the exact
tag and produces the authoritative published digest.

## Evidence handling

Raw logs, distribution checksums, SBOM, OCI metadata/provenance, and the Trivy
JSON report remain in the ignored local release-evidence directory
`release/rehearsal-973701ee56b9/`. They are intentionally excluded from the
source tree. This sanitized record contains no credential, private cloud
identifier, customer data, local temporary path, or model output.

The first rehearsal attempt stopped before tests because the isolated cache
lacked the platform-specific locked PostgreSQL wheel. After caching that exact
dependency, the next run reached the suite and exposed a release-cut test that
still required the changelog to be undated. The check was refactored without
removing the fail-closed date assertion, and the complete rehearsal then
passed. Neither setup failure was treated as release evidence.
