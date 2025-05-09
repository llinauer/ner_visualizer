from flask import Flask, jsonify, request
import json

app = Flask(__name__)

# Temporary in-memory storage for button config
config_file = 'config.json'

# Load config from file (if exists)
def load_config():
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Save config to file
def save_config(buttons):
    with open(config_file, 'w') as f:
        json.dump(buttons, f)

@app.route('/api/config', methods=['GET'])
def get_config():
    buttons = load_config()
    return jsonify(buttons)

@app.route('/api/config', methods=['POST'])
def update_config():
    data = request.get_json()
    save_config(data)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
