# AWS S3 production golden path — 2026-09-08

## Outcome

El Capitan completed its first measured AWS remediation path against an
owner-testable production application bucket. One confirmed S3 object-
versioning finding advanced through exact-resource validation, contextual
priority, deployed-template-grounded CDK planning, independent operational
reviews, digest-bound human approval, durable scheduling, narrow
CloudFormation execution, health monitoring, independent revalidation,
release audit, completion certificate, and originator handoff.

The final job succeeded in one attempt. The stack remained healthy, bucket
versioning was `Enabled`, both approved application aliases returned HTTP 200,
and the independent read-only evaluator returned `not_confirmed` for the one
approved finding. Rollback was not invoked. Private account, bucket, stack,
hostname, role, package, record, and evidence identifiers remain outside the
repository.

## Exact scope and authority

The approved change altered only
`Resources.<logical-id>.Properties.VersioningConfiguration.Status` from
`Suspended` to `Enabled`. The forward template was built from the live
processed template, so unrelated source/template drift could not enter the
update. The package bound the authoritative source commit, source digest,
baseline and proposed syntheses, live and forward templates, exact executor
trust and permissions, stack service-role baseline, monitoring contract,
accepted owner E2E evidence, and exact `Suspended` rollback template.

The ambient IAM user acted only as an STS broker. Execution used the package-
bound role; independent finding validation used a separately minted read-only
federated identity. No object data was read. Azure remained parked.

## Failure and recovery evidence

An earlier approved attempt enabled versioning and reached a healthy
CloudFormation state, but its one-hour executor session expired during the
mandatory propagation wait. The post-wait template read failed closed, and the
automatic rollback initially reused the expired credentials. The case was
blocked and the job failed without a certificate. A fresh executor session
then applied the already-approved rollback template, restoring the exact
`Suspended` checkpoint with a healthy stack and application.

The adapter was corrected in commit `df5d219` so executor credentials may be
resolved at each AWS command and the independent validator identity may be
minted when its probe actually runs. The failed case, failed job, and recovery
evidence were preserved and disclosed in the successor package; they were not
rewritten or reused. The full suite passed 745 tests before the successful
fresh run.

## Completion evidence

The successful package produced durable records for:

- package-bound human approval and a one-attempt execution schedule;
- healthy pre-change state and an exact `Suspended` checkpoint;
- the exact forward CloudFormation update and processed-template digest;
- healthy post-change stack and S3 control-plane observations;
- direct confirmation that versioning is `Enabled`;
- HTTP 200 responses with matching body digests from both approved aliases;
- independent read-only revalidation of the approved finding as
  `not_confirmed`;
- acceptance of the disclosed owner E2E result from the byte-identical forward
  template run;
- release-audit acceptance, a one-finding remediation certificate, and a
  completed originator handoff.

## Residual boundaries

- The existing CloudFormation service role still has `AdministratorAccess`.
- The package-bound executor role was removed after completion and verified
  absent; see the [sanitized cleanup record](aws-pilot-access-cleanup-2026-09-08.md).
- Retained historical object versions may increase S3 storage cost.
- The accepted owner E2E result predates the final execution; fresh HTTPS,
  stack, template, S3, and finding checks mitigate but do not erase that timing
  distinction.
- This proof grants no execution authority to the other 36 AWS validators.
- Future production actions still require their own exact target, identity,
  intended change, rollback, operational contract, and digest-bound approval.
