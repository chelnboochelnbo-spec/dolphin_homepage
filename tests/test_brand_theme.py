import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'automation'))
from apply_brand_theme import themed_html, THEME_HREF

FIXTURE = '''<!DOCTYPE html><html><head><link rel="stylesheet" href="style.css"><style>.month-link.active{color:#111!important}</style></head><body><nav><div class="logo"><a href="index.html">DOLPHIN</a></div></nav><section class="hero"><div class="hero-content fade-in"><h1>Existing copy</h1></div></section><a href="/?event_id=event1#reservation">RESERVATION</a><form action="/original"><input name="date" value="2026-10-25"></form><script src="reservations.js"></script></body></html>'''


def luminance(value):
    vals = [int(value[i:i+2],16)/255 for i in (1,3,5)]
    vals = [x/12.92 if x <= .04045 else ((x+.055)/1.055)**2.4 for x in vals]
    return sum(x*y for x,y in zip(vals, [.2126,.7152,.0722]))


class BrandThemeTests(unittest.TestCase):
    def test_theme_is_idempotent(self):
        once = themed_html(FIXTURE)
        self.assertEqual(once, themed_html(once))
        self.assertEqual(once.count(THEME_HREF), 1)
        self.assertEqual(once.count('class="brand-hero-logo"'), 1)

    def test_theme_is_last_after_inline_styles(self):
        html = themed_html(FIXTURE)
        self.assertGreater(html.index(THEME_HREF), html.index('</style>'))
        self.assertLess(html.index(THEME_HREF), html.index('</head>'))

    def test_operational_information_untouched(self):
        html = themed_html(FIXTURE)
        for source in ['href="/?event_id=event1#reservation"', 'action="/original"',
                       'value="2026-10-25"', '<script src="reservations.js"></script>',
                       '<h1>Existing copy</h1>', 'href="index.html"']:
            self.assertIn(source, html)

    def test_body_classes_preserved(self):
        html = themed_html(FIXTURE.replace('<body>', '<body class="event-page">'))
        self.assertIn('<body class="event-page" data-brand-theme="monochrome">', html)

    def test_inbound_page_supported(self):
        html = themed_html('<html><head><link href="/assets/inbound.css" rel="stylesheet"></head><body class="inbound-page"><a class="inbound-brand" href="/">DOLPHIN</a><header class="inbound-hero"><h1>English copy</h1></header></body></html>')
        self.assertIn(THEME_HREF, html)
        self.assertIn('brand-nav-logo', html)
        self.assertIn('brand-hero-logo', html)
        self.assertIn('<h1>English copy</h1>', html)

    def test_non_public_unstyled_documents_untouched(self):
        doc = '<html><head></head><body>Internal</body></html>'
        self.assertEqual(themed_html(doc), doc)

    def test_invalid_page_fails_instead_of_silent_damage(self):
        with self.assertRaises(ValueError):
            themed_html('<link href="style.css">')

    def test_palette_text_contrast(self):
        for foreground, background in [('#f5f5f5','#0b0b0b'), ('#b3b3b3','#181818'),
                                       ('#171717','#ffffff'), ('#5c5c5c','#f2f2f2'),
                                       ('#ffffff','#171717'), ('#171717','#f5f5f5'),
                                       ('#666666','#ffffff')]:
            with self.subTest(foreground=foreground,background=background):
                a,b=sorted([luminance(foreground),luminance(background)])
                self.assertGreaterEqual((b+.05)/(a+.05),4.5)

    def test_theme_has_no_chromatic_palette_or_global_photo_filter(self):
        import re
        css=(Path(__file__).resolve().parents[1]/'brand-monochrome.css').read_text()
        for value in re.findall(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b',css):
            rgb=value[1:] if len(value)==7 else ''.join(c*2 for c in value[1:])
            self.assertEqual(rgb[:2],rgb[2:4])
            self.assertEqual(rgb[:2],rgb[4:])
        self.assertNotRegex(css,r'filter\s*:\s*grayscale')

if __name__ == '__main__':
    unittest.main()
