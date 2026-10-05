const {test}=require('node:test');
const assert=require('node:assert/strict');
const {todayJST,upcoming,chargeEN,reservationURL,emailURL}=require('../reservations.js');
const data=require('../data/events.json');
test('JST day boundary and last day of multi-day events',()=>{
  assert.equal(todayJST(new Date('2026-10-05T14:59:59Z')),'2026-10-05');
  assert.equal(todayJST(new Date('2026-10-05T15:00:00Z')),'2026-10-06');
  assert.deepEqual(upcoming([{id:'multi',status:'published',date:'2026-10-03',end_date:'2026-10-05',title:'x'},{id:'past',status:'published',date:'2026-10-04',title:'x'},{id:'draft',status:'draft',date:'2026-10-06',title:'x'}],'2026-10-05').map(e=>e.id),['multi']);
});
test('correct Suzuki date and both Wakai events are selectable',()=>{
  const events=upcoming(data.events,'2026-10-05');
  assert(events.some(e=>e.id==='2026-10-11_chiaki-suzuki-quartet-live-session'));
  for(const date of ['2026-11-20','2026-11-21']) assert(events.some(e=>e.date===date&&e.title.includes('若井')));
  assert(!events.some(e=>e.date==='2026-10-16'&&e.title.includes('鈴木')));
});
test('fees preserve amounts, unknown does not imply free',()=>{
  assert.match(chargeEN(''),/to be confirmed/);
  assert.equal(chargeEN('Charge 予約 ¥5,000 / 当日 ¥5,500'),'Admission: Advance reservation ¥5,000 / At the door ¥5,500');
  assert.match(chargeEN('Charge ¥1,000 + 投げ銭'),/pay-what-you-wish/);
});
test('English event handoff and email preserve punctuation, no send action',()=>{
  assert.equal(reservationURL('a&b',true),'/en/?event_id=a%26b#reservation');
  const link=emailURL({event:'MIKIKO & GRIGORIS',date:'2026-11-03',name:'Test',email:'test@example.invalid',people:'2',tel:'',message:'a&b'},true);
  assert(link.startsWith('mailto:'));
  const params=new URLSearchParams(link.split('?')[1]);
  assert.match(params.get('subject'),/MIKIKO & GRIGORIS/);
  assert.match(params.get('body'),/Japan time.*2026-11-03/);
});
