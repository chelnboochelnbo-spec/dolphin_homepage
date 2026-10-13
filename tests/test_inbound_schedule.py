import json
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'automation'))
from render_operating_schedule import regular_closure

class EnglishClosureParity(unittest.TestCase):
    def test_english_rule_matches_canonical_calendar(self):
        ops = json.loads((ROOT / 'data/operations.json').read_text())
        first = date.fromisoformat(ops['closure_rule']['effective_from'])
        last = date.fromisoformat(ops['closure_rule']['holiday_calendar']['valid_through'])
        days = [first + timedelta(days=i) for i in range((last-first).days + 1)]
        program = """
const fs = require('fs');
const {isRegularClosure} = require('./reservations.js');
const {days, operations} = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(days.map(day => isRegularClosure(day, operations))));
"""
        output = subprocess.check_output(['node','-e',program], cwd=ROOT, text=True,
            input=json.dumps({'days':[d.isoformat() for d in days], 'operations':ops}))
        self.assertEqual(json.loads(output), [regular_closure(d, ops) for d in days])

if __name__ == '__main__':
    unittest.main()
