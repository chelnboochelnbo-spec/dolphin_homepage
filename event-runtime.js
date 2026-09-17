document.addEventListener('DOMContentLoaded', () => {
    const formatter = new Intl.DateTimeFormat('en-US', {
        timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit'
    });
    const parts = Object.fromEntries(formatter.formatToParts(new Date()).map(part => [part.type, part.value]));
    const today = `${parts.year}-${parts.month}-${parts.day}`;

    document.querySelectorAll('.lineup-item[data-date]').forEach(item => {
        const start = item.dataset.date;
        const end = item.dataset.endDate || start;
        const isPast = end < today;
        const isCurrent = start <= today && end >= today;

        if (isPast) {
            item.style.display = 'none';
            item.classList.add('past-event');
            return;
        }

        item.classList.remove('past-event');
        if (item.style.display === 'none') item.style.display = '';

        if (isCurrent) {
            item.classList.add('is-today');
            const info = item.querySelector('.lineup-info');
            if (info && !info.querySelector('.badge-today')) {
                const badge = document.createElement('span');
                badge.className = 'badge-today';
                badge.textContent = 'TODAY';
                info.prepend(badge);
            }
        }
    });

    // Temporary operational notice for Kanazawa Jazz Street 2026.
    // Only the 9/20 daytime session is cancelled; the night session and all other dates remain unchanged.
    document.querySelectorAll('[data-event-id="2026-09-19_legacy-860e02187a"]').forEach(eventCard => {
        const info = eventCard.querySelector('.lineup-info');
        if (!info || info.querySelector('.jazz-street-update-notice')) return;

        const notice = document.createElement('p');
        notice.className = 'lineup-intro jazz-street-update-notice';
        notice.setAttribute('role', 'status');
        notice.style.fontWeight = '700';
        notice.style.borderLeft = '3px solid #b51f24';
        notice.style.paddingLeft = '0.85rem';
        notice.style.marginTop = '0.8rem';
        notice.textContent = '【重要】9/20（土）のDAY SESSIONのみ中止となりました。NIGHT SESSIONは告知通り開催します。9/19（土）・9/21（月）を含むその他の内容に変更はありません。';

        const details = info.querySelector('.lineup-details');
        if (details) {
            info.insertBefore(notice, details);
        } else {
            info.appendChild(notice);
        }

        eventCard.querySelectorAll('.detail-item').forEach(detail => {
            if (detail.textContent.includes('【DAY】') && !detail.textContent.includes('9/20')) {
                detail.append(' ※9/20（土）のみ中止');
            }
        });
    });
});
