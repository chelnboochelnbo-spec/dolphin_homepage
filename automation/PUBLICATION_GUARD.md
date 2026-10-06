# Verified image publication

`publication_guard.py` is the shared decision for home/schedule, archive,
both event-render entry points, event OG/JSON-LD, and `social_package.py`.
Missing or stale evidence hides only the event image. Text dates and details
remain; a logo or another month's flyer is never substituted. Cancelled/draft
events are excluded, including artist appearances. Cancellation tombstones
also block a stale import with a different ID but the same date/title.

## Record a real review

1. Read current `data/events.json`. Open the actual full-resolution image bytes.
2. Compare its visible title, date(s), opening/start time, prices, performers
   and cancellation status/context with the event. Record omissions rather than
   inventing text (for example, no student drink condition on November 5).
3. Add one `visual_review` to `data/flyer_verifications.json` with reviewer,
   timezone-aware inspection time, literal transcription, `pixels_inspected`,
   repository path and actual SHA256. For every target include the current
   `event_facts(event)` snapshot, `fingerprint(event)` and observed text.
   Computing hashes is bookkeeping **after** visual inspection, not evidence
   that inspection happened. Never create attestations from filenames or OCR
   alone. The ledger is a review artifact, not a cryptographic proof of human
   attention; reviewers must inspect its evidence when approving changes.
4. Ordinary recurring flyers cover exactly one event/date. A shared special
   two-day flyer requires one review containing the complete target set, exact
   two consecutive dates and `shared_approval` with owner attribution/reference
   and the time that approval evidence was recorded. All targets invalidate
   together when any event facts or image bytes change. No generic recurring
   multi-date exception is inferred.
5. Run `python automation/publication_guard.py`, all tests and all renderers,
   then `python automation/audit_rendered_publication.py` and `git diff --check`.

The initial ledger includes only seven files actually viewed in this task
(eight events, including the explicitly approved Wakai two-day flyer).
Other existing images remain **unverified**, including archived images.
Merging this PR hides those images until a genuine review is added. It does
not delete source images or event facts. The CI report enumerates the hold list.

## SNS adapter contract — not connected to production yet

This repository contains no external scheduler sender. This CLI does not post,
schedule, or update a live social account. The existing external automation
must be updated separately to invoke the contract; its prompt has not been
changed by this PR. Do not report the production integration as complete.

Record the owner's approved caption in `event.social.<channel>_caption` and
`event.social.approvals.<channel>`: `caption_sha256` (UTF-8), `review_id`,
`approved_by`, and timezone-aware `approved_at`. A changed caption or image
review needs refreshed approval evidence. No production approvals are invented
by this PR.

Use a persisted state file (one serialized writer; do not discard it between
runs). Resolve the actual channel/account ID using the authorized connector.

```
python automation/social_package.py --state /persistent/social.json prepare \
  --event-id EVENT_ID --channel instagram --channel-id RESOLVED_ID \
  --days-before 14 --output /private/package.json
```

No package is emitted for unverified/cancelled media or unapproved copy. The
targeted recurring series in `config.json` use **14 days before, 18:00
Asia/Tokyo**. Other one-off sessions retain their existing 7-day policy.
The explicit two-day exception produces a single package per channel/slot.

The adapter must obey `action`: `create`, `update` with the existing external
ID, or `noop`. Before first adoption, reconcile existing remote scheduled posts
into the state or existing event schedule records. This CLI cannot discover
unresolved account identities: legacy schedule records also require a verified
`channel_id`, or a matching reconciled state record, before an update is prepared.
It cannot discover
unrecorded remote posts. Do not replace a legacy ID with a fresh post merely
because its date/copy/media changed. Ambiguous existing IDs block preparation.
An unresolved earlier request also blocks another create. Use the stable
`key` as connector idempotency key where supported. If a request times out,
query the scheduler by that key/account and reconcile before retrying.

```
python automation/social_package.py --state /persistent/social.json accept \
  --package /private/package.json --response /private/ack.json
python automation/social_package.py --state /persistent/social.json confirm \
  --package /private/package.json --response /private/readback.json
```

Acknowledgement requires `external_id`, `channel`, `channel_id` and produces
`accepted_pending_readback`, never DONE. Independently fetch the stored remote
post; do not echo request values as verification. The adapter must retrieve
its actual image and compute SHA256. Readback requires `readback: true`, a
fresh timezone-aware `fetched_at`, `external_id`, `status` (scheduled/published),
and exact `channel`, `channel_id`, `event_ids`, `publish_at`, `caption`, and
`image_sha256`. Include its public URL when available. If the provider rewrites
image bytes, exact verification fails closed until the adapter has an approved
alternative proof; do not fabricate a matching SHA. Only matching readback
and still-current event/image facts produce `confirmed`.

State and package files are operational evidence. Back up state and synchronize
external IDs across machines; local file locking is not a distributed lock.
Never run multiple unsynchronized state stores against the same social account.
