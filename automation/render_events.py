from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
EVENTS_FILE = ROOT / "data" / "events.json"
INDEX_FILE = ROOT / "index.html"
SCHEDULE_FILE = ROOT / "schedule.html"
ARCHIVE_FILE = ROOT / "archive.html"

MONTH_IDS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
WEEKDAYS = ["mon.", "tue.", "wed.", "thu.", "fri.", "sat.", "sun."]
WEEKDAYS_UPPER = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def load_events() -> list[dict]:
    payload = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    events = payload.get("events", [])
    seen = set()
    for event in events:
        for key in ("id", "date", "title", "type", "status", "flyer"):
            if key not in event:
                raise ValueError(f"Event missing required field: {key}")
        if event["id"] in seen:
            raise ValueError(f"Duplicate event id: {event['id']}")
        seen.add(event["id"])
        date.fromisoformat(event["date"])
    return events


def performer_text(event: dict) -> str:
    parts = []
    for p in event.get("performers") or []:
        name = p.get("name") or ""
        inst = p.get("instrument") or ""
        if name:
            parts.append(f"{inst} {name}".strip())
    return " / ".join(parts)


def time_text(event: dict) -> str:
    bits = []
    if event.get("open"):
        bits.append(f"Open {event['open']}")
    if event.get("start"):
        bits.append(f"Start {event['start']}")
    return " / ".join(bits)


def flyer_path(event: dict) -> str:
    flyer = event.get("flyer") or {}
    return flyer.get("github_path") or "logo_new.png"


def render_schedule_article(event: dict) -> str:
    d = date.fromisoformat(event["date"])
    performers = performer_text(event)
    time = time_text(event)
    charge = event.get("charge") or ""
    badge = escape(event["type"])
    reserve_url = event.get("reservation_url") or "index.html#reservation"
    details = []
    if time:
        details.append(f'                                    <div class="detail-item"><i class="far fa-clock"></i>{escape(time)}</div>')
    if performers:
        details.append(f'                                    <div class="detail-item"><i class="fas fa-users"></i>{escape(performers)}</div>')
    if charge:
        details.append(f'                                    <div class="lineup-price">{escape(charge)}</div>')
    detail_html = "\n".join(details)
    return f'''                    <article class="lineup-item" data-date="{event['date']}" data-event-id="{escape(event['id'])}">
                        <div class="lineup-date">{d.year} {d.month}.{d.day:02d}<span class="weekday">{WEEKDAYS[d.weekday()]}</span></div>
                        <div class="lineup-body">
                            <img src="{escape(flyer_path(event))}" alt="{escape(event['title'])} Flyer" class="lineup-flyer-thumb" onclick="window.open(this.src)">
                            <div class="lineup-info">
                                <span class="lineup-badge">{badge}</span>
                                <h3 class="lineup-artist">{escape(event['title'])}</h3>
                                <div class="lineup-details">
{detail_html}
                                </div>
                                <a href="{escape(reserve_url)}" class="lineup-reserve-btn">RESERVATION</a>
                            </div>
                        </div>
                    </article>'''


def render_archive_article(event: dict) -> str:
    d = date.fromisoformat(event["date"])
    performers = performer_text(event)
    time = time_text(event)
    detail_parts = []
    if time:
        detail_parts.append(f'                        <div class="detail-item"><i class="far fa-clock"></i>{escape(time)}</div>')
    detail_parts.append(f'                        <h3 class="schedule-artist">{escape(event["title"])}</h3>')
    if performers:
        detail_parts.append(f'                        <div class="detail-item"><i class="fas fa-users"></i>{escape(performers)}</div>')
    details = "\n".join(detail_parts)
    month_en = MONTH_IDS[d.month - 1].upper()
    return f'''            <article class="schedule-item" data-date="{event['date']}" data-event-id="{escape(event['id'])}">
                <div class="schedule-date">
                    <span class="day">{d.day}</span>
                    <span class="weekday">{WEEKDAYS_UPPER[d.weekday()]}</span>
                    <span class="month">{d.month}月 {month_en}</span>
                </div>
                <div class="schedule-info">
                    <div class="lineup-details">
{details}
                    </div>
                </div>
            </article>'''


def remove_auto_article(html: str, event_id: str, class_name: str) -> str:
    pattern = re.compile(
        rf'\s*<article class="{re.escape(class_name)}"[^>]*data-event-id="{re.escape(event_id)}"[^>]*>.*?</article>\s*',
        re.S,
    )
    return pattern.sub("\n", html)


def upsert_schedule_event(html: str, event: dict) -> str:
    html = remove_auto_article(html, event["id"], "lineup-item")
    d = date.fromisoformat(event["date"])
    month_id = MONTH_IDS[d.month - 1]
    section_start = html.find(f'<section id="{month_id}" class="lineup-month-group">')
    if section_start < 0:
        raise ValueError(f"Could not find month section: {month_id}")
    section_end = html.find("</section>", section_start)
    if section_end < 0:
        raise ValueError(f"Could not find end of month section: {month_id}")

    section = html[section_start:section_end]
    new_article = render_schedule_article(event)

    candidates = []
    for m in re.finditer(r'<article class="lineup-item"[^>]*data-date="(\d{4}-\d{2}-\d{2})"', section):
        candidates.append((m.start(), m.group(1)))

    insert_pos_rel = None
    for pos, existing_date in candidates:
        if existing_date > event["date"]:
            insert_pos_rel = pos
            break

    if insert_pos_rel is None:
        last_div = section.rfind("</div>")
        if last_div < 0:
            raise ValueError(f"Could not find lineup-list closing div for {month_id}")
        insert_pos = section_start + last_div
        prefix = "\n" if not html[:insert_pos].endswith("\n") else ""
        return html[:insert_pos] + prefix + new_article + "\n" + html[insert_pos:]

    insert_pos = section_start + insert_pos_rel
    return html[:insert_pos] + new_article + "\n\n" + html[insert_pos:]


def upsert_archive_event(html: str, event: dict) -> str:
    html = remove_auto_article(html, event["id"], "schedule-item")
    marker = '<div class="archive-list">'
    pos = html.find(marker)
    if pos < 0:
        raise ValueError("Could not find archive-list")
    pos += len(marker)
    return html[:pos] + "\n" + render_archive_article(event) + "\n" + html[pos:]


def rebuild_home_preview(index_html: str, schedule_html: str) -> str:
    today = date.today().isoformat()
    articles = []
    for m in re.finditer(r'(<article class="lineup-item"[^>]*data-date="(\d{4}-\d{2}-\d{2})"[^>]*>.*?</article>)', schedule_html, re.S):
        if m.group(2) >= today:
            articles.append((m.group(2), m.group(1)))
    articles.sort(key=lambda x: x[0])
    preview = "\n\n".join(article for _, article in articles[:3])

    pattern = re.compile(
        r'(<div class="lineup-list" style="margin-bottom: 3rem;">)(.*?)(\n\s*</div>\n\s*<div style="text-align: center;">)',
        re.S,
    )
    if not pattern.search(index_html):
        raise ValueError("Could not find home lineup preview block")
    return pattern.sub(lambda m: m.group(1) + "\n\n" + preview + m.group(3), index_html, count=1)


def main() -> None:
    events = load_events()
    schedule_html = SCHEDULE_FILE.read_text(encoding="utf-8")
    archive_html = ARCHIVE_FILE.read_text(encoding="utf-8-sig")

    today = date.today()
    for event in sorted(events, key=lambda e: e["date"]):
        event_date = date.fromisoformat(event["date"])
        is_ready = event["status"] in {"ready", "published", "archived"}
        if not is_ready:
            continue
        if event_date < today or event["status"] == "archived":
            schedule_html = remove_auto_article(schedule_html, event["id"], "lineup-item")
            archive_html = upsert_archive_event(archive_html, event)
        else:
            archive_html = remove_auto_article(archive_html, event["id"], "schedule-item")
            schedule_html = upsert_schedule_event(schedule_html, event)

    index_html = INDEX_FILE.read_text(encoding="utf-8")
    index_html = rebuild_home_preview(index_html, schedule_html)

    SCHEDULE_FILE.write_text(schedule_html, encoding="utf-8")
    INDEX_FILE.write_text(index_html, encoding="utf-8")
    ARCHIVE_FILE.write_text(archive_html, encoding="utf-8")


if __name__ == "__main__":
    main()
