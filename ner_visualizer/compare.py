from __future__ import annotations
from typing import Any
from .cache import get_cached_ner_result


def collect_cached_comparisons(configs: list[dict], text: str, extra_args: dict[str, Any]):
    """
    Returns:
      columns: list of {model_name, items:[(entity,label)], counts:{label:count}}
      table:   {models:[model_name...], rows:[{entity: str, by_model:{model_name: label}}]}
      all_labels: set of all labels seen
    """
    comps: dict[str, dict] = {}
    name_order: list[str] = []

    for c in configs:
        url = c.get("url", "")
        if not url:
            continue
        name = c.get("button_name", url)
        cached = get_cached_ner_result(url, text, extra_args)
        if cached:
            comps[name] = cached
            name_order.append(name)

    if not comps:
        return [], {"models": [], "rows": []}, set()

    # per-model columns
    columns = []
    all_labels: set[str] = set()
    for name in name_order:
        res = comps[name]
        items = sorted(res.items(), key=lambda kv: (kv[0].lower(), kv[1]))
        counts: dict[str, int] = {}
        for _, label in res.items():
            counts[label] = counts.get(label, 0) + 1
            all_labels.add(label)
        counts = dict(sorted(counts.items(), key=lambda kv: kv[0].lower()))
        columns.append({"model_name": name, "items": items, "counts": counts})

    # unified table
    entity_keys: set[str] = set()
    normalized: dict[str, dict[str, str]] = {}
    display_entity: dict[str, str] = {}

    for name, res in comps.items():
        norm = {}
        for ent, label in res.items():
            key = ent.lower()
            norm[key] = label
            if key not in display_entity:
                display_entity[key] = ent
        normalized[name] = norm
        entity_keys.update(norm.keys())

    rows = []
    for key in sorted(entity_keys):
        rows.append(
            {
                "entity": display_entity.get(key, key),
                "by_model": {name: normalized.get(name, {}).get(key, "") for name in name_order},
            }
        )

    table = {"models": name_order, "rows": rows}
    return columns, table, all_labels
