import copy
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'automation'))
from render_operating_schedule import MONTH_IDS, build_days, rename_schedule, render_schedule

OPS = {'timezone': 'Asia/Tokyo', 'closed_policy': 'irregular',
       'standard_hours': {'open': '19:00', 'close': '01:00'}, 'overrides': {}}


def event(day, end=None, status='published'):
    item = {'id': day + '_test', 'date': day, 'title': 'Test Live', 'status': status}
    if end:
        item['end_date'] = end
    return item


def card(item):
    return f'<article class="lineup-item" data-date="{item["date"]}" data-event-id="{item["id"]}"><h3>{item["title"]}</h3></article>'


def fixture():
    return ('<html><head><title>Live Schedule</title></head><body><h1>LIVE SCHEDULE</h1>'
            '<!-- Month Navigation -->' + ''.join(
                f'<section id="{key}" class="lineup-month-group"><div class="lineup-list"></div></section>'
                for key in MONTH_IDS) + '</body></html>')


class OperatingScheduleTests(unittest.TestCase):
    def test_regular_day_and_hours(self):
        months = build_days([], OPS, date(2026, 10, 5), card)
        self.assertEqual(len(months[10]), 27)
        self.assertIn('通常営業', months[10][0][1])
        self.assertIn('19:00–翌01:00', months[10][0][1])
        self.assertNotIn('休業', months[10][0][1])

    def test_closure_takes_priority_over_event(self):
        ops = copy.deepcopy(OPS)
        ops['overrides']['2026-10-05'] = {'state': 'closed', 'note': '臨時休業'}
        row = build_days([event('2026-10-05')], ops, date(2026, 10, 5), card)[10][0][1]
        self.assertIn('休業', row)
        self.assertNotIn('Test Live', row)
        self.assertNotIn('通常営業', row)
        self.assertNotIn('19:00', row)

    def test_private_is_not_regular(self):
        ops = copy.deepcopy(OPS)
        ops['overrides']['2026-10-05'] = {'state': 'private'}
        row = build_days([], ops, date(2026, 10, 5), card)[10][0][1]
        self.assertIn('貸切営業', row)
        self.assertNotIn('通常営業', row)

    def test_multiday_and_cancelled_events(self):
        events = [event('2026-10-05', '2026-10-06'), event('2026-10-07', status='cancelled')]
        days = dict(build_days(events, OPS, date(2026, 10, 5), card)[10])
        self.assertIn('Test Live', days[date(2026, 10, 5)])
        self.assertIn('Test Live', days[date(2026, 10, 6)])
        self.assertNotIn('通常営業', days[date(2026, 10, 6)])
        self.assertIn('通常営業', days[date(2026, 10, 7)])

    def test_year_boundary_and_no_recreated_january_jam(self):
        months = build_days([event('2027-01-07')], OPS, date(2026, 12, 31), card)
        january = dict(months[1])
        self.assertIn('2027 1.02', january[date(2027, 1, 2)])
        self.assertIn('通常営業', january[date(2027, 1, 2)])
        self.assertNotIn('Test Live', january[date(2027, 1, 2)])

    def test_future_closure_extends_visible_window(self):
        ops = copy.deepcopy(OPS)
        ops['overrides']['2027-01-04'] = {'state': 'closed'}
        months = build_days([], ops, date(2026, 12, 30), card)
        self.assertIn('休業', dict(months[1])[date(2027, 1, 4)])

    def test_idempotent_and_renamed(self):
        events = [event('2026-10-08')]
        first = render_schedule(fixture(), events, OPS, date(2026, 10, 5), card)
        second = render_schedule(first, events, OPS, date(2026, 10, 5), card)
        self.assertEqual(first, second)
        self.assertNotIn('LIVE SCHEDULE', first)
        self.assertNotIn('Live Schedule', first)
        self.assertEqual(first.count('id="operating-schedule-styles"'), 1)
        self.assertEqual(first.count('id="operating-schedule-note"'), 1)
        self.assertEqual(first.count('data-event-id="2026-10-08_test"'), 1)
        self.assertEqual(rename_schedule('ライブスケジュール'), 'スケジュール')

    def test_escaped_note_and_invalid_override(self):
        ops = copy.deepcopy(OPS)
        ops['overrides']['2026-10-05'] = {'state': 'closed', 'note': '<script>alert(1)</script>'}
        row = build_days([], ops, date(2026, 10, 5), card)[10][0][1]
        self.assertNotIn('<script>', row)
        self.assertIn('&lt;script&gt;', row)
        ops['overrides']['2026-10-05']['state'] = 'unconfirmed'
        with self.assertRaises(ValueError):
            build_days([], ops, date(2026, 10, 5), card)

    def test_no_past_days_and_input_unchanged(self):
        events = [event('2026-10-01', '2026-10-06')]
        original_events, original_ops = copy.deepcopy(events), copy.deepcopy(OPS)
        months = build_days(events, OPS, date(2026, 10, 5), card)
        self.assertEqual(months[10][0][0], date(2026, 10, 5))
        self.assertEqual(events, original_events)
        self.assertEqual(OPS, original_ops)


if __name__ == '__main__':
    unittest.main()
