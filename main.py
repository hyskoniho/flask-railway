from flask import Flask, jsonify, request
from library import clob, psoffice, moodle
import os, requests

app = Flask(__name__)


@app.route('/foo')
def index():
    return jsonify({"Choo Choo": "Welcome to your Flask app 🚅"})

@app.route('/server_address')
def server_address():
    try:
        try:
            r = requests.get("https://api.ipify.org?format=json", timeout=5)
            r.raise_for_status()
            external_ip = r.json().get("ip")
        except Exception:
            r = requests.get("https://checkip.amazonaws.com/", timeout=5)
            r.raise_for_status()
            external_ip = r.text.strip()
    except Exception as exc:
        return jsonify({"server_address": request.host_url, "external_ip": None, "error": str(exc)}), 502

    return jsonify({"server_address": request.host_url, "external_ip": external_ip})

@app.route('/clob_test', methods=['GET'])
def clob_test():
    try:
        r = requests.get(r"https://clob.polymarket.com")
        r.raise_for_status()
        
    except Exception:
        return {"error": "CLOB API unreachable"}
            
    return jsonify({"request": "successful", "status_code": r.status_code, "text": r.text})

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

@app.route('/psoffice_week', methods=['GET'])
def psoffice_week():
    username = request.args.get('username')
    password = request.args.get('password')

    if not username or not password:
        return jsonify({"error": "Missing 'username' or 'password' query parameters"}), 400

    try:
        week_data = psoffice.get_week(username, password)
    except Exception as e:
        return jsonify({"error": "Failed to retrieve week data", "details": str(e)}), 500

    return jsonify({"week_data": week_data})

@app.route('/moodle_session', methods=['GET'])
def moodle_session():
    username = request.args.get('username')
    password = request.args.get('password')

    if not username or not password:
        return jsonify({"error": "Missing 'username' or 'password' query parameters"}), 400

    try:
        cookies, sesskey, id = moodle.buildSession(username, password)
    except Exception as e:
        return jsonify({"error": "Failed to build Moodle session", "details": str(e)}), 500

    return jsonify({
        "cookies": cookies,
        "sesskey": sesskey,
        "id": id
    })

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
