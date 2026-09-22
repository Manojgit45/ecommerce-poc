import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import pymssql
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from flask import Flask, jsonify, request

app = Flask(__name__)
SERVICE_NAME = os.getenv("SERVICE_NAME", "order")
STARTED_AT = datetime.now(timezone.utc)
_secret_client = None
_schema_ready = False


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def secret_value(name):
    global _secret_client
    direct_value = os.getenv(name)
    if direct_value:
        return direct_value
    if _secret_client is None:
        _secret_client = SecretClient(os.environ["KEY_VAULT_URL"], DefaultAzureCredential())
    return _secret_client.get_secret(name).value


def database_connection():
    return pymssql.connect(
        server=os.environ["SQL_SERVER"],
        user=os.environ["SQL_USERNAME"],
        password=secret_value(os.getenv("SQL_PASSWORD_SECRET", "SQL_PASSWORD")),
        database=os.environ["SQL_DATABASE"],
        port=1433,
        tds_version="7.4",
        login_timeout=10,
        timeout=10,
    )


def ensure_schema():
    global _schema_ready
    if _schema_ready:
        return
    with database_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            IF OBJECT_ID('dbo.orders', 'U') IS NULL
            CREATE TABLE dbo.orders (
                id NVARCHAR(64) NOT NULL PRIMARY KEY,
                status NVARCHAR(32) NOT NULL,
                created_at DATETIME2 NOT NULL,
                payload NVARCHAR(MAX) NOT NULL
            )
            """
        )
        connection.commit()
    _schema_ready = True


def save_order(order):
    ensure_schema()
    with database_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "MERGE dbo.orders AS target USING (SELECT %s AS id) AS source ON target.id = source.id "
            "WHEN MATCHED THEN UPDATE SET status=%s, payload=%s "
            "WHEN NOT MATCHED THEN INSERT (id, status, created_at, payload) VALUES (%s, %s, %s, %s);",
            (
                order["id"], order["status"], json.dumps(order), order["id"], order["status"],
                datetime.fromisoformat(order["createdAt"]), json.dumps(order),
            ),
        )
        connection.commit()


def read_orders(status=None):
    ensure_schema()
    with database_connection() as connection:
        cursor = connection.cursor(as_dict=True)
        if status:
            cursor.execute("SELECT payload FROM dbo.orders WHERE status=%s ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT payload FROM dbo.orders ORDER BY created_at DESC")
        return [json.loads(row["payload"]) for row in cursor.fetchall()]


def read_order(order_id):
    ensure_schema()
    with database_connection() as connection:
        cursor = connection.cursor(as_dict=True)
        cursor.execute("SELECT payload FROM dbo.orders WHERE id=%s", (order_id,))
        row = cursor.fetchone()
        return json.loads(row["payload"]) if row else None


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
    return jsonify(service=SERVICE_NAME, status="ok", persistence="sql", startedAt=STARTED_AT.isoformat())


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
    save_order(order)
    return jsonify(service=SERVICE_NAME, order=order), 201


@app.get("/api/orders")
def list_orders():
    status = request.args.get("status", "").strip().lower()
    orders = read_orders(status)
    return jsonify(service=SERVICE_NAME, count=len(orders), orders=orders)


@app.get("/api/orders/<order_id>")
def get_order(order_id):
    order = read_order(order_id)
    if not order:
        return jsonify(error="order not found", orderId=order_id), 404
    return jsonify(service=SERVICE_NAME, order=order)


@app.post("/api/orders/<order_id>/cancel")
def cancel_order(order_id):
    order = read_order(order_id)
    if not order:
        return jsonify(error="order not found", orderId=order_id), 404
    if order["status"] in {"shipped", "delivered"}:
        return jsonify(error="cannot cancel a shipped order", order=order), 409
    order["status"] = "cancelled"
    order["timeline"].append({"at": now_iso(), "status": "cancelled", "message": "Customer cancelled the order"})
    save_order(order)
    return jsonify(service=SERVICE_NAME, order=order)


@app.post("/api/orders/<order_id>/ship")
def ship_order(order_id):
    order = read_order(order_id)
    if not order:
        return jsonify(error="order not found", orderId=order_id), 404
    order["status"] = "shipped"
    order["timeline"].append({"at": now_iso(), "status": "shipped", "message": "Handed to carrier"})
    save_order(order)
    return jsonify(service=SERVICE_NAME, order=order)


@app.get("/api/orders/<order_id>/timeline")
def order_timeline(order_id):
    order = read_order(order_id)
    if not order:
        return jsonify(error="order not found", orderId=order_id), 404
    return jsonify(service=SERVICE_NAME, orderId=order_id, timeline=order["timeline"])


@app.get("/api/dashboard")
def dashboard():
    counts = {"confirmed": 0, "cancelled": 0, "shipped": 0, "delivered": 0}
    revenue = 0.0
    for order in read_orders():
        counts[order["status"]] = counts.get(order["status"], 0) + 1
        if order["status"] != "cancelled":
            revenue += order["summary"]["total"]
    return jsonify(service=SERVICE_NAME, counts=counts, revenue=round(revenue, 2), currency="USD")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
