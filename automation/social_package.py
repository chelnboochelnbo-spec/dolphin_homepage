"""Offline SNS contract; no network sender or production scheduler integration."""
from __future__ import annotations
import argparse
import hashlib
import json
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from publication_guard import ROOT, assess, aware_timestamp, fingerprint, migration_decision, read_json, strict_website_scope


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def lead_days(event, config):
    publishing = config["publishing"]
    for series in publishing.get("recurring_series", []):
        if event.get("title") in series["titles"]:
            return series["days_before"]
    key = "session" if event["event_type"] == "session" else (
        "important_live" if event.get("importance") == "important" else "normal_live")
    return publishing[key]


def october_post(root, review_id, channel, channel_id, slot_id):
    records = read_json(root / "data/october_kiraku_migration.json", {"records": []})["records"]
    matches = [p for r in records if r["record_id"] == review_id for p in r.get("existing_posts", [])
               if p.get("channel") == channel and p.get("channel_id") == channel_id and p.get("slot_id") == slot_id]
    if len(matches) != 1:
        raise ValueError("No unique existing October reservation for this account and slot")
    return matches[0]


def content(event_id, channel, channel_id, days, root=ROOT, slot_id=None):
    """Check facts/bytes/approval only, independently of trusted identity."""
    if channel not in {"instagram", "facebook"} or not channel_id.strip():
        raise ValueError("Resolved channel and channel ID required")
    events = read_json(root / "data/events.json", {"events": []})["events"]
    by_id = {e["id"]: e for e in events}
    event = by_id[event_id]
    review = assess(event, root, events=events)
    if not review.allowed:
        review = migration_decision(event, root, october=True)
    if not review.allowed:
        raise ValueError(f"Publication blocked: {review.reason}")
    config = read_json(root / "automation/config.json", {})
    if days not in lead_days(event, config):
        raise ValueError("Unapproved lead time for this series")
    targets = list(review.targets)
    fact_targets = list(targets)
    anchor = min(date.fromisoformat(by_id[i]["date"]) for i in targets)
    publish_at = datetime.combine(anchor-timedelta(days=days), time.fromisoformat(config["publishing"]["post_time"]),
                                  ZoneInfo(config["timezone"])).isoformat()
    if review.evidence_kind == "october_existing_publication":
        existing = october_post(root, review.review_id, channel, channel_id, slot_id)
        if (event_id not in existing["event_ids"] or days != existing["days_before"]
                or not set(existing["event_ids"]).issubset(targets)
                or existing["image_sha256"] != review.sha256
                or hashlib.sha256(existing["caption"].encode()).hexdigest() != existing["caption_sha256"]):
            raise ValueError("October reservation content is outside its frozen migration scope")
        desired = {"event_ids": existing["event_ids"], "channel": channel, "channel_id": channel_id,
            "publish_at": existing["publish_at"], "caption": existing["caption"], "image_path": review.path,
            "image_sha256": review.sha256, "event_fingerprints": {i: fingerprint(by_id[i]) for i in fact_targets}}
        return {**desired, "key": digest([existing["event_ids"], channel, channel_id, slot_id]),
            "package_hash": digest(desired), "slot_id": slot_id, "days_before": days,
            "review_id": review.review_id, "evidence_kind": review.evidence_kind}, events
    captions = {str((by_id[i].get("social") or {}).get(channel+"_caption") or "").strip() for i in targets}
    if len(captions) != 1 or not next(iter(captions)):
        raise ValueError("Approved, identical caption required for every target")
    caption = next(iter(captions))
    for target_id in targets:
        approval = ((by_id[target_id].get("social") or {}).get("approvals") or {}).get(channel, {})
        if (approval.get("caption_sha256") != hashlib.sha256(caption.encode()).hexdigest()
                or approval.get("review_id") != review.review_id or not approval.get("approved_by")
                or not aware_timestamp(approval.get("approved_at"))):
            raise ValueError("Current caption and reviewed image need recorded social approval")
    slot_id = slot_id or f"lead-{days}"
    desired = {"event_ids": targets, "channel": channel, "channel_id": channel_id, "publish_at": publish_at,
        "caption": caption, "image_path": review.path, "image_sha256": review.sha256,
        "event_fingerprints": {i: fingerprint(by_id[i]) for i in targets}}
    return {**desired, "key": digest([targets, channel, channel_id, slot_id]), "package_hash": digest(desired),
        "slot_id": slot_id, "days_before": days, "review_id": review.review_id,
        "evidence_kind": review.evidence_kind}, events


def slot_matches(slot, slot_id, days, anchor):
    if slot.get("slot_id"):
        return slot["slot_id"] == slot_id
    if slot_id != f"lead-{days}":
        return False
    if slot.get("days_before") is not None:
        return slot["days_before"] == days
    if aware_timestamp(slot.get("publish_at")):
        local_day = datetime.fromisoformat(slot["publish_at"]).astimezone(ZoneInfo("Asia/Tokyo")).date()
        return (anchor-local_day).days == days
    raise ValueError("Legacy reminder slot unresolved")


def same_remote(a, b):
    if a.get("provider", "generic") != b.get("provider", "generic"):
        return False
    if a.get("provider_uuid") and b.get("provider_uuid"):
        return a["provider_uuid"] == b["provider_uuid"]
    return bool(a.get("external_id")) and str(a["external_id"]) == str(b.get("external_id"))


def collision_check(package, records):
    for record in records:
        if record["key"] == package["key"] or record["channel"] != package["channel"] or record["channel_id"] != package["channel_id"]:
            continue
        if same_remote(record, package):
            raise ValueError("External post already belongs to another publication slot")
        if record.get("image_sha256") == package["image_sha256"] and (
                record.get("event_ids") != package["event_ids"] or record.get("publish_at") == package["publish_at"]):
            raise ValueError("Duplicate media for channel/account/target or time")


def october_identity_allowed(package, root):
    if package["evidence_kind"] != "october_existing_publication":
        return
    records = read_json(root / "data/october_kiraku_migration.json", {"records": []})["records"]
    record = next(r for r in records if r["record_id"] == package["review_id"])
    if not any(p.get("channel") == package["channel"] and p.get("channel_id") == package["channel_id"]
               and p.get("provider_account_id") == package.get("provider_account_id")
               and p.get("slot_id") == package["slot_id"] and same_remote(p, package) for p in record.get("existing_posts", [])):
        raise ValueError("October exception permits only its recorded existing reservation IDs")


def prepare(event_id, channel, channel_id, days, state, root=ROOT, slot_id=None,
            *, provider=None, provider_account_id=None):
    package, events = content(event_id, channel, channel_id, days, root, slot_id)
    records = state.get("records", [])
    matches = [r for r in records if r["key"] == package["key"]]
    if len(matches) > 1:
        raise ValueError("Duplicate publication key")
    previous = matches[0] if matches else None
    anchor = min(date.fromisoformat(e["date"]) for e in events if e["id"] in package["event_ids"])
    all_slots = [s for e in events if e["id"] in package["event_ids"] for s in (e.get("social") or {}).get("schedule", [])
                 if s.get("channel") == channel and s.get("external_id") and s.get("status") != "cancelled"]
    slots = [s for s in all_slots if slot_matches(s, package["slot_id"], days, anchor)]
    old_records = [r for r in records if r.get("event_ids") == package["event_ids"]
                   and r.get("channel") == channel and r.get("channel_id") == channel_id]
    recurring = any(e["id"] == event_id and strict_website_scope(e, root) for e in events)
    if recurring and not previous and not slots and (all_slots or old_records):
        raise ValueError("Existing recurring reminder needs an explicit cadence slot mapping")
    if previous and previous.get("days_before") != days and days not in previous.get("allowed_days_before", []):
        raise ValueError("Reminder cadence migration needs an explicit slot mapping")
    identity = dict(previous or {})
    if package["evidence_kind"] == "october_existing_publication" and not identity:
        identity = dict(october_post(root, package["review_id"], channel, channel_id, package["slot_id"]))
    for slot in slots:
        trusted = previous and same_remote(previous, slot) and previous.get("channel_id") == channel_id
        if slot.get("channel_id") != channel_id and not trusted:
            raise ValueError("Existing post account unresolved: reconcile its channel ID first")
        if (slot.get("days_before") is not None and slot["days_before"] != days
                and days not in slot.get("allowed_days_before", [])
                and not (previous and days in previous.get("allowed_days_before", []))):
            raise ValueError("Reminder cadence migration needs an explicit slot mapping")
        if identity.get("external_id") and not same_remote(identity, slot):
            raise ValueError("Multiple existing posts for this reminder slot")
        if not identity.get("external_id"):
            identity = dict(slot)
    if provider and identity.get("provider") and provider != identity["provider"]:
        raise ValueError("Requested provider conflicts with existing identity")
    if provider_account_id and identity.get("provider_account_id") and provider_account_id != identity["provider_account_id"]:
        raise ValueError("Requested provider account conflicts with existing identity")
    provider = identity.get("provider", provider or "generic")
    provider_account_id = identity.get("provider_account_id", provider_account_id)
    external_id = str(identity["external_id"]) if identity.get("external_id") else None
    uuid = identity.get("provider_uuid")
    if provider == "metricool" and (not provider_account_id or (external_id and not uuid)):
        raise ValueError("Metricool correction requires reconciled stable provider UUID and brand account")
    if previous and not external_id:
        raise ValueError("Earlier request unresolved: reconcile before creating another post")
    action = "update" if external_id else "create"
    if previous and previous.get("state") == "confirmed" and previous.get("package_hash") == package["package_hash"]:
        action = "noop"
    package.update(provider=provider, provider_account_id=provider_account_id, provider_uuid=uuid, external_id=external_id, action=action,
        allowed_days_before=identity.get("allowed_days_before", [days]), state="prepared",
        prepared_at=datetime.now(ZoneInfo("UTC")).isoformat(), integration="external_adapter_required")
    october_identity_allowed(package, root)
    collision_check(package, records)
    return package


def response_identity(package, response):
    if not response.get("external_id") or any(response.get(k) != package[k] for k in ("channel", "channel_id")):
        raise ValueError("Response requires resolved post/channel IDs")
    provider = package.get("provider", "generic")
    if response.get("provider", provider) != provider:
        raise ValueError("Provider changed")
    uuid = response.get("provider_uuid")
    if provider == "metricool":
        if response.get("provider_account_id") != package.get("provider_account_id"):
            raise ValueError("Provider account changed")
        if not uuid or (package.get("provider_uuid") and uuid != package["provider_uuid"]):
            raise ValueError("Stable provider UUID changed or missing")
    elif package.get("external_id") and str(response["external_id"]) != str(package["external_id"]):
        raise ValueError("Correction changed external post ID")
    return {"external_id": str(response["external_id"]), "provider_uuid": uuid or package.get("provider_uuid")}


def verify_readback(package, response):
    if response.get("readback") is not True or not aware_timestamp(response.get("fetched_at")):
        raise ValueError("An acknowledgement is not readback")
    if datetime.fromisoformat(response["fetched_at"]) < datetime.fromisoformat(package["prepared_at"]):
        raise ValueError("Readback predates this request")
    if response.get("status") not in {"scheduled", "published"}:
        raise ValueError("Scheduler has not confirmed final state")
    identity = response_identity(package, response)
    for key in ("channel", "channel_id", "event_ids", "publish_at", "caption", "image_sha256"):
        if response.get(key) != package[key]:
            raise ValueError(f"Readback differs: {key}")
    return {**package, **identity, "state": "confirmed", "verified_at": response["fetched_at"],
        "remote_status": response["status"], "public_url": response.get("public_url")}


def validate_pending_package(package, existing, checked):
    fields = ("key", "package_hash", "event_ids", "channel", "channel_id", "days_before", "slot_id", "publish_at",
        "caption", "image_path", "image_sha256", "event_fingerprints", "review_id", "evidence_kind", "prepared_at", "action", "provider", "provider_account_id", "allowed_days_before")
    if not existing or any(package.get(k) != existing.get(k) for k in fields):
        raise ValueError("Stale, modified or unknown package")
    if any(package.get(k) != checked.get(k) for k in fields if k not in {"prepared_at", "action", "provider", "provider_account_id", "allowed_days_before"}):
        raise ValueError("Image, facts or caption changed while request was pending")


def adapter_update_payload(package, remote_readback=None):
    """Allowlisted adapter input, NOT a Metricool wire schema or echoed GET object."""
    if package["action"] != "update":
        raise ValueError("Update requires a reconciled existing post")
    return {key: package.get(key) for key in ("provider", "provider_account_id", "provider_uuid", "external_id", "channel",
        "channel_id", "caption", "publish_at", "image_path", "image_sha256")}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temp.replace(path)


@contextmanager
def state_lock(path):
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
    for name in ("event-id", "channel", "channel-id"):
        create.add_argument("--"+name, required=True)
    create.add_argument("--days-before", required=True, type=int)
    create.add_argument("--slot-id")
    create.add_argument("--provider", choices=["generic", "metricool"])
    create.add_argument("--provider-account-id")
    create.add_argument("--output", type=Path, required=True)
    for verb in ("accept", "confirm"):
        command = sub.add_parser(verb)
        command.add_argument("--package", type=Path, required=True)
        command.add_argument("--response", type=Path, required=True)
    args = parser.parse_args()
    state_path = args.state or args.root / "data/social_publications.json"
    with state_lock(state_path.with_suffix(".lock")):
        state = read_json(state_path, {"schema_version": 2, "records": []})
        if args.command == "prepare":
            package = prepare(args.event_id, args.channel, args.channel_id, args.days_before, state, args.root, args.slot_id,
                              provider=args.provider, provider_account_id=args.provider_account_id)
        else:
            package = read_json(args.package, {})
            response = read_json(args.response, {})
            matches = [r for r in state["records"] if r["key"] == package["key"]]
            if len(matches) != 1:
                raise ValueError("No unique saved request")
            existing = matches[0]
            checked, _ = content(package["event_ids"][0], package["channel"], package["channel_id"],
                package["days_before"], args.root, package["slot_id"])
            validate_pending_package(package, existing, checked)
            # Keep trusted state across acknowledgements, including numeric ID changes.
            package = {**package, **{k: existing.get(k) for k in ("provider", "provider_account_id", "provider_uuid", "external_id")}}
            october_identity_allowed(package, args.root)
            if args.command == "confirm":
                package = verify_readback(package, response)
            else:
                package = {**package, **response_identity(package, response), "state": "accepted_pending_readback"}
        collision_check(package, state["records"])
        if args.command == "prepare" and package["action"] == "noop":
            package["state"] = "confirmed"
            write_json(args.output, package)
            print(json.dumps({"key": package["key"], "action": "noop", "state": "confirmed"}))
            return
        state["records"] = [r for r in state["records"] if r["key"] != package["key"]] + [package]
        write_json(state_path, state)
        if args.command == "prepare":
            write_json(args.output, package)
        print(json.dumps({"key": package["key"], "state": package["state"], "action": package["action"]}))


if __name__ == "__main__":
    main()
