from flask import Flask, render_template, request, jsonify
from markupsafe import Markup
import json
import re
import os
import requests

app = Flask(__name__)

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_configs() -> list:
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON from the config file.")
            return []
    else:
        print("Config file not found.")
        return []


def save_configs(configs: list[dict]) -> None:
    with open(CONFIG_FILE_PATH, "w") as file:
        json.dump(configs, file, indent=4)


def send_ner_request(model_url: str, text: str) -> dict:
    try:
        response = requests.post(model_url, headers={"Content-Type": "application/json"}, json={"text": text})
        response.raise_for_status()
    except requests.HTTPError as e:
        print(f"Error sending POST request to {model_url}: {e}")
        return {}
    except requests.exceptions.ConnectionError as e:
        print(f"Could not reach model at {model_url}: {e}")
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

    def replacer(match):
        word = match.group(0)
        meta = entities.get(word, "")
        type_name = meta.get("type", "")
        tooltip = meta.get("tooltip", "")
        color = get_color_by_type(type_name)
        return f'<span class="highlight" style="background-color: {color};" data-tooltip="{tooltip}">{word}</span>'

    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in entities) + r")\b", re.IGNORECASE)
    return pattern.sub(replacer, text)


@app.route("/", methods=["GET", "POST"])
def index():
    raw_text = ""
    highlighted_html = ""
    type_color_map = {}

    config = load_configs()

    if request.method == "POST":
        url = request.form.get("url")
        raw_text = request.form.get("text")
        ner_result = send_ner_request(url, raw_text)
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
    app.run(debug=True)
