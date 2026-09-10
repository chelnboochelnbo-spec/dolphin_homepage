from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
EVENT_TYPE_LABELS = {
    "live": "LIVE",
    "session": "SESSION",
    "live_session": "LIVE & SESSION",
}


def normalize_event_type(event: dict) -> str:
    value = event.get("event_type")
    if value in EVENT_TYPE_LABELS:
        return value
    legacy = str(event.get("type") or "").strip().upper().replace(" ", "")
    if "LIVE" in legacy and "SESSION" in legacy:
        return "live_session"
    if "SESSION" in legacy:
        return "session"
    if legacy == "LIVE":
        return "live"
    raise ValueError(f"Unknown event_type for {event.get('id')}: {value or event.get('type')}")


def event_type_label(event_or_type) -> str:
    if isinstance(event_or_type, dict):
        value = normalize_event_type(event_or_type)
    else:
        value = str(event_or_type)
    return EVENT_TYPE_LABELS[value]


def current_jst_date(now: datetime | None = None) -> date:
    if now is None:
        now = datetime.now(JST)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=JST)
    else:
        now = now.astimezone(JST)
    return now.date()


def event_end_date(event: dict) -> date:
    return date.fromisoformat(event.get("end_date") or event["date"])


def event_start_date(event: dict) -> date:
    return date.fromisoformat(event["date"])


def event_is_past(event: dict, today: date | None = None) -> bool:
    # Archive only after the full local calendar day (or end_date for multi-day events) has ended.
    today = today or current_jst_date()
    return event_end_date(event) < today


def event_is_upcoming_or_current(event: dict, today: date | None = None) -> bool:
    return not event_is_past(event, today=today)
