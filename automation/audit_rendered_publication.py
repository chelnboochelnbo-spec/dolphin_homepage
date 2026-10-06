"""Reject stale event media in generated cards, detail pages, OG and JSON-LD."""
import json
from html.parser import HTMLParser
from pathlib import Path

from publication_guard import ROOT, website_decision, event_publishable, read_json


class Media(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.og = []
        self.cards = {}
        self.card = None
        self.json_ld = []
        self.in_json = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "article":
            self.card = a.get("data-event-id")
            if self.card:
                self.cards.setdefault(self.card, [])
        if tag == "img":
            source = a.get("src", "")
            if "event-flyer" in a.get("class", "").split():
                self.images.append(source)
            if self.card:
                self.cards[self.card].append(source)
        if tag == "meta" and a.get("property") == "og:image":
            self.og.append(a.get("content"))
        if tag == "script" and a.get("type") == "application/ld+json":
            self.in_json = True

    def handle_endtag(self, tag):
        if tag == "article": self.card = None
        if tag == "script": self.in_json = False

    def handle_data(self, data):
        if self.in_json: self.json_ld.append(data)


def audit(root: Path = ROOT):
    events = read_json(root / "data/events.json", {"events": []})["events"]
    by_id = {e["id"]: e for e in events}
    for event in events:
        page = root / "events" / event["id"] / "index.html"
        if not event_publishable(event, root):
            if page.exists(): raise ValueError(f"Inactive event page remains: {event['id']}")
            continue
        parsed = Media(); parsed.feed(page.read_text(encoding="utf-8-sig"))
        result = website_decision(event, root, events=events)
        expected = ["/"+result.path.lstrip("/")] if result.allowed else []
        if parsed.images != expected: raise ValueError(f"Unverified detail image: {event['id']}")
        urls = ["https://www.bardolphin-kanazawa.com"+p for p in expected]
        if parsed.og != urls: raise ValueError(f"Unverified OG image: {event['id']}")
        for item in parsed.json_ld:
            if json.loads(item).get("image", []) != urls:
                raise ValueError(f"Unverified JSON-LD image: {event['id']}")
    for name in ("index.html", "schedule.html", "archive.html", "archive/index.html"):
        parsed = Media(); parsed.feed((root/name).read_text(encoding="utf-8-sig"))
        for event_id, images in parsed.cards.items():
            event = by_id.get(event_id)
            if not event or not event_publishable(event, root):
                raise ValueError(f"Inactive card: {event_id}")
            result = website_decision(event, root, events=events)
            expected = [result.path.lstrip("/")] if result.allowed else []
            if [p.lstrip("/") for p in images] != expected:
                raise ValueError(f"Unverified card image: {event_id}")
    print("Rendered publication guard passed")


if __name__ == "__main__":
    audit()
