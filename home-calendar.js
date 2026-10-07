(function () {
    'use strict';
    const root = document.getElementById('home-calendar');
    if (!root) return;
    const links = Array.from(root.querySelectorAll('[data-calendar-month]'));
    const panels = Array.from(root.querySelectorAll('[data-calendar-panel]'));
    const steps = Array.from(root.querySelectorAll('[data-calendar-step]'));
    const parts = new Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Tokyo', year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
    const part = type => parts.find(p => p.type === type).value;
    const today = `${part('year')}-${part('month')}-${part('day')}`;
    const current = links.findIndex(a => a.dataset.calendarMonth === today.slice(0,7));
    let selected = Math.max(0, current);
    function show(index, announce = true) {
        selected = Math.max(0, Math.min(links.length - 1, index));
        panels.forEach((panel, i) => { panel.hidden = i !== selected; });
        links.forEach((link, i) => {
            if (i === selected) link.setAttribute('aria-current','date');
            else link.removeAttribute('aria-current');
        });
        steps.forEach(button => {button.disabled = Number(button.dataset.calendarStep) < 0 ? selected === 0 : selected === links.length - 1;});
        if (announce) root.querySelector('[data-calendar-announcement]').textContent = links[selected].textContent + 'を表示';
        const nav = root.querySelector('.calendar-months');
        nav.scrollLeft = links[selected].offsetLeft - nav.offsetLeft - 20;
    }
    links.forEach((link, i) => {
        link.addEventListener('click', event => {event.preventDefault(); show(i);});
        link.addEventListener('keydown', event => {
            const offsets = {ArrowLeft:-1, ArrowRight:1, Home:-i, End:links.length-1-i};
            if (!(event.key in offsets)) return;
            event.preventDefault();
            const next = Math.max(0,Math.min(links.length-1,i+offsets[event.key]));
            show(next); links[next].focus();
        });
    });
    steps.forEach(button => button.addEventListener('click', () => show(selected + Number(button.dataset.calendarStep))));
    root.querySelector('[data-calendar-today]').addEventListener('click', () => show(Math.max(0,current)));
    root.querySelector('.calendar-controls').hidden = false;
    const todayCell = root.querySelector(`[data-calendar-date="${today}"]`);
    if (todayCell) {todayCell.classList.add('calendar-today');todayCell.querySelector('time').setAttribute('aria-current','date');}
    show(selected, false);
})();
