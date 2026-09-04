# AWS CDK/CloudFormation execution checkpoint — 2026-09-03

## Outcome

El Capitan now has a contract-tested action path for the AWS S3 object-
versioning control. It links one deployed CloudFormation logical resource to
one exact CDK construct, synthesizes offline, admits only
`VersioningConfiguration.Status = Enabled`, carries the resulting template
through package-bound human approval, and can drive the approved stack update
through a separately supplied short-lived executor session.

This checkpoint made no AWS mutation. It establishes local product authority;
it is not evidence that the production action has run.

## Exact admitted change

The connector is deliberately narrower than a general CDK deployment path:

1. The finding must identify one bucket-level S3 ARN.
2. A current processed stack template must identify the owning stack, logical
   resource, account, region, bucket name, and exact TypeScript CDK construct.
3. The source materializer may add only `versioned: true` to that construct.
4. Dependencies install from a checked-in pnpm or npm lockfile, with lifecycle
   scripts disabled, inside the copied workspace.
5. Baseline and proposed CDK synthesis run without cloud, model, scanner, or
   ambient profile credentials and with lookups disabled.
6. Removing the proposed versioning property from the proposed synthesis must
   make it canonically identical to the baseline synthesis.
7. The forward artifact is constructed from the live processed template, so
   unrelated pre-existing source/template drift is recorded but not deployed.
8. The forward and containment templates are persisted with SHA-256 digests in
   the review package. Any source, template, stack, account, resource, or live-
   state drift blocks execution.

The executor accepts only a complete `ELCAP_EXECUTOR_AWS_*` session. Shared
credential/config files, profiles, metadata credentials, scanner credentials,
planner credentials, model credentials, and other-cloud credentials are not
eligible. The caller must be the exact short-lived role recorded for the
package. The stack's existing CloudFormation service-role state is pinned and
the update does not attach a new service role.

## Operations and recovery

The approved operating contract includes a 15-minute application write freeze
after first enablement, CloudFormation completion monitoring, stack and S3
control-plane health reads, a direct `GetBucketVersioning` probe, deterministic
post-change finding validation, and the existing release-audit, certificate,
and originator-handoff records.

First-time S3 versioning enablement is irreversible: a bucket cannot return to
the never-versioned state. The recovery template therefore sets the status to
`Suspended`. If recovery is required after first enablement, El Capitan records
the result as **contained**, leaves the case blocked for human follow-up, and
does not claim that the checkpoint was restored. A bucket whose approved prior
state was already `Suspended` can be restored exactly.

## Production boundary

The first proposed production target is an owner-testable application bucket,
but its private account, resource, stack, traffic baseline, identities, window,
and package digest are not recorded in this public-safe checkpoint. Before any
write, the operator must receive and approve one final package that restates:

- exact AWS account, region, stack, logical resource, and bucket;
- exact short-lived executor role and unchanged stack service-role baseline;
- the one-property forward template and both template digests;
- the application write-freeze window and owner-run end-to-end checks;
- the irreversible first-enable fact and `Suspended` containment route; and
- the approval command bound to the final package digest.

Until that separate approval is received, execution remains `not_started`.
