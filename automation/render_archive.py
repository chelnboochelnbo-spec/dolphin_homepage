from __future__ import annotations

import json
import re
from datetime import date
from html import escape
from pathlib import Path

from event_utils import event_is_past, event_type_label, normalize_event_type

ROOT = Path(__file__).resolve().parents[1]
EVENTS_FILE = ROOT / "data" / "events.json"
ARCHIVE_DIR = ROOT / "archive"
ARCHIVE_ALIAS = ROOT / "archive.html"
INDEX_FILE = ROOT / "index.html"
BASE_URL = "https://www.bardolphin-kanazawa.com"


def load_events() -> list[dict]:
    payload = json.loads(EVENTS_FILE.read_text(encoding="utf-8-sig"))
    return [event for event in payload.get("events", []) if event.get("status") != "draft"]


def root_asset(path: str) -> str:
    if not path:
        return ""
    if path.startswith(("http://", "https://", "/")):
        return path
    return "/" + path.lstrip("/")


def performer_labels(event: dict) -> list[str]:
    labels = []
    for performer in event.get("performers") or []:
        label = " ".join(filter(None, [performer.get("instrument"), performer.get("name")])).strip()
        if label:
            labels.append(label)
    return labels


def time_label(event: dict) -> str:
    bits = []
    if event.get("open"):
        bits.append(f"Open {event['open']}")
    if event.get("start"):
        bits.append(f"Start {event['start']}")
    return " / ".join(bits)


def event_url(event: dict) -> str:
    return f"/events/{event['id']}/"


def event_card(event: dict) -> str:
    start = date.fromisoformat(event["date"])
    end_raw = event.get("end_date")
    if end_raw and end_raw != event["date"]:
        end = date.fromisoformat(end_raw)
        date_text = f"{start.month:02d}.{start.day:02d} — {end.month:02d}.{end.day:02d}"
    else:
        date_text = f"{start.month:02d}.{start.day:02d}"

    performers = performer_labels(event)
    search_text = " ".join([event.get("title", ""), *performers]).strip()
    flyer = root_asset((event.get("flyer") or {}).get("github_path") or "")
    if flyer:
        media = (
            f'<a class="archive-card-media" href="{event_url(event)}">'
            f'<img src="{escape(flyer, quote=True)}" alt="{escape(event["title"], quote=True)} Flyer" loading="lazy">'
            f'</a>'
        )
        card_class = "archive-card"
    else:
        media = ""
        card_class = "archive-card no-image"

    meta = []
    t = time_label(event)
    if t:
        meta.append(f'<span>{escape(t)}</span>')
    if event.get("charge"):
        meta.append(f'<span>{escape(event["charge"])}</span>')

    performers_html = ""
    if performers:
        performers_html = f'<p class="archive-card-performers">{escape(" / ".join(performers))}</p>'

    return f'''<article class="{card_class}" data-archive-card data-year="{start.year}" data-event-type="{normalize_event_type(event)}" data-search="{escape(search_text, quote=True)}">
    {media}
    <div class="archive-card-body">
        <div class="archive-card-topline">
            <time datetime="{event['date']}" class="archive-card-date">{date_text}</time>
            <span class="archive-type">{event_type_label(event)}</span>
        </div>
        <h2 class="archive-card-title"><a href="{event_url(event)}">{escape(event['title'])}</a></h2>
        {performers_html}
        <div class="archive-card-meta">{''.join(meta)}</div>
        <a class="archive-card-link" href="{event_url(event)}">VIEW EVENT</a>
    </div>
</article>'''


def render_archive(events: list[dict]) -> str:
    past = sorted(
        (e for e in events if event_is_past(e)),
        key=lambda e: (e.get("end_date") or e["date"], e["date"], e["title"]),
        reverse=True,
    )
    years = sorted({date.fromisoformat(e["date"]).year for e in past}, reverse=True)

    year_controls = ""
    if len(years) > 1:
        buttons = ['<button type="button" class="archive-filter active" data-archive-year="ALL">ALL YEARS</button>']
        buttons.extend(
            f'<button type="button" class="archive-filter" data-archive-year="{year}">{year}</button>'
            for year in years
        )
        year_controls = f'<div class="archive-filter-group archive-year-filters" aria-label="年で絞り込み">{"".join(buttons)}</div>'

    type_controls = (
        '<div class="archive-filter-group" aria-label="イベントタイプで絞り込み">'
        '<button type="button" class="archive-filter active" data-archive-type="ALL">ALL</button>'
        '<button type="button" class="archive-filter" data-archive-type="live">LIVE</button>'
        '<button type="button" class="archive-filter" data-archive-type="session">SESSION</button>'
        '<button type="button" class="archive-filter" data-archive-type="live_session">LIVE &amp; SESSION</button>'
        '</div>'
    )

    sections = []
    for year in years:
        cards = "\n".join(
            event_card(e) for e in past if date.fromisoformat(e["date"]).year == year
        )
        sections.append(f'''<section class="archive-year" data-archive-year-section="{year}">
    <h2 class="archive-year-title">{year}</h2>
    <div class="archive-grid">{cards}</div>
</section>''')

    if not sections:
        sections.append('<p class="archive-empty-state">過去のライブはこれからここに蓄積されていきます。</p>')

    title = "LIVE ARCHIVE | Jazz & Bar DOLPHIN 金沢"
    description = "Jazz & Bar DOLPHIN（金沢）で開催してきたライブとセッションの記録。公演終了後、自動的に蓄積されるDOLPHINのライブアーカイブです。"
    canonical = f"{BASE_URL}/archive/"
    return f'''<!-- GENERATED: DOLPHIN LIVE ARCHIVE -->
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description, quote=True)}">
    <link rel="canonical" href="{canonical}">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape(title, quote=True)}">
    <meta property="og:description" content="{escape(description, quote=True)}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:image" content="{BASE_URL}/logo_new.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Josefin+Sans:ital,wght@0,300;0,400;0,600;0,700;1,300;1,400&family=Noto+Sans+JP:wght@300;400;500&family=Lato:wght@300;400&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/style.css">
    <link rel="stylesheet" href="/archive.css">
    <link rel="icon" type="image/png" href="/logo_new.png">
</head>
<body class="live-archive-page">
<nav class="main-nav">
    <div class="logo"><a href="/">DOLPHIN</a></div>
    <div class="nav-right">
        <ul class="nav-links">
            <li><a href="/">Home</a></li>
            <li><a href="/schedule.html">Schedule</a></li>
            <li><a href="/artists/">Artists</a></li>
            <li><a href="/archive/" class="active">Archive</a></li>
        </ul>
        <button class="menu-toggle" aria-label="Toggle Menu">
            <span class="bar"></span><span class="bar"></span><span class="bar"></span>
        </button>
    </div>
</nav>

<header class="archive-hero">
    <div class="archive-inner">
        <p class="archive-kicker">DOLPHIN MUSIC HISTORY</p>
        <h1>LIVE ARCHIVE</h1>
        <p class="archive-lead">ここで鳴った音楽の記録。開催を終えたライブやセッションが、時系列で静かに積み重なっていきます。</p>
    </div>
</header>

<main class="archive-main">
    <div class="archive-tools">
        <input type="search" class="archive-search" placeholder="イベント名・アーティスト名で検索" aria-label="アーカイブを検索" data-archive-search>
        {year_controls}
        {type_controls}
    </div>
    {''.join(sections)}
    <p class="archive-no-results" data-archive-empty>該当するイベントはありません。</p>
</main>

<script src="/script.js"></script>
<script src="/archive.js"></script>
</body>
</html>
'''


def ensure_home_archive_link() -> None:
    if not INDEX_FILE.exists():
        return
    html = INDEX_FILE.read_text(encoding="utf-8-sig")
    marker = '<a href="/archive/" class="lineup-archive-link">LIVE ARCHIVE</a>'
    if marker in html:
        return
    target = re.search(
        r'(<a href="schedule\.html" class="lineup-reserve-btn">VIEW FULL LINEUP</a>)',
        html,
    )
    if not target:
        return
    replacement = target.group(1) + '\n                <a href="/archive/" class="lineup-archive-link">LIVE ARCHIVE</a>'
    html = html[:target.start()] + replacement + html[target.end():]
    INDEX_FILE.write_text(html, encoding="utf-8")


def main() -> None:
    events = load_events()
    html = render_archive(events)
    ARCHIVE_DIR.mkdir(exist_ok=True)
    (ARCHIVE_DIR / "index.html").write_text(html, encoding="utf-8")
    ARCHIVE_ALIAS.write_text(html, encoding="utf-8")
    ensure_home_archive_link()


if __name__ == "__main__":
    main()
