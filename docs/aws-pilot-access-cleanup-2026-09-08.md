# AWS pilot executor access cleanup — 2026-09-08

## Outcome

The temporary, package-bound IAM executor role used by the completed AWS S3
golden path was removed after the successful job and verified absent. This
closed the pilot's standing mutation path without modifying the application
stack, bucket, CloudFormation templates, object data, or any Azure resource.

Private account, role, policy, trust-condition, and target identifiers remain
outside the repository.

## Verification and deletion boundary

Before deletion, the operator verified that:

- the authenticated caller resolved to the approved target account;
- the exact executor role existed;
- its trust document was semantically identical to the preserved,
  digest-reviewed trust document;
- its sole inline permissions policy was semantically identical to the
  preserved, digest-reviewed execution policy; and
- it had no attached managed policies or unexpected inline policies.

Only that inline policy and role were deleted. A subsequent exact-name lookup
confirmed the role was absent. The private trust and policy documents remain
available with the pilot evidence so the role can be recreated under a future
separately authorized package; no reusable AWS session credential is committed
or retained by El Capitan.

## Residual target-owned risk

The existing CDK bootstrap CloudFormation service role still has
`AdministratorAccess`. It predated El Capitan, remained unchanged during the
pilot, and is not an El Capitan runtime credential. CloudFormation necessarily
used that target-owned service role for the approved stack update, so its broad
privilege remains part of the target application's AWS governance debt.

Reducing or replacing that service role requires a separate stack-wide impact
review covering every resource type and deployment path that uses it. It must
not be narrowed as an incidental release-cleanup action. Future El Capitan
production packages must continue to disclose and pin the service-role
baseline, even when the calling executor role itself is least privilege.
