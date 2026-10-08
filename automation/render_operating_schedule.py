"""Render opening days as well as events, using the existing operations record.

Run after render_events.py. No business dates or event facts are written here.
"""
from __future__ import annotations

import calendar
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from html import escape
from pathlib import Path
from typing import Callable
from publication_guard import event_publishable

ROOT = Path(__file__).resolve().parents[1]
MONTH_IDS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
WEEKDAYS = ['月', '火', '水', '木', '金', '土', '日']
VISIBLE_STATUSES = {'ready', 'published', 'archived'}
STYLES = '''<style id="operating-schedule-styles">
.operating-schedule-note{color:#555;font-size:.9rem;line-height:1.8;margin:0 0 2rem}
.lineup-item.operating-day{display:flex;align-items:center;gap:1.5rem;padding:1rem 1.25rem;min-height:0;border-bottom:1px solid #ddd}
.operating-day .lineup-date{font-size:1.2rem;min-width:145px;margin:0;padding:0;flex-shrink:0}
.operating-day .lineup-date .weekday{font-size:.85rem;margin-left:.4rem}
.operating-day .lineup-body{display:block;min-width:0;flex:1}
.operating-day .lineup-artist{font-size:1.05rem;line-height:1.5;margin:0}
.operating-day .lineup-details{font-size:.85rem;line-height:1.6;margin:.25rem 0 0}
.lineup-item.operating-day--closed{background:#f2f2f2;border-left:4px solid #666}
.lineup-item.operating-day--private{background:#f7f4ec;border-left:4px solid #8b7651}
.operating-day a{color:inherit}
@media(max-width:600px){.lineup-item.operating-day{gap:.75rem;padding:.85rem .65rem}.operating-day .lineup-date{min-width:105px;font-size:1rem}.operating-day .lineup-artist{font-size:.95rem}}
</style>'''


def rename_schedule(html: str) -> str:
    return html.replace('LIVE SCHEDULE', 'SCHEDULE').replace('Live Schedule', 'Schedule').replace('ライブスケジュール', 'スケジュール')


def validate_operations(operations: dict) -> None:
    if operations.get('timezone') != 'Asia/Tokyo':
        raise ValueError('Operations timezone must be Asia/Tokyo')
    if operations.get('closed_policy') not in {'irregular', 'sunday_holiday_end'}:
        raise ValueError('A changed closure policy needs an explicit schedule rule')
    if operations.get('closed_policy') == 'sunday_holiday_end':
        rule = operations['closure_rule']
        date.fromisoformat(rule['effective_from'])
        holidays = rule['holiday_calendar']
        first, last = date.fromisoformat(holidays['valid_from']), date.fromisoformat(holidays['valid_through'])
        if first > last or not holidays.get('source'):
            raise ValueError('Verified holiday calendar coverage is required')
        for value in holidays['dates']:
            if not first <= date.fromisoformat(value) <= last:
                raise ValueError('Holiday outside verified calendar coverage')
    hours = operations.get('standard_hours', {})
    for key in ('open', 'close'):
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', str(hours.get(key, ''))):
            raise ValueError(f'Invalid standard_hours.{key}')
    overrides = operations.get('overrides', {})
    if not isinstance(overrides, dict):
        raise ValueError('Operations overrides must be a date-keyed object')
    for day, override in overrides.items():
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError('Override dates must use YYYY-MM-DD')
        if not isinstance(override, dict) or override.get('state') not in {'closed', 'private', 'open', 'bar'}:
            raise ValueError(f'Unknown operating state for {day}')


def regular_closure(day: date, operations: dict) -> bool:
    """Sunday closes unless contiguous public holidays move it to their last day.

    Explicit overrides and published events are resolved by callers first.
    Do not retroactively change historical operating days or guess future holidays.
    """
    if operations.get('closed_policy') != 'sunday_holiday_end':
        return False
    rule = operations['closure_rule']
    if day < date.fromisoformat(rule['effective_from']):
        return False
    calendar_data = rule['holiday_calendar']
    if not date.fromisoformat(calendar_data['valid_from']) <= day <= date.fromisoformat(calendar_data['valid_through']):
        raise ValueError('Update the verified Japanese holiday calendar before publishing this date')
    holidays = set(calendar_data['dates'])
    closure = day - timedelta(days=(day.weekday() + 1) % 7)
    while (closure + timedelta(days=1)).isoformat() in holidays:
        closure += timedelta(days=1)
    return day == closure


def operating_row(day: date, state: str, title: str, note: str = '', event_id: str = '') -> str:
    label = escape(title)
    if event_id:
        label = f'<a href="/events/{escape(event_id, quote=True)}/">{label}</a>'
    detail = f'<div class="lineup-details">{escape(note)}</div>' if note else ''
    return (
        f'<article class="lineup-item operating-day operating-day--{state}" '
        f'data-date="{day.isoformat()}" data-end-date="{day.isoformat()}" data-operating-state="{state}">'
        f'<div class="lineup-date">{day.year} {day.month}.{day.day:02d}'
        f'<span class="weekday">（{WEEKDAYS[day.weekday()]}）</span></div>'
        f'<div class="lineup-body"><div class="lineup-info"><h3 class="lineup-artist">{label}</h3>'
        f'{detail}</div></div></article>'
    )


def build_days(events: list[dict], operations: dict, today: date,
               render_event: Callable[[dict], str]) -> dict[int, list[tuple[date, str]]]:
    """Fill today through the last published event/override month, never past days."""
    validate_operations(operations)
    overrides = operations.get('overrides', {})
    visible = []
    for event in events:
        if not event_publishable(event, ROOT):
            continue
        start = date.fromisoformat(event['date'])
        end = date.fromisoformat(event.get('end_date') or event['date'])
        if end < start:
            raise ValueError(f'Invalid event date range: {event["id"]}')
        if end >= today:
            visible.append((start, end, event))
    visible.sort(key=lambda item: (item[0], item[2]['title'], item[2]['id']))
    last_day = max([today] + [end for _, end, _ in visible] + [date.fromisoformat(day) for day in overrides])
    last_day = last_day.replace(day=calendar.monthrange(last_day.year, last_day.month)[1])
    hours = operations['standard_hours']
    close_prefix = '翌' if hours['close'] <= hours['open'] else ''
    normal_hours = f'{hours["open"]}–{close_prefix}{hours["close"]}'
    months = defaultdict(list)
    day = today
    shown_events = set()
    while day <= last_day:
        override = overrides.get(day.isoformat(), {})
        state = override.get('state')
        if state in {'closed', 'private'}:
            title = '休業' if state == 'closed' else '貸切営業'
            rows = [operating_row(day, state, title, override.get('note') or '')]
        else:
            matches = [(start, end, event) for start, end, event in visible if start <= day <= end]
            rows = []
            for _, _, event in matches:
                if event['id'] not in shown_events:
                    # Preserve the full original event card and its actual date range.
                    rows.append(render_event(event))
                    shown_events.add(event['id'])
                else:
                    rows.append(operating_row(day, 'event', event['title'], '開催日・詳細はイベントページをご確認ください。', event['id']))
            if not rows:
                if state not in {'open', 'bar'} and regular_closure(day, operations):
                    rows = [operating_row(day, 'closed', '休業')]
                else:
                    rows = [operating_row(day, 'bar', '通常営業', normal_hours)]
        months[day.month].append((day, '\n'.join(rows)))
        day += timedelta(days=1)
    return dict(months)


def render_schedule(html: str, events: list[dict], operations: dict, today: date,
                    render_event: Callable[[dict], str]) -> str:
    months = build_days(events, operations, today, render_event)
    html = rename_schedule(html)
    for month, month_id in enumerate(MONTH_IDS, 1):
        entries = months.get(month, [])
        years = sorted({day.year for day, _ in entries})
        if not years:
            years = [today.year + (month < today.month)]
        year_label = ' / '.join(map(str, years))
        body = '\n'.join(row for _, row in entries)
        if not body:
            body = '<p class="operating-schedule-note">この月のスケジュールは順次更新します。</p>'
        section = (
            f'<section id="{month_id}" class="lineup-month-group">\n'
            f'<h2 class="lineup-month-header">{month}<span>{calendar.month_name[month].upper()} {year_label}</span></h2>\n'
            f'<div class="lineup-list">\n{body}\n</div>\n</section>'
        )
        pattern = rf'<section id="{month_id}" class="lineup-month-group">.*?</section>'
        html, count = re.subn(pattern, lambda _: section, html, count=1, flags=re.S)
        if count != 1:
            raise ValueError(f'Schedule month section missing: {month_id}')
    html = re.sub(r'<style id="operating-schedule-styles">.*?</style>\s*', '', html, flags=re.S)
    if '</head>' not in html:
        raise ValueError('Schedule head is missing')
    html = html.replace('</head>', STYLES + '\n</head>', 1)
    html = re.sub(r'<p id="operating-schedule-note"[^>]*>.*?</p>\s*', '', html, flags=re.S)
    policy_note = ('原則日曜休業。翌日から祝日・休日が続く場合は連休最終日を休業とします。'
                   'ライブ・イベント開催日は営業します。'
                   if operations.get('closed_policy') == 'sunday_holiday_end' else '不定休。')
    note = ('<p id="operating-schedule-note" class="operating-schedule-note">'
            'ライブ・セッション・通常営業・休業日をご案内します。日付は営業開始日を表示しています。'
            + policy_note + '休業日は「休業」と表示します。</p>\n')
    marker = '<!-- Month Navigation -->'
    if marker not in html:
        raise ValueError('Schedule month navigation marker is missing')
    return html.replace(marker, note + marker, 1)


def main() -> None:
    from event_utils import current_jst_date
    from render_events import load_events, render_schedule_article

    operations = json.loads((ROOT / 'data/operations.json').read_text(encoding='utf-8-sig'))
    schedule_path = ROOT / 'schedule.html'
    index_path = ROOT / 'index.html'
    rendered = render_schedule(schedule_path.read_text(encoding='utf-8-sig'), load_events(), operations,
                               current_jst_date(), render_schedule_article)
    index = rename_schedule(index_path.read_text(encoding='utf-8-sig'))
    # This renderer changes presentation only; neither canonical data file is written.
    schedule_path.write_text(rendered, encoding='utf-8')
    index_path.write_text(index, encoding='utf-8')


if __name__ == '__main__':
    main()
