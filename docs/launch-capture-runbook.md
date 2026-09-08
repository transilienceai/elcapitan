# v0.1 launch demo and screenshot runbook

This runbook prepares launch media without expanding product claims. Recording,
publication, and any live-lab segment require their own authorization. Never use
customer data, a customer identity, Eiger, or a production resource.

## Seven-minute recording

| Time | Segment | Proof to show |
|---:|---|---|
| 0:00–0:45 | Trust boundary | README architecture diagram; validation, planning, and execution are separate |
| 0:45–1:45 | Offline import | Import a sanitized OCSF/ASFF export and reconcile exact outcome counts |
| 1:45–2:45 | Authorized lab validation | One bounded read-only validation; show identity scope and normalized evidence, not raw cloud JSON |
| 2:45–3:40 | Evidence inspection | Resource/control identity, observation time, provenance, availability, and evidence grade |
| 3:40–5:05 | Package review | Exact source diff, plan gates, SRE review, window, rollback, and package hash |
| 5:05–5:45 | Human boundary | Typed package-specific decision; explain that approval is not generic execution authority |
| 5:45–6:45 | Synthetic rollback | Separate labeled scenario triggers health failure, restores the checkpoint, and proves recovery |
| 6:45–7:00 | Limitations | Technical-preview limits and capability/evidence matrix |

The live-lab segment must stop unless the subscription, resource, read-only
identity, role scope, and sanitized output contract are explicitly approved.
Use a recorded or contract fixture if those prerequisites are absent, and label
it accurately rather than implying live proof.

## Screenshot set

Capture from a clean local quickstart at 1440×900 or larger. The minimum public
set is the first three views; package-review and rollback views may be added
when a clean browser surface is available:

1. `shadow-fleet.png` — synthetic fleet overview with source type and exact
   finding accounting visible.
2. `capability-boundaries.png` — one control showing separate validation,
   planning, execution, and evidence-grade labels.
3. `import-preview.png` — synthetic no-write preview with exact intake
   accounting and explicit no-cloud/no-model language.
4. `package-review.png` — optional synthetic review package with exact diff, rollback,
   and package-bound confirmation.
5. `synthetic-rollback.png` — optional clearly labeled rollback and recovered health.

Before committing any image, inspect every pixel for access tokens, cookies,
connection strings, personal browser chrome, account/subscription/resource
identifiers, private URLs, customer names, and local filesystem paths. Prefer a
fresh browser profile and the checked-in synthetic tenant. Optimize the final
PNG files and record the commit that produced them.

## Current capture status

The written sequence is ready. The authenticated PostgreSQL quickstart and UI
HTTP/accessibility contract passed on 2026-08-29, including hardened cookies,
read-only route boundaries, dialog semantics, keyboard-focus styling, and
reduced-motion behavior. Manual Chromium acceptance passed on 2026-08-30 after
correcting copy, focus, typography, hidden-placeholder, and recursive-detail
defects; see the [dated record](manual-browser-acceptance-2026-08-30.md).

Three release-safe viewport-only PNGs now exist under `docs/assets/v0.1/`:

- `shadow-fleet.png` — SHA-256
  `134948a102658312c9459a62c1558365cca16d8cfbe1eb6460898ce8a1b6ce72`;
- `capability-boundaries.png` — SHA-256
  `32f053790ce769fbabf2adabeccd7b3c7d9447e3bcebe1e8bedb3280ef1fdbb6`; and
- `import-preview.png` — SHA-256
  `940a23ba356a06049476b63cd9ea80079996ddc4c5eadda885211864c47ba145`.

They were cropped from the owner-supplied local acceptance recording after a
full-frame review. The crop excludes browser chrome, profile indicators, the
file chooser, local filesystem details, and the recording controls. Visible
resource data is the checked-in synthetic Azure sample with a truncated zero
account identifier; connectors are visibly offline and the workspace is
read-only. Pixel review found no access token, cookie, credential, private URL,
customer name, personal identifier, or local path. The original recording is
preserved unmodified and untracked.

Package-review and rollback screenshots remain optional launch follow-ups, not
substitutes for the existing typed/tested lifecycle evidence. The live-lab
segment remains outside this no-cloud capture. Do not replace browser proof
with HTTP assertions, a fabricated image, or an unlabeled synthetic claim.
