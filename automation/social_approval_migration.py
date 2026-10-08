"""Apply explicitly sourced approval metadata without editing canonical facts."""
from copy import deepcopy
import hashlib
from publication_guard import read_json, fingerprint, image_file, image_sha, aware_timestamp


def external_path(root, path):
    """Private inputs/outputs must resolve outside the public checkout."""
    from pathlib import Path
    resolved = Path(path).resolve()
    if resolved.is_relative_to(root.resolve()):
        raise ValueError('Private operational path must be outside repository')
    return resolved


def approved_events(root, approvals_path=None):
    events = deepcopy(read_json(root/'data/events.json', {'events': []})['events'])
    records = (read_json(external_path(root, approvals_path), {})['records']
               if approvals_path is not None else [])
    ids = [r['event_id'] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate approval migration event')
    for record in records:
        matches = [e for e in events if e['id'] == record['event_id']]
        if len(matches) != 1:
            continue
        event = matches[0]
        # Validate lazily in social.content for the requested event, so an
        # unrelated event's stale migration never stops a valid publication.
        event['_approval_migration'] = record
    return events


def apply_approval(event, root):
    record = event.pop('_approval_migration', None)
    if record is None:
        return
    if (record['event_fingerprint'] != fingerprint(event)
            or record['image_sha256'] != image_sha(image_file(record['image_path'], root))
            or record['image_path'] != event['flyer']['github_path']):
        raise ValueError('Approval migration facts or image changed')
    if (not record.get('source_references') or not record.get('approved_by')
            or not aware_timestamp(record.get('recorded_at'))):
        raise ValueError('Approval migration requires actual source evidence')
    caption = record['caption']
    if hashlib.sha256(caption.encode()).hexdigest() != record['caption_sha256']:
        raise ValueError('Approval migration caption changed')
    social = event.setdefault('social', {})
    for channel in ('instagram', 'facebook'):
        key = channel+'_caption'
        if social.get(key) and social[key] != caption:
            raise ValueError('Migration conflicts with canonical caption')
        social[key] = caption
        approval = {'caption_sha256':record['caption_sha256'], 'review_id':record['review_id'],
            'approved_by':record['approved_by'], 'approved_at':record['recorded_at'],
            'source_reference':'; '.join(record['source_references']),
            'approval_basis':record['approval_basis']}
        existing = social.setdefault('approvals', {}).get(channel)
        if existing and existing != approval:
            raise ValueError('Migration conflicts with canonical approval')
        social['approvals'][channel] = approval
    if social.get('schedule') and social['schedule'] != record['existing_schedule']:
        raise ValueError('Migration conflicts with canonical reservation identity')
    social['schedule'] = deepcopy(record['existing_schedule'])
