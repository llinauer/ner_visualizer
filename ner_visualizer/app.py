from flask import Flask, render_template, request, redirect, url_for, jsonify
from markupsafe import Markup
from jinja2 import Environment
import json
import re
import os

app = Flask(__name__)

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

# Function to load the config from a file
def load_configs():
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON from the config file.")
            return []  # Return an empty list if there is an error decoding the JSON
    else:
        print("Config file not found.")
        return [] 

def save_configs(configs):
    with open("configs.json", "w") as file:
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
    "#fca5a5", "#fcd34d", "#6ee7b7", "#93c5fd", "#c4b5fd",
    "#f9a8d4", "#fdba74", "#a5f3fc", "#d9f99d", "#fcd5ce",
    "#e0f2fe", "#f0abfc", "#bbf7d0", "#fde68a", "#fecaca",
    "#c7d2fe", "#ddd6fe", "#fef9c3", "#bae6fd", "#fecdd3"
]

def get_color_by_type(type_name):
    index = abs(hash(type_name)) % len(COLOR_PALETTE)
    return COLOR_PALETTE[index]

def highlight_text(text, strategy):
    """Wrap matching words based on the chosen strategy."""
    if strategy == "important":
        keywords = {k: v for k, v in HIGHLIGHTS.items() if v["type"] == "priority"}
    else:  # strategy == "all"
        keywords = HIGHLIGHTS

    def replacer(match):
        word = match.group(0)
        meta = keywords[word.lower()]
        type_name = meta["type"]
        tooltip = meta["tooltip"]
        color = get_color_by_type(type_name)
        return (
            f'<span class="highlight" '
            f'style="background-color: {color};" '
            f'data-tooltip="{tooltip}">{word}</span>'
        )

    pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b', re.IGNORECASE)
    return pattern.sub(replacer, text)

@app.route("/", methods=["GET", "POST"])
def index():
    raw_text = ""
    highlighted_html = ""
    type_color_map = {}

    if request.method == "POST":
        raw_text = request.form.get("text_input", "")
        action = request.form.get("action", "all")

        # Filter keywords by strategy
        if action == "important":
            keywords = {k: v for k, v in HIGHLIGHTS.items() if v["type"] == "priority"}
        else:
            keywords = HIGHLIGHTS

        # Get all unique types from the keywords
        unique_types = {meta["type"] for meta in keywords.values()}
        type_color_map = {type_name: get_color_by_type(type_name) for type_name in unique_types}

        # Perform highlight
        highlighted_html = highlight_text(raw_text, strategy=action)
    
    config = load_configs()

    return render_template(
        "index.html",
        raw_text=raw_text,
        highlighted_text=Markup(highlighted_html),
        type_colors=type_color_map,
        configs=config
    )

@app.route('/send-url', methods=['POST'])
def send_url():
    url = request.form['url']
    # Do something with the URL, like process it or store it
    return jsonify({'status': 'success', 'url': url})

@app.route("/config", methods=["GET", "POST"])
def config():
    configs = load_configs()  # Load current configs from the file
    env = Environment()  # Create a Jinja2 environment

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            button_name = request.form.get("button_name")
            url_input = request.form.get("url_input")
            configs.append({"button_name": button_name, "url": url_input})
            save_configs(configs)

        elif action == "delete":
            index = int(request.form.get("index"))
            if 0 <= index < len(configs):
                del configs[index]
                save_configs(configs)

        elif action == "update":
            index = int(request.form.get("index"))
            new_url = request.form.get("new_url")
            if 0 <= index < len(configs):
                configs[index]["url"] = new_url
                save_configs(configs)

    return render_template("config.html", configs=configs, enumerate=enumerate)

if __name__ == "__main__":
    app.run(debug=True)