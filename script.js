document.addEventListener('DOMContentLoaded', async () => {
    await initAutomatedEventPipeline();
    initScheduleFilter();
    initReservationSystem();

    const overlay = document.getElementById('opening-overlay');
    if (overlay) {
        document.body.classList.add('no-scroll');
        setTimeout(() => {
            overlay.classList.add('slide-out');
            setTimeout(() => document.body.classList.remove('no-scroll'), 1200);
        }, 3500);
    }

    const menuToggle = document.querySelector('.menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    const links = document.querySelectorAll('.nav-links a');
    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', () => {
            menuToggle.classList.toggle('active');
            navLinks.classList.toggle('active');
        });
        links.forEach(link => link.addEventListener('click', () => {
            menuToggle.classList.remove('active');
            navLinks.classList.remove('active');
        }));
    }

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));
});

async function initAutomatedEventPipeline() {
    try {
        const response = await fetch('data/events.json', { cache: 'no-store' });
        if (!response.ok) return;
        const payload = await response.json();
        const events = Array.isArray(payload.events) ? payload.events : [];
        const publishable = events.filter(event => ['ready', 'published', 'completed'].includes(event.status));
        if (!publishable.length) return;

        injectAutomationStyles();
        renderScheduleEvents(publishable);
        renderHomepageEvents(publishable);
        renderArchiveEvents(publishable);
    } catch (error) {
        console.warn('DOLPHIN event automation data could not be loaded:', error);
    }
}

function injectAutomationStyles() {
    if (document.getElementById('dolphin-automation-styles')) return;
    const style = document.createElement('style');
    style.id = 'dolphin-automation-styles';
    style.textContent = `
        .event-type-badge{display:inline-block;background:#111;color:#fff;font-size:.68rem;font-weight:700;letter-spacing:.08em;padding:3px 8px;margin-bottom:.5rem;border-radius:2px}
        .event-type-badge[data-type="LIVE"]{background:#111}
        .event-type-badge[data-type="SESSION"]{background:#555}
        .event-type-badge[data-type="LIVE&SESSION"]{background:#7b6b00}
    `;
    document.head.appendChild(style);
}

function eventDate(event) {
    return String(event.date || '');
}

function isPast(event) {
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    return eventDate(event) < todayStr;
}

function weekdayLabel(dateString, upper = false) {
    const d = new Date(`${dateString}T00:00:00+09:00`);
    const names = upper ? ['SUN','MON','TUE','WED','THU','FRI','SAT'] : ['sun.','mon.','tue.','wed.','thu.','fri.','sat.'];
    return names[d.getDay()];
}

function performerText(event) {
    if (!Array.isArray(event.performers)) return event.description || '';
    const text = event.performers.map(p => [p.instrument, p.name].filter(Boolean).join(' ')).join(' / ');
    return text || event.description || '';
}

function timeText(event) {
    if (event.open_time && event.start_time) return `Open ${event.open_time} / Start ${event.start_time}`;
    if (event.start_time) return `Start ${event.start_time}`;
    return '';
}

function flyerPath(event) {
    return event.flyer?.asset_path || 'logo_new.png';
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function typeBadge(event) {
    const type = ['LIVE', 'SESSION', 'LIVE&SESSION'].includes(event.type) ? event.type : 'LIVE';
    return `<span class="event-type-badge" data-type="${escapeHtml(type)}">${escapeHtml(type)}</span>`;
}

function scheduleArticle(event) {
    const d = new Date(`${event.date}T00:00:00+09:00`);
    const y = d.getFullYear();
    const m = d.getMonth() + 1;
    const day = String(d.getDate()).padStart(2, '0');
    return `
        <article class="lineup-item automated-event" data-event-id="${escapeHtml(event.id)}" data-date="${escapeHtml(event.date)}">
            <div class="lineup-date">${y} ${m}.${day}<span class="weekday">${weekdayLabel(event.date)}</span></div>
            <div class="lineup-body">
                <img src="${escapeHtml(flyerPath(event))}" alt="${escapeHtml(event.title)} Flyer" class="lineup-flyer-thumb" onclick="window.open(this.src)">
                <div class="lineup-info">
                    ${typeBadge(event)}
                    <h3 class="lineup-artist">${escapeHtml(event.title)}</h3>
                    ${event.description ? `<p class="lineup-intro">${escapeHtml(event.description)}</p>` : ''}
                    <div class="lineup-details">
                        ${timeText(event) ? `<div class="detail-item"><i class="far fa-clock"></i>${escapeHtml(timeText(event))}</div>` : ''}
                        ${performerText(event) ? `<div class="detail-item"><i class="fas fa-users"></i>${escapeHtml(performerText(event))}</div>` : ''}
                        <div class="lineup-price">${escapeHtml(event.charge || '')}</div>
                    </div>
                    ${event.reservation?.enabled === false ? '' : '<a href="index.html#reservation" class="lineup-reserve-btn">RESERVATION</a>'}
                </div>
            </div>
        </article>`;
}

function homepageArticle(event) {
    return `
        <article class="lineup-item automated-event" data-event-id="${escapeHtml(event.id)}" data-date="${escapeHtml(event.date)}">
            <div class="lineup-date">${escapeHtml(event.date.replaceAll('-', ' '))}<span class="weekday">${weekdayLabel(event.date)}</span></div>
            <div class="lineup-body">
                <img src="${escapeHtml(flyerPath(event))}" alt="Flyer" class="lineup-flyer-thumb" onclick="window.open(this.src)">
                <div class="lineup-info">
                    ${typeBadge(event)}
                    <h3 class="lineup-artist">${escapeHtml(event.title)}</h3>
                    <div class="lineup-details">
                        ${timeText(event) ? `<div class="detail-item"><i class="far fa-clock"></i>${escapeHtml(timeText(event))}</div>` : ''}
                        ${performerText(event) ? `<div class="detail-item"><i class="fas fa-users"></i>${escapeHtml(performerText(event))}</div>` : ''}
                    </div>
                </div>
            </div>
            <div class="lineup-action">
                <div class="lineup-price">${escapeHtml(event.charge || '')}</div>
                ${event.reservation?.enabled === false ? '' : `<a href="#reservation" class="lineup-reserve-btn" onclick="selectDate('${escapeHtml(event.date)}')">ONLINE RESERVATION</a>`}
            </div>
        </article>`;
}

function archiveArticle(event) {
    const d = new Date(`${event.date}T00:00:00+09:00`);
    const monthNames = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
    return `
        <article class="schedule-item automated-event" data-event-id="${escapeHtml(event.id)}" data-date="${escapeHtml(event.date)}">
            <div class="schedule-date">
                <span class="day">${d.getDate()}</span>
                <span class="weekday">${weekdayLabel(event.date, true)}</span>
                <span class="month">${d.getMonth() + 1}月 ${monthNames[d.getMonth()]}</span>
            </div>
            <div class="schedule-info">
                <div class="lineup-details">
                    ${typeBadge(event)}
                    ${timeText(event) ? `<div class="detail-item"><i class="far fa-clock"></i>${escapeHtml(timeText(event))}</div>` : ''}
                    <h3 class="schedule-artist">${escapeHtml(event.title)}</h3>
                    ${performerText(event) ? `<div class="detail-item"><i class="fas fa-users"></i>${escapeHtml(performerText(event))}</div>` : ''}
                </div>
            </div>
        </article>`;
}

function alreadyRendered(root, event) {
    return root.querySelector(`[data-event-id="${CSS.escape(event.id)}"]`) ||
        [...root.querySelectorAll(`[data-date="${CSS.escape(event.date)}"]`)].some(el => el.textContent.includes(event.title));
}

function renderScheduleEvents(events) {
    const wrapper = document.querySelector('.lineup-wrapper');
    if (!wrapper) return;
    const monthIds = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
    events.filter(e => !isPast(e) && e.status !== 'cancelled').forEach(event => {
        if (alreadyRendered(wrapper, event)) return;
        const d = new Date(`${event.date}T00:00:00+09:00`);
        const group = document.getElementById(monthIds[d.getMonth()]);
        const list = group?.querySelector('.lineup-list');
        if (list) list.insertAdjacentHTML('beforeend', scheduleArticle(event));
    });
}

function renderHomepageEvents(events) {
    const list = document.querySelector('#schedule-preview .lineup-list');
    if (!list) return;
    events.filter(e => !isPast(e) && e.status !== 'cancelled').forEach(event => {
        if (!alreadyRendered(list, event)) list.insertAdjacentHTML('beforeend', homepageArticle(event));
    });
    const items = [...list.querySelectorAll('.lineup-item[data-date]')];
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    items.sort((a, b) => a.dataset.date.localeCompare(b.dataset.date));
    items.forEach(item => list.appendChild(item));
    items.forEach(item => item.style.display = item.dataset.date >= todayStr ? '' : 'none');
    [...list.querySelectorAll('.lineup-item[data-date]')].filter(i => i.dataset.date >= todayStr).forEach((item, index) => {
        if (index >= 3) item.style.display = 'none';
    });
}

function renderArchiveEvents(events) {
    const list = document.querySelector('.archive-list');
    if (!list) return;
    events.filter(e => isPast(e) && e.status !== 'cancelled').forEach(event => {
        if (!alreadyRendered(list, event)) list.insertAdjacentHTML('beforeend', archiveArticle(event));
    });
}

function initReservationSystem() {
    const form = document.getElementById('reserveForm');
    const monthSelect = document.getElementById('month');
    const eventSelect = document.getElementById('event');
    const dateInput = document.getElementById('date');
    if (!form) return;

    if (monthSelect && eventSelect) {
        monthSelect.addEventListener('change', () => {
            const selectedMonth = monthSelect.value;
            eventSelect.querySelectorAll('option').forEach(opt => {
                const optMonth = opt.dataset.month;
                opt.style.display = optMonth === 'all' || optMonth === 'other' || !selectedMonth || optMonth === selectedMonth ? 'block' : 'none';
            });
            if (eventSelect.selectedOptions[0]?.style.display === 'none') eventSelect.value = '';
        });
        const now = new Date();
        const monthNames = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
        const currentMonth = monthNames[now.getMonth()];
        if (monthSelect.querySelector(`option[value="${currentMonth}"]`)) monthSelect.value = currentMonth;
        monthSelect.dispatchEvent(new Event('change'));
    }

    if (eventSelect && dateInput) {
        eventSelect.addEventListener('change', () => {
            const optDate = eventSelect.selectedOptions[0]?.dataset.date;
            if (optDate) dateInput.value = optDate;
        });
    }

    form.addEventListener('submit', e => {
        e.preventDefault();
        const name = document.getElementById('name')?.value || '';
        const userEmail = document.getElementById('email')?.value || '';
        const tel = document.getElementById('tel')?.value || '';
        const message = document.getElementById('message')?.value || '';
        const event = eventSelect?.options[eventSelect.selectedIndex]?.text || '';
        const date = dateInput?.value || '';
        const time = document.getElementById('time')?.value || '';
        const people = document.getElementById('people')?.value || '';
        const subject = encodeURIComponent(`【Dolphin ライブ予約】${date} ${event}`);
        const body = encodeURIComponent(`以下の内容で予約メールを送信します。\n\nお名前：${name} 様\nメール：${userEmail}\n人数：${people} 名\nお電話番号：${tel}\n希望日：${date}\n希望時間：${time}\n\nその他ご要望：\n${message}`);
        window.location.href = `mailto:bardolphinsince2016@gmail.com?subject=${subject}&body=${body}`;
    });

    document.addEventListener('click', e => {
        const btn = e.target.closest('.lineup-reserve-btn, .reserve-btn');
        if (!btn || btn.innerText.includes('FULL LINEUP')) return;
        const article = btn.closest('.lineup-item, .schedule-item');
        if (!article) return;
        e.preventDefault();
        const dateStr = article.dataset.date || '';
        const artist = article.querySelector('.lineup-artist, .schedule-artist')?.innerText.trim() || '';
        const subject = encodeURIComponent(`【Dolphin ライブ予約】${dateStr} ${artist}`);
        const body = encodeURIComponent('以下のテンプレートを記入して送信してください。\n\nお名前：\n人数：\nお電話番号：\n備考：');
        window.location.href = `mailto:bardolphinsince2016@gmail.com?subject=${subject}&body=${body}`;
    });
}

function initScheduleFilter() {
    const filterBtns = document.querySelectorAll('.month-link');
    const monthGroups = document.querySelectorAll('.lineup-month-group');
    if (!filterBtns.length || !monthGroups.length) return;

    function setActiveTab(targetId) {
        filterBtns.forEach(btn => btn.classList.toggle('active', btn.dataset.month === targetId));
        monthGroups.forEach(group => {
            const active = group.id === targetId;
            group.classList.toggle('active', active);
            group.style.display = active ? 'block' : 'none';
        });
    }

    filterBtns.forEach(btn => btn.addEventListener('click', () => setActiveTab(btn.dataset.month)));
    const now = new Date();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const items = document.querySelectorAll('.lineup-item[data-date]');
    let todayEventTitle = '';

    items.forEach(item => {
        const itemDateStr = item.dataset.date;
        if (!itemDateStr) return;
        if (itemDateStr < todayStr) {
            item.style.display = 'none';
            item.classList.add('past-event');
        } else if (itemDateStr === todayStr) {
            item.classList.add('is-today');
            const info = item.querySelector('.lineup-info');
            if (info && !info.querySelector('.badge-today')) {
                const badge = document.createElement('span');
                badge.className = 'badge-today';
                badge.innerText = 'TODAY';
                info.prepend(badge);
            }
            const artist = item.querySelector('.lineup-artist')?.innerText || '';
            const time = item.querySelector('.lineup-details')?.innerText.match(/\d{2}:\d{2}/)?.[0] || '';
            todayEventTitle += `【TODAY】${time} ${artist} `;
        }
    });

    const ticker = document.querySelector('.ticker-content');
    if (ticker) ticker.innerText = todayEventTitle ? `TODAY'S EVENT: ${todayEventTitle} | 皆様のご来店をお待ちしております。` : 'Enjoy Jazz & Bar Dolphin - Open tonight from 20:00. | 今夜も20時より営業。皆様のご来店をお待ちしております。';

    let firstAvailableMonthId = null;
    monthGroups.forEach(group => {
        const visibleItems = group.querySelectorAll('.lineup-item:not(.past-event)');
        const btn = document.querySelector(`.month-link[data-month="${group.id}"]`);
        if (visibleItems.length === 0) {
            if (btn) btn.style.display = 'none';
        } else {
            if (btn) btn.style.display = 'inline-block';
            if (!firstAvailableMonthId) firstAvailableMonthId = group.id;
        }
    });

    const monthNames = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
    const currentMonthId = monthNames[now.getMonth()];
    const currentMonthGroup = document.getElementById(currentMonthId);
    const currentMonthHasEvents = currentMonthGroup && currentMonthGroup.querySelectorAll('.lineup-item:not(.past-event)').length > 0;
    if (currentMonthHasEvents) setActiveTab(currentMonthId);
    else if (firstAvailableMonthId) setActiveTab(firstAvailableMonthId);
    else if (filterBtns.length) setActiveTab(filterBtns[0].dataset.month);
}
