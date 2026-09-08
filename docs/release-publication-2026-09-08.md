# v0.1.0 publication record

## Outcome

El Capitan v0.1.0 was published on 2026-09-08 as a self-hosted technical
preview. The immutable release tag resolves to
`522eabb51fe0394f97516dae2a7f97746e604b0c`.

- Public release: <https://github.com/kkmookhey/elcapitan/releases/tag/v0.1.0>
- Final CI: <https://github.com/kkmookhey/elcapitan/actions/runs/34288299192>
- Protected release workflow: <https://github.com/kkmookhey/elcapitan/actions/runs/34288616030>
- Image: `ghcr.io/kkmookhey/elcapitan:v0.1.0`
- Image index digest: `sha256:155511fcaab4546e13af396695560a0b7c11f7278d124ac7ef5d89b83d0ea774`
- Image provenance: <https://github.com/kkmookhey/elcapitan/attestations/46105551>

The release used committed `RELEASE_APPROVAL.json` with SHA-256
`0f851d504e6a62a1bd26e9b0c0a9df66281e07e1310e4a220288e6b92ac61b09`.
The protected environment approval preceded all registry publication.

## Published assets

| Asset | SHA-256 |
|---|---|
| `elcapitan-0.1.0-py3-none-any.whl` | `209fb7112a3df868b5171bb977c96e9349b016a3ac367a345090e83c921f723e` |
| `elcapitan-0.1.0.tar.gz` | `5a9d80302757f3c68933c6b36e21cc5b3994793c727d9e24473e667342e17785` |
| `elcapitan-v0.1.0.cdx.json` | `3bba168ae06bdc5e1b583931d00d32cd58ac59be108648e960b4fdb009c35d77` |
| `SHA256SUMS` | `44cef0ec32decbc14781f63ab55e08ecdc009ef0077ecaa407ed3a989e7dd27f` |

The GitHub Actions release bundle contained the same four files. Its uploaded
artifact SHA-256 was
`4e56c069151cb9080fef1e87cc2a0bac0cf1af3bb6f2fbfefd78891ab2594a54`.

## Independent post-publication verification

The downloaded wheel and source archive passed `SHA256SUMS`. The CycloneDX
document parsed as specification 1.6. Strict `gh attestation verify` checks
passed for the wheel, source archive, CycloneDX document, and immutable image
digest while enforcing:

- repository `kkmookhey/elcapitan`;
- signer workflow `.github/workflows/release.yml`;
- source digest `522eabb51fe0394f97516dae2a7f97746e604b0c`; and
- source ref `refs/tags/v0.1.0`.

An unauthenticated GHCR token and manifest request returned HTTP 200 and the
expected image index digest. The index contains Linux AMD64 manifest
`sha256:34b7b320857753caf774e115469fc31b83727b6c4a98095797e37c5dc5f7f505`
and Linux ARM64 manifest
`sha256:91845e99229bc6dd7d6d12c47ce295833fb10948258b03a894970c5210239cbe`,
plus their Buildx attestation manifests.

The protected workflow independently repeated the final release gate, 748-test
suite, distribution build and inspection, CycloneDX generation, runtime image
build, fixed high/critical vulnerability rejection, distribution attestations,
multi-architecture image build, image attestation, and evidence-bundle upload.

## Scope boundaries

This publication made no Azure or AWS call, customer-data access, model call,
PyPI publication, hosted-service claim, or unattended-remediation claim. The
temporary AWS pilot executor role was already removed and verified absent; the
target account's pre-existing CDK bootstrap service role remains a separately
documented target-owned risk. The local owner screen recording remains
untracked and was not published.
