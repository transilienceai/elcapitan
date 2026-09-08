# v0.1.0 publication authorization — 2026-09-08

The repository owner explicitly directed completion of the six named release
tasks for El Capitan `v0.1.0`: synchronize the measured Azure/AWS checkpoints,
refresh public claims, run the clean release/security rehearsal, prepare
privacy-safe synthetic launch media, close the temporary AWS pilot executor
access, and commit and exercise the exact digest-bound release gate.

This authorizes creation and publication of tag `v0.1.0`, the workflow-built
wheel/source bundle, checksums, CycloneDX SBOM, provenance attestations, and the
versioned GHCR image after every automated and reviewer-protected gate passes.
It does not authorize another Azure or AWS resource change, a customer-data
operation, a model call, a mutable `latest` image, PyPI publication, a hosted
multi-tenant service, or claims beyond the technical-preview boundaries in the
release notes.

The exact approval record remains `RELEASE_APPROVAL.json`. Its committed bytes
must pass the release-tree validator, and its SHA-256 must be supplied to the
manual workflow for the exact `v0.1.0` tag. A failed gate stops publication and
does not authorize weakening or bypassing the gate.
