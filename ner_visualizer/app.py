from flask import Flask, render_template, request, jsonify
from markupsafe import Markup
import json
import re
import os
import requests
from ner_visualizer.config import Config
from typing import Any
import html

app = Flask(__name__)

MODEL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_config.json")


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
    try:
        response = requests.post(model_url, headers={"Content-Type": "application/json"}, json={"text": text, **extra_args})
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

    return response.json()


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


@app.route("/", methods=["GET", "POST"])
def index():
    raw_text = ""
    highlighted_html = ""
    type_color_map = {}

    config = load_configs()

    if request.method == "POST":
        url = request.form.get("url", "")
        raw_text = request.form.get("text", "")
        extra_args = process_extra_args(request.form.get("extra_args", ""))
        ner_result = send_ner_request(url, raw_text, extra_args)
        highlighted_html = highlight_text(raw_text, ner_result)
        type_color_map = {type_name: get_color_by_type(type_name) for type_name in ner_result.values()}

    return render_template(
        "index.html", raw_text=raw_text, highlighted_text=Markup(highlighted_html), type_colors=type_color_map, configs=config
    )


@app.route("/save-config", methods=["POST"])
def save_config_form():
    if data := request.get_json():
        save_configs(data)
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": "Failed to save configs"})


@app.route("/config", methods=["GET", "POST"])
def config():
    configs = load_configs()
    return render_template("config.html", configs=configs, enumerate=enumerate)


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
