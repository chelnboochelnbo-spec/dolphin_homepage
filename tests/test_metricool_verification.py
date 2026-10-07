"""Synthetic provider captures; no remote writes or real approval records."""
import copy
import hashlib
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'automation'))
import test_publication_guard as fixtures
import metricool_verification as adapter


class MetricoolVerification(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PublicationGuard()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        event = self.fixture.events[0]
        approval = event['social']['approvals']['instagram']
        approval['source_reference'] = 'SYNTHETIC TEST APPROVAL SOURCE'
        event['social']['facebook_caption'] = event['social']['instagram_caption']
        event['social']['approvals']['facebook'] = copy.deepcopy(approval)
        event['social']['schedule'] = [dict(channel=c, channel_id=i, external_id='123',
            provider='metricool', provider_account_id='BRAND', provider_uuid='UUID',
            days_before=14, slot_id='lead-14') for c, i in [('instagram','IG'),('facebook','FB')]]
        (self.root/'data/events.json').write_text(json.dumps({'events': self.fixture.events}))
        self.request = dict(event_id=event['id'], days_before=14, brand_id='BRAND',
                            accounts={'instagram':'IG', 'facebook':'FB'})
        self.state = {'schema_version':2, 'records':[]}
        self.snapshot = lambda root, paths=(): {'main_commit':'TEST', 'sha256':{}}
        self.plan = adapter.prepare_batch(self.root, self.state, [self.request], self.snapshot)
        p = self.plan['packages'][0]
        now = datetime.now(timezone.utc).isoformat()
        self.capture = dict(fetched_at=now, brand_id='BRAND',
            brands=[dict(id='BRAND', timezone='Asia/Tokyo', networksData=dict(instagramData='IG',facebookData='FB'))],
            posts=[dict(id=456, uuid='UUID', text=p['caption'],
                publicationDate=dict(dateTime=p['publish_at'][:19],timezone='Asia/Tokyo'),
                providers=[dict(network=c,status='PENDING') for c in ('facebook','instagram')],
                media=['https://example.invalid/test.png'], draft=False,
                facebookData={'type':'POST'},instagramData={'type':'POST'},twitterData={'type':'POST'})],
            media=[dict(url='https://example.invalid/test.png',fetched_at=now,
                        local_path=str(self.root/p['image_path']))])

    def run_capture(self):
        return adapter.reconcile(self.root,self.state,self.plan,self.capture,self.snapshot)

    def test_normal_14_days_shared_uuid_one_preview_then_noop(self):
        state, result = self.run_capture()
        self.assertEqual([],result['holds'])
        self.assertEqual(2,len(state['records']))
        self.assertEqual(1,len(result['results']))
        self.assertEqual(0,result['remote_write_count'])
        preview = result['results'][0]['wire_preview']
        self.assertEqual('456',preview['id'])
        self.assertNotIn('twitterData',json.loads(preview['info']))
        second = adapter.prepare_batch(self.root,state,[self.request],self.snapshot)
        self.assertEqual(['noop','noop'],[p['action'] for p in second['packages']])

    def test_remote_negatives_atomic_both_destinations(self):
        original = copy.deepcopy(self.capture)
        changes = [lambda c:c.update(brand_id='OTHER'),
                   lambda c:c['posts'][0].update(uuid='OTHER'),
                   lambda c:c['posts'][0]['providers'].pop(),
                   lambda c:c['posts'].append(copy.deepcopy(c['posts'][0])),
                   lambda c:c['posts'][0].update(text='UNAPPROVED'),
                   lambda c:c['posts'][0]['publicationDate'].update(dateTime='2026-11-01T18:00:00'),
                   lambda c:c.update(fetched_at=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()),
                   lambda c:c['brands'][0]['networksData'].update(facebookData='OTHER')]
        for change in changes:
            self.capture=copy.deepcopy(original); change(self.capture)
            with self.subTest(capture=self.capture):
                state,result=self.run_capture()
                self.assertEqual([],state['records'])
                self.assertTrue(result['holds'])

    def test_fact_and_image_changes_hold_only_affected_event(self):
        for field,value in [('date','2026-11-13'),('performers',[]),('charge','CHANGED')]:
            events=copy.deepcopy(self.fixture.events)
            events[0][field]=value
            (self.root/'data/events.json').write_text(json.dumps({'events':events}))
            state,result=self.run_capture()
            self.assertEqual([],state['records']); self.assertTrue(result['holds'])
        (self.root/'data/events.json').write_text(json.dumps({'events':self.fixture.events}))
        Path(self.capture['media'][0]['local_path']).write_bytes(b'CHANGED')
        state,result=self.run_capture()
        self.assertEqual([],state['records']); self.assertTrue(result['holds'])

    def test_unknown_event_does_not_stop_valid_one(self):
        requests=[self.request,{**self.request,'event_id':'MISSING'}]
        plan=adapter.prepare_batch(self.root,self.state,requests,self.snapshot)
        self.assertEqual(2,len(plan['packages']))
        self.assertEqual(1,len(plan['holds']))

    def test_unapproved_caption_holds_pair(self):
        self.fixture.events[0]['social']['instagram_caption']='UNAPPROVED'
        (self.root/'data/events.json').write_text(json.dumps({'events':self.fixture.events}))
        plan=adapter.prepare_batch(self.root,self.state,[self.request],self.snapshot)
        self.assertEqual([],plan['packages']); self.assertTrue(plan['holds'])

    def test_missing_approval_source_holds_pair(self):
        self.fixture.events[0]['social']['approvals']['instagram'].pop('source_reference')
        (self.root/'data/events.json').write_text(json.dumps({'events':self.fixture.events}))
        plan=adapter.prepare_batch(self.root,self.state,[self.request],self.snapshot)
        self.assertEqual([],plan['packages']); self.assertTrue(plan['holds'])

    def test_tampered_plan_identity_rejected(self):
        for package in self.plan['packages']:
            package['provider_uuid']='OTHER'
        self.capture['posts'][0]['uuid']='OTHER'
        state,result=self.run_capture()
        self.assertEqual([],state['records']); self.assertTrue(result['holds'])

    def test_cancelled_january2_does_not_cancel_january16(self):
        import publication_guard as guard
        event2=self.fixture.event('2027-01-02')
        event16=self.fixture.event('2027-01-16')
        event2['title']=event16['title']='Saturday Jam Session 2'
        (self.root/'data/publication_tombstones.json').write_text(json.dumps({'events':[
            {'event_id':event2['id'],'date':event2['date'],'title':event2['title']}]}))
        self.assertFalse(guard.event_publishable(event2,self.root))
        self.assertTrue(guard.event_publishable(event16,self.root))
        self.assertNotEqual(event2['id'],event16['id'])

    def test_changed_main_blocks_reconciliation(self):
        with self.assertRaisesRegex(ValueError,'Main'):
            adapter.reconcile(self.root,self.state,self.plan,self.capture,
                              lambda root,paths=():{'main_commit':'CHANGED','sha256':{}})

    def test_duplicate_requested_slot_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            adapter.prepare_batch(self.root,self.state,[self.request,self.request],self.snapshot)

    def test_duplicate_reservation_on_another_uuid_is_not_adopted(self):
        other=copy.deepcopy(self.capture['posts'][0])
        other.update(uuid='SECOND-UUID',id=789)
        self.capture['posts'].append(other)
        state,result=self.run_capture()
        self.assertEqual([],state['records']); self.assertTrue(result['holds'])

    def test_missing_actual_bytes_and_unsupported_settings_hold(self):
        original=copy.deepcopy(self.capture)
        for change in [lambda c:c['media'][0].update(local_path=str(self.root/'absent.png')),
                       lambda c:c['posts'][0].update(autoPublish=False),
                       lambda c:c['posts'][0].update(firstCommentText='EXISTING COMMENT')]:
            self.capture=copy.deepcopy(original);change(self.capture)
            state,result=self.run_capture()
            self.assertEqual([],state['records']);self.assertTrue(result['holds'])


if __name__=='__main__':
    unittest.main()
