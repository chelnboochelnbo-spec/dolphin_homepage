# Read-only Metricool verification

The adapter checks a fresh independent provider read and actual media bytes
against current public event facts, visual reviews and private approval metadata.
It does not call a sender or change an automation. Both intended destinations
must match before their persistent state is updated together.

## Public and private boundary

Public code contains validators, schemas and synthetic tests. Public event facts
and image bytes remain pinned to the latest main commit. Real captions, approval
references, conversation text, account mappings, provider IDs, captures, state,
plans and readback proofs belong outside every public checkout and deployment.
Do not paste these values into PR descriptions, comments, CI logs or artifacts.

Both CLIs require an explicit external state path. The adapter additionally
requires external request/plan, capture and output paths. Approval metadata is
loaded only with `--approvals`; there is no repository-relative fallback. The
legacy reservation exception requires `--october-reservations` outside the repo.
Symlinks resolving inside the checkout are rejected. Downloaded capture media
must also be external. Private input hashes are checked before and after each
operation and belong only in private output proofs. Console output is counts.

```sh
python automation/metricool_verification.py prepare --state /private/state.json --approvals /private/approvals.json --input /private/requests.json --output /private/plan.json
python automation/metricool_verification.py reconcile --state /private/state.json --approvals /private/approvals.json --input /private/plan.json --capture /private/capture.json --output /private/proof.json
```

The operator must initialize a persistent schema-version-2 state file once.
Do not substitute an empty state on subsequent runs. A lock and atomic local
replace protect one writer; they do not coordinate multiple machines.

Request schema (synthetic placeholders):

```json
{"requests":[{"event_id":"TEST-EVENT","days_before":14,"brand_id":"TEST-BRAND","accounts":{"instagram":"TEST-IG","facebook":"TEST-FB"}}]}
```

Captures contain `fetched_at`, `brand_id`, returned `brands`, returned `posts`,
and `media` entries with exact URL, local downloaded path and fetch timestamp.
Capture after preparation and include the full relevant scheduling window.
Freshness is limited to five minutes. Captures are trusted operator input, not
cryptographically authenticated API receipts. Never collect cookie values or
authorization headers for this workflow.

Approval records bind event fingerprint, image path/SHA, review ID, exact caption
SHA, approver, recording time, actual source references and existing identities.
Standing approval is an explicit instruction source, not scheduler existence.
Canonical public facts are not modified; social metadata is applied in memory.
Changed facts, image bytes, caption or identity fail closed for that event.

One shared UUID produces one allowlisted preview with both destinations and the
current numeric ID. It never echoes provider GET defaults such as `twitterData`.
The preview is not sent. After independent matching readback, re-preparation is
`noop`; missing or conflicting identities never trigger blind recreation.

## Remaining production gates

Production transport, a fresh pre-action read, one coalesced write, independent
post-action readback, recovery of ambiguous results, and owner notification are
not connected. Keep live automation unchanged until these pass separate review.
Public CI uses synthetic SNS data only; real-account dry runs stay local.

Previously tracked operational data and documentation still exist in public
history. Ignore rules do not remove tracked data or history. Cleanup requires a
separately reviewed action; this local code change does not perform it.
