"""Prepare guarded SNS requests and verify connector readback. Does not send.

The external scheduler must adopt this contract; this CLI alone is not a live
integration. Keep one serialized writer for the publication state file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from publication_guard import ROOT, assess, aware_timestamp, fingerprint, read_json


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def lead_days(event: dict, config: dict) -> list[int]:
    publishing = config["publishing"]
    for series in publishing.get("recurring_series", []):
        if event.get("title") in series["titles"]:
            return series["days_before"]
    key = "session" if event["event_type"] == "session" else (
        "important_live" if event.get("importance") == "important" else "normal_live")
    return publishing[key]


def prepare(event_id: str, channel: str, channel_id: str, days: int,
            state: dict, root: Path = ROOT) -> dict:
    if channel not in {"instagram", "facebook"} or not channel_id.strip():
        raise ValueError("Resolved channel and channel ID required")
    events = read_json(root / "data/events.json", {"events": []})["events"]
    by_id = {e["id"]: e for e in events}
    event = by_id[event_id]
    review = assess(event, root, events=events)
    if not review.allowed:
        raise ValueError(f"Publication blocked: {review.reason}")
    config = read_json(root / "automation/config.json", {})
    if days not in lead_days(event, config):
        raise ValueError("Unapproved lead time for this series")
    targets = list(review.targets)
    # A shared special flyer produces one package, not one copy per event.
    anchor = min(date.fromisoformat(by_id[i]["date"]) for i in targets)
    publish_at = datetime.combine(anchor-timedelta(days=days),
                                  time.fromisoformat(config["publishing"]["post_time"]),
                                  ZoneInfo(config["timezone"])).isoformat()
    captions = {str((by_id[i].get("social") or {}).get(channel+"_caption") or "").strip()
                for i in targets}
    if len(captions) != 1 or not next(iter(captions)):
        raise ValueError("Approved, identical caption required for every target")
    caption = next(iter(captions))
    for target_id in targets:
        approval = ((by_id[target_id].get("social") or {}).get("approvals") or {}).get(channel, {})
        if (approval.get("caption_sha256") != hashlib.sha256(caption.encode()).hexdigest()
                or approval.get("review_id") != review.review_id or not approval.get("approved_by")
                or not aware_timestamp(approval.get("approved_at"))):
            raise ValueError("Current caption and reviewed image need recorded social approval")
    key = digest([targets, channel, channel_id, days])
    desired = {"event_ids": targets, "channel": channel, "channel_id": channel_id,
               "publish_at": publish_at, "caption": caption, "image_path": review.path,
               "image_sha256": review.sha256,
               "event_fingerprints": {i: fingerprint(by_id[i]) for i in targets}}
    package_hash = digest(desired)
    records = state.get("records", [])
    matches = [r for r in records if r["key"] == key]
    if len(matches) > 1:
        raise ValueError("Duplicate publication key")
    previous = matches[0] if matches else None
    for record in records:
        if record["key"] == key:
            continue
        same_account = record["channel"] == channel and record["channel_id"] == channel_id
        if same_account and record.get("image_sha256") == review.sha256 and (
            record.get("event_ids") != targets or record.get("publish_at") == publish_at
        ):
            raise ValueError("Duplicate media for channel/account/target or time")
    legacy_slots = [slot for i in targets
                    for slot in (by_id[i].get("social") or {}).get("schedule", [])
                    if slot.get("channel") == channel and slot.get("external_id")
                    and slot.get("status") != "cancelled"]
    for slot in legacy_slots:
        resolved_previous = (previous and previous.get("external_id") == str(slot["external_id"])
                             and previous.get("channel_id") == channel_id)
        if slot.get("channel_id") != channel_id and not resolved_previous:
            raise ValueError("Existing post account unresolved: reconcile its channel ID first")
    legacy_ids = {str(slot["external_id"]) for slot in legacy_slots}
    if len(legacy_ids) > 1:
        raise ValueError("Multiple existing posts: resolve the exact correction target first")
    external_id = (previous or {}).get("external_id") or next(iter(legacy_ids), None)
    if previous and previous.get("external_id") and legacy_ids and external_id not in legacy_ids:
        raise ValueError("Existing post identity conflict")
    for record in records:
        if (record["key"] != key and external_id and record.get("external_id") == external_id
                and record["channel"] == channel and record["channel_id"] == channel_id):
            raise ValueError("External post already belongs to another publication key")
    if previous and not external_id:
        raise ValueError("Earlier request unresolved: reconcile before creating another post")
    action = "update" if external_id else "create"
    if previous and previous.get("state") == "confirmed" and previous.get("package_hash") == package_hash:
        action = "noop"
    return {**desired, "key": key, "package_hash": package_hash, "action": action,
            "external_id": external_id, "days_before": days, "state": "prepared",
            "prepared_at": datetime.now(ZoneInfo("UTC")).isoformat(),
            "integration": "external_adapter_required", "review_id": review.review_id}


def verify_readback(package: dict, response: dict) -> dict:
    """Only an independently fetched final scheduler object can confirm a request."""
    if response.get("readback") is not True or not response.get("fetched_at"):
        raise ValueError("An acknowledgement is not readback")
    fetched = datetime.fromisoformat(response["fetched_at"])
    if fetched.utcoffset() is None:
        raise ValueError("Readback time must include timezone")
    if fetched < datetime.fromisoformat(package["prepared_at"]):
        raise ValueError("Readback predates this request")
    if response.get("status") not in {"scheduled", "published"} or not response.get("external_id"):
        raise ValueError("Scheduler has not confirmed final state")
    if package.get("external_id") and str(response["external_id"]) != str(package["external_id"]):
        raise ValueError("Correction changed external post ID")
    for key in ("channel", "channel_id", "event_ids", "publish_at", "caption", "image_sha256"):
        if response.get(key) != package[key]:
            raise ValueError(f"Readback differs: {key}")
    return {**package, "external_id": str(response["external_id"]), "state": "confirmed",
            "verified_at": response["fetched_at"], "remote_status": response["status"],
            "public_url": response.get("public_url")}


def validate_pending_package(package: dict, existing: dict, checked: dict):
    """Bind a completion to the exact saved request and freshly checked content."""
    fields = ("key", "package_hash", "event_ids", "channel", "channel_id", "days_before",
              "publish_at", "caption", "image_path", "image_sha256", "event_fingerprints",
              "review_id", "prepared_at", "action")
    if not existing or any(package.get(k) != existing.get(k) for k in fields):
        raise ValueError("Stale, modified or unknown package")
    current_fields = tuple(k for k in fields if k not in {"prepared_at", "action"})
    if any(package.get(k) != checked.get(k) for k in current_fields):
        raise ValueError("Image, facts or caption changed while request was pending")


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temp.replace(path)


@contextmanager
def state_lock(path: Path):
    handle = path.open("x")
    try:
        yield
    finally:
        handle.close()
        path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--state", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("prepare")
    create.add_argument("--event-id", required=True)
    create.add_argument("--channel", required=True, choices=["instagram", "facebook"])
    create.add_argument("--channel-id", required=True)
    create.add_argument("--days-before", required=True, type=int)
    create.add_argument("--output", type=Path, required=True)
    for verb in ("accept", "confirm"):
        command = sub.add_parser(verb)
        command.add_argument("--package", type=Path, required=True)
        command.add_argument("--response", type=Path, required=True)
    args = parser.parse_args()
    state_path = args.state or args.root / "data/social_publications.json"
    # Atomic exclusive lock prevents concurrent scheduler requests creating duplicates.
    lock = state_path.with_suffix(".lock")
    with state_lock(lock):
        try:
            state = read_json(state_path, {"schema_version": 1, "records": []})
            if args.command == "prepare":
                package = prepare(args.event_id, args.channel, args.channel_id, args.days_before, state, args.root)
            else:
                package = read_json(args.package, {})
                response = read_json(args.response, {})
                existing = next((r for r in state["records"] if r["key"] == package["key"]), None)
                # Recheck image bytes/facts at completion, not only at preparation.
                checked = prepare(package["event_ids"][0], package["channel"], package["channel_id"],
                                  package["days_before"], {"records": []}, args.root)
                validate_pending_package(package, existing, checked)
                if args.command == "confirm":
                    package = verify_readback({**package, "external_id": existing.get("external_id")}, response)
                else:
                    if not response.get("external_id") or response.get("channel_id") != package["channel_id"] or response.get("channel") != package["channel"]:
                        raise ValueError("Acknowledgement requires resolved post/channel IDs")
                    if existing.get("external_id") and str(response["external_id"]) != str(existing["external_id"]):
                        raise ValueError("Correction must update existing post")
                    package = {**package, "external_id": str(response["external_id"]), "state": "accepted_pending_readback"}
            if args.command == "prepare" and package["action"] == "noop":
                write_json(args.output, package)
                print(json.dumps({"key": package["key"], "action": "noop", "state": "confirmed"}))
                return
            for record in state["records"]:
                if (record["key"] != package["key"] and package.get("external_id")
                        and record.get("external_id") == package["external_id"]
                        and record["channel"] == package["channel"]
                        and record["channel_id"] == package["channel_id"]):
                    raise ValueError("Duplicate external post/channel ID")
            state["records"] = [r for r in state["records"] if r["key"] != package["key"]] + [package]
            write_json(state_path, state)
            if args.command == "prepare":
                write_json(args.output, package)
            print(json.dumps({"key": package["key"], "state": package["state"], "action": package["action"]}))
        finally:
            # On Windows the lock handle must be closed before unlink.
            pass


if __name__ == "__main__":
    main()
