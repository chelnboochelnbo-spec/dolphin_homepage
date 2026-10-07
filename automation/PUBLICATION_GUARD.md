# Publication guard and migration

The common guard covers home/schedule/archive, both event-render entry points,
event OG/JSON-LD and the offline SNS package CLI. Cancelled/draft events are
excluded everywhere; the January 2 tombstone also blocks stale legacy imports.
No event image falls back to a logo or another month's flyer.

## Three distinct evidence types

- `visual_review`: actual pixels were inspected; the ledger binds image SHA256,
  path, event ID/date/end_date/open/start/charge/performers/title/status/display,
  a reviewer, timezone-aware inspection timestamp, and literal transcription.
  Record omissions; never infer review from a filename, OCR or `ready` flag.
- `website_baseline_unverified`: frozen images already published on main
  `94d5cb7c6f85d0e48be44127f3a0c544fedbebba`. The 86 baseline event snapshots
  preserve past/out-of-scope HP display only. They are NOT visually verified
  and cannot authorize new SNS use. Changed facts/path/bytes invalidate them.
  Two previously remote images are mirrored byte-for-byte locally so mutable
  remote URLs cannot bypass the pinned SHA. Their original source paths remain
  in event data and baseline provenance.
- `october_existing_publication`: the explicitly retained October 8/22 Kiraku
  asset, exact date set, event IDs, facts/path/SHA, and existing reservation
  identities. It is not a general multi-date exception or new SNS permission.

Future target recurring events (from October 7, 2026, exact series titles in
config) require visual evidence; a website baseline cannot bypass this rule.
The October exception is separate because the owner's single-date change
starts in November. Recurring visual reviews cannot cover multiple dates.
The approved Wakai November 20/21 special instead requires one complete
two-day review and explicit approval; all target facts invalidate together.

The revised ledger records 27 files actually opened by this DAIV worker
(28 events: 26 single-date recurring events plus the Wakai special). Twenty
additional images were opened during revision, including all twelve new
Kiraku/Open Groove images from main. The parent environment's ledger was not
assumed accessible or fabricated. Of the 32 future recurring events, 26 have
single-date visual evidence, two use the fixed October exception, and four
Saturday Session 1 events remain on hold for missing approved host/image
information. January 2 is cancelled and excluded from that count.

## October SNS preservation

A direct Metricool read found the existing October 22 reservation, UUID
`-5433884878909716328`, numeric ID `389093625`, brand `6910064`, for
October 8 at 18:00 Asia/Tokyo. Its image SHA matched the frozen HP image.
The two intended networks and accounts came from `providers` and brand
settings; `twitterData` in the GET response is not a posting destination.

Only `slot_id=october-22-existing`, its exact existing caption/time/image,
and its recorded Facebook/Instagram account identities are eligible. The
image review scope still binds both October event facts, while the post's
target is October 22. No October 8 post is inferred. A new slot/account/UUID
is blocked. This record preserves an existing reservation; it does not invent
a fresh owner approval or send/update anything remotely.

## Offline SNS contract — not production connected

The read-only Metricool reconciliation adapter is documented in
`METRICOOL_VERIFICATION.md`. It consumes independent GET captures and actual
downloaded image bytes, coalesces the shared Instagram/Facebook UUID, and
persists verified existing identities. It emits previews only; the production
write transport and ordinary approval migration remain gated.

There is no network sender in this repository. External automation and its
prompt are unchanged. Do not report this CLI as a completed live integration.
The external adapter must adopt and independently verify the contract.

For ordinary visually reviewed events, approved copy is recorded under
`event.social.<channel>_caption` and `event.social.approvals.<channel>`:
UTF-8 `caption_sha256`, `review_id`, `approved_by`, and timezone-aware
`approved_at`. Changed copy or review requires refreshed evidence.

Use a persistent state file and one serialized writer. Resolve actual network
account IDs and provider account IDs (Metricool brand/blog ID) through the
connector. Reconcile existing posts before adoption; the CLI cannot discover
unrecorded remote posts. Version 2 keys bind event targets, channel/account
and a stable reminder `slot_id`, rather than the current lead-time value.

```
python automation/social_package.py --state /persistent/social.json prepare \
  --event-id EVENT_ID --channel instagram --channel-id RESOLVED_ID \
  --provider metricool --provider-account-id RESOLVED_BRAND_ID \
  --days-before 14 --slot-id lead-7 --output /private/package.json
```

An explicit slot mapping is required when moving an existing 7-day reminder
to 14 days: retain `slot_id=lead-7`, its identity and
`allowed_days_before: [7, 14]`. Default creation is blocked if a recurring
event already has an unresolved reminder. Separate 30/7-day reminders retain
their separate slots and identities. Legacy records need `slot_id` or an
unambiguous `days_before`/publication date, plus account identity or matching
trusted state. Multiple identities in one slot block preparation.

Target recurring series use 14 days before at 18:00 Asia/Tokyo; other sessions
retain 7 days. The explicit October slot retains its existing time. The Wakai
special has one complete target set per reminder/channel.

The adapter must obey `create`, `update`, or `noop`. Updates retain stable
`provider_uuid` and `provider_account_id`; `external_id` is the current numeric
ID and can change for Metricool. Re-read the remote object before sending and
use its current ID. Never recreate merely because the numeric ID changed.
Do not discard persisted state after timeouts; reconcile before retrying.

`adapter_update_payload` returns an allowlisted internal contract, not a
Metricool wire request. Never echo a GET object as an update: omit read-only
defaults such as non-target `twitterData`. An external adapter must construct
the provider's writable schema, preserve all intended destinations of a shared
post and their approved settings, and coalesce per-channel packages for the
same provider UUID/account before a full-object update. It must not drop the
other intended Facebook/Instagram destination. No live adapter is implemented.

```
python automation/social_package.py --state /persistent/social.json accept \
  --package /private/package.json --response /private/ack.json
python automation/social_package.py --state /persistent/social.json confirm \
  --package /private/package.json --response /private/readback.json
```

Acceptance is `accepted_pending_readback`, never DONE. Both completion paths
recheck content separately from identity, retaining trusted saved account/UUID
and the latest numeric ID. A Metricool response must include matching
`provider`, `provider_account_id`, `provider_uuid`, `channel`, `channel_id`,
and its current `external_id`. UUID/account changes are rejected; a changed
numeric ID under the same UUID/account is saved after matching readback.

Independently fetch the final remote post and actual media bytes; never echo
request data as proof. Confirmation additionally requires `readback: true`, a
fresh timezone-aware `fetched_at`, status `scheduled`/`published`, and matching
event IDs, publication time, caption and media SHA. Provider re-encoding fails
closed until an approved alternative proof exists. Baseline permission alone
can never satisfy SNS checks.

## Validation

Run all Node/Python tests, all existing generators, then
`python automation/audit_rendered_publication.py` and `git diff --check`.
CI uploads the hold report and desktop/mobile browser previews. Synthetic test
fixtures are labeled and never written to the real visual ledger. Keep state
backups; local file locking does not coordinate different machines.
