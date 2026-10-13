(function (root) {
    'use strict';
    const months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
    const typeLabels = { live: 'LIVE', session: 'JAM', live_session: 'LIVE & JAM' };
    const discoverySources = new Set(['Google Maps', 'Hotel', 'SNS', 'Friend', 'Other']);
    function todayJST(now = new Date()) {
        const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now).map(p => [p.type, p.value]));
        return `${parts.year}-${parts.month}-${parts.day}`;
    }
    function upcoming(events, today = todayJST(), tombstones = []) {
        const cancelled = e => tombstones.some(t => t.event_id === e.id ||
            (t.date === e.date && t.title.trim().toLowerCase() === e.title.trim().toLowerCase()));
        return events.filter(e => ['ready','published','archived'].includes(e.status) && !e.cancelled && !e.cancellation && !cancelled(e) && (e.end_date || e.date) >= today)
            .sort((a,b) => a.date.localeCompare(b.date) || (a.start || '').localeCompare(b.start || '') || a.title.localeCompare(b.title));
    }
    function chargeEN(value) {
        if (!value || !value.trim()) return 'Admission to be confirmed — please contact us.';
        return value.replace(/投げ銭|Choose Your Price/gi, 'pay-what-you-wish contribution')
            .replace(/学生/g, 'Students').replace(/予約/g, 'Advance reservation')
            .replace(/前売り?/g, 'Advance').replace(/当日/g, 'At the door').replace(/参加費/g, 'Admission')
            .replace(/(\d+)\s*Drink\s*Order/gi, '$1-drink minimum')
            .replace(/\+(\d+)d\b/gi, '+ $1-drink minimum')
            .replace(/^Charge\s*:?\s*(?:MC\s*)?/i, 'Admission: ').replace(/^MC\s*/i, 'Admission: ');
    }
    function drinkConditionsEN(value) {
        return /\d+\s*Drink\s*Order|\+\d+d\b/i.test(value || '')
            ? 'Drinks required by the minimum are ordered and paid for separately. Food is separate.'
            : 'Drinks and food are separate. A drink minimum is not listed; please confirm when requesting.';
    }
    function dateEN(value) {
        return new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Tokyo', weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(`${value}T12:00:00+09:00`));
    }
    function addDays(day, count) {
        const value = new Date(`${day}T12:00:00Z`);
        value.setUTCDate(value.getUTCDate() + count);
        return value.toISOString().slice(0, 10);
    }
    // Mirrors the canonical Python operating-calendar rule. Parity is tested over
    // the full verified holiday range; no visitor-device time zone is used.
    function isRegularClosure(day, operations) {
        if (operations.closed_policy === 'irregular') return false;
        if (operations.closed_policy !== 'sunday_holiday_end') throw new Error('Unknown closure policy');
        const rule = operations.closure_rule;
        if (day < rule.effective_from) return false;
        const calendar = rule.holiday_calendar;
        if (day < calendar.valid_from || day > calendar.valid_through) throw new Error('Unverified holiday date');
        const holidays = new Set(calendar.dates);
        let closure = addDays(day, -new Date(`${day}T12:00:00Z`).getUTCDay());
        while (holidays.has(addDays(closure, 1))) closure = addDays(closure, 1);
        return closure === day;
    }
    function operatingDay(day, events, operations) {
        const unknown = { date: day, state: 'unknown', events: [] };
        try {
            if (operations?.timezone !== 'Asia/Tokyo') return unknown;
            const override = operations.overrides?.[day] || {};
            const state = override.state;
            if (state && !['closed', 'private', 'open', 'bar'].includes(state)) return unknown;
            if (state === 'closed' || state === 'private') return { date: day, state, events: [], note: override.note || '' };
            const matches = upcoming(events, day).filter(e => e.date <= day);
            if (matches.length) return { date: day, state: 'event', events: matches };
            if (!['open', 'bar'].includes(state) && isRegularClosure(day, operations)) return { date: day, state: 'closed', events: [] };
            const hours = operations.standard_hours;
            if (!hours || ![hours.open, hours.close].every(t => /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(t))) return unknown;
            return { date: day, state: 'bar', events: [], hours: `${hours.open}–${hours.close}${hours.close <= hours.open ? ' (next day)' : ''}`, charge: operations.bar_charge };
        } catch (_) { return unknown; }
    }
    function nextSevenDays(events, operations, today = todayJST()) {
        return Array.from({ length: 7 }, (_, i) => operatingDay(addDays(today, i), events, operations));
    }
    function reservationURL(id, english = false) {
        return `${english ? '/en/' : '/'}?event_id=${encodeURIComponent(id)}#reservation`;
    }
    function webFormURL(eventTitle = '', date = '', embedded = false) {
        const url = new URL('https://docs.google.com/forms/d/e/1FAIpQLSdGlHzvaeYnQnrwqLqkeK-PyIePHlo4aI-AsOjuaE-W2cYk6Q/viewform');
        url.searchParams.set(embedded ? 'embedded' : 'usp', embedded ? 'true' : 'pp_url');
        // Only public event facts are prefilled. Never put customer fields in URLs.
        if (eventTitle) url.searchParams.set('entry.1102411826', eventTitle);
        if (/^\d{4}-\d{2}-\d{2}$/.test(date)) url.searchParams.set('entry.1475276432', date);
        return url.href;
    }
    function emailURL(fields, english = false) {
        const subject = `${english ? '[Dolphin reservation request]' : '【Dolphin ライブ予約】'} ${fields.date} ${fields.event}`;
        let body = english ? `Reservation request\n\nEvent: ${fields.event}\nDate (Japan time): ${fields.date}\nName: ${fields.name}\nEmail: ${fields.email}\nGuests: ${fields.people}\nPhone: ${fields.tel}\n\nMessage:\n${fields.message}` : `以下の内容で予約を希望します。\n\n公演：${fields.event}\n希望日：${fields.date}\nお名前：${fields.name}\nメール：${fields.email}\n人数：${fields.people}\nお電話番号：${fields.tel}\n\nその他ご要望：\n${fields.message}`;
        if (discoverySources.has(fields.discovery)) body += `\n\n${english ? 'How I heard about Dolphin' : 'Dolphinを知ったきっかけ'}: ${fields.discovery}`;
        return `mailto:bardolphinsince2016@gmail.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    }
    const api = { todayJST, upcoming, chargeEN, drinkConditionsEN, dateEN, addDays, isRegularClosure, operatingDay, nextSevenDays, reservationURL, webFormURL, emailURL };
    if (typeof module !== 'undefined') module.exports = api;
    root.DolphinReservations = api;
    if (typeof document === 'undefined') return;

    document.addEventListener('DOMContentLoaded', async () => {
        const english = document.documentElement.lang === 'en';
        const form = document.getElementById('reserveForm');
        const select = document.getElementById('event');
        const month = document.getElementById('month');
        const date = document.getElementById('date');
        const status = document.getElementById('reservationStatus');
        const fees = document.getElementById('reservationFees');
        const list = document.getElementById('englishEvents');
        const week = document.getElementById('englishWeek');
        const reservationFrame = document.getElementById('reservationFrame');
        const openForm = document.getElementById('openReservationForm');
        let events = [], operations = null, loadedDay = '', loading = false;
        const say = message => { if (status) status.textContent = message; };
        function node(tag, text, className = '') {
            const element = document.createElement(tag);
            element.textContent = text;
            if (className) element.className = className;
            return element;
        }
        function syncDate() {
            const option = select?.selectedOptions[0];
            const selected = events.find(e => e.id === select?.value);
            if (date) {
                const first = selected ? (selected.date < todayJST() ? todayJST() : selected.date) : '';
                const last = selected ? (selected.end_date || selected.date) : '';
                date.value = first || option?.dataset.date || '';
                date.min = first; date.max = last;
                date.readOnly = !selected || first === last;
            }
            if (fees) {
                fees.replaceChildren();
                if (selected) fees.append(node('strong', chargeEN(selected.charge)), node('p', drinkConditionsEN(selected.charge), 'small'));
                else if (select?.value === 'Normal') fees.textContent = operations?.bar_charge
                    ? `Regular bar nights: ${operations.bar_charge} cover. Drinks and food are separate. For event nights, the event's published price applies. Please include your preferred visit date below.`
                    : 'Please confirm the charge and your preferred visit date with Dolphin.';
                else fees.textContent = 'Choose an event to see its admission and drink conditions.';
            }
        }
        function syncWebForm() {
            if (!reservationFrame || !openForm) return;
            const selected = events.find(e => e.id === select?.value);
            const title = selected ? selected.title + (selected.display?.subtitle ? ` — ${selected.display.subtitle}` : '')
                : select?.value === 'Normal' ? 'Bar visit / other enquiry' : '';
            const chosenDate = selected ? date?.value : '';
            const embedded = webFormURL(title, chosenDate, true);
            // Do not reload an in-progress form if a data refresh left the choice unchanged.
            if (reservationFrame.src !== embedded) reservationFrame.src = embedded;
            openForm.href = webFormURL(title, chosenDate);
        }
        function fill(selected = '') {
            if (!select) return;
            select.replaceChildren(new Option(english ? 'Choose an event' : '公演を選択してください', ''));
            for (const e of events) {
                if (month?.value && months[Number(e.date.slice(5,7))-1] !== month.value) continue;
                const subtitle = e.display?.subtitle ? ` — ${e.display.subtitle}` : '';
                const option = new Option(`${english ? dateEN(e.date) : e.date} — ${e.title}${subtitle}`, e.id);
                option.dataset.date = e.date;
                select.add(option);
            }
            select.add(new Option(english ? 'Bar visit / other enquiry' : '通常営業・その他のお問い合わせ', 'Normal'));
            select.value = [...select.options].some(o => o.value === selected) ? selected : '';
            syncDate();
        }
        function applyURL() {
            const id = new URL(location.href).searchParams.get('event_id');
            if (!id) { fill(''); syncWebForm(); say(''); return; }
            const event = events.find(e => e.id === id);
            if (!event) { if (select) select.value = ''; syncDate(); syncWebForm(); say(english ? 'This event is unavailable. Please choose another event or contact us.' : 'この公演は選択できません。別の公演を選ぶかお問い合わせください。'); return; }
            if (month) month.value = months[Number(event.date.slice(5,7))-1];
            fill(id); syncWebForm(); say('');
        }
        function appendEvent(card, event, showDate) {
            card.append(node('p', typeLabels[event.event_type] || 'EVENT', 'night-type'));
            card.append(node('h3', event.title + (event.display?.subtitle ? ` — ${event.display.subtitle}` : '')));
            if (showDate) card.append(node('p', `${dateEN(event.date)}${event.end_date && event.end_date !== event.date ? ` – ${dateEN(event.end_date)}` : ''}`, 'small'));
            card.append(node('p', `${event.open ? `Doors ${event.open}` : 'Doors to be confirmed'} / ${event.start ? `Starts ${event.start}` : 'Start time to be confirmed'} (JST)`, 'small'));
            card.append(node('p', chargeEN(event.charge), 'event-charge'));
            card.append(node('p', drinkConditionsEN(event.charge), 'small'));
            if (showDate) card.append(node('p', (event.performers || []).map(p => [p.instrument, p.name].filter(Boolean).join(' ')).join(' / '), 'small'));
            const reserve = node('a', 'Request a reservation', 'btn'); reserve.href = reservationURL(event.id, true);
            const details = node('a', 'Event details', 'btn'); details.href = `/events/${encodeURIComponent(event.id)}/`;
            const actions = node('div', '', 'cta-row'); actions.append(details, reserve);
            card.append(actions);
        }
        function renderEnglish() {
            if (!list) return;
            list.replaceChildren();
            for (const event of events) {
                const card = node('article', '', 'card');
                appendEvent(card, event, true); list.append(card);
            }
            if (!events.length) list.textContent = 'No upcoming events are listed. Please contact us before visiting.';
        }
        function renderWeek(eventsAvailable = true) {
            if (!week) return;
            week.replaceChildren();
            const today = todayJST();
            for (const day of nextSevenDays(events, eventsAvailable ? operations : null, today)) {
                const card = node('article', '', 'card night-card');
                card.dataset.date = day.date; card.dataset.state = day.state;
                const heading = node('h3', `${day.date === today ? 'Tonight · ' : ''}${dateEN(day.date)}`, 'night-date');
                card.append(heading);
                if (day.state === 'event') {
                    for (const event of day.events) {
                        const details = node('div', '', 'night-event');
                        appendEvent(details, event, false); card.append(details);
                    }
                } else {
                    const labels = { closed: 'CLOSED', private: 'PRIVATE', bar: 'BAR NIGHT', unknown: 'PLEASE CHECK' };
                    card.append(node('p', labels[day.state], 'night-type'));
                    if (day.state === 'bar') {
                        card.append(node('p', day.hours + ' (JST)', 'small'));
                        card.append(node('p', day.charge ? `Bar charge ${day.charge}` : 'Bar charge to be confirmed', 'event-charge'));
                        card.append(node('p', 'Drinks and food are separate. Listening and solo visits are welcome.', 'small'));
                    } else if (day.state === 'closed') card.append(node('p', 'Closed for the evening. Please choose another date.', 'small'));
                    else if (day.state === 'private') card.append(node('p', 'Private booking. Not open for general admission.', 'small'));
                    else card.append(node('p', 'Opening information could not be confirmed. Please call before visiting.', 'small'));
                    if (day.note) card.append(node('p', day.note, 'small'));
                    if (day.state === 'unknown') {
                        const call = node('a', 'Call Dolphin', 'btn'); call.href = 'tel:+818038950821'; card.append(call);
                    }
                }
                week.append(card);
            }
            week.setAttribute('aria-busy', 'false');
        }
        async function readJSON(path) {
            const controller = new AbortController();
            const timeout = window.setTimeout(() => controller.abort(), 10000);
            try {
                const response = await fetch(path, { cache: 'no-cache', signal: controller.signal });
                if (!response.ok) throw new Error('Schedule data unavailable');
                return await response.json();
            } finally { window.clearTimeout(timeout); }
        }
        async function refresh(initial = false) {
            if (loading) return;
            loading = true;
            const results = await Promise.allSettled([
                readJSON('/data/events.json'),
                english ? readJSON('/data/operations.json') : Promise.resolve(null),
                readJSON('/data/publication_tombstones.json')
            ]);
            operations = results[1].status === 'fulfilled' ? results[1].value : null;
            try {
                if (results[0].status !== 'fulfilled' || !Array.isArray(results[0].value.events)) throw new Error('Invalid events');
                if (results[2].status !== 'fulfilled' || !Array.isArray(results[2].value.events)) throw new Error('Cancellation guard unavailable');
                events = upcoming(results[0].value.events, todayJST(), results[2].value.events);
                if (initial && month) month.value = '';
                // Preserve any selection made while the asynchronous refresh was pending.
                const selectedId = select?.value, selectedDate = date?.value;
                fill(selectedId);
                if (date && select?.value === selectedId && selectedDate && selectedDate >= date.min && selectedDate <= date.max) date.value = selectedDate;
                syncWebForm();
                if (initial) applyURL();
                renderEnglish(); renderWeek();
            } catch (_) {
                events = [];
                // Keep the contact route usable, but never label a failed event load a bar night.
                if (english) fill(select?.value === 'Normal' ? 'Normal' : '');
                syncWebForm();
                if (list) list.textContent = 'The schedule could not be loaded. Please call +81-80-3895-0821 or visit the Japanese schedule.';
                renderWeek(false);
                say(english ? 'Could not refresh event information. Please confirm your date with us.' : '最新公演情報を取得できませんでした。ご希望日をお店へご確認ください。');
            } finally { loadedDay = todayJST(); loading = false; }
        }
        month?.addEventListener('change', () => fill(select.value));
        select?.addEventListener('change', () => { syncDate(); syncWebForm(); say(''); });
        date?.addEventListener('change', syncWebForm);
        window.addEventListener('popstate', applyURL);
        document.addEventListener('click', event => {
            const link = event.target.closest('a[href]');
            if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target === '_blank') return;
            const url = new URL(link.href, location.href);
            if (url.origin === location.origin && url.pathname === location.pathname && url.searchParams.has('event_id')) {
                event.preventDefault();
                if (url.href !== location.href) history.pushState(null, '', url);
                applyURL(); document.getElementById('reservation')?.scrollIntoView(); select?.focus({ preventScroll: true });
            }
        });
        form?.addEventListener('submit', event => {
            event.preventDefault();
            if (!select?.value) { select?.focus(); return; }
            const value = id => document.getElementById(id)?.value || '';
            const fields = { event: select.selectedOptions[0].textContent, date: value('date'), name: value('name'), email: value('email'), people: value('people'), tel: value('tel'), message: value('message'), discovery: value('discovery') };
            say(english ? 'Your email app will open. Send the request there and wait for confirmation from Dolphin. Your reservation is not confirmed yet.' : 'メールアプリで内容を確認して送信し、お店からの返信をお待ちください。この操作だけでは予約は確定しません。');
            location.href = emailURL(fields, english);
        });
        // Register form/navigation handlers before any asynchronous read.
        // Loading must never let the browser submit contact fields as a GET URL.
        await refresh(true);
        if (english) {
            const refreshDay = () => { if (loadedDay !== todayJST()) refresh(); };
            window.setInterval(refreshDay, 60000);
            document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshDay(); });
        }
    });
})(typeof window === 'undefined' ? globalThis : window);
