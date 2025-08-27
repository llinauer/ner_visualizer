# ner_visualizer/compare.py
from __future__ import annotations
from typing import Any
from .cache import get_cached_ner_result


def build_entity_columns(configs: list[dict], text: str, extra_args: dict[str, Any]):
    """
    Returns:
      model_names: list[str]              # one per config entry (order of config)
      entity_columns: dict[name, list[(entity, label)]]
      all_labels: set[str]                # labels seen (for coloring/legend if needed)
    """
    model_names: list[str] = []
    entity_columns: dict[str, list[tuple[str, str]]] = {}
    all_labels: set[str] = set()

    for c in configs:
        url = c.get("url", "")
        name = c.get("button_name", url or "Model")
        model_names.append(name)

        items: list[tuple[str, str]] = []
        if url:
            cached = get_cached_ner_result(url, text, extra_args)
            if cached:
                # cached is {entity: label}
                for ent, label in cached.items():
                    items.append((ent, label))
                    all_labels.add(label)
                items.sort(key=lambda x: x[0].lower())  # sort by entity

        entity_columns[name] = items

    return model_names, entity_columns, all_labels
