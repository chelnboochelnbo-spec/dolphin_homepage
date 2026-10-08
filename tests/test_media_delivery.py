"""Original approval remains separate from a hash-bound website derivative."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'automation'))
from publication_guard import Decision, image_file
import media_delivery as media


class MediaDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'data').mkdir()
        (self.root/'assets').mkdir()
        self.original = b'SYNTHETIC ORIGINAL'
        self.delivery = b'SYNTHETIC WEB DELIVERY'
        (self.root/'assets/test.webp').write_bytes(self.delivery)
        self.record = dict(source_path='assets/test.png', source_sha256=media.sha(self.original),
            source_commit='a'*40, source_git_blob='b'*40, delivery_path='assets/test.webp',
            delivery_sha256=media.sha(self.delivery), encoding='webp-lossless')
        self.save()
        self.decision = Decision(True, 'verified', 'assets/test.png', media.sha(self.original), 'TEST-REVIEW')

    def save(self, records=None):
        (self.root/'data/media_delivery.json').write_text(json.dumps({'schema_version':1,
            'records': records if records is not None else [self.record]}))

    def test_website_uses_derivative_without_changing_approval(self):
        result = media.website_asset(self.decision, self.root)
        self.assertEqual(result.path, 'assets/test.webp')
        self.assertEqual(result.sha256, media.sha(self.delivery))
        self.assertEqual(result.review_id, self.decision.review_id)
        self.assertEqual(self.decision.path, 'assets/test.png')
        self.assertEqual(self.decision.sha256, media.sha(self.original))

    def test_modified_derivative_is_blocked(self):
        (self.root/'assets/test.webp').write_bytes(b'CHANGED')
        with self.assertRaises(ValueError): media.website_asset(self.decision, self.root)

    def test_wrong_source_hash_and_duplicate_mapping_blocked(self):
        self.record['source_sha256'] = '0'*64; self.save()
        with self.assertRaises(ValueError): media.website_asset(self.decision, self.root)
        self.save([self.record,self.record])
        with self.assertRaises(ValueError): media.records(self.root)

    def test_traversal_blocked(self):
        for path in ('../outside.webp','/outside.webp','C:/outside.webp','assets/../../outside.webp'):
            self.record['delivery_path']=path; self.save()
            with self.assertRaises(ValueError): media.website_asset(self.decision, self.root)

    def test_original_recovered_outside_public_tree(self):
        with patch.object(media.subprocess,'check_output',side_effect=[b'b'*40+b'\n',self.original]):
            result = image_file('assets/test.png',self.root)
        self.assertEqual(result.read_bytes(),self.original)
        self.assertFalse(result.is_relative_to(self.root))
        self.assertFalse((self.root/'assets/test.png').exists())

    def test_wrong_git_source_fails_closed(self):
        with patch.object(media.subprocess,'check_output',side_effect=[b'c'*40+b'\n']):
            with self.assertRaises(ValueError): image_file('assets/test.png',self.root)

    def test_unmapped_missing_image_not_restored(self):
        with self.assertRaises(ValueError): image_file('assets/unknown.png',self.root)


if __name__ == '__main__': unittest.main()
