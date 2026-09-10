document.addEventListener('DOMContentLoaded', () => {
  const search = document.querySelector('[data-artist-search]');
  const filters = [...document.querySelectorAll('[data-artist-filter]')];
  const cards = [...document.querySelectorAll('[data-artist-card]')];
  const empty = document.querySelector('[data-artists-empty]');
  if (!cards.length) return;

  let activeInstrument = 'ALL';

  const normalize = (value) => (value || '').toString().toLowerCase().normalize('NFKC');

  const apply = () => {
    const query = normalize(search?.value || '');
    let visible = 0;

    cards.forEach((card) => {
      const haystack = normalize(card.dataset.search || '');
      const instrument = (card.dataset.instrument || 'OTHER').toUpperCase();
      const matchesQuery = !query || haystack.includes(query);
      const matchesInstrument = activeInstrument === 'ALL' || instrument === activeInstrument;
      const show = matchesQuery && matchesInstrument;
      card.hidden = !show;
      if (show) visible += 1;
    });

    if (empty) empty.style.display = visible ? 'none' : 'block';
  };

  search?.addEventListener('input', apply);

  filters.forEach((button) => {
    button.addEventListener('click', () => {
      activeInstrument = button.dataset.artistFilter || 'ALL';
      filters.forEach((item) => item.classList.toggle('active', item === button));
      apply();
    });
  });

  apply();
});
