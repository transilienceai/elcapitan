# Changelog

All notable changes to El Capitan are recorded here. Dates use ISO 8601.

## [Unreleased]

### Security

- Rebuild the pinned Terraform 1.16.1 source with
  `google.golang.org/grpc` 1.83.2 after the 2026-09-08 publication of
  CVE-2026-84445. The fixed dependency is verified in the compiled binary and
  the runtime image again passes the no-fixed-HIGH-or-CRITICAL Trivy gate.

### Changed

- Run the checksum-verified Gitleaks 8.30.1 OSS binary directly in CI so the
  complete-history secret gate works identically in personal and organization
  repositories without depending on the Action wrapper's organization license.

## [0.1.0] - 2026-09-08

### Added

- One E2E-measured AWS S3 object-versioning action path through exact CDK
  construct and deployed CloudFormation-resource linkage, lockfile-bound dual
  offline synthesis, a three-way one-property template proof that excludes
  pre-existing source/template drift, digest-bound human approval, an isolated
  pinned executor role, stack/S3 monitoring, deterministic post-change
  validation, and completion certification. First enablement's irreversible
  semantics are explicit: recovery to `Suspended` becomes a contained, blocked
  outcome rather than a false exact-rollback claim. The approved production
  package completed in one attempt after point-of-use credential refresh was
  added: the stack and both application aliases remained healthy, versioning
  was `Enabled`, independent validation returned `not_confirmed`, and the
  workflow issued a one-finding certificate and completed handoff.
- One owner-authorized Azure disposable-resource golden path through scoped
  validation, canonical package approval, durable scheduling, least-privilege
  execution, health monitoring, independent live revalidation, exact-finding
  certification, handoff, and verified identity/tag cleanup. Mixed-case review,
  post-change validation, and certificate scope now remain bound to the
  approved finding IDs, and local Azure planning accepts a complete isolated
  service-principal contract without inheriting scanner or ambient identity.
- AWS S3 object-versioning evidence-to-review parity. A confirmed finding can
  now link only to an exact `aws_s3_bucket_versioning` state address, materialize
  only `Disabled`/`Suspended` to `Enabled`, admit only that one in-place plan
  attribute change, and proceed through the existing SRE, window, rollback, and
  mechanical human-review gate. AWS planning requires a separate short-lived
  `ELCAP_PLANNER_AWS_*` credential set, ignores ambient/scanner/other-cloud
  identities, persists no plan artifact, performs no apply, and adds no AWS
  execution authority.
- Evidence-minimized Layer 2 promotion for mixed resource cases. A promotion
  now binds only findings that are both live-confirmed and deterministically
  planning-capable, records every excluded sibling, and passes that exact
  finding scope into remediation planning. The Azure trial now exposes six
  preparation candidates; no plan or review package is claimed until
  authoritative IaC, service context, telemetry, and human routes are supplied.
- Lifecycle count language that distinguishes 21 validated resource cases
  from 23 checked cases and 93 confirmed findings from 95 supported findings.
- Owner-authorized Azure test validation through a temporary, isolated
  Reader-scoped scanner identity: 23 resource cases checked, 93 of 95
  supported findings confirmed, and two kind-mismatched OpenAI findings kept
  unavailable. The live pass also added canonical File Service child-to-parent
  collection and explicit absent-policy semantics for container soft delete,
  without adding any shadow approval or mutation route.
- Screenshot-led readability improvements across the lifecycle, queue,
  connector panel, and case-evidence drawer, with unrun validation shown as
  “Not run” and completed validation counted by resource case.
- Evidence-to-outcome shadow workspace that exposes scanner source and input
  format, normalized resource cases, validation state, transparent priority,
  and current outcome, followed by a visibly separate and locked remediation
  lifecycle from plan preparation through monitoring. Fleet summaries include
  source, format, priority, outcome, and downstream capability counts without
  adding approval, scheduling, or execution authority to shadow mode.
- Exact-resource asset-context manifests for shadow intake, including no-write
  match/gap preview, per-resource deterministic priority signals, immutable row
  digests and provenance, explicit synthetic business labels, and customer
  result views for owner, environment, criticality, and observed exposure.
  Resource drill-downs identify the score-driving observation and show every
  grouped finding's independent score instead of implying that scores add.
- Guided Shadow Trial onboarding with safe-sample and scanner-export entry
  paths, a fail-closed no-write intake preview, and plain-language validation
  outcomes that retain the existing read-only evidence boundary. Supported
  controls are distinguished from connector-ready checks, grouped scanner
  observations identify their resource count, and unavailable batch actions
  remain disabled.
- Two validation-only AWS EBS volume controls for encryption and owned-snapshot
  presence, using exact-resource `DescribeVolumes` and bounded
  `DescribeSnapshots` reads.
- Twenty validation-only AWS EC2 security-group controls for public port and
  CIDR exposure, default and Launch Wizard groups, and excessive rule counts,
  using exact-group and bounded attachment reads.
- Eight validation-only AWS RDS DB-instance controls for backups, snapshot tag
  copying, enhanced monitoring, IAM database authentication, VPC placement,
  CloudWatch Logs exports, automatic minor upgrades, and storage encryption,
  using one exact-ARN `DescribeDBInstances` read.
- Six validation-only AWS S3 controls for KMS encryption, server access
  logging, event notifications, lifecycle configuration, Object Lock, and MFA
  Delete, using the existing bounded bucket-state collector.
- Release governance, CI security gates, and guarded artifact provenance.
- Registry-generated capability/evidence matrix and explicit browser labels for
  source type, live outcome, validation, planning, execution, and evidence grade.
- Local-only Docker Compose quickstart with PostgreSQL and a timed synthetic
  acceptance journey that receives no cloud or model credentials.
- Clean-checkout release-candidate rehearsal with distribution checksums,
  CycloneDX container SBOM, and BuildKit provenance inspection.

### Included

- Evidence-bound intake for Prowler OCSF and AWS Security Hub ASFF exports.
- Explicit AWS and Azure deterministic live-validation capability registry.
- Separate read-only shadow and human-review services.
- Typed immutable evidence, package-bound approval, durable scheduling, bounded
  action connectors, deterministic verification, and rollback evidence.
- Synthetic local lifecycle and cloud-free contract-test fixtures.

### Security

- Shadow mode contains no approval, scheduling, model, or mutation route.
- Missing, stale, malformed, unauthorized, and unsupported evidence fails
  closed.

### Known limitations

- This is not an autonomous remediation service or a multi-tenant hosted SaaS.
- Most registered controls validate only; consult `elcapitan capabilities` for
  separate planning and execution flags.
- Shared-token authentication remains a demonstration and bounded-pilot bridge;
  production customer approval requires SSO and named-user audit.
- Broad AWS execution remains deliberately unsupported beyond the separately
  gated S3 object-versioning path.

[Unreleased]: https://github.com/transilienceai/elcapitan/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/transilienceai/elcapitan/releases/tag/v0.1.0
