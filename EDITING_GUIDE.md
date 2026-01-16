# Editing Guide for Dolphin Website

This guide explains how to update the content of the Dolphin Jazz Bar website.

## 1. Updating the Live Schedule
Find the `<div class="schedule-list">` in `index.html`.
Copy an existing `<article class="schedule-item">` block and modify:

```html
<article class="schedule-item">
    <div class="schedule-date">
        <span class="month">MONTH</span>
        <span class="day">DATE</span>
        <span class="weekday">DAY</span>
    </div>
    <div class="schedule-info">
        <div class="schedule-time">Open 19:00 / Start 20:00</div>
        <!-- Artist Name & Genre -->
        <h3 class="schedule-artist">Artist Name <span class="genre">- Jazz/Funk</span></h3>
        <!-- Charge -->
        <p class="schedule-charge">Music Charge: ¥2,500</p>
    </div>
    <div class="schedule-action">
        <!-- Update the date in selectDate('YYYY-MM-DD') for the reservation button -->
        <a href="#reservation" class="reserve-btn" onclick="selectDate('2024-10-XX')">RESERVE</a>
    </div>
</article>
```

## 2. Updating the Menu
Find the `<section id="menu">` block. Content is divided into `menu-column`s.

### Adding a new item:
```html
<li>
    <span class="item-name">Menu Item Name</span>
    <span class="item-desc">Short description (optional)</span>
    <span class="item-price">¥000</span>
</li>
```

## 3. Changing Colors/Theme
Open `style.css` and modify the `:root` variables at the top:

- `--color-primary`: The main Yellow-Green color.
- `--bg-body`: Background color of the page.
- `--color-text-main`: Main text color (currently Black).

## 4. Reservation Settings
The reservation form is currently static (client-side only).
To make it functional, you would typically integrate a form service (like Formspree) or backend API in `script.js`.
