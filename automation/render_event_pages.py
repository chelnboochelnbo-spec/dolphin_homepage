from __future__ import annotations

import json
import shutil
from datetime import date
from html import escape
from pathlib import Path

from event_utils import event_end_date, event_is_past, event_type_label

ROOT = Path(__file__).resolve().parents[1]
EVENTS_FILE = ROOT / "data" / "events.json"
ARTISTS_FILE = ROOT / "data" / "artists.json"
EVENTS_DIR = ROOT / "events"
BASE_URL = "https://www.bardolphin-kanazawa.com"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def root_asset(path: str) -> str:
    if not path:
        return ""
    if path.startswith(("http://", "https://", "/")):
        return path
    return "/" + path.lstrip("/")


def event_flyer_path(event: dict) -> str:
    path = (event.get("flyer") or {}).get("github_path") or ""
    if event.get("legacy_imported") and path.lstrip("/") == "logo_new.png":
        return ""
    return root_asset(path)


def event_url(event: dict) -> str:
    return f"/events/{event['id']}/"


def performer_name(performer: dict) -> str:
    return " ".join(filter(None, [performer.get("instrument"), performer.get("name")])).strip()


def json_ld(event: dict, artists_by_id: dict[str, dict]) -> str:
    end = event_end_date(event)
    start_date = event["date"] + (f"T{event['start']}:00+09:00" if event.get("start") else "")
    payload = {
        "@context": "https://schema.org",
        "@type": "MusicEvent",
        "name": event["title"],
        "url": f"{BASE_URL}{event_url(event)}",
        "startDate": start_date,
        "endDate": end.isoformat(),
        "eventStatus": "https://schema.org/EventCompleted" if event_is_past(event) else "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {
            "@type": "MusicVenue",
            "name": "Jazz & Bar DOLPHIN",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "金沢市",
                "addressRegion": "石川県",
                "postalCode": "920-0981",
                "streetAddress": "片町2-13-11 ミリオンビル4階",
                "addressCountry": "JP"
            }
        }
    }
    if event.get("description"):
        payload["description"] = event["description"]
    flyer = event_flyer_path(event)
    if flyer:
        payload["image"] = [f"{BASE_URL}{flyer}"]
    performers = []
    for performer in event.get("performers") or []:
        item = {"@type": "Person", "name": performer.get("name") or performer_name(performer)}
        artist_id = performer.get("artist_id")
        if artist_id and artist_id in artists_by_id:
            item["url"] = f"{BASE_URL}/artists/{artist_id}/"
        performers.append(item)
    if performers:
        payload["performer"] = performers
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")


def render(event: dict, artists_by_id: dict[str, dict]) -> str:
    start = date.fromisoformat(event["date"])
    end = event_end_date(event)
    is_past = event_is_past(event)
    canonical = f"{BASE_URL}{event_url(event)}"
    title = f"{event['title']} | Jazz & Bar DOLPHIN 金沢"
    fallback = f"{start.year}年{start.month}月{start.day}日、Jazz & Bar DOLPHIN（金沢）で開催{'した' if is_past else '予定の'}「{event['title']}」。"
    description = event.get("description") or fallback
    flyer = event_flyer_path(event)
    og_image = f"{BASE_URL}{flyer}" if flyer else f"{BASE_URL}/logo_new.png"

    if flyer:
        media = f'<img class="event-flyer" src="{escape(flyer, quote=True)}" alt="{escape(event["title"], quote=True)} Flyer">'
    else:
        media = '<div class="event-flyer-empty">NO IMAGE</div>'

    performers = []
    for performer in event.get("performers") or []:
        label = performer_name(performer)
        artist_id = performer.get("artist_id")
        if artist_id and artist_id in artists_by_id:
            performers.append(f'<li><a href="/artists/{escape(artist_id, quote=True)}/">{escape(label)}</a></li>')
        else:
            performers.append(f'<li>{escape(label)}</li>')
    performer_html = "".join(performers) or "<li>出演者情報は未登録です。</li>"

    date_text = f"{start.year}.{start.month:02d}.{start.day:02d}"
    if end != start:
        date_text += f" — {end.year}.{end.month:02d}.{end.day:02d}"

    meta = []
    if event.get("open"):
        meta.append(f"OPEN {event['open']}")
    if event.get("start"):
        meta.append(f"START {event['start']}")
    if event.get("charge"):
        meta.append(event["charge"])

    archive_data = event.get("archive") or {}
    extras = []
    if archive_data.get("comment"):
        extras.append(f'<section class="event-extra"><h2>NOTE</h2><p>{escape(archive_data["comment"])}</p></section>')
    if archive_data.get("setlist"):
        items = "".join(f"<li>{escape(str(item))}</li>" for item in archive_data["setlist"])
        extras.append(f'<section class="event-extra"><h2>SETLIST</h2><ol>{items}</ol></section>')
    external = []
    for label, url in (("YOUTUBE", archive_data.get("youtube")), ("INSTAGRAM", archive_data.get("instagram"))):
        if url:
            external.append(f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>')
    for item in archive_data.get("external_links") or []:
        if isinstance(item, dict) and item.get("url"):
            external.append(f'<a href="{escape(item["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{escape(item.get("label") or "LINK")}</a>')
    if external:
        extras.append(f'<section class="event-extra"><h2>LINKS</h2><div class="event-links">{"".join(external)}</div></section>')

    action = '<a class="event-action" href="/archive/">BACK TO LIVE ARCHIVE</a>' if is_past else '<a class="event-action" href="/#reservation">RESERVATION</a>'
    status = "PAST EVENT" if is_past else "UPCOMING"
    description_html = f'<p class="event-description">{escape(event.get("description") or "")}</p>' if event.get("description") else ""
    extras_html = "".join(extras)

    lines = [
        '<!-- GENERATED: DOLPHIN EVENT -->',
        '<!DOCTYPE html>',
        '<html lang="ja">',
        '<head>',
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'<title>{escape(title)}</title>',
        f'<meta name="description" content="{escape(description, quote=True)}">',
        f'<link rel="canonical" href="{canonical}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:title" content="{escape(title, quote=True)}">',
        f'<meta property="og:description" content="{escape(description, quote=True)}">',
        f'<meta property="og:url" content="{canonical}">',
        f'<meta property="og:image" content="{og_image}">',
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link href="https://fonts.googleapis.com/css2?family=Josefin+Sans:ital,wght@0,300;0,400;0,600;0,700;1,300;1,400&family=Noto+Sans+JP:wght@300;400;500&family=Lato:wght@300;400&display=swap" rel="stylesheet">',
        '<link rel="stylesheet" href="/style.css">',
        '<link rel="stylesheet" href="/event-types.css">',
        '<link rel="stylesheet" href="/event-page.css">',
        '<link rel="icon" type="image/png" href="/logo_new.png">',
        f'<script type="application/ld+json">{json_ld(event, artists_by_id)}</script>',
        '</head>',
        '<body class="event-page">',
        '<nav class="main-nav">',
        '<div class="logo"><a href="/">DOLPHIN</a></div>',
        '<div class="nav-right"><ul class="nav-links">',
        '<li><a href="/">Home</a></li><li><a href="/schedule.html">Schedule</a></li><li><a href="/artists/">Artists</a></li><li><a href="/archive/">Archive</a></li>',
        '</ul><button class="menu-toggle" aria-label="Toggle Menu"><span class="bar"></span><span class="bar"></span><span class="bar"></span></button></div>',
        '</nav>',
        '<main class="event-detail">',
        '<div class="event-detail-grid">',
        f'<div class="event-media">{media}</div>',
        '<div class="event-copy">',
        f'<div class="event-status-row"><span class="event-type-inline">{event_type_label(event)}</span><span class="event-status">{status}</span></div>',
        f'<p class="event-date">{date_text}</p>',
        f'<h1>{escape(event["title"])}</h1>',
        f'<p class="event-meta">{escape(" / ".join(meta))}</p>',
        f'<ul class="event-performers">{performer_html}</ul>',
    ]
    if description_html:
        lines.append(description_html)
    lines.extend([action, '</div>', '</div>'])
    if extras_html:
        lines.append(extras_html)
    lines.extend(['</main>', '<script src="/script.js"></script>', '</body>', '</html>'])
    return "\n".join(lines)


def main() -> None:
    events = [event for event in load(EVENTS_FILE).get("events", []) if event.get("status") != "draft"]
    artists = load(ARTISTS_FILE).get("artists", [])
    artists_by_id = {artist["id"]: artist for artist in artists}
    EVENTS_DIR.mkdir(exist_ok=True)

    valid = {event["id"] for event in events}
    for child in EVENTS_DIR.iterdir():
        if child.is_dir() and child.name not in valid:
            marker = child / "index.html"
            if marker.exists() and "GENERATED: DOLPHIN EVENT" in marker.read_text(encoding="utf-8-sig"):
                shutil.rmtree(child)

    for event in events:
        target = EVENTS_DIR / event["id"]
        target.mkdir(exist_ok=True)
        (target / "index.html").write_text(render(event, artists_by_id), encoding="utf-8")


if __name__ == "__main__":
    main()
