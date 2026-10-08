# Publication guard

Public event facts, image bytes and visual-review scope are checked by one guard
for schedule, home, archive, event pages, OG/JSON-LD and social preparation.
Inactive events and cancellation tombstones are excluded everywhere.

## Public website evidence

- Visual records bind exact image SHA, path, event facts, inspection timestamp
  and transcription. Filenames and ready flags are not visual evidence.
- A two-day special records only its public `shared_publication` target set
  and policy version. Recurring flyers remain single-date.
- Existing website baselines preserve exact historical assets and facts.
  They never authorize new social posts.
- The narrowly scoped legacy publication exception preserves its exact existing
  asset and covered dates using `website_preservation`. Provider identities,
  captions and approval references are not public website evidence.

## Private social operations

Approval evidence and all reservation identities belong outside this checkout.
Use the explicit private inputs documented in `METRICOOL_VERIFICATION.md`.
Public website scope alone cannot authorize a social reservation. The private
approval must bind the current caption SHA and visual review; the legacy
exception additionally requires its separately supplied private reservation file.

One persistent private state file retains provider UUID/account and current
numeric ID across preparations and independent readbacks. A pending response is
not completed work. Shared destinations are reconciled together; incomplete or
conflicting content is held. No live sender or automation configuration is changed
by this repository's read-only adapter.

## Validation

Public CI uses synthetic social approvals and reservations. It checks factual
drift, image bytes, duplicate identities, cancellation scope and private paths.
Run Node/Python tests, normal generators and `audit_rendered_publication.py`.
Never upload real operation captures, private state, approval references or
captions as CI logs/artifacts. History cleanup is separate from current-file
sanitization; this workflow does not rewrite historical commits.
