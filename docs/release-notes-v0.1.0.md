# El Capitan v0.1.0 technical preview release notes

**Release date:** 2026-09-08

El Capitan is a self-hosted, evidence-bound cloud remediation control plane.
The technical preview imports scanner findings, revalidates explicitly
supported claims against live configuration, prepares exact remediation
packages, stops for package-bound human approval, and permits deployment only
through a separately proven action connector and identity.

## Important limitations

- This is a technical preview, not an autonomous DevOps/SRE replacement or a
  public multi-tenant SaaS.
- Read-only live validation covers 72 deterministic controls (35 Azure and 37
  AWS), but only four controls support remediation planning and only three have
  action connectors: two Azure Storage paths and one AWS S3 path.
- Validation capability never grants planning or execution authority.
- Shared-token browser authentication is for local demonstration and bounded
  pilots, not production customer approval. Production approval requires SSO
  and named-user audit.
- Azure OpenAI and Cosmos DB are contract tested and export observed rather
  than E2E measured. Key Vault diagnostic logging, six additional S3 controls,
  eight RDS controls, twenty EC2 security-group controls, and two EBS volume
  controls are contract tested but not E2E measured.
- No unattended production remediation, generic VM/OS patching, arbitrary
  application-code remediation, broad AWS execution, or complete benchmark
  coverage is claimed.

## What is included

- OCSF and AWS Security Hub ASFF intake with exact FAIL/PASS/MANUAL accounting,
  replay deduplication, tenant isolation, correlation, transparent priority,
  and optional exact-resource asset context.
- An authenticated, read-only shadow console with explicit source, outcome,
  validation, planning, execution, and evidence-grade labels.
- Bounded Azure and AWS collectors with minimized typed evidence and
  deterministic fail-closed evaluation.
- Conservative Terraform or AWS CDK/CloudFormation linkage, isolated
  complete-file proposals, and engine-specific scope checks.
- Independent SRE, change-window, rollback, human-decision, execution,
  verification, certificate, and originator-handoff records.
- Durable runtime budgets, idempotent replay, equivalent-failure circuit
  breaking, and operator-visible needs-human outcomes.
- A Docker Compose quickstart with PostgreSQL and checked-in synthetic data.
- A generated capability/evidence matrix, pinned container inputs, package and
  container security checks, CycloneDX SBOM, provenance, and guarded release
  automation.

## Measured end-to-end evidence

The Azure disposable-resource golden path completed validation, exact
Terraform planning, independent reviews, digest-bound approval,
least-privilege execution, monitoring, deterministic revalidation,
certification, handoff, and complete temporary-identity cleanup.

The AWS S3 object-versioning golden path completed the same control contract
through an exact CDK construct and deployed CloudFormation logical resource.
An initial attempt failed closed when a session expired during stabilization;
the exact checkpoint was recovered, point-of-use credential refresh was added,
and the preserved successor package then succeeded in one attempt. The stack
and application aliases remained healthy, versioning was `Enabled`, and the
approved finding revalidated as `not_confirmed`. The sanitized evidence record
is [here](aws-s3-production-golden-path-2026-09-08.md).

Those measured paths prove their named controls only. They do not grant action
authority to the other registered validators.

The temporary AWS executor role was removed after the completed pilot and
verified absent. The target stack's pre-existing broad CloudFormation service
role was not changed and remains explicitly documented target-owned risk.

## Local preview

```bash
docker compose up --build --detach --wait
```

Open `http://127.0.0.1:8770` and follow the [five-minute
quickstart](quickstart.md). It uses synthetic data and needs no cloud or model
credentials.

The final release evidence, checksums, SBOM, provenance, attestations, and OCI
digest are produced by the reviewer-protected release workflow for the exact
`v0.1.0` tag.
