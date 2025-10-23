from urllib import request
from flask import Flask, jsonify
from library import clob
import os

app = Flask(__name__)


@app.route('/foo')
def index():
    return jsonify({"Choo Choo": "Welcome to your Flask app 🚅"})

@app.route('/clob_order', methods=['POST'])
def clob_order():
    data = request.json
    response = clob.create_and_post_order(
        private_key=data.get("private_key"),
        proxy_address=data.get("proxy_address"),
        token_id=data.get("token_id"),
        price=data.get("price"),
        size=data.get("size"),
        side=data.get("side")
    )
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
