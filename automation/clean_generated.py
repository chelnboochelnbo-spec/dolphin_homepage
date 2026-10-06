from pathlib import Path
import re
from apply_brand_theme import main as apply_brand_theme

ROOT = Path(__file__).resolve().parents[1]


def clean_navigation(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8-sig")
    text = re.sub(
        r"\n[ \t]+\n(?=[ \t]*<li><a href=\"/artists/\">Artists</a></li>)",
        "\n",
        text,
    )
    path.write_text(text, encoding="utf-8")


for filename in ("index.html", "schedule.html", "archive.html"):
    clean_navigation(ROOT / filename)

apply_brand_theme(ROOT)
