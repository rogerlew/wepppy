# I-CREWS correctness and user experience review

## Metadata

- Date: 2026-11-19.
- Independent reviewer: `icrews_contract`.
- Candidate branch: `task/i-crews-interface`.
- Contract: [I-CREWS WEPPcloud interface](../../../ui-docs/contracts/i-crews-interface-contract.md).
- Reviewed checkpoints: `9867163fb` and corrected WBT-MOFE source `ac1e41236`.
- Related evidence: [Validation](20261119_validation.md) and [security review](20261119_security_review.md).

## User outcome and valid states

| State or request | Outcome and evidence |
| --- | --- |
| Signed-in user opens Interfaces | One Site Specific Resources card, two forms, attribution and responsive artwork. Chromium clicked both buttons and captured the submitted IDs. |
| Anonymous creation enabled or disabled | The same card renders under existing CAPTCHA policy. Jinja coverage checks the enabled and disabled states. |
| New run in either creation mode | The API returns the matching 303 URL. Four disposable runs cover both writer modes and reload the effective preset and units from disk. |
| Direct I-CREWS run | The saved preset selects the funding footer and Idaho outline. The actual Jinja bootstrap and the deck.gl layer registration are tested. |
| Ordinary run with a boundary | Rendering of the Lake Tahoe preset confirms I-CREWS attribution and default outline activation are scoped to the two new presets. |
| Extent overlaps Idaho or falls entirely outside | Both configs produce channels across the border. A disjoint selection yields the existing actionable error, preserves channel bytes and permits a valid retry. |
| Unsupported override or alternate config selector | The API returns HTTP 400 with `project_config_validation_failed` before allocating state. A canonical request can be retried. |

## Generated artifact evidence

| Stage | Readback |
| --- | --- |
| User selection and persisted config | Chromium form payload, API redirect, matching on-disk snapshots and Ron reload. Parsed settings match each exact source outside the Idaho map stanza. |
| Native channel products | Both disposable WBT runs produce positive channel cells in the network raster and a populated map FeatureCollection. |
| Prepared model inputs | The real MOFE preparer reads a seeded two-segment hillslope and writes a management file and slope file that each retain both segments. |
| UI and artifact observability | The existing channel map consumes the normal channel GeoJSON. The bootstrap identifies the same Census polygon used for admission. The UI test checks the visible outline layer and that subsequent bootstrap adds no duplicate. |

The source review required evidence from the real run-template bootstrap.
The candidate now tests the rendered bootstrap for both new presets and
one existing interface. There are no open source correctness findings.
Local generated-artifact acceptance uses disposable runs. This evidence
covers the component boundaries through executable input preparation. Hosted
verification uses the existing channel and prepared model artifact paths.
