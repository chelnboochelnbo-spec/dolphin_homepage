// Dependency-free DOM-path checks of the real script. No socket, navigation, or
// external send is possible: fetch, location, history, and timers are local fakes.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../reservations.js'), 'utf8');
const flush = () => new Promise(resolve => setImmediate(resolve));
const fixture = (extra = {}) => ({
  id: 'TEST-live', title: 'TEST live', status: 'published', date: '2026-10-13',
  event_type: 'live', open: '19:30', start: '20:00', charge: 'Charge ¥4,500',
  performers: [{ instrument: 'Piano', name: 'TEST performer' }], ...extra,
});
const fixtures = () => ({
  '/data/events.json': { events: [
    fixture(),
    fixture({ id: 'TEST-student', title: 'TEST student jam', date: '2026-10-15', event_type: 'session', charge: 'Charge ¥2,000 2Drink Order / 学生 ¥1,000 1Drink Order' }),
    fixture({ id: 'TEST-other', title: 'TEST other show', date: '2026-10-16', charge: 'Charge ¥3,000 +2d' }),
    fixture({ id: 'TEST-multi', title: 'TEST multi-day', date: '2026-10-12', end_date: '2026-10-16', charge: '' }),
    fixture({ id: 'TEST-november', title: 'TEST November', date: '2026-11-02' }),
  ] },
  '/data/operations.json': { timezone: 'Asia/Tokyo', closed_policy: 'irregular', standard_hours: { open: '19:00', close: '01:00' }, bar_charge: '¥500', overrides: { '2026-10-14': { state: 'closed' } } },
  '/data/publication_tombstones.json': { events: [] },
});
const response = data => ({ ok: true, json: async () => structuredClone(data) });
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

// Only the small DOM surface used by reservations.js is implemented. Missing
// optional elements (including the native Google Forms iframe) return null.
class EventTarget {
  constructor() { this.listeners = new Map(); }
  addEventListener(type, listener) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(listener);
  }
  emit(type, extra = {}) {
    const event = { type, target: this, button: 0, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, ...extra };
    const results = (this.listeners.get(type) || []).map(listener => listener(event));
    return { event, results };
  }
}
class Element extends EventTarget {
  constructor(tag = 'div') {
    super(); this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {};
    this.attributes = new Map(); this._text = ''; this._value = ''; this.focusCalls = [];
  }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  set textContent(text) { this._text = String(text); this.children = []; }
  append(...children) {
    for (const child of children) { child.parentElement = this; this.children.push(child); }
  }
  replaceChildren(...children) {
    this._text = ''; this.children = []; this.append(...children);
    if (this.tagName === 'SELECT') this._value = this.options[0]?.value || '';
  }
  add(option) { this.append(option); }
  get options() { return this.children.filter(child => child.tagName === 'OPTION'); }
  get value() { return this._value; }
  set value(value) {
    this._value = this.tagName !== 'SELECT' || this.options.some(option => option.value === String(value)) ? String(value) : '';
  }
  get selectedOptions() { return this.options.filter(option => option.value === this.value); }
  setAttribute(key, value) { this.attributes.set(key, String(value)); }
  getAttribute(key) { return this.attributes.get(key) ?? null; }
  focus(options) { this.focusCalls.push(options); }
  scrollIntoView() { this.scrollCalls = (this.scrollCalls || 0) + 1; }
  closest(selector) {
    assert.equal(selector, 'a[href]');
    return this.tagName === 'A' && this.href ? this : this.parentElement?.closest(selector) || null;
  }
}
class Option extends Element {
  constructor(text, value) { super('option'); this.textContent = text; this.value = value; }
}
function harness({ data = fixtures(), href = 'https://test.example.invalid/en/', lang = 'en', legacyForm = false, fetch: fetchOverride } = {}) {
  const window = new EventTarget();
  const elements = Object.fromEntries(['event', 'month', 'date', 'reservationStatus', 'reservationFees', 'englishEvents', 'englishWeek', 'reservation'].map(id => [id, new Element(id === 'event' ? 'select' : 'div')]));
  elements.event.replaceChildren(new Option('Choose an event', ''), new Option('Bar enquiry', 'Normal'));
  elements.englishWeek.setAttribute('aria-busy', 'true');
  if (legacyForm) {
    for (const id of ['reserveForm', 'name', 'email', 'people', 'tel', 'message', 'discovery']) elements[id] = new Element();
    elements.name.value = 'TEST - do not book'; elements.email.value = 'test@example.invalid'; elements.people.value = '1';
  }
  const document = new EventTarget();
  Object.assign(document, { documentElement: { lang }, hidden: false,
    getElementById: id => elements[id] || null, createElement: tag => new Element(tag) });
  let currentURL = new URL(href);
  const location = {
    get href() { return currentURL.href; }, set href(value) { currentURL = new URL(value, currentURL); },
    get origin() { return currentURL.origin; }, get pathname() { return currentURL.pathname; },
  };
  const entries = [location.href]; let historyIndex = 0;
  const history = {
    pushes: [], get length() { return entries.length; },
    pushState(state, title, url) {
      const target = new URL(url, location.href);
      assert.equal(target.origin, location.origin, 'Cross-origin history mutation');
      this.pushes.push(target.href); entries.splice(++historyIndex); entries.push(target.href); location.href = target.href;
    },
    back() { if (historyIndex > 0) { location.href = entries[--historyIndex]; window.emit('popstate'); } },
    forward() { if (historyIndex + 1 < entries.length) { location.href = entries[++historyIndex]; window.emit('popstate'); } },
  };
  let now = Date.parse('2026-10-13T03:00:00Z'), nextTimer = 1;
  const timeouts = new Map(), intervals = new Map();
  class FixedDate extends Date {
    constructor(...args) { super(...(args.length ? args : [now])); }
    static now() { return now; }
  }
  window.setTimeout = (callback, delay) => { const id = nextTimer++; timeouts.set(id, { callback, due: now + delay }); return id; };
  window.clearTimeout = id => timeouts.delete(id);
  window.setInterval = (callback, delay) => { const id = nextTimer++; intervals.set(id, { callback, delay }); return id; };
  const requests = [];
  const fetch = (url, options) => {
    const request = { url, ...options }; requests.push(request);
    assert(Object.hasOwn(data, url), `Unexpected fetch: ${url}`);
    // The fake rejects on abort, just as a stalled native fetch would.
    return new Promise((resolve, reject) => {
      options.signal.addEventListener('abort', () => {
        const error = new Error('TEST aborted request'); error.name = 'AbortError'; reject(error);
      }, { once: true });
      Promise.resolve(fetchOverride ? fetchOverride(request, requests.length) : response(data[url])).then(resolve, reject);
    });
  };
  vm.runInNewContext(source, { window, document, location, history, Option, fetch, URL, URLSearchParams, AbortController, Date: FixedDate }, { filename: 'reservations.js' });
  return { window, document, elements, requests, history, location, timeouts, intervals,
    start() { return Promise.all(document.emit('DOMContentLoaded').results); },
    choose(id) { elements.event.value = id; elements.event.emit('change'); },
    setNow(value) { now = Date.parse(value); },
    runIntervals() { for (const timer of intervals.values()) timer.callback(); },
    advanceTimeouts(ms) {
      now += ms;
      for (const [id, timer] of [...timeouts]) if (timer.due <= now) { timeouts.delete(id); timer.callback(); }
    },
    click(href, extra = {}) {
      const link = new Element('a'); link.href = href;
      if (extra.targetBlank) link.target = '_blank';
      const child = new Element('span'); link.append(child);
      return document.emit('click', { target: child, ...extra }).event;
    },
  };
}
const optionIDs = h => h.elements.event.options.map(option => option.value);
const states = h => h.elements.englishWeek.children.map(card => card.dataset.state);

test('DOM loading waits for all feeds, then renders seven JST days and usable events', async () => {
  const data = fixtures(); const gates = Object.fromEntries(Object.keys(data).map(key => [key, deferred()]));
  const h = harness({ data, fetch: request => gates[request.url].promise });
  const ready = h.start();
  assert.deepEqual(h.requests.map(request => request.url), Object.keys(data));
  assert(h.requests.every(request => request.cache === 'no-cache' && request.signal instanceof AbortSignal));
  assert.equal(h.elements.englishWeek.getAttribute('aria-busy'), 'true');
  gates['/data/events.json'].resolve(response(data['/data/events.json'])); await flush();
  assert.equal(h.elements.englishEvents.children.length, 0, 'Do not publish events before checking tombstones');
  for (const key of ['/data/operations.json', '/data/publication_tombstones.json']) gates[key].resolve(response(data[key]));
  await ready;
  assert.equal(h.elements.englishWeek.getAttribute('aria-busy'), 'false');
  assert.equal(h.elements.englishWeek.children.length, 7);
  assert.equal(h.elements.englishWeek.children[0].dataset.date, '2026-10-13');
  assert.match(h.elements.englishWeek.children[0].textContent, /Tonight.*TEST live.*Doors 19:30 \/ Starts 20:00.*¥4,500/);
  assert.deepEqual(states(h), ['event', 'closed', 'event', 'event', 'bar', 'bar', 'bar']);
  assert.equal(h.elements.englishEvents.children.length, 5);
  assert.deepEqual(optionIDs(h), ['', 'TEST-multi', 'TEST-live', 'TEST-student', 'TEST-other', 'TEST-november', 'Normal']);
  assert.equal(h.timeouts.size, 0, 'Successful reads clear their abort timers');
});

test('DOM deep links, selection changes, multi-day dates, month filtering, and fee summaries stay synchronized', async () => {
  const h = harness({ href: 'https://test.example.invalid/en/?event_id=TEST-student#reservation' });
  await h.start();
  assert.equal(h.elements.month.value, 'oct');
  assert.equal(h.elements.event.value, 'TEST-student');
  assert.equal(h.elements.date.value, '2026-10-15');
  assert.equal(h.elements.date.min, '2026-10-15');
  assert.equal(h.elements.date.max, '2026-10-15');
  assert.equal(h.elements.date.readOnly, true);
  assert.match(h.elements.reservationFees.textContent, /Students ¥1,000 1-drink minimum/);
  assert.match(h.elements.reservationFees.textContent, /paid for separately/);
  h.choose('TEST-multi');
  assert.equal(h.elements.date.value, '2026-10-13');
  assert.equal(h.elements.date.min, '2026-10-13');
  assert.equal(h.elements.date.max, '2026-10-16');
  assert.equal(h.elements.date.readOnly, false);
  assert.match(h.elements.reservationFees.textContent, /Admission to be confirmed/);
  h.choose('TEST-live');
  assert.match(h.elements.reservationFees.textContent, /minimum is not listed/);
  h.elements.month.value = 'nov'; h.elements.month.emit('change');
  assert.deepEqual(optionIDs(h), ['', 'TEST-november', 'Normal']);
  assert.equal(h.elements.event.value, '');
  assert.equal(h.elements.date.value, '');
  h.choose('Normal');
  assert.match(h.elements.reservationFees.textContent, /¥500 cover.*Drinks and food are separate/);
  assert.equal(h.elements.date.value, '');
});

for (const failed of ['events', 'operations', 'publication_tombstones']) {
  test(`DOM ${failed} fetch failure produces safe unknown nights and preserves the contact route`, async () => {
    const data = fixtures();
    const h = harness({ data, fetch: request => request.url === `/data/${failed}.json` ? { ok: false } : response(data[request.url]) });
    await h.start();
    assert.deepEqual(states(h), Array(7).fill('unknown'));
    assert.equal(h.elements.englishWeek.getAttribute('aria-busy'), 'false');
    assert(h.elements.englishWeek.children.every(card => /Call Dolphin/.test(card.textContent)));
    assert(optionIDs(h).includes('Normal'));
    if (failed === 'operations') {
      assert(optionIDs(h).includes('TEST-live'), 'Operations failure must not hide verified events');
      assert.equal(h.elements.englishEvents.children.length, 5);
    } else {
      assert.deepEqual(optionIDs(h), ['', 'Normal']);
      assert.match(h.elements.englishEvents.textContent, /schedule could not be loaded/);
      assert.match(h.elements.reservationStatus.textContent, /Could not refresh/);
    }
    h.choose('Normal');
    assert.equal(h.elements.event.value, 'Normal');
    assert.equal(h.elements.reservationStatus.textContent, '');
    assert.equal(h.timeouts.size, 0);
  });
}

test('DOM malformed or unparseable schedule/guard JSON fails closed', async () => {
  for (const [key, mode] of [['events', 'shape'], ['publication_tombstones', 'shape'], ['events', 'parse'], ['publication_tombstones', 'parse']]) {
    const data = fixtures();
    const h = harness({ data, fetch: request => request.url === `/data/${key}.json`
      ? (mode === 'shape' ? response({ events: null }) : { ok: true, json: async () => { throw new SyntaxError('TEST invalid JSON'); } })
      : response(data[request.url]) });
    await h.start();
    assert.deepEqual(optionIDs(h), ['', 'Normal'], `${key}: ${mode}`);
    assert.deepEqual(states(h), Array(7).fill('unknown'), `${key}: ${mode}`);
    assert.match(h.elements.englishEvents.textContent, /could not be loaded/);
  }
});

test('DOM cancellation tombstones filter IDs and normalized titles, including deep links', async () => {
  const data = fixtures();
  data['/data/events.json'].events = [fixture(),
    fixture({ id: 'TEST-cancelled-id', title: 'TEST renamed title' }),
    fixture({ id: 'TEST-reissued-id', title: '  TEST cancelled title  ' }),
    fixture({ id: 'TEST-flagged', cancelled: true }),
    fixture({ id: 'TEST-cancellation', cancellation: { reason: 'TEST cancellation' } }),
    fixture({ id: 'TEST-draft', status: 'draft' }),
    fixture({ id: 'TEST-past', date: '2026-10-12' }),
  ];
  data['/data/publication_tombstones.json'].events = [
    { event_id: 'TEST-cancelled-id', date: '2026-10-13', title: 'TEST previous title' },
    { event_id: 'TEST-original-id', date: '2026-10-13', title: 'test cancelled title' },
  ];
  const h = harness({ data, href: 'https://test.example.invalid/en/?event_id=TEST-reissued-id#reservation' });
  await h.start();
  assert.deepEqual(optionIDs(h), ['', 'TEST-live', 'Normal']);
  assert.equal(h.elements.englishEvents.children.length, 1);
  assert.equal(h.elements.event.value, '');
  assert.equal(h.elements.date.value, '');
  assert.match(h.elements.reservationStatus.textContent, /event is unavailable/);
  assert.doesNotMatch(h.elements.englishWeek.textContent, /TEST renamed title|TEST cancelled title/);
});

for (const stalled of ['events', 'operations', 'publication_tombstones']) {
  test(`DOM a stalled ${stalled} read is aborted at ten seconds and loading settles safely`, async () => {
    const data = fixtures();
    const h = harness({ data, fetch: request => request.url === `/data/${stalled}.json` ? new Promise(() => {}) : response(data[request.url]) });
    const ready = h.start(); await flush();
    const request = h.requests.find(request => request.url === `/data/${stalled}.json`);
    assert.equal(h.timeouts.size, 1);
    h.advanceTimeouts(9999); assert.equal(request.signal.aborted, false);
    assert.equal(h.elements.englishWeek.getAttribute('aria-busy'), 'true');
    h.advanceTimeouts(1); await ready;
    assert.equal(request.signal.aborted, true);
    assert.equal(h.timeouts.size, 0);
    assert.equal(h.elements.englishWeek.getAttribute('aria-busy'), 'false');
    assert.deepEqual(states(h), Array(7).fill('unknown'));
    assert.equal(optionIDs(h).includes('TEST-live'), stalled === 'operations');
  });
}

test('DOM midnight refresh preserves the newer selection and TEST form fields while preventing parallel reads', async () => {
  const data = fixtures(), pending = deferred(); let operationReads = 0;
  const h = harness({ data, legacyForm: true, fetch: request => request.url === '/data/operations.json' && ++operationReads > 1 ? pending.promise : response(data[request.url]) });
  await h.start();
  h.choose('TEST-student');
  h.setNow('2026-10-13T15:00:01Z'); // Midnight in Japan, still October 13 in UTC.
  h.runIntervals(); await flush();
  assert.equal(h.requests.length, 6);
  h.choose('TEST-other');
  h.document.emit('visibilitychange'); h.runIntervals();
  assert.equal(h.requests.length, 6, 'Only one refresh may be pending');
  pending.resolve(response(data['/data/operations.json'])); await flush();
  assert.equal(h.elements.englishWeek.children[0].dataset.date, '2026-10-14');
  assert.equal(h.elements.event.value, 'TEST-other');
  assert.equal(h.elements.date.value, '2026-10-16');
  assert.match(h.elements.reservationFees.textContent, /¥3,000 \+ 2-drink minimum/);
  assert.equal(h.elements.name.value, 'TEST - do not book');
  assert.equal(h.elements.email.value, 'test@example.invalid');
  h.runIntervals(); assert.equal(h.requests.length, 6, 'No repeated refresh on the same JST date');
});

test('DOM legacy form submission is intercepted before initial loading can expose contact fields in a GET URL', async () => {
  const data = fixtures(), pending = deferred();
  const h = harness({ data, legacyForm: true, fetch: () => pending.promise });
  const ready = h.start();
  const originalURL = h.location.href;
  const { event } = h.elements.reserveForm.emit('submit');
  assert.equal(event.defaultPrevented, true);
  assert.equal(h.elements.event.focusCalls.length, 1);
  assert.equal(h.location.href, originalURL);
  assert.equal(h.history.pushes.length, 0);
  // Complete the pending lifecycle without submitting or opening any URL.
  pending.resolve(response({ events: [] })); await ready;
});

test('DOM reservation navigation handles Back/Forward and duplicate clicks without hijacking other links', async () => {
  const h = harness(); await h.start();
  const eventURL = 'https://test.example.invalid/en/?event_id=TEST-student#reservation';
  assert.equal(h.click(eventURL).defaultPrevented, true);
  assert.equal(h.elements.event.value, 'TEST-student');
  assert.equal(h.elements.date.value, '2026-10-15');
  assert.equal(h.history.length, 2);
  assert.equal(h.elements.reservation.scrollCalls, 1);
  assert.equal(h.elements.event.focusCalls.length, 1);
  assert.equal(h.click(eventURL).defaultPrevented, true);
  assert.equal(h.history.length, 2, 'Same URL must not add duplicate history entries');
  h.history.back();
  assert.equal(h.elements.event.value, ''); assert.equal(h.elements.date.value, '');
  h.history.forward();
  assert.equal(h.elements.event.value, 'TEST-student');
  assert.match(h.elements.reservationFees.textContent, /Students ¥1,000/);
  const count = h.history.pushes.length;
  for (const extra of [{ button: 1 }, { metaKey: true }, { ctrlKey: true }, { shiftKey: true }, { altKey: true }, { targetBlank: true }]) {
    assert.equal(h.click(eventURL, extra).defaultPrevented, false);
  }
  for (const href of ['https://external.example.invalid/en/?event_id=TEST-live', '/?event_id=TEST-live', '/en/#reservation', 'mailto:test@example.invalid']) {
    assert.equal(h.click(href).defaultPrevented, false);
  }
  assert.equal(h.history.pushes.length, count);
  assert.equal(h.location.href, eventURL);
  assert.equal(h.click('/en/?event_id=TEST-missing#reservation').defaultPrevented, true);
  assert.equal(h.elements.event.value, '');
  assert.equal(h.elements.date.value, '');
  assert.match(h.elements.reservationStatus.textContent, /event is unavailable/);
});


test('DOM native form prefill preserves an edited multi-day date without reloading on refresh', async () => {
  const data = fixtures(), pending = deferred(); let operationReads = 0;
  const h = harness({ data, href: 'https://test.example.invalid/en/?event_id=TEST-multi#reservation',
    fetch: request => request.url === '/data/operations.json' && ++operationReads > 1 ? pending.promise : response(data[request.url]) });
  const frame = h.elements.reservationFrame = new Element('iframe');
  h.elements.openReservationForm = new Element('a');
  let src = '', loads = 0;
  // Assignments are recorded locally; no iframe or external request is created.
  Object.defineProperty(frame, 'src', { get: () => src, set: value => { src = value; loads++; } });
  await h.start();
  assert.equal(new URL(frame.src).searchParams.get('entry.1102411826'), 'TEST multi-day');
  assert.equal(new URL(frame.src).searchParams.get('embedded'), 'true');
  assert.equal(new URL(h.elements.openReservationForm.href).searchParams.get('usp'), 'pp_url');
  h.elements.date.value = '2026-10-15'; h.elements.date.emit('change');
  assert.equal(new URL(frame.src).searchParams.get('entry.1475276432'), '2026-10-15');
  h.setNow('2026-10-14T03:00:00Z'); h.runIntervals(); await flush();
  // A still newer date chosen while the refresh waits must also survive.
  h.elements.date.value = '2026-10-16'; h.elements.date.emit('change');
  const before = loads;
  pending.resolve(response(data['/data/operations.json'])); await flush();
  assert.equal(h.elements.date.value, '2026-10-16');
  assert.equal(h.elements.date.min, '2026-10-14');
  assert.equal(loads, before, 'Unchanged event/date must not reload a partly completed Google Form');
  assert.equal(new URL(h.elements.openReservationForm.href).searchParams.get('entry.1475276432'), '2026-10-16');
  h.setNow('2026-10-17T03:00:00Z'); h.runIntervals(); await flush();
  assert.equal(h.elements.event.value, '');
  assert.equal(h.elements.date.value, '');
  assert.equal(new URL(frame.src).searchParams.has('entry.1102411826'), false);
  assert.equal(new URL(frame.src).searchParams.has('entry.1475276432'), false);
  h.choose('Normal');
  assert.equal(new URL(frame.src).searchParams.get('entry.1102411826'), 'Bar visit / other enquiry');
  assert.equal(new URL(frame.src).searchParams.has('entry.1475276432'), false);
});
