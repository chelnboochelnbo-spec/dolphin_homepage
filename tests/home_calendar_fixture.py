"""Render an isolated browser fixture without rewriting any published files."""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'automation'))
from home_calendar import rebuild_home_calendar

today = date.fromisoformat(sys.argv[1])
events = json.loads((ROOT / 'data/events.json').read_text(encoding='utf-8-sig'))['events']
operations = json.loads((ROOT / 'data/operations.json').read_text(encoding='utf-8-sig'))
print(rebuild_home_calendar((ROOT / 'index.html').read_text(encoding='utf-8-sig'),
                            events, operations, today, ROOT))
