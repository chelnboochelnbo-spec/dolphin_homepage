# DOLPHIN Website Editing Guide

The website is a static HTML/CSS/JS site deployed from GitHub to Vercel. Structured event and artist data should be updated instead of hand-editing generated content.

## 1. EVENT database: schedule and LIVE ARCHIVE use the same record

`data/events.json` is the single source of truth for events.

Do not copy an event into a separate archive data file after it ends.

Lifecycle in Japan time (`Asia/Tokyo`):

- While `end_date` (or `date` when no `end_date` exists) is today or later → LIVE SCHEDULE
- After the entire local event day has ended → LIVE ARCHIVE
- The permanent event URL remains `/events/<event-id>/` before and after the event

The content pipeline runs automatically at approximately 03:30 JST each day, after DOLPHIN's late-night operating hours, so the previous event day is moved from the schedule view to the archive view without manual work.

## 2. New events

Add or update records in `data/events.json`.

Required core fields:

- `id`: `YYYY-MM-DD_slug`
- `date`: `YYYY-MM-DD`
- `title`
- `event_type`: `live`, `session`, or `live_session`
- `status`
- `flyer`

Optional fields used by the archive include:

- `end_date` for multi-day events
- `archive.gallery`
- `archive.setlist`
- `archive.comment`
- `archive.youtube`
- `archive.instagram`
- `archive.external_links`

Unknown archive information should stay empty. Never generate a fake photo because an event has no image.

UI labels are generated automatically:

- `live` → `LIVE`
- `session` → `SESSION`
- `live_session` → `LIVE & SESSION`

For performers who have an ARTISTS ARCHIVE page, add `artist_id` to the performer entry. Example:

```json
{
  "instrument": "Piano",
  "name": "Example Artist",
  "artist_id": "example-artist"
}
```

The content pipeline then links the schedule/event page to the artist page automatically.

## 3. Updating a past event

Past events remain editable because the archive is a view of the same EVENT record.

For example, after a live finishes you may add photos, a setlist, comment, YouTube URL, Instagram URL, or other links to the existing event in `data/events.json`. The next content pipeline run updates the archive and the same permanent `/events/<event-id>/` page.

## 4. New artists / returning artists

The source of truth is `data/artists.json`.

Do not create a new record when the same artist already exists. Add a new appearance to the existing artist or connect the new event with `artist_id`.

Core fields:

- `id`
- `artist_name`
- `artist_name_en`
- `instrument`
- `photo`
- `profile`
- `website`
- `instagram`
- `youtube`
- `appearances`

Unknown information must stay blank. Do not invent artist biographies, links, or photos.

Artist photos may be stored under `/artists/` and referenced as e.g. `artists/example-artist.jpg`.

## 5. Generated pages

GitHub Actions runs:

- `automation/render_events.py` — current/future schedule
- `automation/render_artists.py` — artist archive
- `automation/render_event_pages.py` — permanent event pages and MusicEvent SEO data
- `automation/render_archive.py` — past event view from the same EVENT database

It generates or updates:

- Home page upcoming lineup
- `schedule.html`
- `/archive/`
- compatibility URL `archive.html`
- `/artists/`
- `/artists/<artist-slug>/`
- `/events/<event-id>/`

Structural code changes should use a feature branch and Pull Request. Routine structured event/artist content can be updated through the data files.

## 6. Flyers

New automated flyer files should use `assets/flyers/` and the naming convention defined in `automation/config.json`.

Legacy flyers remain at repository root for compatibility.

## 7. Menu / theme

Menu content remains in `index.html` for now. Global visual variables are in `style.css` under `:root`.

Do not modify generated HTML to change event or artist facts; update the structured data and let the pipeline regenerate it.
