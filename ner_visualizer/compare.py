# ner_visualizer/compare.py
from __future__ import annotations
from .cache import get_cached_by_text


def build_entity_columns(configs: list[dict], text: str):
    """
    Returns:
      model_names: list[str]
      entity_columns: dict[name, list[(entity,label)]], alphabetically by entity
    """
    model_names: list[str] = []
    entity_columns: dict[str, list[tuple[str, str]]] = {}

    for c in configs:
        url = c.get("url", "")
        name = c.get("button_name", url or "Model")
        model_names.append(name)

        items: list[tuple[str, str]] = []
        if url:
            cached = get_cached_by_text(url, text)  # latest result for this text (any extra_args)
            if cached:
                items = sorted(cached.items(), key=lambda kv: kv[0].lower())

        entity_columns[name] = items

    return model_names, entity_columns
