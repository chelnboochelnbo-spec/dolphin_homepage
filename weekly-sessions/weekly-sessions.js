/* The same published schedule that guests see is the source for upcoming links. */
(() => {
  'use strict';
  const panels = Array.from(document.querySelectorAll('[data-ws-events]'));
  if (!panels.length) return;
  const jst = new Intl.DateTimeFormat('en', { timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit' });
  const parts = Object.fromEntries(jst.formatToParts(new Date()).map(({type,value}) => [type,value]));
  const today = [parts.year, parts.month, parts.day].join('-');
  const types = { jpop:'J-POP LIVE & SESSION', funk:'FUNK LIVE & SESSION', vocal:'JAZZ VOCAL SESSION' };
  const normalize = (s) => s.trim().replace(/\s+/g, ' ').toUpperCase();
  const jp = new Intl.DateTimeFormat('ja-JP', { year:'numeric', month:'numeric', day:'numeric', weekday:'short', timeZone:'Asia/Tokyo' });
  fetch('/schedule.html', {cache:'no-cache', credentials:'same-origin'})
    .then((response) => { if (!response.ok) throw Error('schedule'); return response.text(); })
    .then((html) => {
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const root = doc.querySelector('.lineup-wrapper');
      if (!root) return;
      const entries = Array.from(root.querySelectorAll('.lineup-item[data-event-id][data-date]')).map((card) => {
        const a = card.querySelector('.lineup-artist > a[href]');
        const id = card.dataset.eventId;
        const date = card.dataset.date;
        if (!a || !/^\d{4}-\d{2}-\d{2}$/.test(date) || date < today || !/^\d{4}-\d{2}-\d{2}_[a-z0-9-]+$/.test(id)) return null;
        if (a.getAttribute('href') !== '/events/' + id + '/') return null;
        const when = new Date(date + 'T12:00:00+09:00');
        if (!Number.isFinite(when.getTime())) return null;
        return { title:a.textContent.trim(), id,date,when,href:a.getAttribute('href') };
      }).filter(Boolean).sort((a,b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));

      for (const list of panels) {
        const kind = list.dataset.wsEvents;
        const found = entries.filter((event) => kind === 'weekend'
          ? [5,6].includes(event.when.getUTCDay())
          : normalize(event.title) === types[kind]).slice(0, kind === 'weekend' ? 4 : 5);
        const status = list.parentElement.querySelector('[data-ws-status]');
        if (!found.length) { if (status) status.hidden = false; continue; }
        for (const event of found) {
          const li = document.createElement('li');
          const link = document.createElement('a');
          const time = document.createElement('time');
          const label = document.createElement('span');
          const arrow = document.createElement('span');
          link.href = event.href;
          time.dateTime = event.date;
          time.textContent = jp.format(event.when);
          label.className = 'ws-event-label';
          label.textContent = kind === 'weekend' ? event.title : '公演詳細';
          arrow.textContent = '↗';
          arrow.setAttribute('aria-hidden','true');
          link.append(time,label,arrow);
          li.append(link);
          list.append(li);
        }
        list.hidden = false;
      }
    }).catch(() => { /* Static schedule links remain usable without JS or on network error. */ });
})();
