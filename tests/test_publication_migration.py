"""Synthetic migration/connector fixtures, not production evidence or API calls."""
import copy
import io
import json
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import test_publication_guard as fixtures

guard = fixtures.guard
social = fixtures.social


class Migration(unittest.TestCase):
    setUp = fixtures.PublicationGuard.setUp
    event = fixtures.PublicationGuard.event
    review = fixtures.PublicationGuard.review
    persist = fixtures.PublicationGuard.persist
    package = fixtures.PublicationGuard.package
    def migration_record(self, events):
        review = self.review(events)
        return {"record_id": "TEST-MIGRATION", "source_path": review["image_path"],
                "image_path": review["image_path"], "image_sha256": review["image_sha256"],
                "covered_dates": review["covered_dates"], "targets": review["targets"],
                "website_preservation": {"policy_version": 1, "scope": "exact_existing_asset_and_dates"}, "existing_posts": []}

    def test_baseline_keeps_hp_but_never_approves_new_social(self):
        self.events[0]["title"] = "Historical or out-of-scope live"
        self.ledger["reviews"] = []; self.persist()
        record = self.migration_record([self.events[0]])
        social.write_json(self.root/'data/website_image_baseline.json', {"records": [record]})
        decision = guard.website_decision(self.events[0], self.root)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.evidence_kind, "website_baseline_unverified")
        self.assertFalse(guard.assess(self.events[0], self.root).allowed)
        with self.assertRaises(ValueError): self.package()
        changed = {**self.events[0], "start": "21:00"}
        self.assertFalse(guard.website_decision(changed, self.root).allowed)
        (self.root/record['image_path']).write_bytes(b'CHANGED TEST BYTES')
        self.assertFalse(guard.website_decision(self.events[0], self.root).allowed)

    def test_future_recurring_cannot_be_grandfathered(self):
        record = self.migration_record([self.events[0]])
        self.ledger['reviews'] = []; self.persist()
        social.write_json(self.root/'data/website_image_baseline.json', {"records": [record]})
        self.assertFalse(guard.website_decision(self.events[0], self.root).allowed)

    def test_october_exception_is_exact_asset_dates_and_existing_posts(self):
        self.events = [self.event('2026-10-08'), self.event('2026-10-22')]
        for e in self.events: e['flyer']['github_path'] = 'assets/october.png'
        (self.root/'assets/october.png').write_bytes(b'SYNTHETIC OCTOBER IMAGE')
        self.ledger['reviews'] = []; self.persist()
        record = self.migration_record(self.events)
        social.write_json(self.root/'data/october_kiraku_migration.json', {'records':[record]})
        for e in self.events:
            self.assertTrue(guard.website_decision(e,self.root).allowed)
            self.assertFalse(guard.assess(e,self.root).allowed)
        package={'evidence_kind':'october_existing_publication','review_id':record['record_id'],
                 'channel':'instagram','channel_id':'TEST-ACCOUNT','slot_id':'existing-october',
                 'provider':'metricool','provider_uuid':'TEST-UUID','external_id':'100'}
        with self.assertRaises(ValueError): social.october_identity_allowed(package,self.root,self.private/'october.json')
        record['existing_posts']=[copy.deepcopy(package)]
        social.write_json(self.private/'october.json',{'records':[record]})
        social.write_json(self.root/'data/october_kiraku_migration.json',{'records':[record]})
        social.october_identity_allowed({**package,'external_id':'200'},self.root,self.private/'october.json')
        for key,value in [('provider_uuid','OTHER'),('channel_id','OTHER'),('slot_id','new')]:
            with self.assertRaises(ValueError): social.october_identity_allowed({**package,key:value},self.root,self.private/'october.json')
        changed={**self.events[0],'date':'2026-11-12'}
        self.assertFalse(guard.website_decision(changed,self.root).allowed)

    def invoke(self,*args):
        with patch.object(sys,'argv',['social_package','--root',str(self.root),'--state',str(self.private/'state.json'),*args]), patch('sys.stdout',new_callable=io.StringIO):
            social.main()

    def test_reconciled_legacy_account_survives_full_metricool_roundtrip(self):
        seed=self.package()
        seed.update(external_id='100',provider='metricool',provider_account_id='TEST-BRAND',provider_uuid='TEST-UUID',state='confirmed',package_hash='OLDER')
        state_path=self.private/'state.json'
        social.write_json(state_path,{'records':[seed]})
        # Legacy account is absent; trusted saved state supplies it.
        self.events[0]['social']['schedule']=[{'channel':'instagram','external_id':'100','provider':'metricool',
            'provider_uuid':'TEST-UUID','status':'scheduled','days_before':14}]
        self.persist()
        package_path=self.private/'package.json'; response_path=self.private/'response.json'
        self.invoke('prepare','--event-id',self.events[0]['id'],'--channel','instagram','--channel-id','TEST-ACCOUNT',
                    '--days-before','14','--output',str(package_path))
        package=json.loads(package_path.read_text())
        self.assertEqual(package['action'],'update')
        ack={'channel':'instagram','channel_id':'TEST-ACCOUNT','provider':'metricool','provider_account_id':'TEST-BRAND',
             'provider_uuid':'TEST-UUID','external_id':'200'}
        social.write_json(response_path,ack)
        self.invoke('accept','--package',str(package_path),'--response',str(response_path))
        self.assertEqual(json.loads(state_path.read_text())['records'][0]['state'],'accepted_pending_readback')
        response={**package,**ack,'external_id':'201','readback':True,'fetched_at':datetime.now(timezone.utc).isoformat(),'status':'scheduled'}
        social.write_json(response_path,{**response,'provider_uuid':'OTHER'})
        with self.assertRaises(ValueError): self.invoke('confirm','--package',str(package_path),'--response',str(response_path))
        social.write_json(response_path,response)
        self.invoke('confirm','--package',str(package_path),'--response',str(response_path))
        final=json.loads(state_path.read_text())['records'][0]
        self.assertEqual((final['state'],final['provider_uuid'],final['external_id']),('confirmed','TEST-UUID','201'))
        self.assertEqual(self.package({'records':[final]})['action'],'noop')
        outgoing=social.adapter_update_payload(package,{'twitterData':{'readonly':True},'facebookData':{'readonly':True}})
        self.assertNotIn('twitterData',outgoing)
        self.assertNotIn('facebookData',outgoing)

    def test_new_metricool_request_requires_explicit_brand_and_binds_returned_uuid(self):
        with self.assertRaises(ValueError):
            social.prepare(self.events[0]['id'],'instagram','TEST-ACCOUNT',14,{'records':[]},self.root,provider='metricool')
        package=social.prepare(self.events[0]['id'],'instagram','TEST-ACCOUNT',14,{'records':[]},self.root,
            provider='metricool',provider_account_id='TEST-BRAND')
        ack={'provider':'metricool','provider_account_id':'TEST-BRAND','provider_uuid':'NEW-UUID',
             'external_id':'101','channel':'instagram','channel_id':'TEST-ACCOUNT'}
        identity=social.response_identity(package,ack)
        self.assertEqual(identity['provider_uuid'],'NEW-UUID')
        with self.assertRaises(ValueError):
            social.response_identity({**package,**identity},{**ack,'provider_account_id':'OTHER-BRAND'})

    def test_thirty_and_seven_day_reminders_are_separate_identities(self):
        e=self.events[0]; e.update(title='TEST Special Live',event_type='live')
        self.ledger={'reviews':[self.review([e])]}
        e['social']['schedule']=[{'channel':'instagram','channel_id':'TEST-ACCOUNT','days_before':d,
            'status':'scheduled','external_id':str(d),'provider':'metricool','provider_account_id':'TEST-BRAND','provider_uuid':'UUID-'+str(d)} for d in [30,7]]
        self.persist()
        first=social.prepare(e['id'],'instagram','TEST-ACCOUNT',30,{'records':[]},self.root)
        second=social.prepare(e['id'],'instagram','TEST-ACCOUNT',7,{'records':[first]},self.root)
        self.assertEqual((first['external_id'],second['external_id']),('30','7'))
        self.assertNotEqual(first['key'],second['key'])

    def test_fourteen_day_migration_reuses_explicit_seven_day_slot(self):
        seed=self.package(); seed.update(slot_id='lead-7',days_before=7,allowed_days_before=[7,14],external_id='OLD',state='confirmed')
        seed['key']=social.digest([seed['event_ids'],seed['channel'],seed['channel_id'],'lead-7'])
        seed['package_hash']='OLD'
        package=social.prepare(self.events[0]['id'],'instagram','TEST-ACCOUNT',14,{'records':[seed]},self.root,'lead-7')
        self.assertEqual(package['external_id'],'OLD')
        self.assertEqual(package['key'],seed['key'])
        self.assertEqual(package['publish_at'],'2026-10-29T18:00:00+09:00')
        with self.assertRaises(ValueError):
            social.prepare(self.events[0]['id'],'instagram','TEST-ACCOUNT',14,{'records':[seed]},self.root)
        seed['allowed_days_before']=[7]
        with self.assertRaises(ValueError):
            social.prepare(self.events[0]['id'],'instagram','TEST-ACCOUNT',14,{'records':[seed]},self.root,'lead-7')

    def test_synthetic_october_reservation_uses_only_explicit_private_file(self):
        import hashlib
        self.events = [self.event('2026-10-08'), self.event('2026-10-22')]
        for event in self.events:
            event['flyer']['github_path']='assets/october.png'
        (self.root/'assets/october.png').write_bytes(b'SYNTHETIC OCTOBER IMAGE')
        self.ledger['reviews']=[]; self.persist()
        record=self.migration_record(self.events)
        social.write_json(self.root/'data/october_kiraku_migration.json',{'records':[record]})
        caption='SYNTHETIC OCTOBER CAPTION'
        record['existing_posts']=[dict(channel='instagram',channel_id='TEST-ACCOUNT',
            provider='metricool',provider_account_id='TEST-BRAND',provider_uuid='TEST-UUID',
            external_id='TEST-ID',slot_id='existing-slot',days_before=14,
            event_ids=[self.events[1]['id']],image_sha256=record['image_sha256'],
            caption=caption,caption_sha256=hashlib.sha256(caption.encode()).hexdigest(),
            publish_at='2026-10-08T18:00:00+09:00')]
        path=self.private/'october.json'
        social.write_json(path,{'records':[record]})
        with self.assertRaises(ValueError):
            social.prepare(self.events[1]['id'],'instagram','TEST-ACCOUNT',14,{'records':[]},self.root,'existing-slot')
        package=social.prepare(self.events[1]['id'],'instagram','TEST-ACCOUNT',14,
            {'records':[]},self.root,'existing-slot',october_path=path)
        self.assertEqual(package['provider_uuid'],'TEST-UUID')
        self.assertEqual(package['external_id'],'TEST-ID')
        for event_id,slot in [(self.events[0]['id'],'existing-slot'),(self.events[1]['id'],'new-slot')]:
            with self.assertRaises(ValueError):
                social.prepare(event_id,'instagram','TEST-ACCOUNT',14,{'records':[]},self.root,slot,october_path=path)

    def test_approved_production_images_and_cancellation_remain_guarded(self):
        events=guard.read_json(fixtures.ROOT/'data/events.json',{})['events']
        for event in events:
            if event['id']=='2027-01-02_saturday-jam-session-1':
                self.assertFalse(guard.website_decision(event).allowed)
            if event['date']>='2026-10-07' and event['title'] in {
                'Kiraku Jam','Open Groove Night Jam Session','Saturday Jam Session 2','Monthly Voices 〜Vocal Session〜'}:
                with self.subTest(event=event['id']):
                    self.assertTrue(guard.website_decision(event).allowed)
            if event['date']>='2026-11-01' and event['title']=='Saturday Jam Session 1':
                self.assertFalse(guard.website_decision(event).allowed)
