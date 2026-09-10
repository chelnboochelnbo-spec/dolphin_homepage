# DOLPHIN Event Automation

This directory defines the operating contract for automated event publication across the DOLPHIN website, Canva, Instagram, and Facebook.

## Single source of truth

`data/events.json` is the canonical source for event metadata and publication state.

Each event is identified by `id` in the form `YYYY-MM-DD-slug`.

## Input modes

### 1. AI flyer
Set `flyer.mode` to `canva_ai` and provide event information plus artist photo assets when available.

The automation agent must:
1. Validate the event record.
2. Generate a DOLPHIN-branded flyer in Canva.
3. Export the approved/final asset.
4. Save the public flyer to the GitHub repository using the naming rule `flyer_YYYYMMDD.<ext>` unless a collision requires a suffix.
5. Publish the event to the website.
6. Generate Instagram and Facebook copy.
7. Schedule social posts according to `automation/social-policy.json`.
8. Record resulting design/post/deployment state back into `data/events.json`.

### 2. Human-made flyer
Set `flyer.mode` to `human` and provide the finished image.

The automation agent must skip Canva generation, store the supplied flyer in GitHub, then perform the same website and social publishing steps.

## Event types

`type` must be one of:
- `LIVE`
- `SESSION`
- `LIVE&SESSION`

The website must display this type as a visible event mark.

## Website publication

Current production files are static HTML/CSS/JS.
Until the legacy HTML is fully migrated to generated pages, the agent must update all relevant views consistently:
- `index.html`: next three upcoming events
- `schedule.html`: complete schedule
- `archive.html`: past-event archive when applicable
- `artists-data.js`: artist history when applicable

A website update is not complete until the GitHub commit receives a successful Vercel status.

## Social publication

The agent generates platform-specific copy rather than posting the same text verbatim everywhere.

Instagram:
- concise event hook
- date/time
- lineup
- charge
- reservation CTA
- hashtags

Facebook:
- slightly fuller event description
- date/time
- lineup
- charge
- reservation CTA

Scheduling rules come from `automation/social-policy.json` and may be overridden per event with `social.override_schedule`.

## Safety rules

- Never commit secrets, access tokens, passwords, or API keys.
- Prefer a feature branch + pull request for structural changes.
- Routine event additions may be committed to the production workflow only after the automation format has been verified.
- Do not overwrite a human-made flyer with an AI-generated flyer.
- Do not publish an event marked `draft`.
- Do not schedule social posts before the flyer is final.
- If required event fields are missing, stop only that event and report the missing fields.

## Status lifecycle

`status` values:
- `draft`
- `ready`
- `published`
- `completed`
- `cancelled`

`publication.website.status` values:
- `pending`
- `deployed`
- `failed`

`publication.social.instagram.status` and `publication.social.facebook.status` values:
- `pending`
- `scheduled`
- `published`
- `failed`

## Minimum input for a normal event

- date
- title
- type
- start time
- performers or a description
- charge
- flyer mode

Open time, reservation notes, copy notes, and artist photos are optional unless needed for the specific event.
