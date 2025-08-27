from flask import Flask, render_template, request, jsonify, session
from markupsafe import Markup
from threading import RLock
import uuid
import os

from ner_visualizer.config import Config
from ner_visualizer.config_store import load_configs, save_configs
from ner_visualizer.ner_utils import process_extra_args, highlight_text, get_color_by_type
from ner_visualizer.services import send_ner_request
from ner_visualizer.cache import sync_model_caches, get_cached_ner_result
from ner_visualizer.compare import build_entity_columns

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# Initialize per-model caches from existing config on import
try:
    sync_model_caches(load_configs())
except Exception:
    pass

# --- simple per-session "last request" state ---
_LAST_UI_STATE: dict[str, dict] = {}
_LAST_UI_LOCK = RLock()


def _get_sid() -> str:
    sid = session.get("sid")
    if not sid:
        sid = uuid.uuid4().hex
        session["sid"] = sid
    return sid


@app.route("/", methods=["GET", "POST"])
def index():
    raw_text = ""
    highlighted_html = ""
    all_labels: set[str] = set()
    model_names: list[str] = []
    entity_columns: dict[str, list[tuple[str, str]]] = {}

    configs = load_configs()

    if request.method == "POST":
        url = request.form.get("url", "")
        raw_text = request.form.get("text", "")
        extra_args_str = request.form.get("extra_args", "")
        extra_args = process_extra_args(extra_args_str)

        # Run (cached) request + highlight
        ner_result = send_ner_request(url, raw_text, extra_args)
        highlighted_html = highlight_text(raw_text, ner_result)
        all_labels.update(ner_result.values())

        # Save last UI state for this session so GET can restore
        sid = _get_sid()
        with _LAST_UI_LOCK:
            _LAST_UI_STATE[sid] = {"url": url, "text": raw_text, "extra_args": extra_args_str}

        # Build comparison columns (from cache only)
        model_names, entity_columns = build_entity_columns(configs, raw_text)

    else:  # GET
        sid = session.get("sid")
        if sid:
            with _LAST_UI_LOCK:
                state = _LAST_UI_STATE.get(sid)
            if state:
                url = state.get("url", "")
                raw_text = state.get("text", "")
                extra_args = process_extra_args(state.get("extra_args", ""))

                # Restore highlighted view from cache (no network)
                cached = get_cached_ner_result(url, raw_text, extra_args) or {}
                highlighted_html = highlight_text(raw_text, cached)
                all_labels.update(cached.values())

                # Build comparison columns (from cache only)
                model_names, entity_columns = build_entity_columns(configs, raw_text)

    return render_template(
        "index.html",
        raw_text=raw_text,
        highlighted_text=Markup(highlighted_html),
        type_colors={label: get_color_by_type(label) for label in all_labels},
        configs=configs,
        model_names=model_names,
        entity_columns=entity_columns,
    )


@app.route("/save-config", methods=["POST"])
def save_config_form():
    if data := request.get_json():
        save_configs(data)
        try:
            sync_model_caches(data)
        except Exception as e:
            print(f"Cache sync failed: {e}")
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": "Failed to save configs"})


@app.route("/config", methods=["GET"])
def config():
    configs = load_configs()
    return render_template("config.html", configs=configs, enumerate=enumerate)


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
