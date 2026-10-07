"""Install the consent controller, not a Google tag, on public pages."""
import re
from pathlib import Path

def main(root):
    paths=list(root.glob('*.html'))
    for folder in ('events','artists','archive','en','zh-tw'):
        paths.extend((root/folder).rglob('*.html'))
    for path in paths:
        if path.name=='analytics-frame.html':
            continue
        html=path.read_text(encoding='utf-8-sig')
        html=re.sub(r'\s*<script[^>]+src=["\'][^"\']*(?:analytics-config|inbound-analytics|analytics-consent)\.js["\'][^>]*></script>', '', html)
        html=html.replace('</body>','<script defer src="/analytics-consent.js"></script>\n</body>',1)
        path.write_text(html,encoding='utf-8')

if __name__=='__main__':
    main(Path(__file__).resolve().parents[1])
