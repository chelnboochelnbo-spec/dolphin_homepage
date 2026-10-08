"""Homepage-only calendar; event and operating records remain read-only."""
import calendar
import re
from datetime import date, timedelta
from html import escape

from publication_guard import event_publishable
from render_operating_schedule import validate_operations, regular_closure


def month_shift(day, offset):
    year, month = divmod(day.year * 12 + day.month - 1 + offset, 12)
    return date(year, month + 1, 1)


def render_calendar(events, operations, today, root):
    validate_operations(operations)
    visible = sorted((e for e in events if event_publishable(e, root)),
                     key=lambda e: (e['date'], e.get('start') or '', e['id']))
    overrides = operations.get('overrides', {})
    starts = [date.fromisoformat(e['date']) for e in visible]
    ends = [date.fromisoformat(e.get('end_date') or e['date']) for e in visible]
    horizon = max([today] + ends + [date.fromisoformat(d) for d in overrides])
    horizon = horizon.replace(day=calendar.monthrange(horizon.year, horizon.month)[1])
    first = min([month_shift(today, -1)] + starts).replace(day=1)
    last = max(month_shift(today, 1), horizon.replace(day=1))
    months = []
    while first <= last:
        months.append(first)
        first = month_shift(first, 1)
    tabs, panels = [], []
    hours = operations['standard_hours']
    hours_label = hours['open'] + '–' + ('翌' if hours['close'] <= hours['open'] else '') + hours['close']
    for month in months:
        key = month.strftime('%Y-%m')
        label = f'{month.year}年{month.month}月'
        tabs.append(f'<a href="#calendar-{key}" data-calendar-month="{key}">{label}</a>')
        weeks = []
        for week in calendar.Calendar(firstweekday=6).monthdatescalendar(month.year, month.month):
            cells = []
            for day in week:
                if day.month != month.month:
                    cells.append('<td class="calendar-outside" aria-hidden="true"></td>')
                    continue
                iso = day.isoformat()
                state = overrides.get(iso, {}).get('state')
                matches = [e for e in visible if e['date'] <= iso <= (e.get('end_date') or e['date'])]
                if not state and not matches and regular_closure(day, operations):
                    state = 'closed'
                if state in {'closed', 'private'}:
                    content = '<span class="calendar-state">' + ('休業' if state == 'closed' else '貸切営業') + '</span>'
                    note = overrides.get(iso, {}).get('note')
                    if note:
                        content += '<small>' + escape(note) + '</small>'
                elif matches:
                    content = ''.join('<a class="calendar-event" href="/events/' + escape(e['id'], quote=True) + '/">'
                                      + ('<small>' + escape(e['start']) + '</small>' if e.get('start') else '')
                                      + escape(e['title']) + '</a>' for e in matches)
                elif day > horizon or day < today:
                    content = '<span class="calendar-empty">予定の登録なし</span>'
                else:
                    content = '<span class="calendar-state">通常営業</span><small>' + hours_label + '</small>'
                cells.append(f'<td data-calendar-date="{iso}" class="calendar-day calendar-{state or "open"}">'
                             f'<time datetime="{iso}">{day.day}</time>{content}</td>')
            weeks.append('<tr>' + ''.join(cells) + '</tr>')
        panels.append(f'<section class="calendar-month" id="calendar-{key}" data-calendar-panel="{key}">'
                      f'<h3>{label}</h3><div class="calendar-scroll" tabindex="0" role="region" aria-label="{label}のカレンダー（横スクロール可能）">'
                      f'<table><caption class="calendar-sr-only">{label}の営業・イベント予定</caption><thead><tr>'
                      + ''.join(f'<th scope="col">{d}</th>' for d in ['日', '月', '火', '水', '木', '金', '土'])
                      + '</tr></thead><tbody>' + ''.join(weeks) + '</tbody></table></div></section>')
    return ('<div id="home-calendar" class="home-calendar">'
            '<p class="calendar-note">日付は営業開始日です。イベント名から詳細をご覧いただけます。</p>'
            '<div class="calendar-controls" hidden><button type="button" data-calendar-step="-1" aria-label="前の月">← 前月</button>'
            '<button type="button" data-calendar-today>今月</button><button type="button" data-calendar-step="1" aria-label="次の月">次月 →</button></div>'
            '<nav class="calendar-months" aria-label="表示する月">' + ''.join(tabs) + '</nav>'
            '<p class="calendar-mobile-note">カレンダーは左右にスクロールできます。</p>'
            '<p class="calendar-sr-only" data-calendar-announcement aria-live="polite" aria-atomic="true"></p>'
            + ''.join(panels) + '</div>')


def rebuild_home_calendar(html, events, operations, today, root):
    markup = '<!-- HOME CALENDAR START -->\n' + render_calendar(events, operations, today, root) + '\n<!-- HOME CALENDAR END -->'
    if '<!-- HOME CALENDAR START -->' in html:
        html = re.sub(r'<!-- HOME CALENDAR START -->.*?<!-- HOME CALENDAR END -->', lambda _: markup, html, count=1, flags=re.S)
    else:
        pattern = r'<!-- Top 3 Upcoming Schedule Items -->.*?(?=<div style="text-align: center;">)'
        html, count = re.subn(pattern, lambda _: markup + '\n            ', html, count=1, flags=re.S)
        if count != 1:
            raise ValueError('Homepage lineup block missing')
    if 'home-calendar.css' not in html:
        html = html.replace('</head>', '<link rel="stylesheet" href="home-calendar.css">\n</head>', 1)
    if 'home-calendar.js' not in html:
        html = html.replace('</body>', '<script src="home-calendar.js"></script>\n</body>', 1)
    return html
