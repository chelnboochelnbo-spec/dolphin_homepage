import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import date
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'automation'))
import render_events
import render_event_pages

class Options(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'option' and attrs.get('data-date'):
            self.ids.append(attrs['value'])

class Reservations(unittest.TestCase):
    def test_month_headers_cross_year_boundary(self):
        html = '<section id="jan" class="lineup-month-group">\n<h2 class="lineup-month-header">1<span>JANUARY 2026</span></h2>'
        events = [{'date': '2027-01-02', 'status': 'published'}]
        with patch('event_utils.current_jst_date', return_value=date(2026, 10, 5)):
            rendered = render_events.sync_month_years(html, events)
            self.assertIn('JANUARY 2027', rendered)
            self.assertEqual(rendered, render_events.sync_month_years(rendered, events))

    def test_options_and_regeneration(self):
        events = json.loads((ROOT / 'data/events.json').read_text(encoding='utf-8'))['events']
        html = '<select id="event"><option>Old event</option></select>'
        with patch('event_utils.current_jst_date', return_value=date(2026, 10, 5)):
            rendered = render_events.sync_reservation_options(html, events)
            self.assertEqual(rendered, render_events.sync_reservation_options(rendered, events))
            parser = Options()
            parser.feed(rendered)
            expected = [e['id'] for e in events if e['status'] in {'ready','published','archived'} and (e.get('end_date') or e['date']) >= '2026-10-05']
            self.assertCountEqual(expected, parser.ids)
    def test_event_handoff_survives_regeneration(self):
        events = json.loads((ROOT / 'data/events.json').read_text(encoding='utf-8'))['events']
        event = next(e for e in events if e['date'] == '2026-11-03')
        self.assertIn('/?event_id=' + event['id'] + '#reservation', render_events.render_schedule_article(event))
        with patch('render_event_pages.event_is_past', return_value=False):
            self.assertIn('/en/?event_id=' + event['id'] + '#reservation', render_event_pages.render(event, {}))

if __name__ == '__main__':
    unittest.main()
