import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.request import Request, urlopen

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080").rstrip("/")
SERVICE_NAME = os.getenv("SERVICE_NAME", "frontend")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "5"))
PORT = int(os.getenv("PORT", "3000"))

HOME_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Northstar Market</title>
  <style>
    :root { --bg:#f4eee6; --panel:rgba(255,250,245,.84); --text:#201814; --muted:#6f5d52; --accent:#9b5c35; --accent-2:#29435c; --border:rgba(32,24,20,.12); --shadow:0 24px 60px rgba(61,39,22,.12); }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; font-family:"Avenir Next","Segoe UI","Helvetica Neue",sans-serif; background: radial-gradient(circle at top left,#fff7ea 0,transparent 28%), radial-gradient(circle at 90% 10%, rgba(155,92,53,.18) 0, transparent 26%), linear-gradient(180deg,#faf4eb,var(--bg)); color:var(--text); }
    .shell { max-width:1380px; margin:0 auto; padding:24px; }
    .topbar { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:24px; }
    .brand h1 { margin:0; font-size:clamp(2rem,4vw,3.8rem); letter-spacing:-.06em; }
    .brand p { margin:6px 0 0; color:var(--muted); max-width:62ch; line-height:1.5; }
    .pill { border:1px solid var(--border); background:rgba(255,255,255,.6); border-radius:999px; padding:10px 14px; color:var(--accent-2); box-shadow:var(--shadow); white-space:nowrap; }
    .hero { display:grid; grid-template-columns:1.25fr .75fr; gap:18px; align-items:stretch; margin-bottom:20px; }
    .hero-card,.panel,.checkout,.metrics { border:1px solid var(--border); border-radius:28px; background:var(--panel); backdrop-filter:blur(10px); box-shadow:var(--shadow); }
    .hero-card { padding:28px; min-height:280px; }
    .hero-visual { border-radius:24px; min-height:180px; background:linear-gradient(145deg, rgba(41,67,92,.95), rgba(155,92,53,.88)); position:relative; overflow:hidden; }
    .hero-visual::before,.hero-visual::after { content:""; position:absolute; width:220px; height:220px; border-radius:50%; background:rgba(255,255,255,.12); filter:blur(8px); }
    .hero-visual::before { top:-40px; right:-20px; }
    .hero-visual::after { bottom:-80px; left:-40px; }
    .hero-badge { position:absolute; left:18px; top:18px; padding:10px 12px; border-radius:999px; background:rgba(255,255,255,.16); color:white; border:1px solid rgba(255,255,255,.18); }
    .hero-copy { position:absolute; left:18px; bottom:18px; right:18px; color:white; }
    .hero-copy strong { display:block; font-size:28px; margin-bottom:8px; }
    .hero-copy span { color:rgba(255,255,255,.86); }
    .metrics { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; padding:18px; }
    .metric { border-radius:20px; background:rgba(255,255,255,.56); border:1px solid rgba(32,24,20,.08); padding:16px; display:grid; gap:8px; }
    .metric strong { font-size:26px; letter-spacing:-.04em; }
    .metric span { color:var(--muted); font-size:13px; }
    .toolbar { display:grid; grid-template-columns:1.2fr .8fr .6fr auto; gap:12px; margin:18px 0; }
    .toolbar input,.toolbar select,.checkout input,.checkout select,.checkout textarea,.toolbar button,.checkout button { border-radius:16px; border:1px solid var(--border); padding:13px 14px; font:inherit; }
    .toolbar input,.toolbar select,.checkout input,.checkout select,.checkout textarea { background:rgba(255,255,255,.78); color:var(--text); }
    .toolbar button,.checkout button { background:var(--text); color:white; cursor:pointer; }
    .toolbar button:hover,.checkout button:hover { opacity:.92; }
    .layout { display:grid; grid-template-columns:minmax(0,1.15fr) minmax(320px,.85fr); gap:18px; }
    .panel { padding:18px; }
    .section-title { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:14px; }
    .section-title h2 { margin:0; font-size:20px; }
    .section-title span { color:var(--muted); font-size:13px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; }
    .card { border-radius:22px; border:1px solid rgba(32,24,20,.08); background:linear-gradient(180deg,rgba(255,255,255,.86),rgba(255,255,255,.68)); overflow:hidden; display:grid; min-height:320px; }
    .swatch { min-height:120px; padding:16px; color:white; display:flex; align-items:flex-end; background:linear-gradient(145deg,var(--accent),rgba(41,67,92,.8)); font-weight:700; letter-spacing:.03em; }
    .card-body { padding:16px; display:grid; gap:10px; }
    .meta { display:flex; justify-content:space-between; gap:12px; color:var(--muted); font-size:13px; }
    .card-body p { margin:0; color:var(--muted); line-height:1.5; }
    .price { font-size:24px; font-weight:700; letter-spacing:-.04em; }
    .actions { display:flex; gap:10px; }
    .actions button { flex:1; }
    .checkout { padding:18px; display:grid; gap:14px; position:sticky; top:16px; }
    .cart-list { display:grid; gap:10px; }
    .cart-line { display:flex; justify-content:space-between; gap:12px; align-items:start; background:rgba(255,255,255,.7); border:1px solid rgba(32,24,20,.08); border-radius:18px; padding:12px 14px; }
    .cart-line strong { display:block; }
    .cart-line span { color:var(--muted); font-size:13px; }
    .summary { display:grid; gap:8px; color:var(--muted); }
    .summary strong { color:var(--text); }
    .checkout-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
    .checkout-grid .wide { grid-column:1 / -1; }
    #message { min-height:24px; color:var(--accent); font-weight:600; }
    @media (max-width:1100px) { .hero,.layout,.toolbar,.checkout-grid { grid-template-columns:1fr; } .checkout { position:static; } }
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div class="brand">
        <h1>Northstar Market</h1>
        <p>A polished demo storefront backed by live API calls. Browse products, add to cart, and place a checkout order without leaving the page.</p>
      </div>
      <div class="pill" id="backendStatus">Backend: checking...</div>
    </div>

    <div class="hero">
      <div class="hero-card">
        <div class="hero-visual">
          <div class="hero-badge">Curated launch collection</div>
          <div class="hero-copy">
            <strong>Essential goods, premium presentation.</strong>
            <span>Search, sort, and shop a catalog that feels like a real retail experience instead of a placeholder demo.</span>
          </div>
        </div>
      </div>
      <div class="metrics" id="metrics"></div>
    </div>

    <div class="toolbar">
      <input id="search" placeholder="Search products, badges, or categories">
      <select id="category"></select>
      <select id="sort">
        <option value="featured">Featured</option>
        <option value="rating">Top rated</option>
        <option value="price-asc">Price: low to high</option>
        <option value="price-desc">Price: high to low</option>
      </select>
      <button id="refresh">Refresh</button>
    </div>

    <div class="layout">
      <div class="panel">
        <div class="section-title"><h2>Catalog</h2><span id="catalogHint">Loading products...</span></div>
        <div class="grid" id="catalog"></div>
      </div>

      <aside class="checkout">
        <div class="section-title"><h2>Checkout</h2><span id="cartCount">0 items</span></div>
        <div class="cart-list" id="cartList"></div>
        <div class="summary" id="cartSummary">Add items to calculate totals.</div>
        <div class="checkout-grid">
          <input id="name" placeholder="Full name" value="Avery Smith">
          <input id="email" placeholder="Email" value="avery@example.com">
          <textarea id="address" class="wide" rows="3" placeholder="Shipping address">88 Market Street, Austin, TX</textarea>
          <select id="paymentMethod" class="wide"><option value="card">Card</option><option value="wallet">Wallet</option><option value="paypal">PayPal</option></select>
        </div>
        <button id="checkout">Place order</button>
        <div id="message"></div>
      </aside>
    </div>
  </div>

  <script>
    const state = { products: [], categories: [], cart: JSON.parse(localStorage.getItem('northstar-cart') || '[]') };
    function money(value) { return new Intl.NumberFormat('en-US', { style:'currency', currency:'USD' }).format(value || 0); }
    function saveCart() { localStorage.setItem('northstar-cart', JSON.stringify(state.cart)); }
    function setMessage(message) { document.getElementById('message').textContent = message || ''; }
    function getTotals() { const subtotal = state.cart.reduce((sum, item) => sum + item.price * item.quantity, 0); const discount = subtotal >= 100 ? subtotal * 0.08 : 0; const shipping = subtotal >= 75 ? 0 : (subtotal ? 9.99 : 0); const tax = (subtotal - discount) * 0.0725; return { subtotal, discount, shipping, tax, total: subtotal - discount + shipping + tax }; }
    function renderMetrics(meta = {}) { document.getElementById('metrics').innerHTML = `<div class="metric"><strong>${meta.catalogSize ?? 6}</strong><span>products in launch catalog</span></div><div class="metric"><strong>${state.cart.length}</strong><span>distinct cart items</span></div><div class="metric"><strong>${money(getTotals().total)}</strong><span>estimated order total</span></div><div class="metric"><strong>Live</strong><span>API-backed storefront</span></div>`; }
    function renderCategories() { const select = document.getElementById('category'); const current = select.value; select.innerHTML = '<option value="">All categories</option>' + state.categories.map(category => `<option value="${category.name}">${category.name}</option>`).join(''); select.value = current; }
    function renderCatalog() { const search = document.getElementById('search').value.trim(); const category = document.getElementById('category').value; const sort = document.getElementById('sort').value; const params = new URLSearchParams(); if (search) params.set('q', search); if (category) params.set('category', category); if (sort) params.set('sort', sort); document.getElementById('catalogHint').textContent = 'Searching...'; fetch(`/api/products?${params.toString()}`).then(response => response.json()).then(payload => { state.products = payload.products || []; document.getElementById('catalog').innerHTML = state.products.map(product => `<article class="card"><div class="swatch" style="--accent:${product.accent}">${product.badge}</div><div class="card-body"><div class="meta"><span>${product.category}</span><span>${product.rating} ★</span></div><strong>${product.name}</strong><p>${product.description}</p><div class="meta"><span>${product.stock} in stock</span><span>${product.sku}</span></div><div class="price">${money(product.price)}</div><div class="actions"><button onclick='addToCart("${product.sku}")'>Add to cart</button><button onclick='viewProduct("${product.sku}")'>View</button></div></div></article>`).join(''); document.getElementById('catalogHint').textContent = `${payload.count || 0} products found`; renderMetrics({ catalogSize: payload.count || state.products.length }); }).catch(() => { document.getElementById('catalogHint').textContent = 'Could not load catalog'; }); }
    function renderCart() { const cartList = document.getElementById('cartList'); document.getElementById('cartCount').textContent = `${state.cart.reduce((sum, item) => sum + item.quantity, 0)} items`; cartList.innerHTML = state.cart.length ? state.cart.map(item => `<div class="cart-line"><div><strong>${item.name}</strong><span>${item.quantity} × ${money(item.price)}</span></div><strong>${money(item.price * item.quantity)}</strong></div>`).join('') : '<div class="summary">Your cart is empty.</div>'; const totals = getTotals(); document.getElementById('cartSummary').innerHTML = `<strong>Subtotal: ${money(totals.subtotal)}</strong><span>Shipping: ${money(totals.shipping)}</span><span>Tax: ${money(totals.tax)}</span><span><strong>Total: ${money(totals.total)}</strong></span>`; renderMetrics({ catalogSize: state.products.length || 6 }); }
    function addToCart(sku) { const product = state.products.find(item => item.sku === sku); if (!product) return; const existing = state.cart.find(item => item.sku === sku); if (existing) { existing.quantity += 1; } else { state.cart.push({ sku: product.sku, name: product.name, price: product.price, quantity: 1 }); } saveCart(); renderCart(); setMessage(`${product.name} added to cart.`); }
    function viewProduct(sku) { fetch(`/api/products/${sku}`).then(response => response.json()).then(payload => { const product = payload.product || {}; setMessage(`${product.name}: ${product.description}`); }); }
    document.getElementById('search').addEventListener('input', renderCatalog); document.getElementById('category').addEventListener('change', renderCatalog); document.getElementById('sort').addEventListener('change', renderCatalog); document.getElementById('refresh').addEventListener('click', () => { renderCatalog(); renderCart(); setMessage('Catalog refreshed.'); });
    document.getElementById('checkout').addEventListener('click', () => { if (!state.cart.length) { setMessage('Add at least one product before checking out.'); return; } fetch('/api/checkout', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ customer:{ name: document.getElementById('name').value, email: document.getElementById('email').value }, shippingAddress: document.getElementById('address').value, paymentMethod: document.getElementById('paymentMethod').value, items: state.cart }) }).then(response => response.json().then(body => ({ ok: response.ok, status: response.status, body }))).then(result => { if (!result.ok) throw new Error(result.body.error || `Checkout failed (${result.status})`); state.cart = []; saveCart(); renderCart(); setMessage(`Order ${result.body.order.id} confirmed. Tracking ${result.body.fulfillment.tracking}.`); }).catch(error => setMessage(error.message)); });
    fetch('/api/meta').then(response => response.json()).then(payload => { state.categories = payload.categories || []; renderCategories(); renderMetrics(payload); }).catch(() => { document.getElementById('backendStatus').textContent = 'Backend: unavailable'; });
    fetch('/healthz').then(response => response.json()).then(payload => { document.getElementById('backendStatus').textContent = `Backend: ${payload.backend.status}`; }).catch(() => { document.getElementById('backendStatus').textContent = 'Backend: unavailable'; });
    renderCatalog(); renderCart();
  </script>
</body>
</html>
"""


def json_bytes(payload):
    return json.dumps(payload).encode("utf-8")


def send_json(handler, payload, status=200):
    data = json_bytes(payload)
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def send_html(handler, html):
    data = html.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def proxy_request(handler):
    body = None
    if handler.command in {"POST", "PUT", "PATCH", "DELETE"}:
        content_length = int(handler.headers.get("Content-Length", "0") or 0)
        body = handler.rfile.read(content_length) if content_length else None

    headers = {
        key: value
        for key, value in handler.headers.items()
        if key.lower() not in {"host", "content-length", "accept-encoding"}
    }

    request = Request(
        f"{BACKEND_URL}{handler.path}",
        data=body,
        headers=headers,
        method=handler.command,
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as upstream:
            content = upstream.read()
            content_type = upstream.headers.get("content-type", "application/json")
            handler.send_response(upstream.status)
            handler.send_header("Content-Type", content_type)
            handler.send_header("Content-Length", str(len(content)))
            handler.end_headers()
            handler.wfile.write(content)
    except URLError as exc:
        send_json(handler, {"error": "backend unavailable", "detail": str(exc), "backendUrl": BACKEND_URL}, 502)


class StorefrontHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            send_html(self, HOME_PAGE)
        elif path == "/healthz":
            backend_status = "unavailable"
            try:
                with urlopen(f"{BACKEND_URL}/healthz", timeout=REQUEST_TIMEOUT) as response:
                    backend_status = json.loads(response.read().decode("utf-8")).get("status", "ok")
            except URLError:
                pass
            send_json(self, {"service": SERVICE_NAME, "status": "ok", "backend": {"url": BACKEND_URL, "status": backend_status}})
        elif path.startswith("/api/"):
            proxy_request(self)
        else:
            send_json(self, {"error": "not found", "path": path}, 404)

    def do_POST(self):
        if self.path.startswith("/api/"):
            proxy_request(self)
        else:
            send_json(self, {"error": "method not allowed"}, 405)

    def do_PUT(self):
        self.do_POST()

    def do_PATCH(self):
        self.do_POST()

    def do_DELETE(self):
        self.do_POST()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.end_headers()


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), StorefrontHandler)
    print(f"{SERVICE_NAME} listening on :{PORT}, backend={BACKEND_URL}")
    server.serve_forever()


if __name__ == "__main__":
    main()
