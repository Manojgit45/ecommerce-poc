import os
from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, jsonify, request

app = Flask(__name__)
SERVICE_NAME = os.getenv("SERVICE_NAME", "cart")
STARTED_AT = datetime.now(timezone.utc)

CATALOG = {
    "SKU-CRISP-TEE": {"name": "Crisp Cotton Tee", "price": 28.0},
    "SKU-CLOUD-JACKET": {"name": "Cloud Shell Jacket", "price": 124.0},
    "SKU-MOOD-MUG": {"name": "Mood Reset Mug", "price": 18.0},
    "SKU-TRAIL-SNEAKER": {"name": "Trail Sprint Sneaker", "price": 96.0},
    "SKU-WORK-TOTE": {"name": "Workday Carryall Tote", "price": 74.0},
    "SKU-NIGHT-LAMP": {"name": "Night Shift Lamp", "price": 58.0},
}

PROMOTIONS = {"WELCOME10": 0.10, "BUNDLE8": 0.08, "FREESHIP": 0.0}
DEFAULT_SESSION = "guest"
SESSIONS = defaultdict(lambda: {"items": {}, "coupon": None, "createdAt": now_iso()})


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def session_id():
    payload = request.get_json(silent=True) or {}
    return request.headers.get("X-Session-Id") or request.args.get("session_id") or payload.get("session_id") or DEFAULT_SESSION


def cart_state():
    return SESSIONS[session_id()]


def cart_summary(cart):
    items = []
    subtotal = 0.0
    for sku, entry in cart["items"].items():
        quantity = entry["quantity"]
        unit_price = entry["price"]
        line_total = round(quantity * unit_price, 2)
        subtotal += line_total
        items.append(
            {
                "sku": sku,
                "name": entry["name"],
                "quantity": quantity,
                "price": unit_price,
                "lineTotal": line_total,
            }
        )

    subtotal = round(subtotal, 2)
    discount_rate = PROMOTIONS.get(cart["coupon"] or "", 0.0)
    discount = round(subtotal * discount_rate, 2)
    shipping = 0.0 if subtotal >= 75 else (9.99 if subtotal else 0.0)
    tax = round((subtotal - discount) * 0.0725, 2)
    total = round(subtotal - discount + shipping + tax, 2)
    return {
        "sessionId": session_id(),
        "coupon": cart["coupon"],
        "items": items,
        "count": sum(item["quantity"] for item in items),
        "subtotal": subtotal,
        "discount": discount,
        "shipping": shipping,
        "tax": tax,
        "total": total,
    }


def set_item(cart, sku, quantity):
    product = CATALOG.get(sku)
    if not product:
        return None
    quantity = max(int(quantity), 0)
    if quantity == 0:
        cart["items"].pop(sku, None)
    else:
        cart["items"][sku] = {"name": product["name"], "price": product["price"], "quantity": quantity}
    return cart_summary(cart)


@app.get("/healthz")
def healthz():
    return jsonify(service=SERVICE_NAME, status="ok", startedAt=STARTED_AT.isoformat())


@app.get("/")
def index():
    return jsonify(
        service=SERVICE_NAME,
        message="cart service ready",
        routes=[
            "/api/cart",
            "/api/cart/items",
            "/api/cart/items/<sku>",
            "/api/cart/apply-coupon",
            "/api/cart/preview",
            "/api/cart/clear",
        ],
    )


@app.get("/api/cart")
def get_cart():
    return jsonify(service=SERVICE_NAME, cart=cart_summary(cart_state()))


@app.post("/api/cart/items")
def add_item():
    payload = request.get_json(silent=True) or {}
    sku = payload.get("sku")
    quantity = int(payload.get("quantity", 1) or 1)
    cart = cart_state()
    existing_quantity = cart["items"].get(sku, {}).get("quantity", 0)
    updated = set_item(cart, sku, quantity if payload.get("replace") else existing_quantity + quantity)
    if updated is None:
        return jsonify(error="unknown sku", sku=sku), 404
    return jsonify(service=SERVICE_NAME, cart=updated), 201


@app.patch("/api/cart/items/<sku>")
def update_item(sku):
    payload = request.get_json(silent=True) or {}
    updated = set_item(cart_state(), sku, payload.get("quantity", 1))
    if updated is None:
        return jsonify(error="unknown sku", sku=sku), 404
    return jsonify(service=SERVICE_NAME, cart=updated)


@app.delete("/api/cart/items/<sku>")
def delete_item(sku):
    cart = cart_state()
    cart["items"].pop(sku, None)
    return jsonify(service=SERVICE_NAME, cart=cart_summary(cart))


@app.post("/api/cart/apply-coupon")
def apply_coupon():
    payload = request.get_json(silent=True) or {}
    coupon = str(payload.get("code", "")).upper().strip()
    if coupon not in PROMOTIONS:
        return jsonify(error="unknown coupon", validCodes=sorted(PROMOTIONS)), 404
    cart = cart_state()
    cart["coupon"] = coupon
    return jsonify(service=SERVICE_NAME, cart=cart_summary(cart))


@app.post("/api/cart/preview")
def preview():
    return jsonify(service=SERVICE_NAME, preview=cart_summary(cart_state()))


@app.delete("/api/cart")
def clear_cart():
    SESSIONS[session_id()] = {"items": {}, "coupon": None, "createdAt": now_iso()}
    return jsonify(service=SERVICE_NAME, cart=cart_summary(cart_state()))


@app.get("/api/sessions")
def sessions():
    return jsonify(
        service=SERVICE_NAME,
        sessions=[
            {"sessionId": sid, "items": len(cart["items"]), "coupon": cart["coupon"]}
            for sid, cart in SESSIONS.items()
        ],
    )


@app.post("/api/cart/seed")
def seed_cart():
    payload = request.get_json(silent=True) or {}
    cart = cart_state()
    for item in payload.get("items", []):
        set_item(cart, item.get("sku"), item.get("quantity", 1))
    return jsonify(service=SERVICE_NAME, cart=cart_summary(cart), seedId=f"seed_{uuid4().hex[:8]}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
