"""Read-only Metricool reconciliation adapter. Never invokes a remote write.

prepare -> connector GET + actual media download -> reconcile. JSON captures
are trusted operator input, not independently authenticated API responses.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import social_package as social
from publication_guard import read_json, aware_timestamp

INPUTS = ('data/events.json', 'data/flyer_verifications.json',
          'data/october_kiraku_migration.json', 'data/publication_tombstones.json',
          'automation/config.json')


def git(root, *args):
    return subprocess.check_output(['git', '-c', 'safe.directory='+str(root.resolve()),
                                   '-C', str(root), *args], text=True).strip()


def snapshot(root, paths=()):
    """Compare all inputs with the freshly resolved remote main, including bytes."""
    remote = git(root, 'ls-remote', 'origin', 'refs/heads/main').split()[0]
    if git(root, 'rev-parse', 'origin/main') != remote:
        raise ValueError('Fetch latest main before preparing or reconciling')
    hashes = {}
    for path in sorted(set(INPUTS) | set(paths)):
        expected = git(root, 'rev-parse', remote+':'+path)
        if git(root, 'hash-object', path) != expected:
            raise ValueError('Local input differs from main: '+path)
        hashes[path] = hashlib.sha256((root/path).read_bytes()).hexdigest()
    return {'main_commit': remote, 'sha256': hashes}


def prepare_batch(root, state, requests, snapshotter=snapshot):
    initial = snapshotter(root)
    packages, holds = [], []
    for request in requests:
        try:
            pair = []
            for channel, channel_id in request['accounts'].items():
                if channel not in {'instagram', 'facebook'}:
                    raise ValueError('Only Instagram/Facebook are supported')
                package = social.prepare(request['event_id'], channel, channel_id,
                    request['days_before'], state, root, request.get('slot_id'),
                    provider='metricool', provider_account_id=request['brand_id'])
                require_caption_source(root, package)
                pair.append(package)
            if {p['channel'] for p in pair} != {'instagram', 'facebook'}:
                raise ValueError('Both intended destinations required')
            packages.extend(pair)
        except (ValueError, KeyError) as error:
            holds.append({'event_id': request.get('event_id'), 'reason': str(error)})
    final = snapshotter(root, [p['image_path'] for p in packages])
    if initial['main_commit'] != final['main_commit']:
        raise ValueError('Main changed during preparation')
    keys = [p['key'] for p in packages]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate requested publication slot')
    return {'snapshot': final, 'packages': packages, 'holds': holds,
            'remote_write_count': 0, 'mode': 'read_only'}


def require_caption_source(root, package):
    if package['evidence_kind'] == 'october_existing_publication':
        return  # Frozen preservation exception, not a new caption approval.
    events = read_json(root/'data/events.json', {})['events']
    for event in events:
        if event['id'] in package['event_ids']:
            approval = event['social']['approvals'][package['channel']]
            if not str(approval.get('source_reference') or '').strip():
                raise ValueError('Real caption approval source_reference required')


def fresh(value, after=None):
    if not aware_timestamp(value):
        raise ValueError('Timezone-aware read timestamp required')
    stamp = datetime.fromisoformat(value)
    now = datetime.now(timezone.utc)
    if not now-timedelta(minutes=5) <= stamp <= now+timedelta(seconds=5):
        raise ValueError('Remote capture is stale or future-dated')
    if after and stamp < datetime.fromisoformat(after):
        raise ValueError('Read remote again after preparation')


def accounts_from_capture(capture, brand_id):
    fresh(capture['fetched_at'])
    brands = [b for b in capture['brands'] if str(b['id']) == brand_id]
    if len(brands) != 1 or str(capture['brand_id']) != brand_id:
        raise ValueError('Wrong or ambiguous brand account')
    brand = brands[0]
    if brand['timezone'] != 'Asia/Tokyo':
        raise ValueError('Unexpected account timezone')
    return {c: str(brand['networksData'][c+'Data']) for c in ('instagram', 'facebook')}


def remote_fields(post, capture):
    providers = post['providers']
    channels = [p['network'] for p in providers]
    if len(channels) != 2 or set(channels) != {'instagram', 'facebook'}:
        raise ValueError('Missing, duplicate or unexpected destination')
    if post.get('draft') is not False or any(p['status'] != 'PENDING' for p in providers):
        raise ValueError('Expected a scheduled post on both destinations')
    if len(post['media']) != 1:
        raise ValueError('Exactly one approved image required')
    media = [m for m in capture['media'] if m['url'] == post['media'][0]]
    if len(media) != 1:
        raise ValueError('Actual downloaded media evidence required')
    fresh(media[0]['fetched_at'], capture['fetched_at'])
    sha = hashlib.sha256(Path(media[0]['local_path']).read_bytes()).hexdigest()
    when = post['publicationDate']
    parsed = datetime.fromisoformat(when['dateTime'])
    if parsed.tzinfo is not None:
        raise ValueError('Expected provider local dateTime')
    instant = parsed.replace(tzinfo=ZoneInfo(when['timezone'])).isoformat()
    return {'caption': post['text'], 'publish_at': instant, 'image_sha256': sha}


def wire_preview(packages, post):
    """One allowlisted write preview per UUID; never sends it."""
    first = packages[0]
    for field in ('caption', 'publish_at', 'image_sha256', 'provider_account_id', 'provider_uuid'):
        if any(p[field] != first[field] for p in packages):
            raise ValueError('Shared UUID has incompatible desired content')
    if {p['channel'] for p in packages} != {'instagram', 'facebook'} or len(packages) != 2:
        raise ValueError('Shared post must retain both destinations exactly once')
    # Existing media is only usable after reconciliation proves actual bytes.
    info = {'text': first['caption'], 'publicationDate': post['publicationDate'],
            'providers': [{'network': c} for c in ('facebook', 'instagram')],
            'media': post['media'], 'autoPublish': True, 'draft': False}
    allowed = {'facebookData': {'type'},
               'instagramData': {'autoPublish', 'type', 'showReelOnFeed', 'isAiGenerated'}}
    for key, fields in allowed.items():
        info[key] = {k: v for k, v in post.get(key, {}).items() if k in fields}
    if any(info[k].get('type') != 'POST' for k in allowed):
        raise ValueError('Unsupported post format')
    if (post.get('autoPublish', True) is not True or post.get('firstCommentText')
            or post.get('shortener') or any(post.get('mediaAltText') or [])):
        raise ValueError('Additional existing settings require explicit supported mapping')
    return {'blogId': first['provider_account_id'], 'id': str(post['id']),
            'uuid': str(post['uuid']), 'info': json.dumps(info, ensure_ascii=False)}


def reconcile(root, state, plan, capture, snapshotter=snapshot):
    packages = plan['packages']
    current = snapshotter(root, [p['image_path'] for p in packages])
    if current != plan['snapshot']:
        raise ValueError('Main or input bytes changed after preparation')
    groups = {}
    holds = list(plan['holds'])
    for p in packages:
        groups.setdefault((p['provider_account_id'], p['provider_uuid'] or p['key']), []).append(p)
    records = list(state['records'])
    results = []
    for (brand, uuid), pair in groups.items():
        try:
            accounts = accounts_from_capture(capture, brand)
            for p in pair:
                fresh(capture['fetched_at'], p['prepared_at'])
                if accounts[p['channel']] != p['channel_id']:
                    raise ValueError('Connected destination account changed')
                checked, _ = social.content(p['event_ids'][0], p['channel'], p['channel_id'],
                                            p['days_before'], root, p['slot_id'])
                social.validate_pending_package(p, p, checked)
                require_caption_source(root, p)
                trusted = social.prepare(p['event_ids'][0], p['channel'], p['channel_id'],
                    p['days_before'], state, root, p['slot_id'], provider='metricool',
                    provider_account_id=brand)
                for field in ('provider_uuid', 'external_id', 'key', 'package_hash', 'action'):
                    if trusted.get(field) != p.get(field):
                        raise ValueError('Plan differs from persistent identity: '+field)
                social.october_identity_allowed(p, root)
                social.collision_check(p, records)
            matches = [post for post in capture['posts'] if str(post['uuid']) == uuid]
            if not pair[0]['provider_uuid']:
                raise ValueError('New reservation requires reviewed discovery/migration; no write emitted')
            if len(matches) != 1:
                raise ValueError('Missing or duplicate provider UUID')
            post = matches[0]
            fields = remote_fields(post, capture)
            # Exact duplicate text/time on a second UUID must not be adopted.
            if any(str(other['uuid']) != uuid and other.get('text') == fields['caption']
                   and other.get('publicationDate') == post['publicationDate'] for other in capture['posts']):
                raise ValueError('Duplicate reservation on another UUID')
            preview = wire_preview(pair, post)
            verified = []
            for p in pair:
                response = {**fields, 'readback': True, 'fetched_at': capture['fetched_at'],
                    'status': 'scheduled', 'provider': 'metricool', 'provider_account_id': brand,
                    'provider_uuid': uuid, 'external_id': str(post['id']), 'channel': p['channel'],
                    'channel_id': accounts[p['channel']], 'event_ids': p['event_ids']}
                verified.append(social.verify_readback(p, response))
            # Commit both destinations together only after both checks succeed.
            keys = {p['key'] for p in verified}
            records = [r for r in records if r['key'] not in keys] + verified
            results.append({'uuid': uuid, 'external_id': str(post['id']), 'channels': sorted(accounts),
                            'action': 'noop', 'wire_preview': preview, 'image_sha256': fields['image_sha256']})
        except (ValueError, KeyError, OSError) as error:
            holds.append({'event_ids': pair[0]['event_ids'], 'reason': str(error)})
    if snapshotter(root, [p['image_path'] for p in packages]) != current:
        raise ValueError('Inputs changed while reconciling')
    return {**state, 'records': records}, {'snapshot': current, 'results': results,
        'holds': holds, 'remote_write_count': 0, 'mode': 'read_only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'reconcile'])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Explicit, persistent state required; never silently substitute empty state.
    if not args.state.is_file():
        raise ValueError('Initialize a persistent schema_version=2 state explicitly')
    with social.state_lock(args.state.with_suffix('.lock')):
        state = read_json(args.state, {})
        if state.get('schema_version') != 2 or not isinstance(state.get('records'), list):
            raise ValueError('Invalid persistent state')
        if args.command == 'prepare':
            result = prepare_batch(args.root, state, read_json(args.input, {})['requests'])
        else:
            state, result = reconcile(args.root, state, read_json(args.input, {}), read_json(args.capture, {}))
            social.write_json(args.state, state)
        social.write_json(args.output, result)
        print(json.dumps({'remote_write_count': 0, 'holds': result['holds'],
                          'verified_groups': len(result.get('results', []))}))


if __name__ == '__main__':
    main()
