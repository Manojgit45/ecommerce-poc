import os
from flask import Flask, jsonify

app = Flask(__name__)
SERVICE_NAME = os.getenv("SERVICE_NAME", "cart")


@app.get("/healthz")
def healthz():
    return jsonify(service=SERVICE_NAME, status="ok")


@app.get("/")
def index():
    return jsonify(service=SERVICE_NAME, message="ecommerce service ready")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
