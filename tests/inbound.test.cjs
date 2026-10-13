const { test } = require('node:test');
const assert = require('node:assert/strict');
const { upcoming, chargeEN, drinkConditionsEN, nextSevenDays, operatingDay, emailURL } = require('../reservations.js');
const operations = require('../data/operations.json');
const data = require('../data/events.json');
const fixture = (extra = {}) => ({id: 'TEST-event', title: 'TEST only', status: 'published', date: '2026-11-01', event_type: 'live', ...extra});
test('seven days include tonight, real closures, events and regular bar nights', () => {
  const before = JSON.stringify([data, operations]);
  const days = nextSevenDays(data.events, operations, '2026-10-13');
  assert.deepEqual(days.map(d => d.date), ['2026-10-13','2026-10-14','2026-10-15','2026-10-16','2026-10-17','2026-10-18','2026-10-19']);
  assert.deepEqual(days.map(d => d.state), ['event','closed','event','bar','event','closed','bar']);
  assert.equal(days[0].events[0].charge, 'Charge ¥4,500');
  assert.equal(days[4].events[0].charge, 'Charge ¥2,000 + 2Drink Order');
  assert.equal(days[3].hours, '19:00–01:00 (next day)');
  assert.equal(before, JSON.stringify([data, operations]));
});
test('override wins; published Sunday event opens; private is not a bar night', () => {
  const event = fixture();
  assert.equal(operatingDay(event.date, [event], operations).state, 'event');
  for (const state of ['closed', 'private']) {
    const ops = structuredClone(operations); ops.overrides[event.date] = { state };
    assert.equal(operatingDay(event.date, [event], ops).state, state);
  }
  for (const state of ['open', 'bar']) {
    const ops = structuredClone(operations); ops.overrides[event.date] = { state };
    assert.equal(operatingDay(event.date, [], ops).state, 'bar');
  }
});
test('holiday shift, calendar horizon, invalid data and month/year boundaries', () => {
  assert.equal(operatingDay('2027-01-10', [], operations).state, 'bar');
  assert.equal(operatingDay('2027-01-11', [], operations).state, 'closed');
  assert.equal(operatingDay('2028-01-02', [], operations).state, 'unknown');
  assert.equal(operatingDay('2026-10-13', data.events, null).state, 'unknown');
  assert.equal(operatingDay('2026-10-13', [], {}).state, 'unknown');
  assert.deepEqual(nextSevenDays([], operations, '2026-12-30').map(d => d.date), ['2026-12-30','2026-12-31','2027-01-01','2027-01-02','2027-01-03','2027-01-04','2027-01-05']);
});
test('cancelled and draft events stay hidden; multiple and multi-day events remain', () => {
  const base = fixture({date:'2026-10-13',end_date:'2026-10-15'});
  const events = [base, fixture({id:'second',date:'2026-10-14'}), fixture({cancelled:true}), fixture({cancellation:{reason:'TEST'}}), fixture({status:'draft'})];
  assert.equal(upcoming(events,'2026-10-13').length,2);
  assert.equal(operatingDay('2026-10-15',events,operations).events.length,1);
  assert.equal(operatingDay('2026-10-16',events,operations).state,'bar');
  const ops=structuredClone(operations); delete ops.overrides['2026-10-14'];
  assert.equal(operatingDay('2026-10-14',events,ops).events.length,2);
});
test('price tiers preserve currency and per-tier drink minimums without inventing conditions', () => {
  assert.equal(chargeEN('Charge ¥2,000 2Drink Order / 学生 ¥1,000 1Drink Order'), 'Admission: ¥2,000 2-drink minimum / Students ¥1,000 1-drink minimum');
  assert.equal(chargeEN('Charge: ¥2,000 (+2d)'), 'Admission: ¥2,000 (+ 2-drink minimum)');
  assert.equal(chargeEN('前売り ¥4,000 / 当日 ¥4,500'), 'Advance ¥4,000 / At the door ¥4,500');
  assert.equal(chargeEN('Charge ¥2,000 2Drink Order / 学生 ¥1,000'), 'Admission: ¥2,000 2-drink minimum / Students ¥1,000');
  assert.match(chargeEN(null), /to be confirmed/);
  assert.match(drinkConditionsEN('Charge ¥4,500'), /minimum is not listed/);
  assert.match(drinkConditionsEN('Charge ¥2,000 + 2Drink Order'), /paid for separately/);
});
test('optional discovery is safely encoded only when selected; TEST email is never sent', () => {
  const fields = {event:'TEST reservation, do not book', date:'2026-10-13', name:'TEST', email:'test@example.invalid', people:'1', tel:'', message:'TEST & ? #', discovery:'Google Maps'};
  const url = emailURL(fields,true);
  assert(url.startsWith('mailto:bardolphinsince2016@gmail.com?'));
  const body = new URLSearchParams(url.split('?')[1]).get('body');
  assert.match(body, /How I heard about Dolphin: Google Maps/);
  assert.match(body, /TEST & \? #/);
  assert(!decodeURIComponent(emailURL({...fields,discovery:''},true)).includes('How I heard'));
  assert(!decodeURIComponent(emailURL({...fields,discovery:'arbitrary\nvalue'},true)).includes('How I heard'));
});
test('canonical cancellation tombstones cannot be revived by a changed status or id', () => {
  const tombstones = require('../data/publication_tombstones.json').events;
  const original = data.events.find(e => e.id === '2027-01-02_saturday-jam-session-1');
  const revived = {...original, status:'published'};
  assert.deepEqual(upcoming([revived], '2026-10-13', tombstones), []);
  assert.deepEqual(upcoming([{...revived,id:'different'}], '2026-10-13', tombstones), []);
});
test('Google Form prefill contains only public event facts and uses verified entry IDs', () => {
  const { webFormURL } = require('../reservations.js');
  const url = new URL(webFormURL('MIKIKO & GRIGORIS', '2026-11-03'));
  assert.equal(url.origin, 'https://docs.google.com');
  assert.equal(url.pathname, '/forms/d/e/1FAIpQLSdGlHzvaeYnQnrwqLqkeK-PyIePHlo4aI-AsOjuaE-W2cYk6Q/viewform');
  assert.equal(url.searchParams.get('entry.1102411826'), 'MIKIKO & GRIGORIS');
  assert.equal(url.searchParams.get('entry.1475276432'), '2026-11-03');
  assert.deepEqual([...url.searchParams.keys()].sort(), ['entry.1102411826','entry.1475276432','usp']);
  assert.equal(new URL(webFormURL('', '', true)).search, '?embedded=true');
  assert(!new URL(webFormURL('TEST','not-a-date')).searchParams.has('entry.1475276432'));
});
