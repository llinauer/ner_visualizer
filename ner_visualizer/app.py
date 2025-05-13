from flask import Flask, render_template, request, jsonify
from markupsafe import Markup
import json
import re
import os


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


# Shared keyword data
HIGHLIGHTS = {
    "warning": {"type": "alert", "tooltip": "This is a warning"},
    "important": {"type": "priority", "tooltip": "This is important"},
    "note": {"type": "note", "tooltip": "Take note of this"},
    "error": {"type": "alert", "tooltip": "Something went wrong"},
    "caution": {"type": "alert", "tooltip": "Exercise caution"},
    "info": {"type": "info", "tooltip": "General information"},
    "success": {"type": "positive", "tooltip": "Everything is OK"},
    "failure": {"type": "negative", "tooltip": "A failure occurred"},
    "critical": {"type": "priority", "tooltip": "Critical situation"},
    "update": {"type": "info", "tooltip": "An update has been made"},
}

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


def highlight_text(text: str) -> str:
    keywords = HIGHLIGHTS

    def replacer(match):
        word = match.group(0)
        meta = keywords[word.lower()]
        type_name = meta["type"]
        tooltip = meta["tooltip"]
        color = get_color_by_type(type_name)
        return f'<span class="highlight" style="background-color: {color};" data-tooltip="{tooltip}">{word}</span>'

    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in keywords) + r")\b", re.IGNORECASE)
    return pattern.sub(replacer, text)


@app.route("/", methods=["GET", "POST"])
def index():
    raw_text = ""
    highlighted_html = ""
    type_color_map = {}

    if request.method == "POST":
        raw_text = request.form.get("text_input", "")
        keywords = HIGHLIGHTS

        # Get all unique types from the keywords
        unique_types = {meta["type"] for meta in keywords.values()}
        type_color_map = {type_name: get_color_by_type(type_name) for type_name in unique_types}

        # Perform highlight
        highlighted_html = highlight_text(raw_text)

    config = load_configs()

    return render_template(
        "index.html", raw_text=raw_text, highlighted_text=Markup(highlighted_html), type_colors=type_color_map, configs=config
    )


@app.route("/send-url", methods=["POST"])
def send_url():
    url = request.form["url"]
    # Do something with the URL, like process it or store it
    return jsonify({"status": "success", "url": url})


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
