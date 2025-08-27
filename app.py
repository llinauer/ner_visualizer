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
from ner_visualizer.cache import get_cached_by_text, get_timing_by_text
from flask import send_file, Response
import io
import csv
import datetime as dt


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
    model_headers: list[str] = []
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
        model_headers, entity_columns = build_entity_columns(configs, raw_text)

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
                model_headers, entity_columns = build_entity_columns(configs, raw_text)

    return render_template(
        "index.html",
        raw_text=raw_text,
        highlighted_text=Markup(highlighted_html),
        type_colors={label: get_color_by_type(label) for label in all_labels},
        configs=configs,
        model_headers=model_headers,
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


def _fmt_secs_csv(secs: float | None) -> str:
    """One decimal, comma as decimal separator (e.g., 40,3 s). Empty if None."""
    if secs is None:
        return ""
    return f"{secs:.1f}".replace(".", ",") + " s"


def _build_wide_table_for_text(configs: list[dict], text: str):
    """
    Returns:
      headers: list[str]  (model name with timing, e.g., "Flair (40,3 s)")
      names:   list[str]  (plain model names from config, for lookups)
      rows:    list[list[str]]  (each cell "entity — label" or "")
    """
    # Column order = config order
    names = [c.get("button_name", c.get("url", "Model")) for c in configs]

    # Build headers with timing (if present)
    headers = []
    columns = []  # list of lists of strings
    max_len = 0

    for c in configs:
        url = c.get("url", "")
        name = c.get("button_name", url or "Model")

        secs = get_timing_by_text(url, text) if url else None
        timing = _fmt_secs_csv(secs)
        header = f"{name} ({timing})" if timing else name
        headers.append(header)

        # Pull cached result for this text (ignores extra_args)
        cached = get_cached_by_text(url, text) if url else None
        items = []
        if cached:
            # cached is {entity: label}
            for ent, label in sorted(cached.items(), key=lambda kv: kv[0].lower()):
                items.append(f"{ent} — {label}")
        columns.append(items)
        max_len = max(max_len, len(items))

    # Build wide rows (pad with empty strings)
    rows = []
    for i in range(max_len):
        row = []
        for col in columns:
            row.append(col[i] if i < len(col) else "")
        rows.append(row)

    return headers, names, rows


@app.route("/export/comparison.json", methods=["GET"])
def export_comparison_json():
    # use the last text from the session (as you already do elsewhere)
    sid = session.get("sid")
    if not sid or sid not in _LAST_UI_STATE:
        return jsonify({"error": "No last text available to export."}), 400

    text = _LAST_UI_STATE[sid].get("text", "")
    if not text:
        return jsonify({"error": "No last text available to export."}), 400

    configs = load_configs()
    headers, names, rows = _build_wide_table_for_text(configs, text)

    payload = {
        "text": text,
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "columns": headers,  # model names with timing string
        "rows": rows,  # rows of "entity — label" strings
    }
    return jsonify(payload)


@app.route("/export/comparison.csv", methods=["GET"])
def export_comparison_csv():
    sid = session.get("sid")
    if not sid or sid not in _LAST_UI_STATE:
        return Response("No last text available to export.", status=400)

    text = _LAST_UI_STATE[sid].get("text", "")
    if not text:
        return Response("No last text available to export.", status=400)

    configs = load_configs()
    headers, names, rows = _build_wide_table_for_text(configs, text)

    sio = io.StringIO(newline="")
    writer = csv.writer(sio)
    writer.writerow(headers)
    writer.writerows(rows)

    mem = io.BytesIO(sio.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(
        mem,
        mimetype="text/csv",
        as_attachment=True,
        download_name="comparison.csv",
    )


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
