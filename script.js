document.addEventListener('DOMContentLoaded', () => {
    initScheduleFilter();

    initTonight();

    // --- Mobile Menu Toggle ---
    const menuToggle = document.querySelector('.menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    const links = document.querySelectorAll('.nav-links a');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            menuToggle.classList.toggle('active');
            navLinks.classList.toggle('active');
        });
    }

    links.forEach(link => {
        link.addEventListener('click', () => {
            menuToggle.classList.remove('active');
            navLinks.classList.remove('active');
        });
    });

    // --- Fade In Animation ---
    const observerOptions = { threshold: 0.1 };
    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    const fadeElements = document.querySelectorAll('.fade-in');
    fadeElements.forEach(el => observer.observe(el));
});

function getTokyoDateString() {
    const formatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Asia/Tokyo',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
    return formatter.format(new Date());
}

function formatTonightDate(dateString) {
    const [year, month, day] = dateString.split('-').map(Number);
    const date = new Date(Date.UTC(year, month - 1, day, 12));
    return new Intl.DateTimeFormat('ja-JP', {
        timeZone: 'Asia/Tokyo',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'short'
    }).format(date);
}

async function initTonight() {
    const card = document.getElementById('tonight-card');
    if (!card) return;

    const dateEl = document.getElementById('tonight-date');
    const typeEl = document.getElementById('tonight-type');
    const titleEl = document.getElementById('tonight-title');
    const noteEl = document.getElementById('tonight-note');
    const openEl = document.getElementById('tonight-open');
    const priceEl = document.getElementById('tonight-price');
    const linkEl = document.getElementById('tonight-link');
    const ticker = document.querySelector('.ticker-content');
    const today = getTokyoDateString();

    dateEl.textContent = formatTonightDate(today);

    try {
        const [operationsResponse, eventsResponse] = await Promise.all([
            fetch('data/operations.json', { cache: 'no-store' }),
            fetch('data/events.json', { cache: 'no-store' })
        ]);
        if (!operationsResponse.ok || !eventsResponse.ok) throw new Error('Today data unavailable');

        const operations = await operationsResponse.json();
        const eventData = await eventsResponse.json();
        const override = operations.overrides?.[today] || null;
        const event = (eventData.events || []).find(item => {
            const end = item.end_date || item.date;
            return ['ready', 'published'].includes(item.status) && item.date <= today && end >= today;
        });

        if (override?.state === 'closed' || override?.state === 'private') {
            const isClosed = override.state === 'closed';
            card.dataset.state = override.state;
            typeEl.textContent = isClosed ? 'CLOSED' : 'PRIVATE';
            titleEl.textContent = isClosed ? '本日は休業します' : '本日は貸切営業です';
            noteEl.textContent = override.note || '次回の営業情報はScheduleでご確認ください。';
            openEl.textContent = '—';
            priceEl.textContent = '—';
            linkEl.href = 'schedule.html';
            linkEl.textContent = '今後の予定を見る';
            if (ticker) ticker.textContent = `${typeEl.textContent} | ${titleEl.textContent}`;
            return;
        }

        if (event) {
            const typeLabels = { live: 'LIVE', session: 'JAM', live_session: 'LIVE & JAM' };
            const open = event.open || operations.standard_hours.open;
            const timeLabel = event.start ? `Open ${open} / Start ${event.start}` : `Open ${open}`;
            card.dataset.state = 'event';
            typeEl.textContent = typeLabels[event.event_type] || 'EVENT';
            titleEl.textContent = event.title;
            noteEl.textContent = timeLabel;
            openEl.textContent = open;
            priceEl.textContent = event.charge || `イベント料金 ${operations.event_price_from}〜`;
            linkEl.href = `/events/${event.id}/`;
            linkEl.textContent = 'イベント詳細';
            if (ticker) ticker.textContent = `TONIGHT: ${typeEl.textContent} · ${event.title} · ${timeLabel}`;
            return;
        }

        card.dataset.state = 'bar';
        typeEl.textContent = 'BAR NIGHT';
        titleEl.textContent = '音楽と一杯を、片町の4階で。';
        noteEl.textContent = `通常営業 ${operations.standard_hours.open}–${operations.standard_hours.close}`;
        openEl.textContent = operations.standard_hours.open;
        priceEl.textContent = `通常チャージ ${operations.bar_charge}`;
        linkEl.href = '#access';
        linkEl.textContent = 'アクセスを見る';
        if (ticker) ticker.textContent = `TONIGHT: BAR NIGHT · ${operations.standard_hours.open}–${operations.standard_hours.close} · 通常チャージ ${operations.bar_charge}`;
    } catch (error) {
        card.dataset.state = 'unknown';
        typeEl.textContent = 'CHECK BEFORE VISITING';
        titleEl.textContent = '本日の営業情報は確認中です';
        noteEl.textContent = 'ご来店前に電話またはメールでお問い合わせください。';
        openEl.textContent = '—';
        priceEl.textContent = '—';
        linkEl.href = '#reservation';
        linkEl.textContent = '問い合わせる';
        if (ticker) ticker.textContent = '本日の営業情報は確認中です。ご来店前にお問い合わせください。';
    }
}

/**
 * Reservation System Optimization
 */
/**
 * Schedule Filtering & Tab Logic
 */
function firstUpcomingDate(items, today) {
    return items.filter(item => (item.endDate || item.date) >= today)
        .map(item => item.date).sort()[0] || '9999-12-31';
}

function initScheduleFilter() {
    const filterBtns = document.querySelectorAll('.month-link');
    const todayStr = getTokyoDateString();
    const monthGroups = Array.from(document.querySelectorAll('.lineup-month-group'));
    const firstDate = group => firstUpcomingDate(Array.from(group.querySelectorAll('.lineup-item[data-date]'), item => item.dataset), todayStr);
    monthGroups.sort((a, b) => firstDate(a).localeCompare(firstDate(b)));
    monthGroups.forEach(group => {
        // Move the existing nodes: preserve their links, content and listeners.
        group.parentElement.appendChild(group);
        const items = Array.from(group.querySelectorAll('.lineup-item[data-date]'));
        items.sort((a, b) => a.dataset.date.localeCompare(b.dataset.date));
        items.forEach(item => item.parentElement.appendChild(item));
        const button = document.querySelector('.month-link[data-month="' + group.id + '"]');
        if (button) {
            button.parentElement.appendChild(button);
            const date = firstDate(group);
            if (date !== '9999-12-31') button.textContent = date.slice(0, 4) + ' ' + group.id.toUpperCase();
        }
    });

    // --- Tab Switching Logic ---
    function setActiveTab(targetId) {
        filterBtns.forEach(btn => {
            if (btn.dataset.month === targetId) {
                btn.classList.add('active');
                btn.setAttribute('aria-current', 'date');
            } else {
                btn.classList.remove('active');
                btn.removeAttribute('aria-current');
            }
        });

        monthGroups.forEach(group => {
            if (group.id === targetId) {
                group.classList.add('active');
                group.style.display = 'block';
            } else {
                group.classList.remove('active');
                group.style.display = 'none';
            }
        });
    }

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            setActiveTab(btn.dataset.month);
        });
    });

    // --- Date Acquisition ---


    // --- Schedule Item Logic (Hide Past, Highlight Today) ---
    const items = document.querySelectorAll('.lineup-item[data-date]');
    let todayEventTitle = "";

    items.forEach(item => {
        const itemDateStr = item.dataset.date;
        if (!itemDateStr) return;

        const endDateStr = item.dataset.endDate || itemDateStr;
        item.classList.remove('past-event');
        item.style.display = '';
        if (endDateStr < todayStr) {
            // 2. 過去の公演の自動非表示ロジック
            item.style.display = 'none';
            item.classList.add('past-event');
        } else if (itemDateStr === todayStr) {
            // 3. 当日の強調 (TODAYバッジ)
            item.classList.add('is-today');
            const info = item.querySelector('.lineup-info');
            if (info && !info.querySelector('.badge-today')) {
                const badge = document.createElement('span');
                badge.className = 'badge-today';
                badge.innerText = 'TODAY';
                info.prepend(badge);
            }

            // Ticker data
            const artist = item.querySelector('.lineup-artist')?.innerText || "";
            const time = item.querySelector('.lineup-details')?.innerText.match(/\d{2}:\d{2}/)?.[0] || "";
            todayEventTitle += `【TODAY】${time} ${artist} `;
        }
    });

    // Update Ticker
    const ticker = document.querySelector('.ticker-content');
    if (ticker) {
        if (todayEventTitle) {
            ticker.innerText = "TODAY'S EVENT: " + todayEventTitle + " | 皆様のご来店をお待ちしております。";
        } else {
            ticker.innerText = "本日の営業情報を確認しています。";
        }
    }

    // --- Empty Month Message & Dynamic Button Visibility ---
    let firstAvailableMonthId = null;

    monthGroups.forEach(group => {
        const visibleItems = group.querySelectorAll('.lineup-item:not(.past-event)');
        const monthId = group.id;
        const btn = document.querySelector(`.month-link[data-month="${monthId}"]`);

        if (visibleItems.length === 0) {
            // Hide the button if no future events
            if (btn) btn.style.display = 'none';

            const list = group.querySelector('.lineup-list');
            if (list && !list.querySelector('.no-events-msg')) {
                const msg = document.createElement('p');
                msg.className = 'no-events-msg';
                msg.style.padding = '2rem';
                msg.style.textAlign = 'center';
                msg.style.color = '#888';
                msg.innerText = '公演情報は現在準備中です。';
                list.appendChild(msg);
            }
        } else {
            // Show the button and track the first available month
            group.querySelector('.no-events-msg')?.remove();
            if (btn) btn.style.display = 'inline-block';
            if (!firstAvailableMonthId) {
                firstAvailableMonthId = monthId;
            }
        }
    });

    // The earliest upcoming event determines the initial tab, even across years.
    if (firstAvailableMonthId) {
        setActiveTab(firstAvailableMonthId);
        const nav = document.querySelector('.month-nav');
        if (nav) nav.scrollLeft = 0;
    } else if (filterBtns.length > 0) {
        setActiveTab(filterBtns[0].dataset.month);
    }
}
