import copy
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'automation'))
from home_calendar import render_calendar, rebuild_home_calendar, month_shift

ROOT = Path(__file__).resolve().parents[1]
OPS = {'timezone': 'Asia/Tokyo', 'closed_policy': 'irregular',
       'standard_hours': {'open': '19:00', 'close': '01:00'}, 'overrides': {}}


class HomeCalendarTests(unittest.TestCase):
    def test_year_boundary_multiday_and_order(self):
        events = [{'id': 'test', 'date': '2026-12-31', 'end_date': '2027-01-02',
                   'title': 'Test & Live', 'status': 'published'}]
        html = render_calendar(events, OPS, date(2026, 12, 3), ROOT)
        self.assertEqual(html.count('href="/events/test/"'), 3)
        self.assertIn('Test &amp; Live', html)
        self.assertLess(html.index('data-calendar-month="2026-12"'), html.index('data-calendar-month="2027-01"'))
        self.assertEqual(month_shift(date(2026, 12, 31), 1), date(2027, 1, 1))

    def test_closure_priority_cancelled_draft_and_no_input_changes(self):
        ops = copy.deepcopy(OPS)
        ops['overrides']['2026-10-14'] = {'state': 'closed', 'note': '<closed>'}
        events = [{'id': str(i), 'date': '2026-10-14', 'title': 'hidden', 'status': status}
                  for i, status in enumerate(['published', 'cancelled', 'draft'])]
        original = copy.deepcopy((events, ops))
        html = render_calendar(events, ops, date(2026, 10, 7), ROOT)
        self.assertNotIn('hidden</a>', html)
        self.assertIn('休業', html)
        self.assertIn('&lt;closed&gt;', html)
        self.assertIn('通常営業', html)
        self.assertIn('19:00–翌01:00', html)
        self.assertEqual(original, (events, ops))

    def test_empty_future_not_invented_and_leap_day(self):
        html = render_calendar([], OPS, date(2028, 2, 1), ROOT)
        self.assertIn('data-calendar-date="2028-02-29"', html)
        self.assertIn('予定の登録なし', html)
        self.assertEqual(html.count('<th scope="col">'), 21)
        march = html.split('data-calendar-panel="2028-03"')[1]
        self.assertNotIn('通常営業', march)

    def test_idempotent_and_other_content_unchanged(self):
        source = '<head></head><body>BEFORE<!-- Top 3 Upcoming Schedule Items --><div>old</div><div style="text-align: center;">AFTER</div></body>'
        a = rebuild_home_calendar(source, [], OPS, date(2026, 10, 7), ROOT)
        self.assertEqual(a, rebuild_home_calendar(a, [], OPS, date(2026, 10, 7), ROOT))
        self.assertIn('BEFORE', a)
        self.assertIn('AFTER', a)
        self.assertNotIn('<img', a)


if __name__ == '__main__':
    unittest.main()
