import os
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, jsonify, request

app = Flask(__name__)
SERVICE_NAME = os.getenv("SERVICE_NAME", "order")
STARTED_AT = datetime.now(timezone.utc)
ORDERS = {}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def calculate_totals(items, discount_rate=0.0):
    normalized = []
    subtotal = 0.0
    for item in items:
        sku = item.get("sku")
        if not sku:
            continue
        quantity = max(int(item.get("quantity", 1) or 1), 1)
        unit_price = float(item.get("unitPrice", item.get("price", 0)) or 0)
        if unit_price <= 0:
            continue
        line_total = round(quantity * unit_price, 2)
        subtotal += line_total
        normalized.append(
            {
                "sku": sku,
                "name": item.get("name", sku),
                "quantity": quantity,
                "unitPrice": unit_price,
                "lineTotal": line_total,
            }
        )

    subtotal = round(subtotal, 2)
    discount = round(subtotal * float(discount_rate), 2)
    shipping = 0.0 if subtotal >= 75 else (9.99 if subtotal else 0.0)
    tax = round((subtotal - discount) * 0.0725, 2)
    total = round(subtotal - discount + shipping + tax, 2)
    return normalized, subtotal, discount, shipping, tax, total


@app.get("/healthz")
def healthz():
    return jsonify(service=SERVICE_NAME, status="ok", startedAt=STARTED_AT.isoformat())


@app.get("/")
def index():
    return jsonify(service=SERVICE_NAME, message="order service ready")


@app.post("/api/orders")
def create_order():
    payload = request.get_json(silent=True) or {}
    normalized_items, subtotal, discount, shipping, tax, total = calculate_totals(
        payload.get("items", []), payload.get("discountRate", 0)
    )
    if not normalized_items:
        return jsonify(error="order requires at least one line item"), 400

    order_id = f"ord_{uuid4().hex[:10]}"
    order = {
        "id": order_id,
        "status": "confirmed",
        "createdAt": now_iso(),
        "customer": payload.get("customer", {}),
        "shippingAddress": payload.get("shippingAddress", {}),
        "fulfillment": {
            "warehouse": payload.get("warehouse", "phoenix-01"),
            "tracking": f"TRK-{uuid4().hex[:8].upper()}",
            "etaDays": 3 if shipping == 0 else 5,
        },
        "items": normalized_items,
        "summary": {
            "subtotal": subtotal,
            "discount": discount,
            "shipping": shipping,
            "tax": tax,
            "total": total,
            "currency": "USD",
        },
        "timeline": [
            {"at": now_iso(), "status": "created", "message": "Order created"},
            {"at": now_iso(), "status": "confirmed", "message": "Payment approved"},
        ],
    }
    ORDERS[order_id] = order
    return jsonify(service=SERVICE_NAME, order=order), 201


@app.get("/api/orders")
def list_orders():
    status = request.args.get("status", "").strip().lower()
    orders = list(ORDERS.values())
    if status:
        orders = [order for order in orders if order["status"].lower() == status]
    return jsonify(service=SERVICE_NAME, count=len(orders), orders=orders)


@app.get("/api/orders/<order_id>")
def get_order(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify(error="order not found", orderId=order_id), 404
    return jsonify(service=SERVICE_NAME, order=order)


@app.post("/api/orders/<order_id>/cancel")
def cancel_order(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify(error="order not found", orderId=order_id), 404
    if order["status"] in {"shipped", "delivered"}:
        return jsonify(error="cannot cancel a shipped order", order=order), 409
    order["status"] = "cancelled"
    order["timeline"].append({"at": now_iso(), "status": "cancelled", "message": "Customer cancelled the order"})
    return jsonify(service=SERVICE_NAME, order=order)


@app.post("/api/orders/<order_id>/ship")
def ship_order(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify(error="order not found", orderId=order_id), 404
    order["status"] = "shipped"
    order["timeline"].append({"at": now_iso(), "status": "shipped", "message": "Handed to carrier"})
    return jsonify(service=SERVICE_NAME, order=order)


@app.get("/api/orders/<order_id>/timeline")
def order_timeline(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify(error="order not found", orderId=order_id), 404
    return jsonify(service=SERVICE_NAME, orderId=order_id, timeline=order["timeline"])


@app.get("/api/dashboard")
def dashboard():
    counts = {"confirmed": 0, "cancelled": 0, "shipped": 0, "delivered": 0}
    revenue = 0.0
    for order in ORDERS.values():
        counts[order["status"]] = counts.get(order["status"], 0) + 1
        if order["status"] != "cancelled":
            revenue += order["summary"]["total"]
    return jsonify(service=SERVICE_NAME, counts=counts, revenue=round(revenue, 2), currency="USD")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
