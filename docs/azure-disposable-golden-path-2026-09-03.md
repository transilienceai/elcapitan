# Azure disposable-resource golden path — 2026-09-03

This checkpoint completes one owner-authorized remediation against an unused,
non-production Azure Storage account. Exact tenant, subscription, resource,
identity, record, and evidence identifiers remain in the private trial
workspace rather than this repository. AWS execution is the next separate
checkpoint; this run did not access AWS.

## Bound scope and authority

The approved package contained one validated finding and one intended change:
disable public network access on one exact Storage account. The pre-change
configuration was `Enabled`; the rollback checkpoint was to restore that exact
value and verify Azure control-plane health. The owner approved the canonical
package identifier and SHA-256 digest for a fixed 30-minute UTC window.

Three fresh service principals separated duties:

- scanner: Reader on the exact Storage account;
- planner: Reader on the exact Storage account; and
- executor: a temporary custom role assignment on the exact Storage account,
  containing only `storageAccounts/read` and `storageAccounts/write` and no
  data actions.

An initial bootstrap attempt inherited the operator's other test-tenant
context. Those unused identities and assignments were deleted and verified
absent before any planning credential was used or target configuration was
changed. The correct identities were then minted in the target tenant and
independently verified against the pinned subscription and resource.

## Golden-path result

The normal preapproval control plane produced the IaC link, verified plan,
independent SRE review, fixed change window, independent rollback review,
policy decision, and canonical human-review package. Terraform admitted only
one in-place transition, `public_network_access_enabled: true -> false`, with
zero creates, deletes, or replacements.

After exact package approval, the durable scheduler released one job once the
window opened. The Azure action plane then:

1. rechecked package, approval, job, resource, tags, Terraform intent, source
   digest, and vulnerable pre-change value;
2. captured the rollback checkpoint and healthy baseline;
3. changed only public network access from `Enabled` to `Disabled`;
4. observed `Succeeded` provisioning and `available` primary status;
5. probed the exact Azure property as `Disabled`;
6. reread cloud state through the separate scanner identity and evaluated only
   the package-bound finding as `not_confirmed`;
7. accepted the evidence-backed release review; and
8. emitted post-change verification, a remediation certificate scoped to the
   one approved finding, and an originator handoff.

The job succeeded on its first claimed attempt. Rollback was not invoked. The
eight sibling findings in the mixed case remain explicitly outside this
package and are not certified as remediated.

## Cleanup and implementation findings

The two temporary mutation-scope tags were removed and the account's original
tag set restored exactly. All temporary role assignments, the custom executor
role, service principals, application registrations, credential files, and
isolated Azure CLI token caches were deleted and verified absent. The final
read-only check retained `Disabled`, healthy control-plane state, anonymous
blob access disabled, and the original tags.

The run exposed and corrected three fail-closed product defects before or
during the checkpoint:

- review preparation verified a scoped promotion token but did not pass its
  confirmed finding IDs into orchestration, causing mixed-case planning to
  include unrelated findings;
- local Azure Terraform planning had no complete, isolated service-principal
  contract; and
- post-change finding revalidation and certificate issuance used every finding
  in a mixed case instead of the exact approved plan scope.

Regression coverage now proves dedicated Azure planner credential isolation,
partial or mixed identity rejection, approved-finding-only revalidation, and
failure on an unknown scoped finding. The repository passes 729 tests plus its
compile, narrow Ruff, JavaScript syntax, generated-matrix, release-tree, build,
distribution, and whitespace gates.

## Next checkpoint

AWS execution remains next. It must receive its own exact non-production
target, fresh scoped identities, intended change, rollback, approval binding,
monitoring policy, and completion evidence. This Azure approval does not grant
AWS access or mutation authority.
