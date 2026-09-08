# v0.1.0 release readiness

This is the fail-closed release record. `implemented` means the mechanism exists;
`verified` requires recorded run evidence; `blocked` means the release must not
be tagged or published.

## Local gates

| Gate | Status | Evidence or next proof |
|---|---|---|
| Full Python suite | verified | 746 tests passed in the clean-checkout rehearsal at `973701e`; the final approval-tree suite passes 748 after adding explicit dated-changelog, missing-file, untracked-approval, and missing-digest release-gate coverage |
| Wheel and source distribution | verified | The `973701e` clean checkout built, inspected, and checksummed both distributions |
| Syntax/static checks | verified | Clean-checkout compile and narrow Ruff error checks passed at `973701e`; repository-wide Ruff formatting remains migration debt |
| Dependency review | implemented | GitHub dependency review rejects moderate-or-higher vulnerabilities on pull requests |
| Secret scanning | verified | CI prevents new leaks. All 22 historical fingerprints have sanitized dispositions, `.gitleaksignore` is empty, GitHub Support confirmed affected PR cleanup, and the 2026-09-08 clean rehearsal scanned 207 commits with zero findings under the three exact-field false-positive rules |
| Container scan | verified | Runtime, CI, and release pin Terraform 1.16.1 with patched gRPC-Go 1.83.1; Trivy 0.70.0 reported zero fixed high/critical findings across the `973701e` Debian, Python, and Terraform/Go image results |
| Reproducible container inputs | verified | Python, Go, Terraform source, and PostgreSQL inputs are digest/checksum pinned; runtime Python dependencies are version/hash locked and CI checks export drift |
| Governance policies | implemented | Security, contributing, conduct, support, versioning, and changelog files exist |
| Threat model | implemented | `docs/threat-model.md` covers the required trust and failure boundaries |
| Lifecycle operations | implemented | `docs/operations.md` covers upgrade, backup, restore, retention, deletion, and uninstall |
| Capability/evidence matrix | verified | Registry generates checked-in JSON/Markdown; CI rejects drift; CLI reports the same 72-control contract |
| Docker Compose quickstart | verified | The dated verification reached the authenticated synthetic PostgreSQL result plus UI/cookie/write-boundary assertions in 10 seconds; independent new-host evidence remains |
| UI release labels | verified | Fleet API/browser separate synthetic/real input, live outcomes, validation/planning/execution, and evidence grade; semantic accessibility checks pass; [manual Chromium acceptance](manual-browser-acceptance-2026-08-30.md) verified the rendered fleet, review, lifecycle, dialog, and focus states after correcting the defects it exposed |
| Local RC rehearsal | verified | [Dated evidence](release-rehearsal-2026-09-08.md) records 746 tests, distributions, 207-commit zero-leak scan, PostgreSQL quickstart, zero high/critical image findings, 370-component CycloneDX SBOM, OCI digest, and provenance at `973701e` |
| Authorized Azure hosted E2E | verified | [Dated evidence](azure-e2e-2026-08-29.md) records fresh PostgreSQL isolation, authenticated intake, managed-identity validation, scanner mutation denial, both Storage success/rollback lifecycles, restoration, and cleanup at candidate source `57cfcb5` |
| Authorized Azure disposable action | verified | [Dated evidence](azure-disposable-golden-path-2026-09-03.md) records exact finding-to-certificate success plus complete temporary identity and tag cleanup |
| Authorized AWS S3 action | verified | [Dated evidence](aws-s3-production-golden-path-2026-09-08.md) records the disclosed failed-closed attempt, exact recovery, point-of-use identity fix, and successful one-attempt successor through certificate and handoff; the temporary executor role was subsequently removed and verified absent |

## External authorization gates

| Gate | Status | Required authority/evidence |
|---|---|---|
| License selection | verified | Transilience, Inc. approved Apache-2.0; the canonical license, package metadata, notice, and [dated owner record](owner-decisions-2026-08-30.md) are checked in |
| Project-name approval | verified | Transilience, Inc. approved retaining El Capitan after the collision risk was surfaced; the [dated record](owner-decisions-2026-08-30.md) is a business decision, not a trademark opinion |
| Historical secret response | verified | The [sanitized review](historical-secret-review-2026-08-30.md) records all 22 dispositions, completed Eiger credential cleanup, three narrowly constrained false-positive rules, an empty baseline, and a zero-finding isolated all-ref scan |
| Protected release environment | verified | The repository is public. The `release` environment requires reviewer `kkmookhey`, has self-review prevention disabled as approved, and has no branch-policy restriction; this setup does not authorize a tag or workflow run |
| Remote CI | verified | [Run 34288299192](https://github.com/kkmookhey/elcapitan/actions/runs/34288299192) passed tests/package, complete-history secret scanning, Linux high/critical container scanning, and the PostgreSQL/UI quickstart at exact tag commit `522eabb` |
| Publication authorization | verified | The owner directed completion of the exact six-task release sequence on 2026-09-08; the [sanitized scope record](release-authorization-2026-09-08.md) excludes cloud changes, customer data, model calls, PyPI, and broader product claims |
| OCI/distribution publication | verified | [Protected run 34288616030](https://github.com/kkmookhey/elcapitan/actions/runs/34288616030) published the checksum-verified wheel, source distribution, CycloneDX SBOM, signed attestations, and public AMD64/ARM64 image from tag `v0.1.0`; see the [publication record](release-publication-2026-09-08.md) |
| Customer shadow pilot | blocked | Not a v0.1 release gate; requires a separately authorized boundary, customer agreement, identities, data handling, and read-only access |
| Public launch materials | verified | Architecture/trust-boundary README, articles, limitation-forward release notes, capability matrix, and three privacy-reviewed synthetic viewport captures are checked in; live-lab recording remains separately gated and is not required for this release |

The release workflow is manual-only. The completed v0.1.0 run used the exact
tag, approval input, and committed approval digest. Future runs likewise run
only on a tag and require the exact
`RELEASE APPROVED` input and the SHA-256 of the committed
`RELEASE_APPROVAL.json`, use the protected `release` environment, and then
rechecks the license, changelog date, tag/version match, tests, distribution,
checksums, SBOM, provenance, and signed attestations before pushing the
multi-architecture GHCR image. Its existence is not release approval.

Copy `docs/release-approval-record.example.json` to `RELEASE_APPROVAL.json`
only after every named owner has made the recorded decision. Replace every
placeholder, commit the completed record before creating the tag, and calculate
the workflow input from that exact checkout:

```console
sha256sum RELEASE_APPROVAL.json
uv run python scripts/check_release_tree.py --release --tag v0.1.0 \
  --approval-sha256 <64-character digest>
```

The final check rejects a mismatched digest, pending or missing decisions, a
license mismatch, any remaining historical-secret baseline, an incomplete
credential response, or a `release` environment without required reviewers.
Do not commit the example as if it were an approval or infer owner decisions
from technical test results.

## Historical-secret response

The `.gitleaksignore` file is a prevention baseline, not an assertion that the
old matches are safe. Before public release, an authorized security owner must:

1. Review matches without copying secret values into tickets or logs.
2. Identify the owning environment and decide whether each value was a secret,
   private endpoint, customer identifier, or detector false positive.
3. Revoke or rotate every potentially live credential first.
4. Obtain explicit approval before rewriting shared Git history.
5. Remove resolved fingerprints from the baseline, clone afresh, and require a
   zero-finding complete-history scan.
6. Audit wheel, sdist, OCI filesystem/SBOM, fixtures, and launch material for
   customer names, credentials, private endpoints, and unsanitized identifiers.

## Release evidence bundle

The [v0.1.0 publication record](release-publication-2026-09-08.md) indexes the
completed evidence bundle. Each future final evidence bundle must contain the
commit and tag, exact tool versions,
test and clean-machine logs, generated capability matrix, wheel/sdist and image
digests, `SHA256SUMS`, CycloneDX SBOM, GitHub provenance/SBOM attestations,
container scan result, the committed `RELEASE_APPROVAL.json` and its SHA-256,
secret audit adjudication, license/name approvals, threat model review, and
dated changelog/release notes. Verification instructions must use immutable
digests and `gh attestation verify`.

The current cloud-free UI/runtime evidence is recorded in
[`release-verification-2026-08-29.md`](release-verification-2026-08-29.md).
