from __future__ import annotations

import json
import re
import shutil
import unicodedata
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTISTS_FILE = ROOT / "data" / "artists.json"
EVENTS_FILE = ROOT / "data" / "events.json"
ARTISTS_DIR = ROOT / "artists"
EVENTS_DIR = ROOT / "events"
INDEX_FILE = ROOT / "index.html"
SCHEDULE_FILE = ROOT / "schedule.html"
ARCHIVE_FILE = ROOT / "archive.html"
BASE_URL = "https://www.bardolphin-kanazawa.com"

INSTRUMENT_ORDER = ["Vocal", "Piano", "Guitar", "Bass", "Drums", "Sax", "Trumpet", "Other"]
EVENT_TYPE_LABELS = {
    "live": "LIVE",
    "session": "SESSION",
    "live_session": "LIVE & SESSION",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_name(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").strip().casefold()


def load_artists() -> list[dict]:
    artists = load_json(ARTISTS_FILE).get("artists", [])
    ids: set[str] = set()
    names: set[str] = set()
    for artist in artists:
        for key in (
            "id", "artist_name", "artist_name_en", "instrument", "photo", "profile",
            "website", "instagram", "youtube", "appearances"
        ):
            if key not in artist:
                raise ValueError(f"Artist missing required field: {key}")
        if not re.fullmatch(r"[a-z0-9-]+", artist["id"]):
            raise ValueError(f"Invalid artist id: {artist['id']}")
        if artist["id"] in ids:
            raise ValueError(f"Duplicate artist id: {artist['id']}")
        ids.add(artist["id"])

        canonical = normalize_name(artist["artist_name"])
        if canonical in names:
            raise ValueError(f"Duplicate artist name: {artist['artist_name']}")
        names.add(canonical)

        for appearance in artist.get("appearances", []):
            date.fromisoformat(appearance["date"])
    return artists


def load_events() -> list[dict]:
    if not EVENTS_FILE.exists():
        return []
    return load_json(EVENTS_FILE).get("events", [])


def artist_event_ids(event: dict) -> list[str]:
    ids = list(event.get("artist_ids") or [])
    for performer in event.get("performers") or []:
        artist_id = performer.get("artist_id")
        if artist_id and artist_id not in ids:
            ids.append(artist_id)
    return ids


def event_url(event: dict) -> str:
    return f"/events/{event['id']}/"


def merged_appearances(artist: dict, events: list[dict]) -> list[dict]:
    appearances = [dict(item) for item in artist.get("appearances") or []]
    seen = {(item.get("date"), item.get("event_title")) for item in appearances}
    for event in events:
        if artist["id"] not in artist_event_ids(event):
            continue
        if event.get("status") == "draft":
            continue
        key = (event.get("date"), event.get("title"))
        if key in seen:
            for item in appearances:
                if (item.get("date"), item.get("event_title")) == key and not item.get("event_url"):
                    item["event_url"] = event_url(event)
            continue
        appearances.append({
            "date": event["date"],
            "event_title": event["title"],
            "event_url": event_url(event),
        })
        seen.add(key)
    appearances.sort(key=lambda item: item["date"], reverse=True)
    return appearances


def root_asset(path: str) -> str:
    if not path:
        return "/logo_new.png"
    if path.startswith(("http://", "https://", "/")):
        return path
    return "/" + path.lstrip("/")


def initials(artist: dict) -> str:
    source = artist.get("artist_name_en") or artist.get("artist_name") or "D"
    words = [word for word in re.split(r"\s+", source.strip()) if word]
    if len(words) >= 2:
        return escape((words[0][0] + words[-1][0]).upper())
    return escape(source[:2].upper())


def nav_html(active: str = "") -> str:
    def item(label: str, href: str, key: str) -> str:
        class_attr = ' class="active"' if active == key else ""
        return f'<li><a href="{href}"{class_attr}>{label}</a></li>'
    return "\n".join([
        item("Home", "/", "home"),
        item("Schedule", "/schedule.html", "schedule"),
        item("Artists", "/artists/", "artists"),
        item("Archive", "/archive.html", "archive"),
    ])


def shell_head(title: str, description: str, canonical: str, og_image: str, extra_css: str = "") -> str:
    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description, quote=True)}">
    <link rel="canonical" href="{escape(canonical, quote=True)}">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{escape(title, quote=True)}">
    <meta property="og:description" content="{escape(description, quote=True)}">
    <meta property="og:url" content="{escape(canonical, quote=True)}">
    <meta property="og:image" content="{escape(og_image, quote=True)}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Josefin+Sans:ital,wght@0,300;0,400;0,600;0,700;1,300;1,400&family=Noto+Sans+JP:wght@300;400;500&family=Lato:wght@300;400&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/style.css">
    <link rel="stylesheet" href="/artists.css">
    {extra_css}
    <link rel="icon" type="image/png" href="/logo_new.png">
</head>'''


def nav_block(active: str = "") -> str:
    return f'''<nav class="main-nav">
    <div class="logo"><a href="/">DOLPHIN</a></div>
    <div class="nav-right">
        <ul class="nav-links">
            {nav_html(active)}
        </ul>
        <button class="menu-toggle" aria-label="Toggle Menu">
            <span class="bar"></span><span class="bar"></span><span class="bar"></span>
        </button>
    </div>
</nav>'''


def render_artist_card(artist: dict, appearance_count: int) -> str:
    photo = artist.get("photo") or ""
    if photo:
        media = f'<img src="{escape(root_asset(photo), quote=True)}" alt="{escape(artist["artist_name"], quote=True)}">'
    else:
        media = f'<div class="artist-photo-placeholder" aria-label="Photo pending">{initials(artist)}</div>'
    search_text = " ".join([artist["artist_name"], artist.get("artist_name_en", ""), artist.get("instrument", "")])
    return f'''<article class="artist-card" data-artist-card data-instrument="{escape(artist['instrument'].upper(), quote=True)}" data-search="{escape(search_text, quote=True)}">
    <a class="artist-card-link" href="/artists/{escape(artist['id'], quote=True)}/">
        <div class="artist-card-media">{media}</div>
        <div class="artist-card-meta">
            <h2 class="artist-card-name">{escape(artist['artist_name'])}</h2>
            <p class="artist-card-en">{escape(artist.get('artist_name_en') or '')}</p>
            <p class="artist-card-instrument">{escape(artist['instrument'])}</p>
            <p class="artist-card-count">{appearance_count} appearance{'s' if appearance_count != 1 else ''}</p>
        </div>
    </a>
</article>'''


def render_artists_index(artists: list[dict], events: list[dict]) -> str:
    available = {artist["instrument"] for artist in artists}
    filter_buttons = ['<button class="artist-filter active" type="button" data-artist-filter="ALL">ALL</button>']
    for instrument in INSTRUMENT_ORDER:
        if instrument in available:
            filter_buttons.append(
                f'<button class="artist-filter" type="button" data-artist-filter="{escape(instrument.upper(), quote=True)}">{escape(instrument.upper())}</button>'
            )
    cards = "\n".join(render_artist_card(artist, len(merged_appearances(artist, events))) for artist in artists)
    title = "ARTISTS | Jazz & Bar DOLPHIN 金沢"
    description = "Jazz & Bar DOLPHIN（金沢）に出演してきたミュージシャンのアーカイブ。出演履歴とともに、DOLPHINに積み重なってきた音楽の時間を記録します。"
    canonical = f"{BASE_URL}/artists/"
    return f'''<!-- GENERATED: DOLPHIN ARTISTS INDEX -->
{shell_head(title, description, canonical, f'{BASE_URL}/logo_new.png')}
<body class="artists-page">
{nav_block('artists')}
<header class="artists-hero">
    <div class="artists-hero-inner">
        <p class="artists-kicker">DOLPHIN MUSIC ARCHIVE</p>
        <h1 class="artists-title">ARTISTS</h1>
        <p class="artists-lead">DOLPHINで音を重ねてきたミュージシャンたち。公演の記憶を、出演履歴とともに残していきます。</p>
    </div>
</header>
<main class="artists-main">
    <div class="artists-tools">
        <input class="artist-search" type="search" placeholder="名前で検索" aria-label="アーティストを名前で検索" data-artist-search>
        <div class="artist-filter-list" aria-label="楽器・パートで絞り込み">{' '.join(filter_buttons)}</div>
    </div>
    <div class="artists-grid">{cards}</div>
    <p class="artists-empty" data-artists-empty>該当するアーティストはありません。</p>
</main>
<script src="/script.js"></script>
<script src="/artists.js"></script>
</body>
</html>
'''


def artist_json_ld(artist: dict, canonical: str) -> str:
    payload: dict = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": artist["artist_name"],
        "url": canonical,
    }
    if artist.get("artist_name_en"):
        payload["alternateName"] = artist["artist_name_en"]
    if artist.get("photo"):
        payload["image"] = f"{BASE_URL}{root_asset(artist['photo'])}"
    same_as = [artist.get("website"), artist.get("instagram"), artist.get("youtube")]
    same_as = [url for url in same_as if url]
    if same_as:
        payload["sameAs"] = same_as
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")


def render_artist_detail(artist: dict, events: list[dict]) -> str:
    appearances = merged_appearances(artist, events)
    canonical = f"{BASE_URL}/artists/{artist['id']}/"
    title = f"{artist['artist_name']} | ARTISTS | Jazz & Bar DOLPHIN 金沢"
    description_parts = [artist["artist_name"]]
    if artist.get("instrument"):
        description_parts.append(artist["instrument"])
    description = " / ".join(description_parts) + "。Jazz & Bar DOLPHIN（金沢）での出演履歴を掲載しています。"
    og_image = f"{BASE_URL}{root_asset(artist.get('photo') or 'logo_new.png')}"

    if artist.get("photo"):
        photo_html = f'<img src="{escape(root_asset(artist["photo"]), quote=True)}" alt="{escape(artist["artist_name"], quote=True)}">'
    else:
        photo_html = f'<div class="artist-photo-placeholder" aria-label="Photo pending">{initials(artist)}</div>'

    profile = escape(artist.get("profile") or "")
    profile_html = profile if profile else "プロフィールは準備中です。"
    profile_class = "artist-profile" if profile else "artist-profile is-empty"

    appearance_html = []
    for item in appearances:
        d = date.fromisoformat(item["date"])
        date_label = f"{d.year}.{d.month:02d}.{d.day:02d}"
        if item.get("event_url"):
            title_html = f'<a href="{escape(item["event_url"], quote=True)}">{escape(item["event_title"])}</a>'
        else:
            title_html = escape(item["event_title"])
        appearance_html.append(
            f'<li class="appearance-item"><time class="appearance-date" datetime="{item["date"]}">{date_label}</time><div class="appearance-title">{title_html}</div></li>'
        )
    if not appearance_html:
        appearance_html.append('<li class="appearance-item"><div class="appearance-title">出演履歴は準備中です。</div></li>')

    links = []
    for label, key in (("WEBSITE", "website"), ("INSTAGRAM", "instagram"), ("YOUTUBE", "youtube")):
        if artist.get(key):
            links.append(f'<a href="{escape(artist[key], quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>')
    links_html = "".join(links) if links else '<span style="color:#666;font-size:.82rem;">External links are not registered.</span>'

    return f'''<!-- GENERATED: DOLPHIN ARTIST -->
{shell_head(title, description, canonical, og_image)}
<body class="artist-detail-page">
{nav_block('artists')}
<header class="artist-detail-hero">
    <div class="artist-detail-inner artist-detail-grid">
        <div class="artist-detail-photo">{photo_html}</div>
        <div>
            <p class="artist-eyebrow">DOLPHIN ARTISTS ARCHIVE</p>
            <h1 class="artist-detail-name">{escape(artist['artist_name'])}</h1>
            <p class="artist-detail-name-en">{escape(artist.get('artist_name_en') or '')}</p>
            <p class="artist-detail-instrument">{escape(artist['instrument'])}</p>
        </div>
    </div>
</header>
<main class="artist-detail-content">
    <section>
        <h2 class="artist-section-title">PROFILE</h2>
        <p class="{profile_class}">{profile_html}</p>
        <div style="margin-top:2.5rem;">
            <h2 class="artist-section-title">LINKS</h2>
            <div class="artist-links">{links_html}</div>
        </div>
        <a class="artist-back" href="/artists/">← VIEW ALL ARTISTS</a>
    </section>
    <section>
        <h2 class="artist-section-title">APPEARANCES AT DOLPHIN</h2>
        <ul class="appearance-list">{''.join(appearance_html)}</ul>
    </section>
</main>
<script type="application/ld+json">{artist_json_ld(artist, canonical)}</script>
<script src="/script.js"></script>
</body>
</html>
'''


def event_type_label(event: dict) -> str:
    value = event.get("event_type") or event.get("type") or "live"
    if value in EVENT_TYPE_LABELS:
        return EVENT_TYPE_LABELS[value]
    legacy = str(value).upper().replace("&", " & ")
    if "LIVE" in legacy and "SESSION" in legacy:
        return "LIVE & SESSION"
    if "SESSION" in legacy:
        return "SESSION"
    return "LIVE"


def render_event_detail(event: dict, artists_by_id: dict[str, dict]) -> str:
    d = date.fromisoformat(event["date"])
    canonical = f"{BASE_URL}{event_url(event)}"
    title = f"{event['title']} | Jazz & Bar DOLPHIN 金沢"
    description = event.get("description") or f"{d.year}年{d.month}月{d.day}日、Jazz & Bar DOLPHIN（金沢）で開催する「{event['title']}」の公演情報。"
    flyer = (event.get("flyer") or {}).get("github_path") or "logo_new.png"
    performers = []
    for performer in event.get("performers") or []:
        label = " ".join(filter(None, [performer.get("instrument"), performer.get("name")]))
        artist_id = performer.get("artist_id")
        if artist_id and artist_id in artists_by_id:
            performers.append(f'<li><a href="/artists/{escape(artist_id, quote=True)}/">{escape(label)}</a></li>')
        else:
            performers.append(f'<li>{escape(label)}</li>')
    performer_html = "".join(performers) or "<li>出演者情報は準備中です。</li>"
    time_bits = []
    if event.get("open"):
        time_bits.append(f"OPEN {event['open']}")
    if event.get("start"):
        time_bits.append(f"START {event['start']}")
    time_label = " / ".join(time_bits)
    reservation = event.get("reservation_url") or "/#reservation"
    inline_css = '''<style>
.event-page{background:#0f0f0f;color:#eee;min-height:100vh}.event-detail{max-width:1000px;margin:0 auto;padding:9rem 1.5rem 7rem}.event-detail-grid{display:grid;grid-template-columns:minmax(280px,.85fr) minmax(0,1.15fr);gap:4rem;align-items:start}.event-flyer{width:100%;background:#171717}.event-detail h1{color:#fff;font-size:clamp(2.2rem,6vw,4.7rem);line-height:1.05;margin:1rem 0}.event-meta{color:#aaa;line-height:2}.event-performers{list-style:none;padding:0;margin:2rem 0}.event-performers li{padding:.55rem 0;border-bottom:1px solid #252525}.event-performers a{color:#eee;text-decoration:none}.event-performers a:hover{color:var(--color-primary)}.event-description{color:#aaa;line-height:2;white-space:pre-wrap}.event-reserve{display:inline-block;margin-top:2rem;padding:.75rem 1rem;border:1px solid var(--color-primary);color:#fff;text-decoration:none}.event-type-badge{position:static;margin-bottom:.7rem;background:transparent;color:var(--color-primary);border-color:#444}@media(max-width:760px){.event-detail-grid{grid-template-columns:1fr;gap:2rem}}
</style>'''
    return f'''<!-- GENERATED: DOLPHIN EVENT -->
{shell_head(title, description, canonical, f'{BASE_URL}{root_asset(flyer)}', '<link rel="stylesheet" href="/event-types.css">' + inline_css)}
<body class="event-page">
{nav_block('schedule')}
<main class="event-detail">
    <div class="event-detail-grid">
        <div><img class="event-flyer" src="{escape(root_asset(flyer), quote=True)}" alt="{escape(event['title'], quote=True)} Flyer"></div>
        <div>
            <span class="event-type-badge">{event_type_label(event)}</span>
            <p class="artists-kicker">{d.year}.{d.month:02d}.{d.day:02d}</p>
            <h1>{escape(event['title'])}</h1>
            <p class="event-meta">{escape(time_label)}{'<br>' if time_label and event.get('charge') else ''}{escape(event.get('charge') or '')}</p>
            <ul class="event-performers">{performer_html}</ul>
            <p class="event-description">{escape(event.get('description') or '')}</p>
            <a class="event-reserve" href="{escape(reservation, quote=True)}">RESERVATION</a>
        </div>
    </div>
</main>
<script src="/script.js"></script>
</body>
</html>
'''


def write_generated_pages(artists: list[dict], events: list[dict]) -> None:
    ARTISTS_DIR.mkdir(exist_ok=True)
    (ARTISTS_DIR / "index.html").write_text(render_artists_index(artists, events), encoding="utf-8")

    valid_ids = {artist["id"] for artist in artists}
    for child in ARTISTS_DIR.iterdir():
        if child.is_dir() and child.name not in valid_ids:
            marker = child / "index.html"
            if marker.exists() and "GENERATED: DOLPHIN ARTIST" in marker.read_text(encoding="utf-8-sig"):
                shutil.rmtree(child)

    for artist in artists:
        target = ARTISTS_DIR / artist["id"]
        target.mkdir(exist_ok=True)
        (target / "index.html").write_text(render_artist_detail(artist, events), encoding="utf-8")

    EVENTS_DIR.mkdir(exist_ok=True)
    artists_by_id = {artist["id"]: artist for artist in artists}
    valid_event_ids = {event["id"] for event in events if event.get("status") != "draft"}
    for child in EVENTS_DIR.iterdir():
        if child.is_dir() and child.name not in valid_event_ids:
            marker = child / "index.html"
            if marker.exists() and "GENERATED: DOLPHIN EVENT" in marker.read_text(encoding="utf-8-sig"):
                shutil.rmtree(child)
    for event in events:
        if event.get("status") == "draft":
            continue
        target = EVENTS_DIR / event["id"]
        target.mkdir(exist_ok=True)
        (target / "index.html").write_text(render_event_detail(event, artists_by_id), encoding="utf-8")


def ensure_artists_nav(path: Path) -> None:
    if not path.exists():
        return
    html = path.read_text(encoding="utf-8-sig")
    nav_match = re.search(r'(<ul class="nav-links">)(.*?)(</ul>)', html, re.S)
    if not nav_match:
        return
    if re.search(r'href=["\']/artists/?["\']', nav_match.group(0)):
        return
    new_block = nav_match.group(1) + nav_match.group(2) + '\n                <li><a href="/artists/">Artists</a></li>\n            ' + nav_match.group(3)
    html = html[:nav_match.start()] + new_block + html[nav_match.end():]
    path.write_text(html, encoding="utf-8")


def ensure_feature_slot() -> None:
    if not INDEX_FILE.exists():
        return
    html = INDEX_FILE.read_text(encoding="utf-8-sig")
    marker = "<!-- ARTISTS FEATURE SLOT: set featured=true in data/artists.json to activate -->"
    if marker in html:
        return
    schedule_end = html.find("</section>", html.find('id="schedule-preview"'))
    if schedule_end < 0:
        return
    schedule_end += len("</section>")
    html = html[:schedule_end] + "\n\n    " + marker + html[schedule_end:]
    INDEX_FILE.write_text(html, encoding="utf-8")


def main() -> None:
    artists = load_artists()
    events = load_events()

    known_ids = {artist["id"] for artist in artists}
    for event in events:
        for artist_id in artist_event_ids(event):
            if artist_id not in known_ids:
                raise ValueError(f"Event {event.get('id')} references unknown artist: {artist_id}")

    write_generated_pages(artists, events)
    for path in (INDEX_FILE, SCHEDULE_FILE, ARCHIVE_FILE):
        ensure_artists_nav(path)
    ensure_feature_slot()


if __name__ == "__main__":
    main()
