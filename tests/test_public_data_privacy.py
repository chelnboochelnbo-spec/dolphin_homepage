"""Public data must not contain social operational records or chat references."""
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN={'caption','instagram_caption','facebook_caption','external_id','provider_uuid',
 'provider_account_id','channel_id','approved_by','approved_at','approval_reference',
 'source_reference','source_references','source_thread_id','existing_posts','shared_approval'}


class PublicDataPrivacy(unittest.TestCase):
    def test_public_json_has_no_operational_fields_or_conversation_references(self):
        files=['events.json','flyer_verifications.json','october_kiraku_migration.json',
               'website_image_baseline.json','social_publications.json']
        def visit(value,path):
            if isinstance(value,dict):
                for key,child in value.items():
                    self.assertNotIn(key,FORBIDDEN,path+'.'+key)
                    visit(child,path+'.'+key)
            elif isinstance(value,list):
                for index,child in enumerate(value):visit(child,path+f'[{index}]')
            elif isinstance(value,str):
                self.assertFalse(re.search(r'Sentinel_[a-z0-9]+|(?:parent|source) thread [0-9a-f-]{36}',value,re.I),path)
        for name in files:visit(json.loads((ROOT/'data'/name).read_text(encoding='utf-8')),name)
        self.assertEqual([],json.loads((ROOT/'data/social_publications.json').read_text())['records'])

    def test_social_test_files_use_no_real_reservation_accounts(self):
        for name in ('test_metricool_verification.py','test_publication_migration.py'):
            text=(ROOT/'tests'/name).read_text(encoding='utf-8')
            self.assertNotRegex(text,r'Sentinel_[a-z0-9]+|\b\d{9,}\b')


if __name__=='__main__':unittest.main()
