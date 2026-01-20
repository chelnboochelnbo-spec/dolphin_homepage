document.addEventListener('DOMContentLoaded', () => {
    initScheduleFilter();

    // --- Opening Animation ---
    const overlay = document.getElementById('opening-overlay');

    if (overlay) {
        document.body.classList.add('no-scroll');
        setTimeout(() => {
            overlay.classList.add('slide-out');
            setTimeout(() => {
                document.body.classList.remove('no-scroll');
            }, 1200);
        }, 3500);
    }

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

    // --- Reservation Logic (Month Filter) ---
    const monthSelect = document.getElementById('month');
    const eventSelect = document.getElementById('event');

    if (monthSelect && eventSelect) {
        const allOptions = Array.from(eventSelect.options);

        monthSelect.addEventListener('change', () => {
            const selectedMonth = monthSelect.value;
            // Reset event selection
            eventSelect.value = "";

            allOptions.forEach(option => {
                const monthData = option.getAttribute('data-month');

                if (selectedMonth === "") {
                    // If no month selected, show all (or could hide all except prompt)
                    option.style.display = "block";
                } else {
                    if (monthData === selectedMonth || monthData === "all") {
                        option.style.display = "block";
                    } else {
                        option.style.display = "none";
                    }
                }
            });
        });
    }

});

// --- Reservation Scroll Helper ---
function selectDate(dateString) {
    const formSection = document.getElementById('reservation');
    if (formSection) {
        formSection.scrollIntoView({ behavior: 'smooth' });
        const dateInput = document.getElementById('date');
        if (dateInput) dateInput.value = dateString;
    }
}

// --- Schedule/Archive Filtering ---
function initScheduleFilter() {
    const items = document.querySelectorAll('.schedule-item[data-date]');
    if (items.length === 0) return;

    // Get today's date in YYYY-MM-DD format (local time)
    const now = new Date();
    const offset = now.getTimezoneOffset();
    const localNow = new Date(now.getTime() - (offset * 60 * 1000));
    const todayStr = localNow.toISOString().split('T')[0];

    const isArchivePage = window.location.pathname.includes('archive.html');
    let visibleCount = 0;

    items.forEach(item => {
        const itemDate = item.getAttribute('data-date');

        if (isArchivePage) {
            // Archive Page: Show past events
            if (itemDate < todayStr) {
                item.style.display = 'flex';
                visibleCount++;
            } else {
                item.style.display = 'none';
            }
        } else {
            // Schedule Page or Home Preview: Show today and future events
            if (itemDate >= todayStr) {
                item.style.display = 'flex';
                visibleCount++;
            } else {
                item.style.display = 'none';
            }
        }
    });

    // Show "No events" message if applicable
    const noEventsMsg = document.getElementById('no-events');
    if (noEventsMsg) {
        noEventsMsg.style.display = visibleCount === 0 ? 'block' : 'none';
    }
}
