from flask import Flask, render_template, request, jsonify, session
from markupsafe import Markup
import json
import re
import os
import requests
from ner_visualizer.config import Config
from typing import Any
import html
from collections import OrderedDict
from threading import RLock
import hashlib
import uuid

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

MODEL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_config.json")
CACHE_MAXSIZE_PER_MODEL = 256  # adjust as needed

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

_MODEL_CACHES: dict[str, OrderedDict[str, dict]] = {}
_MODEL_LOCKS: dict[str, RLock] = {}
_TOP_LOCK = RLock()  # protects structures above
_LAST_UI_STATE: dict[str, dict] = {}
_LAST_UI_LOCK = RLock()


def _get_sid() -> str:
    sid = session.get("sid")
    if not sid:
        sid = uuid.uuid4().hex
        session["sid"] = sid
    return sid


def load_configs() -> list:
    if os.path.exists(MODEL_CONFIG_PATH):
        try:
            with open(MODEL_CONFIG_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON from the config file.")
            return []
    else:
        print("Config file not found.")
        return []


def save_configs(configs: list[dict]) -> None:
    with open(MODEL_CONFIG_PATH, "w") as file:
        json.dump(configs, file, indent=4)


def _canonicalize_extra_args(extra_args: dict[str, Any]) -> str:
    # Stable JSON so key order doesn't matter
    return json.dumps({str(k): str(v) for k, v in extra_args.items()}, sort_keys=True, separators=(",", ":"))


def _make_payload_key(text: str, extra_args: dict[str, Any]) -> str:
    # Key within a model cache (model is chosen by URL)
    payload = f"{text}\n{_canonicalize_extra_args(extra_args)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _get_cache_handles(model_key: str):
    # model_key = model URL
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
            cache.move_to_end(key)  # mark as MRU
        return val


def _cache_set(model_key: str, key: str, value: dict):
    cache, lock = _get_cache_handles(model_key)
    with lock:
        if key in cache:
            cache.move_to_end(key)
        cache[key] = value
        if len(cache) > CACHE_MAXSIZE_PER_MODEL:
            cache.popitem(last=False)  # evict LRU


def _sync_model_caches(configs: list[dict]):
    """Ensure we have one cache per model URL in the current config;
    remove caches for models no longer present."""
    urls = {c.get("url", "") for c in configs if c.get("url")}
    with _TOP_LOCK:
        # create new
        for u in urls:
            if u not in _MODEL_CACHES:
                _MODEL_CACHES[u] = OrderedDict()
                _MODEL_LOCKS[u] = RLock()
        # drop removed
        for u in list(_MODEL_CACHES.keys()):
            if u not in urls:
                _MODEL_CACHES.pop(u, None)
                _MODEL_LOCKS.pop(u, None)


def get_cached_ner_result(model_url: str, text: str, extra_args: dict[str, Any]) -> dict | None:
    try:
        payload_key = _make_payload_key(text, extra_args)
        return _cache_get(model_url, payload_key)
    except NameError:
        # If you didn't add the per-model cache functions yet, just return None
        return None


try:
    _sync_model_caches(load_configs())
except Exception:
    pass


def process_extra_args(extra_args_str: str) -> dict[str, Any]:
    if not extra_args_str:
        return {}

    args_list = extra_args_str.split(",")
    try:
        extra_args = {key_val_pair.split(":")[0].strip(): key_val_pair.split(":")[1].strip() for key_val_pair in args_list}
    except Exception:
        print("Could not parse Extra Args. Check if format matches key1: value1, key2: value2, ...")
        return {}

    return extra_args


def send_ner_request(model_url: str, text: str, extra_args: dict[str, Any]) -> dict:
    model_key = model_url  # one cache per model URL
    payload_key = _make_payload_key(text, extra_args)

    cached = _cache_get(model_key, payload_key)
    if cached is not None:
        return cached

    try:
        response = requests.post(
            model_url,
            headers={"Content-Type": "application/json"},
            json={"text": text, **extra_args},
            timeout=30,
        )
    except requests.exceptions.ConnectionError as e:
        print(f"Could not reach model at {model_url}: {e}")
        return {}
    except Exception as e:
        print(f"Request to {model_url} failed: {e}")
        return {}

    if response.status_code > 299:
        try:
            error_response = json.loads(response.text)
            print(f"Unsuccessful request to {model_url}: {error_response.get('error', '')}")
        except json.JSONDecodeError:
            print(f"Unsuccessful request to {model_url}: {response.text}")
        return {}

    result = response.json()

    if isinstance(result, dict) and result:
        _cache_set(model_key, payload_key, result)

    return result


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


@app.route("/", methods=["GET", "POST"])
def index():
    raw_text = ""
    highlighted_html = ""
    type_color_map = {}

    config = load_configs()

    if request.method == "POST":
        url = request.form.get("url", "")
        raw_text = request.form.get("text", "")
        extra_args_str = request.form.get("extra_args", "")
        extra_args = process_extra_args(extra_args_str)

        ner_result = send_ner_request(url, raw_text, extra_args)
        highlighted_html = highlight_text(raw_text, ner_result)
        type_color_map = {type_name: get_color_by_type(type_name) for type_name in ner_result.values()}

        # Save last UI state for this browser session
        sid = _get_sid()
        with _LAST_UI_LOCK:
            _LAST_UI_STATE[sid] = {
                "url": url,
                "text": raw_text,
                "extra_args": extra_args_str,
            }

    else:  # GET
        sid = session.get("sid")
        if sid:
            with _LAST_UI_LOCK:
                state = _LAST_UI_STATE.get(sid)
            if state:
                url = state.get("url", "")
                raw_text = state.get("text", "")
                extra_args = process_extra_args(state.get("extra_args", ""))

                # Use cached result if available (no network)
                cached = get_cached_ner_result(url, raw_text, extra_args) or {}
                highlighted_html = highlight_text(raw_text, cached)
                type_color_map = {type_name: get_color_by_type(type_name) for type_name in cached.values()}

    return render_template(
        "index.html",
        raw_text=raw_text,
        highlighted_text=Markup(highlighted_html),
        type_colors=type_color_map,
        configs=config,
    )


@app.route("/save-config", methods=["POST"])
def save_config_form():
    if data := request.get_json():
        save_configs(data)
        try:
            _sync_model_caches(data)
        except Exception as e:
            print(f"Cache sync failed: {e}")
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": "Failed to save configs"})


@app.route("/config", methods=["GET", "POST"])
def config():
    configs = load_configs()
    return render_template("config.html", configs=configs, enumerate=enumerate)


@app.route("/_cache/clear", methods=["POST"])
def clear_all_caches():
    with _TOP_LOCK:
        for c in _MODEL_CACHES.values():
            c.clear()
    return jsonify({"status": "cleared"})


@app.route("/_cache/clear_one", methods=["POST"])
def clear_one_cache():
    url = request.json.get("url", "")
    cache, _ = _get_cache_handles(url)
    with _MODEL_LOCKS[url]:
        cache.clear()
    return jsonify({"status": "cleared", "url": url})


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
