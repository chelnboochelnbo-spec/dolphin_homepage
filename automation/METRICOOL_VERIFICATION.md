# Read-only Metricool verification adapter

This draft connects Metricool GET results and downloaded media bytes to
`publication_guard` and `social_package`. It does not call create/update tools,
change automation prompts, or authorize new captions. A wire request is a
reviewable preview only. Changed remote content fails closed; it is not repaired.

Use one explicitly initialized persistent version-2 state file. Do not recreate
it between runs. The CLI serializes local writes and replaces state atomically.
The repository's initial migration contains only the two independently checked
destinations of the retained October 22 Kiraku reservation.

## Workflow

1. Fetch `origin/main`, then prepare against files whose bytes match that latest
   remote main. The adapter checks remote main before and after reconciliation.
2. Run `prepare` with a request list and persistent state.
3. Read brand settings and scheduled posts through the authorized connector.
   Read after preparation; include the entire relevant scheduling window so
   duplicate detection can work. Capture freshness is limited to five minutes.
4. Download each returned media URL, retain the actual local bytes, and build the
   capture below. Do not use claimed hashes in place of a download.
5. Run `reconcile`. Both Instagram and Facebook must match before either state
   record is committed. Re-prepare to observe `noop`.

```sh
python automation/metricool_verification.py prepare --state /persistent/social.json --input requests.json --output plan.json
python automation/metricool_verification.py reconcile --state /persistent/social.json --input plan.json --capture capture.json --output proof.json
```

Request shape:

```json
{"requests":[{"event_id":"2026-10-22_legacy-a52e331b05","days_before":14,"slot_id":"october-22-existing","brand_id":"6910064","accounts":{"instagram":"dolphin_kanazawa","facebook":"586660311198862"}}]}
```

Capture shape (values come from the actual independent reads):

```json
{"fetched_at":"ISO timestamp after prepare","brand_id":"resolved brand ID","brands":["brand objects from getBrandSettings"],"posts":["all post objects from getScheduledPosts for the relevant window"],"media":[{"url":"exact post media URL","local_path":"absolute downloaded file path","fetched_at":"ISO timestamp after GET"}]}
```

The adapter reads IDs, destinations, caption, publication time and image hash
from the provider capture. Event IDs are a local binding proved by the approved
caption/image/fact package; Metricool itself does not return event IDs. Captures
are trusted operator inputs, not cryptographically authenticated responses.

Each shared UUID yields one allowlisted preview, retaining both destinations
and the current numeric ID. It never echoes `twitterData`, creator fields,
status fields or other GET defaults. Unsupported formats or additional settings
hold the group. Missing facts/approval hold only the affected event.

## Approval migration and remaining rollout gates

Ordinary captions require the existing caption SHA, review ID, approver and
timestamp plus `source_reference` pointing to a real approval message/document.
No ordinary approval was invented or migrated: the parent has been asked for
one actual approved 14-day case. Synthetic tests exercise this path separately.
The October exception retains its narrow recorded preservation permission.

New reservations are prepared but cannot be adopted or sent by this adapter.
They require reviewed remote discovery and a trusted identity migration. Remote
updates and their post-write verification still need a production transport;
do not claim that this draft automates posting. Before enabling one, wire fresh
pre-action reads, one coalesced update and independent post-action readback of
both destinations and actual bytes, retaining pending state across failures.
Do not change automation prompts until a real ordinary approval case and these
transport gates pass. January 2 cancellation and January 16 announcement remain
separate event identities; no automation task was modified.

## Observed read-only run, 2026-10-07

- Source main: `071ab91b7e8b5e9c63b8e432e7b14be0dde49c40`.
- Brand `6910064`, numeric ID `389093625`, UUID `-5433884878909716328`.
- Scheduled October 8, 18:00 Asia/Tokyo; Instagram + Facebook.
- Actual media: 930198 bytes, SHA256
  `ba62c83f63e540a795bf94dcd5202ea5b47f147d6d26609ed607e22abf28bb25`.
- Both destinations verified; one shared preview; subsequent prepare returned
  `noop` for both; remote write count zero.
- Ordinary 14-day synthetic case passes. Actual ordinary case remains held
  until the real caption approval source is supplied.
