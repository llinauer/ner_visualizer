from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow requests from Vite dev server (localhost:5173)

# Dummy config for frontend buttons
@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify([
        {"label": "Highlight Frameworks", "url": "/api/highlight/frameworks"},
        {"label": "Highlight Languages", "url": "/api/highlight/languages"}
    ])

# Dummy endpoint for "frameworks"
@app.route("/api/highlight/frameworks", methods=["POST"])
def highlight_frameworks():
    text = request.json.get("text", "")
    return jsonify({
        "Flask": "framework",
        "Vue.js": "framework"
    })

# Dummy endpoint for "languages"
@app.route("/api/highlight/languages", methods=["POST"])
def highlight_languages():
    text = request.json.get("text", "")
    return jsonify({
        "Python": "language",
        "JavaScript": "language"
    })

if __name__ == "__main__":
    app.run(debug=True)

