from __future__ import annotations
from typing import Any
import re
import html

COLOR_PALETTE = [
    "#fca5a5",
    "#fcd34d",
    "#6ee7b7",
    "#93c5fd",
    "#c4b5fd",
    "#f9a8d4",
    "#fdba74",
    "#a5f3fc",
    "#d9f99d",
    "#fcd5ce",
    "#e0f2fe",
    "#f0abfc",
    "#bbf7d0",
    "#fde68a",
    "#fecaca",
    "#c7d2fe",
    "#ddd6fe",
    "#fef9c3",
    "#bae6fd",
    "#fecdd3",
]


def get_color_by_type(type_name: str) -> str:
    index = abs(hash(type_name)) % len(COLOR_PALETTE)
    return COLOR_PALETTE[index]


def format_ner_result(ner_result: dict) -> dict:
    return {entity: {"type": entity_type, "tooltip": entity_type} for entity, entity_type in ner_result.items()}


def highlight_text(text: str, ner_result: dict) -> str:
    if not ner_result:
        return text

    entities = format_ner_result(ner_result)
    entities_ci = {k.lower(): v for k, v in entities.items()}

    def replacer(match):
        word = match.group(0)
        meta = entities_ci.get(word.lower(), {})
        type_name = meta.get("type", "")
        label = meta.get("tooltip", type_name)
        color = get_color_by_type(type_name)
        safe_label = html.escape(label, quote=True)
        return f'<span class="ner-highlight" style="background-color: {color};" aria-label="{safe_label}">{word}</span>'

    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in entities) + r")\b", re.IGNORECASE)
    return pattern.sub(replacer, text)


def process_extra_args(extra_args_str: str) -> dict[str, Any]:
    if not extra_args_str:
        return {}
    args_list = extra_args_str.split(",")
    try:
        return {kv.split(":")[0].strip(): kv.split(":")[1].strip() for kv in args_list if ":" in kv}
    except Exception:
        print("Could not parse Extra Args. Use: key1: value1, key2: value2, ...")
        return {}
