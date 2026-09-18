import os
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
SERVICE_NAME = os.getenv("SERVICE_NAME", "product")
STARTED_AT = datetime.now(timezone.utc)

CATALOG = [
        {
                "sku": "SKU-CRISP-TEE",
                "name": "Crisp Cotton Tee",
                "category": "Apparel",
                "price": 28.0,
                "rating": 4.8,
                "badge": "Bestseller",
                "stock": 84,
                "description": "Soft everyday tee with a clean fit and premium cotton hand feel.",
                "accent": "#e5b07c",
        },
        {
                "sku": "SKU-CLOUD-JACKET",
                "name": "Cloud Shell Jacket",
                "category": "Outerwear",
                "price": 124.0,
                "rating": 4.9,
                "badge": "New",
                "stock": 31,
                "description": "Lightweight waterproof shell built for city commutes and weekend weather.",
                "accent": "#9bb7d4",
        },
        {
                "sku": "SKU-MOOD-MUG",
                "name": "Mood Reset Mug",
                "category": "Home",
                "price": 18.0,
                "rating": 4.7,
                "badge": "Giftable",
                "stock": 120,
                "description": "Matte ceramic mug with a generous handle and heat-retaining shape.",
                "accent": "#d28c6a",
        },
        {
                "sku": "SKU-TRAIL-SNEAKER",
                "name": "Trail Sprint Sneaker",
                "category": "Footwear",
                "price": 96.0,
                "rating": 4.6,
                "badge": "Popular",
                "stock": 54,
                "description": "Responsive everyday sneaker with grippy outsole and breathable upper.",
                "accent": "#7db4a5",
        },
        {
                "sku": "SKU-WORK-TOTE",
                "name": "Workday Carryall Tote",
                "category": "Accessories",
                "price": 74.0,
                "rating": 4.8,
                "badge": "Editor\'s Pick",
                "stock": 46,
                "description": "Structured tote with laptop sleeve, side pockets, and durable stitching.",
                "accent": "#b58bcc",
        },
        {
                "sku": "SKU-NIGHT-LAMP",
                "name": "Night Shift Lamp",
                "category": "Home",
                "price": 58.0,
                "rating": 4.5,
                "badge": "Limited",
                "stock": 22,
                "description": "Warm desk lamp with dimmable settings and a compact footprint.",
                "accent": "#f1c27d",
        },
]


def now_iso():
        return datetime.now(timezone.utc).isoformat()


def lookup_product(sku):
        for product in CATALOG:
                if product["sku"] == sku:
                        return product
        return None


def product_view(product):
        return {
                **product,
                "inStock": product["stock"] > 0,
                "discountedPrice": round(product["price"] * 0.92, 2),
        }


def response_for_products(products):
        return [product_view(product) for product in products]


def calc_totals(items):
        normalized = []
        subtotal = 0.0
        for item in items:
                sku = item.get("sku")
                product = lookup_product(sku)
                if not product:
                        continue
                quantity = max(int(item.get("quantity", 1)), 1)
                unit_price = float(item.get("price", product["price"]))
                line_total = round(quantity * unit_price, 2)
                subtotal += line_total
                normalized.append(
                        {
                                "sku": sku,
                                "name": product["name"],
                                "quantity": quantity,
                                "unitPrice": unit_price,
                                "lineTotal": line_total,
                        }
                )

        subtotal = round(subtotal, 2)
        discount = round(subtotal * 0.08, 2) if subtotal >= 100 else 0.0
        shipping = 0.0 if subtotal >= 75 else (9.99 if subtotal else 0.0)
        tax = round((subtotal - discount) * 0.0725, 2)
        total = round(subtotal - discount + shipping + tax, 2)
        return {
                "items": normalized,
                "subtotal": subtotal,
                "discount": discount,
                "shipping": shipping,
                "tax": tax,
                "total": total,
        }


@app.get("/healthz")
def healthz():
        return jsonify(service=SERVICE_NAME, status="ok", startedAt=STARTED_AT.isoformat())


@app.get("/api/meta")
def meta():
        categories = sorted({product["category"] for product in CATALOG})
        return jsonify(
                service=SERVICE_NAME,
                status="ok",
                generatedAt=now_iso(),
                catalogSize=len(CATALOG),
                categories=categories,
                routes=[
                        "/",
                        "/api/meta",
                        "/api/categories",
                        "/api/products",
                        "/api/products/<sku>",
                        "/api/featured",
                        "/api/recommendations/<sku>",
                        "/api/quote",
                        "/api/checkout",
                ],
        )


@app.get("/api/categories")
def categories():
        grouped = {}
        for product in CATALOG:
                grouped[product["category"]] = grouped.get(product["category"], 0) + 1
        return jsonify(
                service=SERVICE_NAME,
                categories=[
                        {"name": name, "count": count}
                        for name, count in sorted(grouped.items())
                ],
        )


@app.get("/api/products")
def products():
        query = request.args.get("q", "").strip().lower()
        category = request.args.get("category", "").strip().lower()
        sort = request.args.get("sort", "featured")
        results = []

        for product in CATALOG:
                haystack = " ".join(
                        [
                                product["sku"],
                                product["name"],
                                product["category"],
                                product["description"],
                                product["badge"],
                        ]
                ).lower()
                if query and query not in haystack:
                        continue
                if category and category != product["category"].lower():
                        continue
                results.append(product)

        if sort == "price-asc":
                results.sort(key=lambda item: item["price"])
        elif sort == "price-desc":
                results.sort(key=lambda item: item["price"], reverse=True)
        elif sort == "rating":
                results.sort(key=lambda item: item["rating"], reverse=True)
        else:
                results.sort(key=lambda item: (item["badge"] != "Bestseller", -item["rating"]))

        return jsonify(service=SERVICE_NAME, count=len(results), products=response_for_products(results))


@app.get("/api/products/<sku>")
def product_detail(sku):
        product = lookup_product(sku)
        if not product:
                return jsonify(error="product not found", sku=sku), 404

        related = [
                item
                for item in CATALOG
                if item["sku"] != sku and item["category"] == product["category"]
        ][:3]
        return jsonify(
                service=SERVICE_NAME,
                product={
                        **product_view(product),
                        "related": response_for_products(related),
                },
        )


@app.get("/api/featured")
def featured():
        featured_products = sorted(CATALOG, key=lambda item: (item["badge"] != "Bestseller", -item["rating"]))[:4]
        return jsonify(service=SERVICE_NAME, products=response_for_products(featured_products))


@app.get("/api/recommendations/<sku>")
def recommendations(sku):
        product = lookup_product(sku)
        if not product:
                return jsonify(error="product not found", sku=sku), 404

        recommended = [
                item
                for item in CATALOG
                if item["sku"] != sku and item["category"] in {product["category"], "Accessories", "Home"}
        ][:4]
        return jsonify(service=SERVICE_NAME, recommendations=response_for_products(recommended))


@app.post("/api/quote")
def quote():
        payload = request.get_json(silent=True) or {}
        totals = calc_totals(payload.get("items", []))
        totals.update({"currency": "USD", "estimatedDeliveryDays": 2 if totals["shipping"] == 0 else 5})
        return jsonify(service=SERVICE_NAME, **totals)


@app.post("/api/checkout")
def checkout():
        payload = request.get_json(silent=True) or {}
        totals = calc_totals(payload.get("items", []))
        if not totals["items"]:
                return jsonify(error="checkout requires at least one valid item"), 400

        customer = payload.get("customer", {})
        order_id = f"ord_{uuid4().hex[:10]}"
        payment_id = f"pay_{uuid4().hex[:10]}"
        notification_id = f"ntf_{uuid4().hex[:10]}"

        return jsonify(
                service=SERVICE_NAME,
                order={
                        "id": order_id,
                        "status": "confirmed",
                        "placedAt": now_iso(),
                        "customer": {
                                "name": customer.get("name", "Guest Shopper"),
                                "email": customer.get("email", "guest@example.com"),
                        },
                        "items": totals["items"],
                        "summary": {key: totals[key] for key in ["subtotal", "discount", "shipping", "tax", "total"]},
                },
                payment={
                        "id": payment_id,
                        "status": "captured",
                        "method": payload.get("paymentMethod", "card"),
                },
                notification={
                        "id": notification_id,
                        "channel": "email",
                        "status": "sent",
                        "message": f"Order {order_id} confirmation sent.",
                },
                fulfillment={
                        "warehouse": "phoenix-01",
                        "tracking": f"TRK-{uuid4().hex[:8].upper()}",
                        "etaDays": 3 if totals["shipping"] == 0 else 5,
                },
        )


@app.get("/")
def index():
        return render_template_string(
                """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Northstar Market</title>
    <style>
        :root { color-scheme: light; --bg: #f7f1ea; --panel: #fffaf5; --text: #201915; --muted: #6d5b51; --accent: #9d5c35; --border: rgba(32,25,21,.12); }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif; background: radial-gradient(circle at top left, #fff4e8, var(--bg) 55%); color: var(--text); }
        header { padding: 28px clamp(20px, 4vw, 48px) 18px; display: grid; gap: 18px; }
        .hero { display: grid; gap: 18px; grid-template-columns: 1.3fr .9fr; align-items: end; }
        .eyebrow { text-transform: uppercase; letter-spacing: .22em; font-size: 12px; color: var(--accent); }
        h1 { margin: 0; font-size: clamp(42px, 6vw, 84px); line-height: .92; max-width: 10ch; }
        p { margin: 0; color: var(--muted); max-width: 58ch; line-height: 1.55; }
        .stats { display: flex; flex-wrap: wrap; gap: 12px; }
        .stat { background: rgba(255,255,255,.78); border: 1px solid var(--border); border-radius: 18px; padding: 14px 16px; min-width: 120px; box-shadow: 0 18px 48px rgba(62, 38, 22, .08); }
        .stat strong { display: block; font-size: 24px; }
        .stat span { color: var(--muted); font-size: 13px; }
        main { padding: 0 clamp(20px, 4vw, 48px) 40px; display: grid; gap: 24px; }
        .toolbar, .grid, .checkout { background: rgba(255,255,255,.7); border: 1px solid var(--border); backdrop-filter: blur(10px); border-radius: 24px; box-shadow: 0 18px 48px rgba(62, 38, 22, .08); }
        .toolbar { padding: 16px; display: grid; gap: 12px; grid-template-columns: 1.2fr .8fr auto; }
        .toolbar input, .toolbar select, .checkout input, .checkout button { border-radius: 14px; border: 1px solid var(--border); padding: 12px 14px; font: inherit; }
        .toolbar button, .checkout button { background: var(--text); color: #fff; cursor: pointer; }
        .toolbar button:hover, .checkout button:hover { opacity: .92; }
        .grid { padding: 18px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
        .card { background: var(--panel); border: 1px solid rgba(32,25,21,.08); border-radius: 22px; padding: 18px; display: grid; gap: 12px; min-height: 260px; }
        .swatch { height: 120px; border-radius: 18px; background: linear-gradient(160deg, var(--accent), rgba(255,255,255,.4)); display: grid; place-items: end start; padding: 14px; color: #fff; font-weight: 700; letter-spacing: .04em; }
        .meta { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: 13px; }
        .price { font-size: 24px; font-weight: 700; }
        .actions { display: flex; gap: 10px; }
        .actions button { flex: 1; }
        .checkout { padding: 18px; display: grid; gap: 16px; }
        .checkout-grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
        .summary { display: grid; gap: 8px; color: var(--muted); }
        .summary strong { color: var(--text); }
        #message { min-height: 26px; color: var(--accent); font-weight: 600; }
        @media (max-width: 860px) { .hero, .toolbar { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <header>
        <div class="hero">
            <div>
                <div class="eyebrow">Northstar Market</div>
                <h1>Modern essentials for every checkout.</h1>
                <p>Browse a polished storefront, inspect product detail, build a cart, and complete a demo checkout with order, payment, and notification confirmation in one flow.</p>
            </div>
            <div class="stats" id="stats"></div>
        </div>
    </header>
    <main>
        <section class="toolbar">
            <input id="search" placeholder="Search products, categories, or badges">
            <select id="category"></select>
            <button id="refresh">Refresh catalog</button>
        </section>
        <section class="grid" id="catalog"></section>
        <section class="checkout">
            <div class="summary" id="cartSummary">Your cart is empty.</div>
            <div class="checkout-grid">
                <input id="name" placeholder="Full name" value="Avery Smith">
                <input id="email" placeholder="Email" value="avery@example.com">
                <input id="address" placeholder="Shipping address" value="88 Market Street, Austin, TX">
                <select id="paymentMethod">
                    <option value="card">Card</option>
                    <option value="wallet">Wallet</option>
                    <option value="paypal">PayPal</option>
                </select>
            </div>
            <button id="checkout">Place order</button>
            <div id="message"></div>
        </section>
    </main>
    <script>
        const state = { products: [], cart: JSON.parse(localStorage.getItem('demo-cart') || '[]') };

        function saveCart() {
            localStorage.setItem('demo-cart', JSON.stringify(state.cart));
        }

        function cartCount() {
            return state.cart.reduce((sum, item) => sum + item.quantity, 0);
        }

        function money(value) {
            return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
        }

        function renderStats(meta) {
            document.getElementById('stats').innerHTML = `
                <div class="stat"><strong>${meta.catalogSize}</strong><span>products</span></div>
                <div class="stat"><strong>${cartCount()}</strong><span>items in cart</span></div>
                <div class="stat"><strong>3</strong><span>checkout steps</span></div>`;
        }

        function renderCategories(categories) {
            const select = document.getElementById('category');
            const current = select.value;
            select.innerHTML = '<option value="">All categories</option>' + categories.map(category => `<option value="${category.name}">${category.name}</option>`).join('');
            select.value = current;
        }

        function renderCatalog() {
            const q = document.getElementById('search').value.trim();
            const category = document.getElementById('category').value;
            const params = new URLSearchParams();
            if (q) params.set('q', q);
            if (category) params.set('category', category);
            fetch(`/api/products?${params.toString()}`)
                .then(response => response.json())
                .then(payload => {
                    state.products = payload.products || [];
                    document.getElementById('catalog').innerHTML = state.products.map(product => `
                        <article class="card">
                            <div class="swatch" style="--accent:${product.accent}">${product.badge}</div>
                            <div class="meta"><span>${product.category}</span><span>${product.rating} ★</span></div>
                            <strong>${product.name}</strong>
                            <p>${product.description}</p>
                            <div class="meta"><span>${product.stock} in stock</span><span>${product.sku}</span></div>
                            <div class="price">${money(product.price)}</div>
                            <div class="actions">
                                <button onclick='addToCart("${product.sku}")'>Add to cart</button>
                                <button onclick='showDetails("${product.sku}")'>View</button>
                            </div>
                        </article>
                    `).join('');
                    renderStats({ catalogSize: state.products.length });
                });
        }

        function addToCart(sku) {
            const product = state.products.find(item => item.sku === sku);
            if (!product) return;
            const existing = state.cart.find(item => item.sku === sku);
            if (existing) {
                existing.quantity += 1;
            } else {
                state.cart.push({ sku, name: product.name, price: product.price, quantity: 1 });
            }
            saveCart();
            updateSummary('Added to cart.');
            renderStats({ catalogSize: state.products.length });
        }

        function showDetails(sku) {
            fetch(`/api/products/${sku}`)
                .then(response => response.json())
                .then(payload => updateSummary(`${payload.product.name}: ${payload.product.description}`));
        }

        function updateSummary(message) {
            const subtotal = state.cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
            const shipping = subtotal >= 75 ? 0 : (subtotal ? 9.99 : 0);
            const tax = subtotal * 0.0725;
            const total = subtotal + shipping + tax;
            document.getElementById('cartSummary').innerHTML = `
                <strong>Cart summary</strong>
                <div>${state.cart.length ? state.cart.map(item => `${item.name} x ${item.quantity}`).join('<br>') : 'Your cart is empty.'}</div>
                <div>Subtotal: ${money(subtotal)}</div>
                <div>Shipping: ${money(shipping)}</div>
                <div>Tax: ${money(tax)}</div>
                <div><strong>Total: ${money(total)}</strong></div>`;
            document.getElementById('message').textContent = message || '';
            renderStats({ catalogSize: state.products.length });
        }

        document.getElementById('search').addEventListener('input', renderCatalog);
        document.getElementById('category').addEventListener('change', renderCatalog);
        document.getElementById('refresh').addEventListener('click', () => {
            renderCatalog();
            updateSummary('Catalog refreshed.');
        });
        document.getElementById('checkout').addEventListener('click', () => {
            if (!state.cart.length) {
                updateSummary('Add a product before checking out.');
                return;
            }
            fetch('/api/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    customer: {
                        name: document.getElementById('name').value,
                        email: document.getElementById('email').value,
                        address: document.getElementById('address').value,
                    },
                    paymentMethod: document.getElementById('paymentMethod').value,
                    items: state.cart,
                }),
            }).then(response => response.json()).then(payload => {
                state.cart = [];
                saveCart();
                updateSummary(`Order ${payload.order.id} confirmed. Tracking ${payload.fulfillment.tracking}.`);
            });
        });

        fetch('/api/meta').then(response => response.json()).then(payload => {
            renderStats(payload);
            renderCategories(payload.categories || []);
            renderCatalog();
            updateSummary();
        });
    </script>
</body>
</html>
                """
        )


if __name__ == "__main__":
        app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
