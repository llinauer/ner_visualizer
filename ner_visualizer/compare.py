# ner_visualizer/compare.py
from __future__ import annotations
from .cache import get_cached_by_text, get_timing_by_text


def _fmt_secs(secs: float | None) -> str:
    if secs is None:
        return ""
    if secs < 60:
        s = f"{secs:.1f}"
        return f" ({s} s)"
    m = int(secs // 60)
    r = secs - m * 60
    rs = f"{r:.1f}"
    return f" ({m} m {rs} s)"


def build_entity_columns(configs: list[dict], text: str):
    """
    Returns:
      model_headers: list[str]  # display names like "Flair (40 s)"
      entity_columns: dict[name, list[(entity,label)]]
    """
    model_headers: list[str] = []
    entity_columns: dict[str, list[tuple[str, str]]] = {}

    for c in configs:
        url = c.get("url", "")
        name = c.get("button_name", url or "Model")

        items: list[tuple[str, str]] = []
        if url:
            cached = get_cached_by_text(url, text)
            if cached:
                items = sorted(cached.items(), key=lambda kv: kv[0].lower())

        secs = get_timing_by_text(url, text) if url else None
        display = f"{name}{_fmt_secs(secs)}"
        model_headers.append(display)

        entity_columns[name] = items

    return model_headers, entity_columns
