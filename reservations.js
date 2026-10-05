(function (root) {
    'use strict';
    const months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
    function todayJST(now = new Date()) {
        const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now).map(p => [p.type, p.value]));
        return `${parts.year}-${parts.month}-${parts.day}`;
    }
    function upcoming(events, today = todayJST()) {
        return events.filter(e => ['ready','published','archived'].includes(e.status) && (e.end_date || e.date) >= today).sort((a,b) => a.date.localeCompare(b.date) || a.title.localeCompare(b.title));
    }
    function chargeEN(value) {
        if (!value || !value.trim()) return 'Admission to be confirmed — please contact us.';
        return value.replace(/投げ銭/g, 'pay-what-you-wish contribution').replace(/学生/g, 'Students').replace(/予約/g, 'Advance reservation').replace(/当日/g, 'At the door').replace(/2Drink Order/gi, '2-drink minimum').replace(/1Drink Order/gi, '1-drink minimum').replace(/^Charge\s*/, 'Admission: ');
    }
    function dateEN(value) {
        return new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Tokyo', weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(`${value}T12:00:00+09:00`));
    }
    function reservationURL(id, english = false) {
        return `${english ? '/en/' : '/'}?event_id=${encodeURIComponent(id)}#reservation`;
    }
    function emailURL(fields, english = false) {
        const subject = `${english ? '[Dolphin reservation request]' : '【Dolphin ライブ予約】'} ${fields.date} ${fields.event}`;
        const body = english ? `Reservation request\n\nEvent: ${fields.event}\nDate (Japan time): ${fields.date}\nName: ${fields.name}\nEmail: ${fields.email}\nGuests: ${fields.people}\nPhone: ${fields.tel}\n\nMessage:\n${fields.message}` : `以下の内容で予約を希望します。\n\n公演：${fields.event}\n希望日：${fields.date}\nお名前：${fields.name}\nメール：${fields.email}\n人数：${fields.people}\nお電話番号：${fields.tel}\n\nその他ご要望：\n${fields.message}`;
        return `mailto:bardolphinsince2016@gmail.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    }
    const api = { todayJST, upcoming, chargeEN, dateEN, reservationURL, emailURL };
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
        const list = document.getElementById('englishEvents');
        let events = [];
        const say = message => { if (status) status.textContent = message; };
        function syncDate() {
            const option = select?.selectedOptions[0];
            if (date) date.value = option?.dataset.date || '';
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
            if (!id) { fill(''); say(''); return; }
            const event = events.find(e => e.id === id);
            if (!event) { if (select) select.value = ''; syncDate(); say(english ? 'This event is unavailable. Please choose another event or contact us.' : 'この公演は選択できません。別の公演を選ぶかお問い合わせください。'); return; }
            if (month) month.value = months[Number(event.date.slice(5,7))-1];
            fill(id); say('');
        }
        function renderEnglish() {
            if (!list) return;
            list.replaceChildren();
            for (const e of events) {
                const card = document.createElement('article'); card.className = 'card';
                const title = document.createElement('h3'); title.textContent = e.title + (e.display?.subtitle ? ` — ${e.display.subtitle}` : '');
                const details = document.createElement('p'); details.className = 'small';
                const when = `${dateEN(e.date)}${e.end_date && e.end_date !== e.date ? ` – ${dateEN(e.end_date)}` : ''}`;
                details.textContent = `${when} · ${e.open ? `Doors ${e.open} / ` : ''}${e.start ? `Starts ${e.start}` : 'Start time to be confirmed'} (Japan time)`;
                const price = document.createElement('p'); price.textContent = chargeEN(e.charge);
                const performers = document.createElement('p'); performers.className = 'small'; performers.textContent = (e.performers || []).map(p => [p.instrument, p.name].filter(Boolean).join(' ')).join(' / ');
                const reserve = document.createElement('a'); reserve.className = 'btn'; reserve.href = reservationURL(e.id, true); reserve.textContent = 'Request a reservation';
                card.append(title, details, price, performers, reserve); list.append(card);
            }
            if (!events.length) list.textContent = 'No upcoming events are listed. Please contact us before visiting.';
        }
        try {
            const response = await fetch('/data/events.json', { cache: 'no-cache' });
            if (!response.ok) throw new Error('Event data unavailable');
            events = upcoming((await response.json()).events || []);
            if (month) month.value = '';
            fill(select?.value); applyURL(); renderEnglish();
        } catch (_) {
            if (list) list.textContent = 'The schedule could not be loaded. Please call +81-80-3895-0821 or visit the Japanese schedule.';
            say(english ? 'Could not refresh event information. Please confirm your date with us.' : '最新公演情報を取得できませんでした。ご希望日をお店へご確認ください。');
        }
        month?.addEventListener('change', () => fill(select.value));
        select?.addEventListener('change', () => { syncDate(); say(''); });
        window.addEventListener('popstate', applyURL);
        document.addEventListener('click', event => {
            const link = event.target.closest('a[href]');
            if (!link) return;
            const url = new URL(link.href, location.href);
            if (url.origin === location.origin && url.pathname === location.pathname && url.searchParams.has('event_id')) {
                event.preventDefault(); history.pushState(null, '', url); applyURL(); document.getElementById('reservation')?.scrollIntoView();
            }
        });
        form?.addEventListener('submit', event => {
            event.preventDefault();
            if (!select?.value) { select?.focus(); return; }
            const value = id => document.getElementById(id)?.value || '';
            const fields = { event: select.selectedOptions[0].textContent, date: value('date'), name: value('name'), email: value('email'), people: value('people'), tel: value('tel'), message: value('message') };
            say(english ? 'Your email app will open. Send the request there and wait for confirmation from Dolphin. Your reservation is not confirmed yet.' : 'メールアプリで内容を確認して送信し、お店からの返信をお待ちください。この操作だけでは予約は確定しません。');
            location.href = emailURL(fields, english);
        });
    });
})(typeof window === 'undefined' ? globalThis : window);
