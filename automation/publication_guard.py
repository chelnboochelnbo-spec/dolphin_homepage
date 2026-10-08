"""Fail-closed media publication. A path/ready flag is never visual evidence.

The ledger is a reviewed human/agent attestation, not automatic OCR validation.
All callers verify current bytes and all approved target facts on every use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACT_FIELDS = ("id", "date", "end_date", "open", "start", "charge", "performers",
               "title", "event_type", "status", "cancelled", "cancellation", "display")
PUBLIC_STATUSES = {"ready", "published", "archived"}


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default


def event_facts(event: dict) -> dict:
    return {key: event.get(key) for key in FACT_FIELDS}


def fingerprint(event: dict) -> str:
    raw = json.dumps(event_facts(event), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_tombstoned(event: dict, root: Path = ROOT) -> bool:
    for item in read_json(root / "data/publication_tombstones.json", {"events": []})["events"]:
        if event.get("id") == item["event_id"] or (
            event.get("date") == item["date"] and
            str(event.get("title", "")).strip().casefold() == item["title"].strip().casefold()
        ):
            return True
    return False


def event_publishable(event: dict, root: Path = ROOT) -> bool:
    return (event.get("status") in PUBLIC_STATUSES and not event.get("cancelled")
            and not event.get("cancellation") and not is_tombstoned(event, root))


def image_file(path: str, root: Path) -> Path:
    # Only repository bytes can be attested; reject URLs, traversal and logos.
    if not isinstance(path, str) or not path or ":" in path or "\\" in path:
        raise ValueError("missing or non-local image")
    relative = Path(path.lstrip("/"))
    if ".." in relative.parts or "logo" in relative.name.casefold():
        raise ValueError("fallback or unsafe image")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("missing or unsafe image")
    if resolved.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("unsupported image")
    return resolved


def image_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aware_timestamp(value: str) -> bool:
    try:
        return datetime.fromisoformat(value).utcoffset() is not None
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    path: str = ""
    sha256: str = ""
    review_id: str = ""
    targets: tuple[str, ...] = ()
    evidence_kind: str = "visual_review"


def assess(event: dict, root: Path = ROOT, *, events=None, ledger=None) -> Decision:
    try:
        if not event_publishable(event, root):
            raise ValueError("event is draft, cancelled or tombstoned")
        path = (event.get("flyer") or {}).get("github_path")
        media = image_file(path, root)
        digest = image_sha(media)
        events = events if events is not None else read_json(root / "data/events.json", {"events": []})["events"]
        by_id = {item["id"]: item for item in events}
        by_id[event["id"]] = event
        ledger = ledger if ledger is not None else read_json(root / "data/flyer_verifications.json", {"reviews": []})
        matches = [r for r in ledger["reviews"] if event["id"] in r.get("targets", {})
                   and r.get("image_path") == path and r.get("image_sha256") == digest]
        if len(matches) != 1:
            raise ValueError("no unique current image review")
        review = matches[0]
        if review.get("kind") != "visual_review" or not review.get("reviewer") or not review.get("review_id"):
            raise ValueError("missing visual reviewer")
        if not aware_timestamp(review.get("reviewed_at")):
            raise ValueError("missing visual review timestamp")
        if not review.get("transcription", "").strip() or review.get("pixels_inspected") is not True:
            raise ValueError("missing pixel inspection or transcription")
        targets = review["targets"]
        dates = set()
        for event_id, evidence in targets.items():
            target = by_id.get(event_id)
            if not target or not event_publishable(target, root):
                raise ValueError("review target missing or cancelled")
            if evidence.get("facts") != event_facts(target) or evidence.get("fingerprint") != fingerprint(target):
                raise ValueError("event facts changed since visual review")
            if not evidence.get("observed_text", "").strip():
                raise ValueError("missing per-event observed text")
            if image_sha(image_file((target.get("flyer") or {}).get("github_path"), root)) != digest:
                raise ValueError("review target image changed")
            start = date.fromisoformat(target["date"])
            end = date.fromisoformat(target.get("end_date") or target["date"])
            if end < start or (end - start).days > 1:
                raise ValueError("unapproved date range")
            dates.update((start + timedelta(days=i)).isoformat() for i in range((end-start).days+1))
        if sorted(dates) != sorted(review.get("covered_dates", [])):
            raise ValueError("image date coverage mismatch")
        if len(targets) > 1 or len(dates) > 1:
            series = read_json(root / "automation/config.json", {}).get("publishing", {}).get("recurring_series", [])
            recurring_titles = {title for item in series for title in item["titles"]}
            if any(by_id[event_id].get("title") in recurring_titles for event_id in targets):
                raise ValueError("recurring flyers must be single-date")
            approval = review.get("shared_publication") or {}
            if (approval.get("type") != "special_two_day" or len(dates) != 2
                    or sorted(approval.get("target_event_ids", [])) != sorted(targets)
                    or approval.get("policy_version") != 1
                    or (date.fromisoformat(max(dates))-date.fromisoformat(min(dates))).days != 1):
                raise ValueError("shared image requires exact two-day publication scope")
        # A second attestation cannot silently reuse this media for another date.
        if any(r is not review and (r.get("image_sha256") == digest or r.get("review_id") == review["review_id"])
               for r in ledger["reviews"]):
            raise ValueError("duplicate media attestation; use one explicit target set")
        return Decision(True, "verified", path, digest, review["review_id"], tuple(sorted(targets)))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return Decision(False, str(exc))


def strict_website_scope(event: dict, root: Path = ROOT) -> bool:
    config = read_json(root / "automation/config.json", {})
    titles = {title for series in config.get("publishing", {}).get("recurring_series", [])
              for title in series["titles"]}
    return event.get("date", "") >= "2026-10-07" and event.get("title") in titles


def migration_decision(event: dict, root: Path = ROOT, *, october=False) -> Decision:
    """Frozen existing publication evidence, never a new visual verification."""
    try:
        if not event_publishable(event, root):
            raise ValueError("inactive event")
        name = "october_kiraku_migration.json" if october else "website_image_baseline.json"
        document = read_json(root / "data" / name, {"records": []})
        matches = [r for r in document["records"] if event["id"] in r.get("targets", {})]
        if len(matches) != 1:
            raise ValueError("no unique migration record")
        record = matches[0]
        if not october and strict_website_scope(event, root):
            raise ValueError("future recurring image requires visual verification")
        if october and (set(record.get("covered_dates", [])) != {"2026-10-08", "2026-10-22"}
                        or record.get("website_preservation") != {
                            "policy_version": 1, "scope": "exact_existing_asset_and_dates"}):
            raise ValueError("not the approved October exception")
        events = {e["id"]: e for e in read_json(root / "data/events.json", {"events": []})["events"]}
        events[event["id"]] = event
        dates = set()
        for event_id, evidence in record["targets"].items():
            target = events[event_id]
            if not event_publishable(target, root) or evidence["facts"] != event_facts(target) or evidence["fingerprint"] != fingerprint(target):
                raise ValueError("migration facts changed")
            if (target.get("flyer") or {}).get("github_path") != record["source_path"]:
                raise ValueError("migration source path changed")
            if october and target.get("title") != "Kiraku Jam":
                raise ValueError("October exception is Kiraku only")
            dates.add(target["date"])
        if sorted(dates) != sorted(record["covered_dates"]):
            raise ValueError("migration date set changed")
        path = record["image_path"]
        if image_sha(image_file(path, root)) != record["image_sha256"]:
            raise ValueError("migration image bytes changed")
        kind = "october_existing_publication" if october else "website_baseline_unverified"
        return Decision(True, kind, path, record["image_sha256"], record["record_id"],
                        tuple(sorted(record["targets"])), kind)
    except (KeyError, ValueError, TypeError, OSError) as exc:
        return Decision(False, str(exc))


def website_decision(event: dict, root: Path = ROOT, *, events=None) -> Decision:
    verified = assess(event, root, events=events)
    if verified.allowed:
        return verified
    october = migration_decision(event, root, october=True)
    if october.allowed:
        return october
    return migration_decision(event, root)


def verified_flyer_path(event: dict, root: Path = ROOT) -> str:
    # Historical name retained for renderer compatibility; callers must not
    # interpret website baseline permission as visual/SNS verification.
    return website_decision(event, root).path


def audit(root: Path = ROOT) -> list[dict]:
    events = read_json(root / "data/events.json", {"events": []})["events"]
    # A changed status must not revive a cancellation even before HTML generation.
    for event in events:
        if is_tombstoned(event, root) and event.get("status") in PUBLIC_STATUSES:
            raise ValueError(f"Cancelled event revived: {event['id']}")
    return [{"event_id": e["id"], "image_allowed": (d := website_decision(e, root, events=events)).allowed,
             "reason": d.reason, "evidence_kind": d.evidence_kind,
             "visual_verified": assess(e, root, events=events).allowed} for e in events]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(audit(args.root), ensure_ascii=False, indent=2))
