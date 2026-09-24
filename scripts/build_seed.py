"""Convert the supplied bilingual editorial Markdown into strict, editable seed data.

This parser is written for the attached editorial format. It does not import or
execute any code from the earlier project.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LANGUAGES = ("fa", "azb")
CATEGORY = {"a": "recall", "b": "infer", "c": "think"}


def required(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"Missing {label}")
    value = match.group(1).strip()
    if not value:
        raise ValueError(f"Empty {label}")
    return value


def parse_question(question_id: str, block: str, step_id: str) -> dict:
    match = re.fullmatch(r"([a-z]+)-([abc])([123])", question_id)
    if not match:
        raise ValueError(f"Invalid question ID: {question_id}")
    prefix, letter, number = match.groups()
    if (step_id, prefix) not in {
        ("ask", "ask"), ("leave", "leave"), ("learn", "learn"),
        ("pelican", "pel"), ("sea", "sea"), ("danger", "dan"),
        ("gone", "gone"),
    }:
        raise ValueError(f"Question {question_id} belongs to the wrong step")

    prompts = {
        "fa": required(r"^\*\*سؤال فارسی:\*\* ([^\n]+)$", block, f"{question_id} fa"),
        "azb": required(r"^\*\*سؤال ترکی آذربایجانی:\*\* ([^\n]+)$", block, f"{question_id} azb"),
    }
    answer_id = required(r"^\*\*answer_id:\*\* `([^`]+)`", block, f"{question_id} answer")
    option_rows = re.findall(
        r"^\| ([123]) \| `([^`]+)` \| ([^|]+) \| ([^|]+) \| `([^`]+)` \| ([^|]*)\|$",
        block,
        flags=re.MULTILINE,
    )
    if len(option_rows) != 3 or [r[0] for r in option_rows] != ["1", "2", "3"]:
        raise ValueError(f"Expected three ordered options in {question_id}")
    if len({row[1] for row in option_rows}) != 3:
        raise ValueError(f"Duplicate option ID in {question_id}")
    marked = [row[1] for row in option_rows if "✅" in row[5]]
    if marked != [answer_id]:
        raise ValueError(f"Answer mark and answer_id disagree in {question_id}")
    options = [
        {"id": row[1], "art_key": row[4], "labels": {"fa": row[2].strip(), "azb": row[3].strip()}}
        for row in option_rows
    ]
    if not all(option["labels"][lang] for option in options for lang in LANGUAGES):
        raise ValueError(f"Untranslated option in {question_id}")
    for lang, heading in (("fa", "فارسی"), ("azb", "ترکی آذربایجانی")):
        shown = required(rf"^\*\*پاسخ صحیح {heading}:\*\* ([^\n]+)$", block, f"{question_id} answer {lang}")
        actual = next(o["labels"][lang] for o in options if o["id"] == answer_id)
        if shown != actual:
            raise ValueError(f"Answer text and option disagree in {question_id} ({lang})")
    return {
        "id": question_id,
        "category": CATEGORY[letter],
        "number": int(number),
        "answer_id": answer_id,
        "prompts": prompts,
        "options": options,
    }


def parse_step(step_id: str, block: str, position: int) -> dict:
    title_fa = required(r"^## عنوان فارسی\n\n(.+?)\n\n## ", block, f"{step_id} title fa")
    title_azb = required(r"^## عنوان ترکی آذربایجانی\n\n(.+?)\n\n## ", block, f"{step_id} title azb")
    lesson_section = required(r"^## پیام / Lesson\n(.*?)\n## صفحات داستان", block, f"{step_id} lesson")
    lesson = {
        "id": f"{step_id}-lesson",
        "kind": "lesson",
        "locales": {
            "fa": {"text": required(r"^\*\*فارسی:\*\* ([^\n]+)$", lesson_section, f"{step_id} lesson fa")},
            "azb": {"text": required(r"^\*\*ترکی آذربایجانی:\*\* ([^\n]+)$", lesson_section, f"{step_id} lesson azb")},
        },
        "art_key": required(r"^\*\*lesson_art:\*\* `([^`]+)`", lesson_section, f"{step_id} lesson art"),
    }
    spreads_section = required(r"^## صفحات داستان\n(.*?)\n## بانک سؤال‌ها", block, f"{step_id} spreads")
    spread_parts = re.split(r"^### ([a-z]+-[1-4])\s*$", spreads_section, flags=re.MULTILINE)
    if len(spread_parts) != 9 or spread_parts[0].strip():
        raise ValueError(f"Expected four spreads in {step_id}")
    pages = []
    for i in range(1, len(spread_parts), 2):
        spread_id, spread = spread_parts[i], spread_parts[i + 1]
        if not spread_id.endswith(f"-{(i + 1) // 2}"):
            raise ValueError(f"Spread order differs from stable ID in {step_id}")
        pages.append({
            "id": spread_id,
            "kind": "story",
            "position": len(pages) + 1,
            "art_key": required(r"^\*\*art:\*\* `([^`]+)`", spread, f"{spread_id} art"),
            "locales": {
                "fa": {"text": required(r"^\*\*فارسی\*\*\n\n(.*?)\n\n\*\*ترکی آذربایجانی\*\*", spread, f"{spread_id} fa")},
                "azb": {"text": required(r"^\*\*ترکی آذربایجانی\*\*\n\n([\s\S]+?)\s*\Z", spread, f"{spread_id} azb")},
            },
        })
    question_parts = re.split(r"^#### ([a-z]+-[abc][123]) — [^\n]+$", block, flags=re.MULTILINE)
    if len(question_parts) != 19:
        raise ValueError(f"Expected nine questions in {step_id}")
    questions = [
        parse_question(question_parts[i], question_parts[i + 1], step_id)
        for i in range(1, len(question_parts), 2)
    ]
    if [(q["category"], q["number"]) for q in questions] != [
        (category, number) for category in CATEGORY.values() for number in (1, 2, 3)
    ]:
        raise ValueError(f"Question bank incomplete or out of order in {step_id}")
    lesson["position"] = 5
    pages.append(lesson)
    pages.append({"id": f"{step_id}-quiz", "kind": "quiz", "position": 6, "questions": questions})
    return {"id": step_id, "position": position, "titles": {"fa": title_fa, "azb": title_azb}, "pages": pages}


def build(source: Path) -> dict:
    text = source.read_text(encoding="utf-8")
    parts = re.split(r"^# مرحله: ([a-z]+)\s*$", text, flags=re.MULTILINE)
    if len(parts) != 15:
        raise ValueError("Expected exactly seven steps")
    steps = [parse_step(parts[i], parts[i + 1], (i + 1) // 2) for i in range(1, len(parts), 2)]
    ids = [step["id"] for step in steps]
    if ids != ["ask", "leave", "learn", "pelican", "sea", "danger", "gone"]:
        raise ValueError(f"Unexpected step IDs/order: {ids}")
    return {"format_version": 1, "languages": list(LANGUAGES), "steps": steps}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}: {len(data['steps'])} steps, 28 story pages, 63 questions")
