"""Lossless website assets, separate from original approval/SNS bytes.

Originals removed from the deployable tree can be read from their immutable
Git commit into a process-private temporary directory. Never restore them into
the public checkout. Website derivatives do not become new visual approvals.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import replace
from functools import lru_cache
from pathlib import Path, PurePosixPath

_CACHE = tempfile.TemporaryDirectory(prefix='dolphin-approved-media-')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def records(root):
    file = Path(root)/'data/media_delivery.json'
    if not file.exists():
        return []
    data = json.loads(file.read_text(encoding='utf-8-sig'))
    if data.get('schema_version') != 1:
        raise ValueError('Unknown media delivery schema')
    rows = data['records']
    for key in ('source_path', 'delivery_path'):
        if len({row[key] for row in rows}) != len(rows):
            raise ValueError('Duplicate media delivery mapping')
    return rows


def record_for(path, root):
    return next((r for r in records(root) if r['source_path'] == path.lstrip('/')), None)


def local_path(path, root):
    if not isinstance(path, str) or ':' in path or '\\' in path or path.startswith('/'):
        raise ValueError('Unsafe media path')
    if '..' in PurePosixPath(path).parts:
        raise ValueError('Unsafe media path')
    resolved = (Path(root)/path).resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        raise ValueError('Media path escapes checkout')
    return resolved


@lru_cache(maxsize=256)
def _restore(root, source, commit, blob, digest):
    if not re.fullmatch('[0-9a-f]{40}', commit) or not re.fullmatch('[0-9a-f]{40}', blob):
        raise ValueError('Invalid immutable original reference')
    if not re.fullmatch('[0-9a-f]{64}', digest):
        raise ValueError('Invalid original SHA256')
    command = ['git', '-c', 'safe.directory='+root, '-C', root]
    try:
        actual = subprocess.check_output(command+['rev-parse', commit+':'+source], stderr=subprocess.PIPE).decode().strip()
        if actual != blob:
            raise ValueError('Original commit/path does not match recorded blob')
        data = subprocess.check_output(command+['cat-file', 'blob', blob], stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        raise ValueError('Original Git bytes unavailable; fetch complete history') from exc
    if sha(data) != digest:
        raise ValueError('Original Git bytes do not match approval hash')
    target = Path(_CACHE.name)/(digest+Path(source).suffix)
    target.write_bytes(data)
    return target


def archived_original(path, root):
    record = record_for(path, root)
    if not record:
        raise ValueError('Missing original and no immutable source mapping')
    local_path(record['source_path'], root)
    return _restore(str(Path(root).resolve()), record['source_path'],
                    record['source_commit'], record['source_git_blob'], record['source_sha256'])


def website_asset(decision, root):
    if not decision.allowed:
        return decision
    record = record_for(decision.path, root)
    if not record:
        return decision
    if record['source_sha256'] != decision.sha256 or record.get('encoding') != 'webp-lossless':
        raise ValueError('Delivery source does not match original publication evidence')
    target = local_path(record['delivery_path'], root)
    if target.suffix != '.webp' or sha(target.read_bytes()) != record['delivery_sha256']:
        raise ValueError('Website derivative bytes changed')
    # Evidence kind/review ID still describe the original; only delivery bytes differ.
    return replace(decision, path=record['delivery_path'], sha256=record['delivery_sha256'])


def audit(root):
    from PIL import Image
    for record in records(root):
        source = archived_original(record['source_path'], root)
        target = local_path(record['delivery_path'], root)
        if local_path(record['source_path'], root).exists():
            raise ValueError('Original duplicated in public output: '+record['source_path'])
        if sha(source.read_bytes()) != record['source_sha256'] or sha(target.read_bytes()) != record['delivery_sha256']:
            raise ValueError('Media hash mismatch')
        with Image.open(source) as original, Image.open(target) as delivery:
            if delivery.format != 'WEBP' or original.size != delivery.size or list(original.size) != [record['width'], record['height']]:
                raise ValueError('Media dimensions or format changed')
            pixels = original.convert('RGBA').tobytes()
            if pixels != delivery.convert('RGBA').tobytes() or sha(pixels) != record['rgba_sha256']:
                raise ValueError('Lossless pixel equality failed')
            for key in ('icc_profile', 'xmp'):
                if original.info.get(key, b'') != delivery.info.get(key, b''):
                    raise ValueError('Color/orientation metadata changed')
            if original.getexif().tobytes() != delivery.getexif().tobytes():
                raise ValueError('EXIF metadata changed')
        if target.stat().st_size >= source.stat().st_size:
            raise ValueError('Derivative does not reduce bytes')
    print('Lossless media audit passed:', len(records(root)), 'original/derivative pairs')


if __name__ == '__main__':
    audit(Path(__file__).resolve().parents[1])
