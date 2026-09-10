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
});
