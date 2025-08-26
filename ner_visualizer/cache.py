from __future__ import annotations
from collections import OrderedDict
from threading import RLock
from typing import Any
import hashlib
import json

# ---- Per-model in-memory LRU caches (live until Flask process exits) ----
CACHE_MAXSIZE_PER_MODEL = 256

_MODEL_CACHES: dict[str, OrderedDict[str, dict]] = {}
_MODEL_LOCKS: dict[str, RLock] = {}
_TOP_LOCK = RLock()


def _canonicalize_extra_args(extra_args: dict[str, Any]) -> str:
    return json.dumps({str(k): str(v) for k, v in extra_args.items()}, sort_keys=True, separators=(",", ":"))


def _make_payload_key(text: str, extra_args: dict[str, Any]) -> str:
    payload = f"{text}\n{_canonicalize_extra_args(extra_args)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_cache_handles(model_key: str):
    with _TOP_LOCK:
        if model_key not in _MODEL_CACHES:
            _MODEL_CACHES[model_key] = OrderedDict()
            _MODEL_LOCKS[model_key] = RLock()
        return _MODEL_CACHES[model_key], _MODEL_LOCKS[model_key]


def _cache_get(model_key: str, key: str):
    cache, lock = _get_cache_handles(model_key)
    with lock:
        val = cache.get(key)
        if val is not None:
            cache.move_to_end(key)
        return val


def _cache_set(model_key: str, key: str, value: dict):
    cache, lock = _get_cache_handles(model_key)
    with lock:
        if key in cache:
            cache.move_to_end(key)
        cache[key] = value
        if len(cache) > CACHE_MAXSIZE_PER_MODEL:
            cache.popitem(last=False)


def get_cached_ner_result(model_url: str, text: str, extra_args: dict[str, Any]) -> dict | None:
    return _cache_get(model_url, _make_payload_key(text, extra_args))


def set_cached_ner_result(model_url: str, text: str, extra_args: dict[str, Any], value: dict) -> None:
    _cache_set(model_url, _make_payload_key(text, extra_args), value)


def sync_model_caches(configs: list[dict]):
    """Create caches for URLs in config; remove caches for URLs no longer present."""
    urls = {c.get("url", "") for c in configs if c.get("url")}
    with _TOP_LOCK:
        for u in urls:
            if u not in _MODEL_CACHES:
                _MODEL_CACHES[u] = OrderedDict()
                _MODEL_LOCKS[u] = RLock()
        for u in list(_MODEL_CACHES.keys()):
            if u not in urls:
                _MODEL_CACHES.pop(u, None)
                _MODEL_LOCKS.pop(u, None)


# (Optional) dev helpers
def clear_all():
    with _TOP_LOCK:
        for c in _MODEL_CACHES.values():
            c.clear()
