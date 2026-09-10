from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENTS_FILE = ROOT / "data" / "events.json"

DISPLAY_FIXES = {
    "2026-09-19_legacy-860e02187a": {
        "display": {
            "badge": "SPECIAL EVENT",
            "intro": "9/19（土）〜9/21（月） 3DAYS JAM SESSION！",
            "detail_lines": [
                {"icon": "clock", "text": "【DAY】Open 11:00 / Start 12:00 / Close 18:00 (Charge ¥1,500)"},
                {"icon": "clock", "text": "【NIGHT】Open 19:00 / Start 20:00 / Until Close (Charge ¥2,500)"}
            ]
        }
    },
    "2026-10-09_legacy-6c888cbbf2": {
        "display": {
            "intro": "西田幾多郎記念哲学館　展示並行パフォーマンス"
        }
    },
    "2026-10-10_legacy-67df69dc7c": {
        "performers": [
            {"instrument": "Pf.", "name": "安部誠彦"},
            {"instrument": "Ba.", "name": "山内健司"},
            {"instrument": "Dr.", "name": "川北隆博"},
            {"instrument": "Vo.", "name": "村上恵"},
            {"instrument": "Vo.", "name": "宮下美貴子"},
            {"instrument": "Sax.", "name": "芳沢彩喜"},
            {"instrument": "Sax.", "name": "吉田茉莉花"},
            {"instrument": "Tb.", "name": "谷村佳之"},
            {"instrument": "Tp.", "name": "木下力"}
        ],
        "display": {
            "badge": "SPECIAL EVENT",
            "intro": "〜トリオ＆昭和歌謡＆ミニビッグバンド祭〜",
            "detail_lines": [
                {"icon": "clock", "text": "Start 19:30"},
                {"icon": "users", "text": "① ABEmaトリオ：Pf. 安部誠彦 / Ba. 山内健司 / Dr. 川北隆博"},
                {"icon": "users", "text": "② 唱和姉妹：Vo. 村上恵 / Vo. 宮下美貴子 / Pf. 安部誠彦 / Ba. 山内健司"},
                {"icon": "users", "text": "③ あ・カウントベイシー楽団：Sax. 芳沢彩喜 / Sax. 吉田茉莉花 / Tb. 谷村佳之 / Tp. 木下力 / Pf. 安部誠彦 / Ba. 山内健司 / Dr. 川北隆博"}
            ]
        }
    },
    "2026-10-13_legacy-25e2d5dd60": {
        "title": "Dolphin 1st Anniversary Special Live #4",
        "display": {
            "badge": "SPECIAL EVENT",
            "subtitle": "Special Jam Session Featuring 橋本現輝・小室響",
            "intro": "ジャズを中心に様々なフィールドで活躍する二人の俊英を迎えるスペシャルなジャムセッション。"
        }
    }
}


def main() -> None:
    payload = json.loads(EVENTS_FILE.read_text(encoding="utf-8-sig"))
    events = payload.get("events", [])
    by_id = {event["id"]: event for event in events}

    missing = [event_id for event_id in DISPLAY_FIXES if event_id not in by_id]
    if missing:
        raise ValueError(f"Legacy events not found: {', '.join(missing)}")

    for event_id, patch in DISPLAY_FIXES.items():
        event = by_id[event_id]
        for key, value in patch.items():
            event[key] = value

    EVENTS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Enriched {len(DISPLAY_FIXES)} legacy events from pre-migration schedule content.")


if __name__ == "__main__":
    main()
