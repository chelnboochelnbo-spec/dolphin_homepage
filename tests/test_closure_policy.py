import copy
import json
import re
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'automation'))
from home_calendar import render_calendar
from render_operating_schedule import build_days, regular_closure, validate_operations

OPS = json.loads((ROOT / 'data/operations.json').read_text())
EVENTS = json.loads((ROOT / 'data/events.json').read_text())['events']


class ClosurePolicyTests(unittest.TestCase):
    def test_confirmed_holiday_shifts_and_no_bridge_day(self):
        for sunday, final in [('2026-10-11', '2026-10-12'), ('2026-11-22', '2026-11-23'),
                              ('2027-01-10', '2027-01-11'), ('2027-03-21', '2027-03-22'),
                              ('2027-05-02', '2027-05-05')]:
            self.assertFalse(regular_closure(date.fromisoformat(sunday), OPS), sunday)
            self.assertTrue(regular_closure(date.fromisoformat(final), OPS), final)
        self.assertTrue(regular_closure(date(2027, 2, 21), OPS))
        self.assertFalse(regular_closure(date(2027, 2, 23), OPS))
        self.assertTrue(regular_closure(date(2027, 1, 3), OPS))
        self.assertFalse(regular_closure(date(2026, 10, 4), OPS))

    def test_complete_visible_calendar_and_preserved_events(self):
        original = copy.deepcopy((OPS, EVENTS))
        html = render_calendar(EVENTS, OPS, date(2026, 10, 8), ROOT)
        cells = dict(re.findall(r'<td data-calendar-date="([^"]+)"[^>]*>(.*?)</td>', html))
        rows = {day.isoformat(): value for month in build_days(EVENTS, OPS, date(2026, 10, 8),
                lambda event: event['title']).values() for day, value in month}
        closed = ['2026-10-12', '2026-10-14', '2026-10-18', '2026-10-25', '2026-11-23',
                  '2027-01-03', '2027-01-11', '2027-03-22']
        opened = ['2026-10-26', '2026-10-27', '2026-10-28', '2027-01-10', '2027-03-21']
        for value in closed:
            self.assertIn('休業', cells[value])
            self.assertIn('休業', rows[value])
            self.assertNotIn('通常営業', cells[value])
        for value in opened:
            self.assertIn('通常営業', cells[value])
            self.assertIn('通常営業', rows[value])
        for value, title in [('2026-10-11', '鈴木千明'), ('2026-11-22', 'BIG APPLE'),
                             ('2026-12-27', '中山拓海')]:
            self.assertIn(title, cells[value])
            self.assertIn(title, rows[value])
            self.assertNotIn('休業', cells[value])
        self.assertEqual(original, (OPS, EVENTS))

    def test_explicit_open_private_and_closure_priority(self):
        for state, label in [('open', '通常営業'), ('bar', '通常営業'), ('private', '貸切営業'), ('closed', '休業')]:
            ops = copy.deepcopy(OPS)
            ops['overrides']['2026-11-01'] = {'state': state}
            rows = dict(build_days([], ops, date(2026, 11, 1), lambda event: '')[11])
            self.assertIn(label, rows[date(2026, 11, 1)])
        ops = copy.deepcopy(OPS)
        ops['overrides']['2026-12-27'] = {'state': 'closed'}
        row = dict(build_days(EVENTS, ops, date(2026, 12, 27), lambda event: event['title'])[12])[date(2026, 12, 27)]
        self.assertIn('休業', row)
        self.assertNotIn('中山拓海', row)

    def test_no_unverified_holiday_guesses(self):
        validate_operations(OPS)
        with self.assertRaises(ValueError):
            regular_closure(date(2028, 1, 2), OPS)
        ops = copy.deepcopy(OPS)
        ops['closure_rule']['holiday_calendar']['dates'].append('2028-01-01')
        with self.assertRaises(ValueError):
            validate_operations(ops)

    def test_javascript_and_python_match_every_verified_future_day(self):
        days = []
        current = date(2026, 10, 8)
        while current <= date(2027, 12, 31):
            days.append(current.isoformat())
            current += timedelta(days=1)
        program = """
const fs=require('fs'),vm=require('vm');
const context={document:{addEventListener(){}},Intl,Date};vm.createContext(context);
vm.runInContext(fs.readFileSync('script.js','utf8'),context);
const data=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(data.days.map(day=>context.isRegularClosure(day,data.operations))));
"""
        js = json.loads(subprocess.check_output(['node', '-e', program], cwd=ROOT,
                        input=json.dumps({'days': days, 'operations': OPS}), text=True))
        self.assertEqual(js, [regular_closure(date.fromisoformat(day), OPS) for day in days])


if __name__ == '__main__':
    unittest.main()
