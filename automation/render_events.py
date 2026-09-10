from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from html import escape

from event_utils import current_jst_date, event_end_date, event_is_past, event_type_label, normalize_event_type

ROOT = Path(__file__).resolve().parents[1]
EVENTS_FILE = ROOT / "data" / "events.json"
INDEX_FILE = ROOT / "index.html"
SCHEDULE_FILE = ROOT / "schedule.html"

MONTH_IDS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
WEEKDAYS = ["mon.", "tue.", "wed.", "thu.", "fri.", "sat.", "sun."]
DETAIL_ICONS = {
    "clock": "far fa-clock",
    "users": "fas fa-users",
    "utensils": "fas fa-utensils",
    "info": "fas fa-circle-info",
}


def load_events() -> list[dict]:
    payload = json.loads(EVENTS_FILE.read_text(encoding="utf-8-sig"))
    events = payload.get("events", [])
    seen = set()
    for event in events:
        for key in ("id", "date", "title", "status", "flyer"):
            if key not in event:
                raise ValueError(f"Event missing required field: {key}")
        normalize_event_type(event)
        if event["id"] in seen:
            raise ValueError(f"Duplicate event id: {event['id']}")
        seen.add(event["id"])
        start = date.fromisoformat(event["date"])
        end = event_end_date(event)
        if end < start:
            raise ValueError(f"end_date is before date for {event['id']}")
    return events


def performer_html(event: dict) -> str:
    parts = []
    for performer in event.get("performers") or []:
        name = performer.get("name") or ""
        instrument = performer.get("instrument") or ""
        if not name:
            continue
        label = escape(f"{instrument} {name}".strip())
        artist_id = performer.get("artist_id")
        if artist_id:
            parts.append(f'<a class="performer-link" href="/artists/{escape(artist_id, quote=True)}/">{label}</a>')
        else:
            parts.append(label)
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
    return flyer.get("github_path") or ""


def event_page_url(event: dict) -> str:
    return f"/events/{event['id']}/"


def date_display(event: dict) -> str:
    start = date.fromisoformat(event["date"])
    end = event_end_date(event)
    start_html = f'{start.year} {start.month}.{start.day:02d}<span class="weekday">{WEEKDAYS[start.weekday()]}</span>'
    if end == start:
        return start_html
    if end.year == start.year:
        return start_html + f' - {end.month}.{end.day:02d}<span class="weekday">{WEEKDAYS[end.weekday()]}</span>'
    return start_html + f' - {end.year} {end.month}.{end.day:02d}<span class="weekday">{WEEKDAYS[end.weekday()]}</span>'


def display_detail_html(event: dict) -> list[str]:
    display = event.get("display") or {}
    override_lines = display.get("detail_lines") or []
    if override_lines:
        details = []
        for item in override_lines:
            text = (item or {}).get("text") or ""
            if not text:
                continue
            icon = DETAIL_ICONS.get((item or {}).get("icon") or "info", DETAIL_ICONS["info"])
            details.append(
                f'                                    <div class="detail-item"><i class="{icon}"></i>{escape(text)}</div>'
            )
        return details

    details = []
    time = time_text(event)
    performers = performer_html(event)
    if time:
        details.append(f'                                    <div class="detail-item"><i class="far fa-clock"></i>{escape(time)}</div>')
    if performers:
        details.append(f'                                    <div class="detail-item"><i class="fas fa-users"></i>{performers}</div>')
    return details


def render_schedule_article(event: dict) -> str:
    charge = event.get("charge") or ""
    event_type = normalize_event_type(event)
    type_badge = event_type_label(event)
    reserve_url = event.get("reservation_url") or "index.html#reservation"
    display = event.get("display") or {}

    details = display_detail_html(event)
    if charge:
        details.append(f'                                    <div class="lineup-price">{escape(charge)}</div>')
    detail_html = "\n".join(details)

    flyer = flyer_path(event)
    if event.get("legacy_imported") and flyer.lstrip("/") == "logo_new.png":
        flyer = ""
    if flyer:
        flyer_html = (
            f'<img src="{escape(flyer, quote=True)}" alt="{escape(event["title"], quote=True)} Flyer" '
            'class="lineup-flyer-thumb" onclick="window.open(this.src)">'
        )
    else:
        flyer_html = '<div class="lineup-flyer-thumb lineup-flyer-empty" aria-label="Flyer not registered"></div>'

    highlight_html = ""
    if display.get("badge"):
        highlight_html = f'<span class="lineup-badge">{escape(display["badge"])}</span>'

    subtitle_html = ""
    if display.get("subtitle"):
        subtitle_html = f'<span class="lineup-title-subtitle">{escape(display["subtitle"])}</span>'

    intro_html = ""
    if display.get("intro"):
        intro_html = f'<p class="lineup-intro">{escape(display["intro"])}</p>'

    info_lines = ['                            <div class="lineup-info">']
    if highlight_html:
        info_lines.append(f'                                {highlight_html}')
    info_lines.append(
        f'                                <h3 class="lineup-artist"><a href="{event_page_url(event)}">{escape(event["title"])}</a>{subtitle_html}</h3>'
    )
    if intro_html:
        info_lines.append(f'                                {intro_html}')
    info_lines.extend([
        '                                <div class="lineup-details">',
        detail_html,
        '                                </div>',
        f'                                <a href="{escape(reserve_url, quote=True)}" class="lineup-reserve-btn">RESERVATION</a>',
        '                            </div>',
    ])
    info_html = "\n".join(line for line in info_lines if line != "")

    return f'''                    <article class="lineup-item" data-date="{event['date']}" data-end-date="{event_end_date(event).isoformat()}" data-event-id="{escape(event['id'])}" data-event-type="{event_type}">
                        <span class="event-type-badge">{type_badge}</span>
                        <div class="lineup-date">{date_display(event)}</div>
                        <div class="lineup-body">
                            {flyer_html}
{info_html}
                        </div>
                    </article>'''


def remove_auto_article(html: str, event_id: str) -> str:
    pattern = re.compile(
        rf'\s*<article class="lineup-item"[^>]*data-event-id="{re.escape(event_id)}"[^>]*>.*?</article>\s*',
        re.S,
    )
    return pattern.sub("\n", html)


def upsert_schedule_event(html: str, event: dict) -> str:
    html = remove_auto_article(html, event["id"])
    start = date.fromisoformat(event["date"])
    month_id = MONTH_IDS[start.month - 1]
    section_start = html.find(f'<section id="{month_id}" class="lineup-month-group">')
    if section_start < 0:
        raise ValueError(
            f"Could not find month section {month_id} for {event['id']}. "
            "Schedule year scaffolding must be extended before publishing this event."
        )
    section_end = html.find("</section>", section_start)
    if section_end < 0:
        raise ValueError(f"Could not find end of month section: {month_id}")

    section = html[section_start:section_end]
    new_article = render_schedule_article(event)
    candidates = [
        (match.start(), match.group(1))
        for match in re.finditer(r'<article class="lineup-item"[^>]*data-date="(\d{4}-\d{2}-\d{2})"', section)
    ]

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


def classify_legacy_title(title: str) -> str:
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


def add_legacy_event_badges(html: str) -> str:
    pattern = re.compile(r'(<article class="lineup-item"[^>]*>)(.*?</article>)', re.S)

    def decorate(match: re.Match[str]) -> str:
        opening = match.group(1)
        rest = match.group(2)
        if "event-type-badge" in rest:
            return match.group(0)
        title_match = re.search(r'<h3 class="lineup-artist">(?:<a[^>]*>)?(.*?)(?:</a>)?</h3>', rest, re.S)
        if not title_match:
            return match.group(0)
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
        value = classify_legacy_title(title)
        label = event_type_label(value)
        if "data-event-type=" not in opening:
            opening = opening[:-1] + f' data-event-type="{value}">'
        return opening + f'\n                        <span class="event-type-badge">{label}</span>' + rest

    return pattern.sub(decorate, html)


def ensure_event_assets(html: str) -> str:
    if "event-types.css" not in html:
        marker = '<link rel="stylesheet" href="style.css">'
        if marker in html:
            html = html.replace(marker, marker + '\n    <link rel="stylesheet" href="event-types.css">', 1)
        else:
            html = html.replace("</head>", '    <link rel="stylesheet" href="event-types.css">\n</head>', 1)
    if "event-runtime.js" not in html:
        html = html.replace("</body>", '    <script src="event-runtime.js"></script>\n</body>', 1)
    return html


def rebuild_home_preview(index_html: str, schedule_html: str) -> str:
    today = current_jst_date().isoformat()
    articles = []
    for match in re.finditer(
        r'(<article class="lineup-item"[^>]*data-date="(\d{4}-\d{2}-\d{2})"[^>]*>.*?</article>)',
        schedule_html,
        re.S,
    ):
        article = match.group(1)
        end_match = re.search(r'data-end-date="(\d{4}-\d{2}-\d{2})"', article)
        end_date = end_match.group(1) if end_match else match.group(2)
        if end_date >= today:
            articles.append((match.group(2), article))
    articles.sort(key=lambda item: item[0])
    preview = "\n\n".join(article for _, article in articles[:3])

    pattern = re.compile(
        r'(<div class="lineup-list" style="margin-bottom: 3rem;">)(.*?)(\n\s*</div>\n\s*<div style="text-align: center;">)',
        re.S,
    )
    if not pattern.search(index_html):
        raise ValueError("Could not find home lineup preview block")
    return pattern.sub(lambda match: match.group(1) + "\n\n" + preview + match.group(3), index_html, count=1)


def main() -> None:
    events = load_events()
    schedule_html = SCHEDULE_FILE.read_text(encoding="utf-8-sig")

    for event in events:
        schedule_html = remove_auto_article(schedule_html, event["id"])

    for event in sorted(events, key=lambda item: (item["date"], item["title"])):
        if event.get("status") not in {"ready", "published", "archived"}:
            continue
        if event_is_past(event):
            continue
        schedule_html = upsert_schedule_event(schedule_html, event)

    schedule_html = add_legacy_event_badges(schedule_html)
    schedule_html = ensure_event_assets(schedule_html)

    index_html = INDEX_FILE.read_text(encoding="utf-8-sig")
    index_html = rebuild_home_preview(index_html, schedule_html)
    index_html = ensure_event_assets(index_html)

    SCHEDULE_FILE.write_text(schedule_html, encoding="utf-8")
    INDEX_FILE.write_text(index_html, encoding="utf-8")


if __name__ == "__main__":
    main()
