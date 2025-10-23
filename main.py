from flask import Flask, jsonify, request
from library import clob
import os

app = Flask(__name__)


@app.route('/foo')
def index():
    return jsonify({"Choo Choo": "Welcome to your Flask app 🚅"})

@app.route('/clob_order', methods=['POST'])
def clob_order():
    # Validate incoming JSON
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    # Extract values with defaults of None
    private_key = data.get("private_key")
    proxy_address = data.get("proxy_address")
    token_id = data.get("token_id")
    price = data.get("price")
    size = data.get("size")
    side = data.get("side")

    # Basic validation
    missing = [k for k, v in {
        "private_key": private_key,
        "proxy_address": proxy_address,
        "token_id": token_id,
        "price": price,
        "size": size,
        "side": side,
    }.items() if v is None]

    if missing:
        return jsonify({"error": "Missing fields", "missing": missing}), 400

    try:
        response = clob.create_and_post_order(
            private_key=private_key,
            proxy_address=proxy_address,
            token_id=token_id,
            price=price,
            size=size,
            side=side
        )
    except Exception as e:
        # Defensive: ensure we return JSON on unexpected errors
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
