document.addEventListener('DOMContentLoaded', () => {
    const cards = [...document.querySelectorAll('[data-archive-card]')];
    const search = document.querySelector('[data-archive-search]');
    const empty = document.querySelector('[data-archive-empty]');
    const yearButtons = [...document.querySelectorAll('[data-archive-year]')];
    const typeButtons = [...document.querySelectorAll('[data-archive-type]')];
    const yearSections = [...document.querySelectorAll('[data-archive-year-section]')];

    if (!cards.length) return;

    let selectedYear = 'ALL';
    let selectedType = 'ALL';
    const normalize = value => (value || '').normalize('NFKC').toLocaleLowerCase('ja');

    function apply() {
        const query = normalize(search?.value);
        let visibleCount = 0;

        cards.forEach(card => {
            const matchesYear = selectedYear === 'ALL' || card.dataset.year === selectedYear;
            const matchesType = selectedType === 'ALL' || card.dataset.eventType === selectedType;
            const matchesSearch = !query || normalize(card.dataset.search).includes(query);
            const visible = matchesYear && matchesType && matchesSearch;
            card.hidden = !visible;
            if (visible) visibleCount += 1;
        });

        yearSections.forEach(section => {
            const hasVisibleCards = [...section.querySelectorAll('[data-archive-card]')].some(card => !card.hidden);
            section.hidden = !hasVisibleCards;
        });

        if (empty) empty.style.display = visibleCount ? 'none' : 'block';
    }

    search?.addEventListener('input', apply);

    yearButtons.forEach(button => {
        button.addEventListener('click', () => {
            selectedYear = button.dataset.archiveYear;
            yearButtons.forEach(item => item.classList.toggle('active', item === button));
            apply();
        });
    });

    typeButtons.forEach(button => {
        button.addEventListener('click', () => {
            selectedType = button.dataset.archiveType;
            typeButtons.forEach(item => item.classList.toggle('active', item === button));
            apply();
        });
    });
});
