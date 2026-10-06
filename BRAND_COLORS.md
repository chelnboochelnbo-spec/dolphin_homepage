# DOLPHIN — monochrome web identity, 2026-10-06

Approved direction: retain the existing Dolphin letterforms; black field and white lettering. The uploaded original green logo was colour-separated into white on transparency for the web asset. It is a raster-based SVG wrapper, not a newly drawn vector wordmark. No typeface or letter geometry was redesigned. Original files remain unchanged.

## Palette and roles

| Role | Colour |
| --- | --- |
| Brand background / navigation / hero | #0B0B0B |
| Dark card | #181818 |
| White logo / dark-page accent | #F5F5F5 |
| Reading surface | #FFFFFF |
| Alternate reading surface | #F2F2F2 |
| Text and action fill on paper | #171717 |
| Secondary text on paper | #5C5C5C |
| Secondary text on dark cards | #B3B3B3 |

Retain light backgrounds for schedule, prices and Japanese reservations. Keep dark event, artist, archive and inbound pages. Button labels, outlines, and underline/focus states carry meaning without green, gold or red accents. Do not desaturate performer photography or approved flyers as part of this palette update.

## Implementation

`brand-monochrome.css` loads last on public pages, after local overrides. `automation/apply_brand_theme.py`, called by the existing normalizer, reapplies the theme after page generation. Logo assets and base styles are not overwritten. The event/artist/operations databases and reservation/analytics scripts are unchanged.

Read-only browser QA checks 1440/390/320px widths, logo loading, navigation, hover/CTA contrast and schedule/inbound pages. Automated palette checks use a 4.5:1 minimum for normal text; these checks are not a complete WCAG audit.

This change publishes the website only. Google Business Profile, social profile graphics, printed signs and menus require a separate execution scope.
