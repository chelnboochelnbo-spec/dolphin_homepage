"""Apply the approved colour-only identity after generated pages are rebuilt.

Original logo outlines are reused; no event, artist, price, closure or booking
record is changed. The base stylesheets remain available for a simple rollback.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME_HREF = '/brand-monochrome.css?v=20261006'
LOGO_HREF = '/assets/brand/dolphin-white.svg'
LINK = f'<link rel="stylesheet" href="{THEME_HREF}" data-dolphin-brand="monochrome">'
NAV_LOGO = f'<img class="brand-nav-logo" src="{LOGO_HREF}" alt="Jazz &amp; Bar Dolphin" width="100" height="64">'
HERO_LOGO = f'<img class="brand-hero-logo" src="{LOGO_HREF}" alt="Jazz &amp; Bar Dolphin" width="310" height="197" decoding="async">'


def themed_html(text: str) -> str:
    if not re.search(r'href=[\"\'][^\"\']*(?:style\.css|inbound\.css)[\"\']', text):
        return text
    # Reinsert last, after schedule-specific inline styles. Idempotent on rebuild.
    text = re.sub(r'[ \t]*<link\b[^>]*data-dolphin-brand="monochrome"[^>]*>\r?\n?', '', text, flags=re.M)
    if '</head>' not in text:
        raise ValueError('Themed page is missing </head>')
    text = text.replace('</head>', LINK + '\n</head>', 1)
    def body(match: re.Match[str]) -> str:
        tag = match[0]
        if 'data-brand-theme=' in tag:
            return re.sub(r'data-brand-theme=[\"\'][^\"\']*[\"\']', 'data-brand-theme="monochrome"', tag)
        return tag[:-1] + ' data-brand-theme="monochrome">'
    text, count = re.subn(r'<body\b[^>]*>', body, text, count=1)
    if count != 1:
        raise ValueError('Themed page is missing body')
    # Preserve home link targets while replacing plain text with the original mark.
    text = re.sub(r'(<div class="logo">\s*<a\b[^>]*>)DOLPHIN(</a>)',
                  lambda m: m[1] + NAV_LOGO + m[2], text)
    text = re.sub(r'(<a\b[^>]*class="inbound-brand"[^>]*>)DOLPHIN(</a>)',
                  lambda m: m[1] + NAV_LOGO + m[2], text)
    if 'class="brand-hero-logo"' not in text:
        text = re.sub(r'(<div class="hero-content(?: fade-in)?">|<header class="inbound-hero">)',
                      lambda m: m[1] + '\n' + HERO_LOGO, text, count=1)
    return text


def main(root: Path = ROOT) -> list[str]:
    paths = list(root.glob('*.html'))
    for folder in ('events', 'artists', 'archive', 'en', 'zh-tw'):
        paths.extend((root / folder).rglob('*.html'))
    changed = []
    for path in sorted(set(paths)):
        before = path.read_text(encoding='utf-8-sig')
        after = themed_html(before)
        if after != before:
            path.write_text(after, encoding='utf-8')
            changed.append(path.relative_to(root).as_posix())
    print(f'Monochrome theme: updated {len(changed)} public HTML pages')
    return changed


if __name__ == '__main__':
    main()
