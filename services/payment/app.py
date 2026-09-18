import os
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, jsonify, request

app = Flask(__name__)
SERVICE_NAME = os.getenv("SERVICE_NAME", "payment")
STARTED_AT = datetime.now(timezone.utc)
PAYMENTS = {}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def risk_decision(payload):
    card_number = str(payload.get("cardNumber", "")).replace(" ", "")
    amount = float(payload.get("amount", 0) or 0)
    if amount <= 0:
        return "declined", "invalid-amount"
    if card_number.endswith("0000"):
        return "declined", "test-card-declined"
    if amount > 5000:
        return "review", "high-value-review"
    return "approved", "card-verified"


@app.get("/healthz")
def healthz():
    return jsonify(service=SERVICE_NAME, status="ok", startedAt=STARTED_AT.isoformat())


@app.get("/")
def index():
    return jsonify(service=SERVICE_NAME, message="payment service ready")


@app.get("/api/methods")
def methods():
    return jsonify(
        service=SERVICE_NAME,
        methods=[
            {"id": "card", "label": "Credit or debit card", "fee": 0.0},
            {"id": "wallet", "label": "Digital wallet", "fee": 0.0},
            {"id": "paypal", "label": "PayPal", "fee": 0.0},
            {"id": "installments", "label": "Pay in 4", "fee": 3.99},
        ],
    )


@app.post("/api/payments/authorize")
def authorize():
    payload = request.get_json(silent=True) or {}
    status, reason = risk_decision(payload)
    payment_id = f"pay_{uuid4().hex[:10]}"
    record = {
        "id": payment_id,
        "orderId": payload.get("orderId"),
        "amount": float(payload.get("amount", 0) or 0),
        "currency": payload.get("currency", "USD"),
        "method": payload.get("method", "card"),
        "status": status,
        "reason": reason,
        "authorizedAt": now_iso() if status != "declined" else None,
        "capturedAt": None,
        "refundedAt": None,
    }
    PAYMENTS[payment_id] = record
    code = 200 if status != "declined" else 402
    return jsonify(service=SERVICE_NAME, payment=record), code


@app.post("/api/payments/capture")
def capture():
    payload = request.get_json(silent=True) or {}
    payment = PAYMENTS.get(payload.get("paymentId"))
    if not payment:
        return jsonify(error="payment not found"), 404
    if payment["status"] == "declined":
        return jsonify(error="declined payment cannot be captured", payment=payment), 409
    payment["status"] = "captured"
    payment["capturedAt"] = now_iso()
    return jsonify(service=SERVICE_NAME, payment=payment)


@app.post("/api/payments/refund")
def refund():
    payload = request.get_json(silent=True) or {}
    payment = PAYMENTS.get(payload.get("paymentId"))
    if not payment:
        return jsonify(error="payment not found"), 404
    if payment["status"] not in {"captured", "approved"}:
        return jsonify(error="payment is not refundable", payment=payment), 409
    payment["status"] = "refunded"
    payment["refundedAt"] = now_iso()
    payment["refundAmount"] = float(payload.get("amount", payment["amount"]))
    return jsonify(service=SERVICE_NAME, payment=payment)


@app.get("/api/payments/<payment_id>")
def get_payment(payment_id):
    payment = PAYMENTS.get(payment_id)
    if not payment:
        return jsonify(error="payment not found", paymentId=payment_id), 404
    return jsonify(service=SERVICE_NAME, payment=payment)


@app.get("/api/payments")
def list_payments():
    return jsonify(service=SERVICE_NAME, count=len(PAYMENTS), payments=list(PAYMENTS.values()))


@app.get("/api/risk")
def risk():
    return jsonify(
        service=SERVICE_NAME,
        checks=[
            {"rule": "invalid-amount", "status": "block"},
            {"rule": "test-card-declined", "status": "block"},
            {"rule": "high-value-review", "status": "manual_review"},
        ],
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
