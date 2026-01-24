document.addEventListener('DOMContentLoaded', () => {
    initScheduleFilter();
    initReservationSystem();

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
});

/**
 * Reservation System Optimization
 */
function initReservationSystem() {
    const form = document.getElementById('reserveForm');
    const monthSelect = document.getElementById('month');
    const eventSelect = document.getElementById('event');
    const dateInput = document.getElementById('date');

    if (!form) return;

    // --- 1. Dropdown Filtering ---
    if (monthSelect && eventSelect) {
        monthSelect.addEventListener('change', () => {
            const selectedMonth = monthSelect.value;
            const options = eventSelect.querySelectorAll('option');

            options.forEach(opt => {
                const optMonth = opt.dataset.month;
                if (optMonth === 'all' || optMonth === 'other' || !selectedMonth || optMonth === selectedMonth) {
                    opt.style.display = 'block';
                } else {
                    opt.style.display = 'none';
                }
            });

            // Reset event selection if current one is hidden
            if (eventSelect.selectedOptions[0]?.style.display === 'none') {
                eventSelect.value = "";
            }
        });

        // Auto-select current month and trigger filter
        const now = new Date();
        const monthNames = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
        const currentMonth = monthNames[now.getMonth()];
        // Check if the option exists to avoid errors later in the year if option is missing
        if (monthSelect.querySelector(`option[value="${currentMonth}"]`)) {
            monthSelect.value = currentMonth;
        }
        monthSelect.dispatchEvent(new Event('change'));
    }

    // --- 2. Synchronize Event Date Input ---
    if (eventSelect && dateInput) {
        eventSelect.addEventListener('change', () => {
            const selectedOpt = eventSelect.selectedOptions[0];
            const optDate = selectedOpt?.dataset.date;
            if (optDate) {
                dateInput.value = optDate;
            }
        });
    }

    // --- 3. Form Submission (Redirect to Mailto) ---
    form.addEventListener('submit', (e) => {
        e.preventDefault();

        const name = document.getElementById('name')?.value || "";
        const userEmail = document.getElementById('email')?.value || "";
        const tel = document.getElementById('tel')?.value || "";
        const message = document.getElementById('message')?.value || "";

        const email = "bardolphinsince2016@gmail.com";
        const event = eventSelect?.options[eventSelect.selectedIndex]?.text || "";
        const date = dateInput?.value || "";
        const time = document.getElementById('time')?.value || "";
        const people = document.getElementById('people')?.value || "";

        const subject = encodeURIComponent(`【Dolphin ライブ予約】${date} ${event}`);
        const body = encodeURIComponent(
            `以下の内容で予約メールを送信します。\n\n` +
            `お名前：${name} 様\n` +
            `メール：${userEmail}\n` +
            `人数：${people} 名\n` +
            `お電話番号：${tel}\n` +
            `希望日：${date}\n` +
            `希望時間：${time}\n\n` +
            `その他ご要望：\n${message}`
        );

        window.location.href = `mailto:${email}?subject=${subject}&body=${body}`;
    });

    // --- 4. Global Link Handling (mailto Redesign) ---
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.lineup-reserve-btn, .reserve-btn');
        if (!btn) return;

        // If it's the full lineup button, don't intercept
        if (btn.innerText.includes('FULL LINEUP')) return;

        const article = btn.closest('.lineup-item, .schedule-item');
        if (article) {
            e.preventDefault();
            const dateStr = article.dataset.date || "";
            const artist = article.querySelector('.lineup-artist, .schedule-artist')?.innerText.trim() || "";

            const email = "bardolphinsince2016@gmail.com";
            const subject = encodeURIComponent(`【Dolphin ライブ予約】${dateStr} ${artist}`);
            const body = encodeURIComponent(
                `以下の内容で予約メールを送信します。\n` +
                `（※必要事項をご記入の上、送信してください）\n\n` +
                `お名前：\n` +
                `メール：\n` +
                `人数：\n` +
                `お電話番号：\n` +
                `備考・ご要望：`
            );

            window.location.href = `mailto:${email}?subject=${subject}&body=${body}`;
        }
    });
}

/**
 * Schedule Filtering & Tab Logic
 */
function initScheduleFilter() {
    const filterBtns = document.querySelectorAll('.month-link');
    const monthGroups = document.querySelectorAll('.lineup-month-group');

    // --- Tab Switching Logic ---
    function setActiveTab(targetId) {
        filterBtns.forEach(btn => {
            if (btn.dataset.month === targetId) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
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
    const now = new Date();
    const todayStr = now.getFullYear() + '-' +
        String(now.getMonth() + 1).padStart(2, '0') + '-' +
        String(now.getDate()).padStart(2, '0');
    const currentMonthNum = now.getMonth() + 1;

    // --- Schedule Item Logic (Hide Past, Highlight Today) ---
    const items = document.querySelectorAll('.lineup-item[data-date]');
    let todayEventTitle = "";

    items.forEach(item => {
        const itemDateStr = item.dataset.date;
        if (!itemDateStr) return;

        if (itemDateStr < todayStr) {
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
            ticker.innerText = "Enjoy Jazz & Bar Dolphin - Open tonight from 20:00. | 今夜も20時より営業。皆様のご来店をお待ちしております。";
        }
    }

    // --- 3. 月別タブの自動選択 (当月) ---
    const monthNames = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
    const currentMonthId = monthNames[currentMonthNum - 1];
    const currentTab = document.querySelector(`.month-link[data-month="${currentMonthId}"]`);

    if (currentTab) {
        setActiveTab(currentMonthId);
    } else if (filterBtns.length > 0) {
        // Fallback to first tab if current month not found
        setActiveTab(filterBtns[0].dataset.month);
    }

    // --- Empty Month Message ---
    monthGroups.forEach(group => {
        const visibleItems = group.querySelectorAll('.lineup-item:not(.past-event)');
        if (visibleItems.length === 0) {
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
        }
    });
}
