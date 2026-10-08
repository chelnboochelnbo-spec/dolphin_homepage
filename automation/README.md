# DOLPHIN Event Automation

## Purpose
This directory defines the operating contract for automating event publication across the DOLPHIN website, Canva, Instagram, and Facebook.

## Single source of truth
New events are registered in `data/events.json` and must conform to `automation/event.schema.json`.

Store-wide facts and the day-by-day operating state are registered in `data/operations.json`. The homepage Tonight panel, home calendar, and full schedule share the operating policy. From 2026-10-08, Sunday is normally closed; if consecutive Japanese public holidays follow Sunday, the closure moves to their final day. Published events remain open exceptions. Explicit date overrides take precedence, including a confirmed closure or private booking. Standard hours remain 19:00–01:00 the following day.

For an irregular closure or private booking, add the date before publication:

```json
"2026-09-30": { "state": "closed", "note": "臨時休業" }
```

Allowed override states are `closed`, `private`, `open`, and `bar`. Explicit `open` / `bar` overrides can open a normally closed date. Do not add routine Sunday closures to `overrides`; they are calculated so newly published events remain visible. Do not cancel an event merely because it falls on a normal closure date.

The official Cabinet Office holiday data is embedded in `data/operations.json` under `closure_rule.holiday_calendar`, verified from https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html on 2026-10-08 and covering 2026–2027. It includes substitute holidays and citizens’ holidays. Update and verify this data before extending publication into 2028; the renderers refuse to guess dates beyond verified coverage, and Tonight shows an unconfirmed state. The policy does not rewrite dates before its effective date.

Existing legacy events in `index.html` / `schedule.html` are preserved during migration. New automated events are managed from `data/events.json`.

## Input flow
A new event starts from one compact instruction containing as much of the following as is known:

- date
- title
- type: LIVE / SESSION / LIVE&SESSION
- open / start
- charge
- performers
- description
- flyer mode: `canva_ai` or `human`
- importance: `normal` or `important`

Missing non-critical fields may remain null. Do not invent factual event information.

## Publication verification

All website media and SNS packages must pass [PUBLICATION_GUARD.md](PUBLICATION_GUARD.md). A ready flag or filename is not verification. Unverified images stay hidden while event text remains.

## Flyer branches

### Canva AI
When `flyer.mode = canva_ai`:
1. Use the event information and supplied artist photos as visual inputs.
2. Generate a 1080x1350 (4:5) promotional design in Canva.
3. Keep DOLPHIN branding restrained and consistent; avoid random style drift.
4. Save the final design ID to `flyer.canva_design_id`.
5. Export the approved image and save it under `assets/flyers/` using the configured filename convention.
6. Set `flyer.status = ready` and `flyer.github_path`.

### Human-made flyer
When `flyer.mode = human`:
1. Use the supplied final flyer without redesigning it unless explicitly requested.
2. Save a web-safe copy under `assets/flyers/`.
3. Set `flyer.status = ready` and `flyer.github_path`.

## Website publishing
For an event with `status = ready` and a ready flyer:
1. Add/update the event in the full schedule.
2. Ensure the event type marker is shown as LIVE / SESSION / LIVE&SESSION.
3. Update the home-page upcoming lineup when the event belongs in the next three upcoming events.
4. Preserve chronological order.
5. Use the event's flyer path.
6. Commit the content update to `main` only after validation.
7. Confirm Vercel deployment status is successful.
8. Set event `status = published`.

Structural changes to templates, CSS, JavaScript, or the automation architecture must use a feature branch and pull request rather than a direct `main` update.

## Social publishing
Default publication rules are stored in `automation/config.json`.

- normal LIVE: 30 and 7 days before the event
- important LIVE: 30, 14 and 3 days before the event
- Approved recurring series: 14 days before, at 18:00 Asia/Tokyo (exact title allowlist in config)
- Other one-off SESSION: 7 days before the event
- default publish time: 18:00 Asia/Tokyo

For each planned slot:
1. Generate a platform-appropriate Instagram caption.
2. Generate a platform-appropriate Facebook caption.
3. Reuse the final flyer unless a platform-specific crop is needed.
4. Schedule each post through the connected social scheduler.
5. Record scheduled state and external IDs in the event object when available.

Do not schedule a new social post before the flyer is visually verified. HP-only migration baselines do not grant SNS permission. The frozen October Kiraku exception only preserves its identified existing reservation. Use the guarded SNS package and readback contract; this repository has no connected production sender.

## Archive lifecycle
After the event date has passed:
1. Mark the event as archived.
2. Remove it from upcoming/home lineup.
3. Preserve it in the website archive.
4. Update artist appearance history when the performer exists in the artist database.
5. Never delete the original event record from `data/events.json`.

## Safety rules
- Never fabricate dates, prices, performer names, or reservation information.
- Never overwrite a human-created flyer with AI output unless explicitly requested.
- Keep GitHub as the authoritative website source.
- Preserve rollback through commits.
- Verify Vercel deployment after production changes.
- If a social connector is unavailable, stop at `planned` rather than pretending a post is scheduled.
