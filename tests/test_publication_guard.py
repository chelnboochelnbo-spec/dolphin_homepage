"""Synthetic fixtures below are test data, never real visual-review evidence."""
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "automation"))
import publication_guard as guard
import social_package as social
import render_events
import render_event_pages
import render_archive
import render_artists


class PublicationGuard(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        private = tempfile.TemporaryDirectory()
        self.addCleanup(private.cleanup)
        self.private = Path(private.name)
        (self.root / "data").mkdir()
        (self.root / "automation").mkdir()
        (self.root / "assets").mkdir()
        self.events = [self.event("2026-11-12"), self.event("2026-11-26")]
        for event in self.events:
            (self.root / event["flyer"]["github_path"]).write_bytes(b"SYNTHETIC TEST IMAGE " + event["date"].encode())
        self.ledger = {"reviews": [self.review([e]) for e in self.events]}
        self.persist()

    def event(self, day):
        return {"id": day+"_kiraku", "date": day, "title": "Kiraku Jam", "status": "published",
                "event_type": "session", "open": None, "start": "20:00", "charge": "JPY 2000 + 2 drinks",
                "performers": [{"name": "TEST Musician", "instrument": "Gt"}],
                "flyer": {"status": "ready", "github_path": "assets/"+day+".png"},
                "social": {"instagram_caption": "TEST APPROVED CAPTION"}}

    def review(self, events):
        path = events[0]["flyer"]["github_path"]
        return {"review_id": "TEST-ONLY-"+events[0]["id"], "kind": "visual_review", "reviewer": "SYNTHETIC TEST FIXTURE",
                "reviewed_at": "2026-10-07T00:00:00+09:00", "pixels_inspected": True,
                "transcription": "SYNTHETIC TEST TEXT; NOT REAL IMAGE EVIDENCE",
                "image_path": path, "image_sha256": guard.image_sha(self.root / path),
                "covered_dates": [e["date"] for e in events],
                "targets": {e["id"]: {"facts": guard.event_facts(e), "fingerprint": guard.fingerprint(e),
                                      "observed_text": "SYNTHETIC TEST OBSERVATION"} for e in events}}

    def persist(self):
        (self.root / "data/events.json").write_text(json.dumps({"events": self.events}))
        (self.root / "data/flyer_verifications.json").write_text(json.dumps(self.ledger))
        config = json.loads((ROOT / "automation/config.json").read_text(encoding="utf-8"))
        (self.root / "automation/config.json").write_text(json.dumps(config))
        for event in self.events:
            for review in self.ledger["reviews"]:
                if event["id"] in review["targets"]:
                    caption = event["social"]["instagram_caption"]
                    event["social"]["approvals"] = {"instagram": {"caption_sha256": hashlib.sha256(caption.encode()).hexdigest(),
                        "review_id": review["review_id"], "approved_by": "TEST", "approved_at": "2026-10-07T00:00:00+09:00"}}
        (self.root / "data/events.json").write_text(json.dumps({"events": self.events}))

    def assess(self, event=None):
        return guard.assess(event or self.events[0], self.root)

    def test_valid_single_day(self):
        self.assertTrue(self.assess().allowed)

    def test_november_12_image_rejected_for_26(self):
        self.events[1]["flyer"] = copy.deepcopy(self.events[0]["flyer"])
        self.persist()
        self.assertFalse(self.assess(self.events[1]).allowed)

    def test_november_19_cannot_reuse_august_20(self):
        stale = copy.deepcopy(self.events[0])
        stale.update(id="2026-11-19_monthly", date="2026-11-19", title="Monthly Voices")
        stale["flyer"]["github_path"] = "assets/flyer_20260820.png"
        (self.root / stale["flyer"]["github_path"]).write_bytes(b"AUGUST TEST IMAGE")
        self.assertFalse(self.assess(stale).allowed)

    def test_any_material_fact_change_invalidates_review(self):
        changes = {"id": "new-id", "date": "2026-11-13", "end_date": "2026-11-13", "open": "18:00",
                   "start": "21:00", "charge": "JPY 3000", "performers": [{"name": "OTHER"}],
                   "title": "Different", "status": "draft", "cancelled": True}
        for key, value in changes.items():
            with self.subTest(key=key):
                event = copy.deepcopy(self.events[0]); event[key] = value
                self.assertFalse(self.assess(event).allowed)

    def test_changed_image_bytes_invalidates_review(self):
        (self.root / self.events[0]["flyer"]["github_path"]).write_bytes(b"CHANGED TEST IMAGE")
        self.assertFalse(self.assess().allowed)

    def test_ready_filename_logo_missing_or_remote_is_not_evidence(self):
        for path in ("logo_new.png", "assets/missing.png", "https://example.test/x.png", "../outside.png"):
            with self.subTest(path=path):
                event = copy.deepcopy(self.events[0]); event["flyer"]["github_path"] = path
                self.assertFalse(self.assess(event).allowed)
        self.ledger["reviews"] = []; self.persist()
        self.assertFalse(self.assess().allowed)

    def test_visual_timestamp_transcription_and_pixel_attestation_required(self):
        for key in ("reviewed_at", "transcription", "pixels_inspected", "reviewer"):
            with self.subTest(key=key):
                ledger = copy.deepcopy(self.ledger); ledger["reviews"][0].pop(key)
                self.assertFalse(guard.assess(self.events[0], self.root, ledger=ledger).allowed)

    def test_two_day_special_needs_exact_approval_and_all_facts(self):
        self.events[1] = self.event("2026-11-13")
        self.events[0]["title"] = "TEST Special Solo"
        self.events[1]["title"] = "TEST Special Jam"
        self.events[1]["flyer"] = copy.deepcopy(self.events[0]["flyer"])
        review = self.review(self.events)
        self.ledger = {"reviews": [review]}; self.persist()
        self.assertFalse(self.assess().allowed)
        review["shared_publication"] = {"type": "special_two_day", "policy_version": 1, "target_event_ids": [e["id"] for e in self.events],
            "approved_by": "TEST", "recorded_at": "2026-10-07T00:00:00+09:00", "reference": "TEST ONLY"}
        self.persist(); self.assertTrue(self.assess().allowed)
        self.events[1]["charge"] = "changed"; self.persist()
        self.assertFalse(self.assess().allowed)

    def test_recurring_series_cannot_use_shared_special_exception(self):
        self.events[1] = self.event("2026-11-13")
        self.events[1]["flyer"] = copy.deepcopy(self.events[0]["flyer"])
        review = self.review(self.events)
        review["shared_publication"] = {"type": "special_two_day", "policy_version": 1, "target_event_ids": [e["id"] for e in self.events],
            "approved_by": "TEST", "recorded_at": "2026-10-07T00:00:00+09:00", "reference": "TEST ONLY"}
        self.ledger = {"reviews": [review]}; self.persist()
        self.assertFalse(self.assess().allowed)

    def test_duplicate_media_attestations_fail(self):
        duplicate = copy.deepcopy(self.ledger["reviews"][0])
        duplicate["targets"] = {self.events[1]["id"]: {}}
        self.ledger["reviews"].append(duplicate); self.persist()
        self.assertFalse(self.assess().allowed)
        duplicate["review_id"] = "duplicate"; self.persist()
        self.assertFalse(self.assess().allowed)

    def test_cancelled_january_2_cannot_be_revived_or_renamed(self):
        event = self.event("2027-01-02"); event.update(id="2027-01-02_saturday-jam-session-1", title="Saturday Jam Session 1")
        self.assertFalse(guard.event_publishable(event, ROOT))
        event["id"] = "2027-01-02_imported-other-id"
        self.assertFalse(guard.event_publishable(event, ROOT))
        for status in ("draft", "cancelled"):
            event["status"] = status
            self.assertFalse(guard.event_publishable(event, self.root))

    def test_every_event_media_renderer_uses_same_guard_without_logo_fallback(self):
        event = self.events[0]
        self.ledger["reviews"] = []; self.persist()
        for module, function, args in (
            (render_events, render_events.render_schedule_article, (event,)),
            (render_archive, render_archive.event_card, (event,)),
            (render_event_pages, render_event_pages.render, (event, {})),
        ):
            with self.subTest(renderer=module.__name__), patch.object(module, "ROOT", self.root):
                html = function(*args)
                self.assertIn(event["title"], html)
                self.assertNotIn(event["flyer"]["github_path"], html)
                self.assertNotIn('property="og:image"', html)
                self.assertNotIn('src="/logo_new.png"', html)
        with patch.object(render_event_pages, "ROOT", self.root):
            self.assertNotIn('property="og:image"', render_artists.render_event_detail(event, {}))

    def package(self, state=None):
        return social.prepare(self.events[0]["id"], "instagram", "TEST-ACCOUNT", 14, state or {"records": []}, self.root)

    def test_series_14_days_18_jst_and_other_sessions_unchanged(self):
        package = self.package()
        self.assertEqual(package["publish_at"], "2026-10-29T18:00:00+09:00")
        with self.assertRaises(ValueError):
            social.prepare(self.events[0]["id"], "instagram", "TEST-ACCOUNT", 7, {"records": []}, self.root)
        event = self.event("2026-11-12"); event["title"] = "One-off Session"
        config = json.loads((self.root / "automation/config.json").read_text())
        self.assertEqual(social.lead_days(event, config), [7])

    def test_unverified_media_produces_no_package(self):
        self.ledger["reviews"] = []; self.persist()
        with self.assertRaises(ValueError): self.package()

    def test_changed_caption_needs_new_approval(self):
        doc = json.loads((self.root / "data/events.json").read_text())
        doc["events"][0]["social"]["instagram_caption"] = "UNAPPROVED CHANGE"
        (self.root / "data/events.json").write_text(json.dumps(doc))
        with self.assertRaises(ValueError): self.package()

    def test_existing_legacy_id_requires_update(self):
        self.events[0]["social"]["schedule"] = [{"channel": "instagram", "channel_id": "TEST-ACCOUNT", "external_id": "EXISTING", "status": "scheduled", "days_before": 14}]
        self.persist(); self.assertEqual(self.package()["action"], "update")
        self.assertEqual(self.package()["external_id"], "EXISTING")

    def test_existing_post_account_must_be_resolved(self):
        self.events[0]["social"]["schedule"] = [{"channel": "instagram", "external_id": "EXISTING", "status": "scheduled", "days_before": 14}]
        self.persist()
        with self.assertRaisesRegex(ValueError, "account unresolved"): self.package()

    def test_cli_accept_requires_matching_independent_readback(self):
        package_path = self.private / "package.json"
        response_path = self.private / "response.json"
        def invoke(*args):
            with patch.object(sys, "argv", ["social_package", "--root", str(self.root), "--state", str(self.private/"state.json"), *args]), patch("sys.stdout", new_callable=io.StringIO):
                social.main()
        invoke("prepare", "--event-id", self.events[0]["id"], "--channel", "instagram",
               "--channel-id", "TEST-ACCOUNT", "--days-before", "14", "--output", str(package_path))
        package = json.loads(package_path.read_text())
        response_path.write_text(json.dumps({"external_id": "REMOTE", "channel": "instagram", "channel_id": "TEST-ACCOUNT"}))
        invoke("accept", "--package", str(package_path), "--response", str(response_path))
        state_path = self.private / "state.json"
        self.assertEqual(json.loads(state_path.read_text())["records"][0]["state"], "accepted_pending_readback")
        with self.assertRaises(ValueError):
            invoke("confirm", "--package", str(package_path), "--response", str(response_path))
        response_path.write_text(json.dumps({**package, "external_id": "REMOTE", "readback": True,
            "fetched_at": datetime.now(timezone.utc).isoformat(), "status": "scheduled"}))
        invoke("confirm", "--package", str(package_path), "--response", str(response_path))
        self.assertEqual(json.loads(state_path.read_text())["records"][0]["state"], "confirmed")

    def test_pending_request_does_not_create_duplicate(self):
        package = self.package()
        with self.assertRaises(ValueError): self.package({"records": [package]})

    def test_completion_rejects_modified_or_replaced_request(self):
        package = self.package()
        social.validate_pending_package(package, package, self.package())
        for key, value in (("caption", "MODIFIED"), ("prepared_at", "2000-01-01T00:00:00Z"),
                           ("channel_id", "OTHER"), ("action", "create-again")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                social.validate_pending_package({**package, key: value}, package, self.package())
        with self.assertRaises(ValueError):
            social.validate_pending_package(package, package, {**self.package(), "review_id": "NEW-REVIEW"})

    def test_duplicate_media_and_external_id_rejected(self):
        package = self.package(); duplicate = {**package, "key": "other", "event_ids": ["other"]}
        with self.assertRaises(ValueError): self.package({"records": [duplicate]})
        self.events[0]["social"]["schedule"] = [{"channel": "instagram", "external_id": "EXISTING", "status": "scheduled", "days_before": 14}]
        self.persist(); duplicate.update(image_sha256="different", external_id="EXISTING")
        with self.assertRaises(ValueError): self.package({"records": [duplicate]})

    def test_acknowledgement_is_not_done_and_readback_must_match(self):
        package = self.package()
        with self.assertRaises(ValueError): social.verify_readback(package, {"external_id": "P", "status": "accepted"})
        response = {**package, "readback": True, "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "external_id": "P", "status": "scheduled"}
        self.assertEqual(social.verify_readback(package, response)["state"], "confirmed")
        for key in ("caption", "image_sha256", "channel_id", "publish_at", "event_ids"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                social.verify_readback(package, {**response, key: "wrong"})
        with self.assertRaises(ValueError):
            social.verify_readback(package, {**response, "fetched_at": "2020-01-01T00:00:00Z"})

    def test_lock_is_released_on_error(self):
        lock = self.root / "state.lock"
        with self.assertRaises(RuntimeError):
            with social.state_lock(lock): raise RuntimeError("TEST FAILURE")
        self.assertFalse(lock.exists())


if __name__ == "__main__":
    unittest.main()
