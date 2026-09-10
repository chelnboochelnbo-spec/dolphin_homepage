# DOLPHIN Website Editing Guide

The website is a static HTML/CSS/JS site deployed from GitHub to Vercel. Structured event and artist data should be updated instead of hand-editing generated content.

## 1. New events

Add or update records in `data/events.json`.

Required core fields:

- `id`: `YYYY-MM-DD_slug`
- `date`: `YYYY-MM-DD`
- `title`
- `event_type`: `live`, `session`, or `live_session`
- `status`
- `flyer`

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

## 2. New artists / returning artists

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

## 3. Generated pages

GitHub Actions runs:

- `automation/render_events.py`
- `automation/render_artists.py`

It generates or updates:

- Home page upcoming lineup
- `schedule.html`
- `archive.html`
- `/artists/`
- `/artists/<artist-slug>/`
- `/events/<event-id>/`

Structural code changes should use a feature branch and Pull Request. Routine structured event/artist content can be updated through the data files.

## 4. Flyers

New automated flyer files should use `assets/flyers/` and the naming convention defined in `automation/config.json`.

Legacy flyers remain at repository root for compatibility.

## 5. Menu / theme

Menu content remains in `index.html` for now. Global visual variables are in `style.css` under `:root`.

Do not modify generated HTML to change event or artist facts; update the structured data and let the pipeline regenerate it.
