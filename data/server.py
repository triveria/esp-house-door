from flask import Flask, request, jsonify, send_from_directory
import json
import os

app = Flask(__name__)

# Path to your static files directory
STATIC_DIR = os.path.abspath(os.path.dirname(__file__))
GUESTS_FILE = os.path.join(STATIC_DIR, 'guests.json')

@app.route('/')
def serve_index():
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route('/save-guests', methods=['POST'])
def save_guests():
    try:
        data = request.get_json()
        with open(GUESTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/guests.json', methods=['GET'])
def get_guests():
    try:
        with open(GUESTS_FILE, 'r') as f:
            guests = json.load(f)
        return jsonify(guests), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
