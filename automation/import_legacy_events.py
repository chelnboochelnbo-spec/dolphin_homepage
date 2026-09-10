from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_FILE = ROOT / "schedule.html"
EVENTS_FILE = ROOT / "data" / "events.json"
ARTISTS_FILE = ROOT / "data" / "artists.json"


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def normalize_name(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").strip().casefold()


def classify_title(title: str) -> str:
    normalized = title.casefold().replace("＆", "&").replace("＋", "+")
    has_live = "live" in normalized or "ライブ" in normalized
    has_session = "session" in normalized or "セッション" in normalized
    if has_live and has_session:
        return "live_session"
    if has_session or " jam" in f" {normalized}" or "jam " in normalized or normalized.endswith("jam"):
        return "session"
    if "workshop" in normalized or "ワークショップ" in normalized:
        return "session"
    return "live"


def stable_id(event_date: str, title: str) -> str:
    digest = hashlib.sha1(f"{event_date}|{title}".encode("utf-8")).hexdigest()[:10]
    return f"{event_date}_legacy-{digest}"


def parse_time(text: str, label: str) -> str | None:
    match = re.search(rf"\b{label}\s*(\d{{1,2}}:\d{{2}})", text, re.I)
    return match.group(1) if match else None


def parse_end_date(article: str, start_date: str) -> str | None:
    date_block = re.search(r'<div class="lineup-date">(.*?)</div>', article, re.S)
    if not date_block:
        return None
    text = clean_text(date_block.group(1))
    match = re.search(r"-\s*(\d{1,2})\.(\d{1,2})", text)
    if not match:
        return None
    start = date.fromisoformat(start_date)
    month, day = int(match.group(1)), int(match.group(2))
    year = start.year + (1 if month < start.month else 0)
    try:
        end = date(year, month, day)
    except ValueError:
        return None
    return end.isoformat() if end >= start else None


def parse_performers(article: str, artist_ids_by_name: dict[str, str]) -> list[dict]:
    match = re.search(
        r'<div class="detail-item">\s*<i class="fas fa-users"></i>(.*?)</div>',
        article,
        re.S,
    )
    if not match:
        return []
    text = clean_text(match.group(1))
    if not text:
        return []
    performers = []
    for raw in re.split(r"\s*/\s*", text):
        raw = raw.strip()
        if not raw:
            continue
        inst = ""
        name = raw
        m = re.match(r"^(Pf|Piano|Gt|Guitar|Ba|Bass|Dr|Drums|Sax|Vo|Vocal|Tp|Trumpet|Tb|Fl|Perc|DJ|講師)\s*[:：]?\s*(.+)$", raw, re.I)
        if m:
            inst, name = m.group(1), m.group(2).strip()
        performer = {"instrument": inst, "name": name}
        artist_id = artist_ids_by_name.get(normalize_name(name))
        if artist_id:
            performer["artist_id"] = artist_id
        performers.append(performer)
    return performers


def parse_article(article: str, artist_ids_by_name: dict[str, str]) -> dict | None:
    date_match = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', article)
    title_match = re.search(r'<h3 class="lineup-artist">(?:<a[^>]*>)?(.*?)(?:</a>)?</h3>', article, re.S)
    if not date_match or not title_match:
        return None
    event_date = date_match.group(1)
    title = clean_text(title_match.group(1))
    if not title:
        return None

    event_id_match = re.search(r'data-event-id="([^"]+)"', article)
    event_id = event_id_match.group(1) if event_id_match else stable_id(event_date, title)

    type_match = re.search(r'data-event-type="(live|session|live_session)"', article)
    event_type = type_match.group(1) if type_match else classify_title(title)

    img_match = re.search(r'<img[^>]+src="([^"]+)"[^>]*class="lineup-flyer-thumb"', article, re.S)
    flyer_path = unescape(img_match.group(1)).strip() if img_match else ""

    clock_match = re.search(
        r'<div class="detail-item">\s*<i class="far fa-clock"></i>(.*?)</div>',
        article,
        re.S,
    )
    time_text = clean_text(clock_match.group(1)) if clock_match else ""

    price_match = re.search(r'<div class="lineup-price">(.*?)</div>', article, re.S)
    charge = clean_text(price_match.group(1)) if price_match else ""

    intro_match = re.search(r'<p class="lineup-intro">(.*?)</p>', article, re.S)
    description = clean_text(intro_match.group(1)) if intro_match else ""

    reserve_match = re.search(r'<a href="([^"]+)" class="lineup-reserve-btn"', article)
    reservation_url = unescape(reserve_match.group(1)).strip() if reserve_match else ""

    event = {
        "id": event_id,
        "date": event_date,
        "title": title,
        "event_type": event_type,
        "status": "published",
        "open": parse_time(time_text, "Open"),
        "start": parse_time(time_text, "Start"),
        "charge": charge,
        "performers": parse_performers(article, artist_ids_by_name),
        "description": description,
        "reservation_url": reservation_url,
        "flyer": {
            "mode": "human",
            "status": "ready" if flyer_path else "missing",
            "source": "legacy_schedule_migration",
            "github_path": flyer_path,
            "canva_design_id": None
        },
        "archive": {
            "gallery": [],
            "setlist": [],
            "comment": "",
            "youtube": "",
            "instagram": "",
            "external_links": []
        },
        "legacy_imported": True
    }
    end_date = parse_end_date(article, event_date)
    if end_date:
        event["end_date"] = end_date
    return event


def inject_event_id(article: str, event: dict) -> str:
    opening = re.match(r'(<article class="lineup-item"[^>]*)(>)', article, re.S)
    if not opening:
        return article
    attrs = opening.group(1)
    if 'data-event-id="' not in attrs:
        attrs += f' data-event-id="{event["id"]}"'
    if 'data-event-type="' not in attrs:
        attrs += f' data-event-type="{event["event_type"]}"'
    return attrs + ">" + article[opening.end():]


def main() -> None:
    schedule_html = SCHEDULE_FILE.read_text(encoding="utf-8-sig")
    artists_payload = json.loads(ARTISTS_FILE.read_text(encoding="utf-8-sig"))
    artist_ids_by_name = {
        normalize_name(artist.get("artist_name", "")): artist["id"]
        for artist in artists_payload.get("artists", [])
        if artist.get("artist_name") and artist.get("id")
    }

    current_payload = json.loads(EVENTS_FILE.read_text(encoding="utf-8-sig")) if EVENTS_FILE.exists() else {"schema_version": 2, "events": []}
    existing_events = current_payload.get("events", [])
    by_id = {event["id"]: event for event in existing_events}
    by_key = {(event.get("date"), normalize_name(event.get("title", ""))): event for event in existing_events}

    pattern = re.compile(r'<article class="lineup-item"[^>]*>.*?</article>', re.S)
    migrated = []
    replacements = []
    for match in pattern.finditer(schedule_html):
        article = match.group(0)
        event = parse_article(article, artist_ids_by_name)
        if not event:
            continue
        key = (event["date"], normalize_name(event["title"]))
        existing = by_id.get(event["id"]) or by_key.get(key)
        if existing:
            event = existing
        else:
            existing_events.append(event)
            by_id[event["id"]] = event
            by_key[key] = event
            migrated.append(event["id"])
        updated_article = inject_event_id(article, event)
        if updated_article != article:
            replacements.append((match.start(), match.end(), updated_article))

    for start, end, replacement in reversed(replacements):
        schedule_html = schedule_html[:start] + replacement + schedule_html[end:]

    existing_events.sort(key=lambda item: (item.get("date", ""), item.get("title", "")))
    payload = {"schema_version": 2, "events": existing_events}
    EVENTS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SCHEDULE_FILE.write_text(schedule_html, encoding="utf-8")
    print(f"Migrated {len(migrated)} legacy schedule events; total structured events: {len(existing_events)}")


if __name__ == "__main__":
    main()
