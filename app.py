from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Generator

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from jinja2 import DictLoader

STORE_NAME = "Green Basket Grocery"
STORE_ADDRESS = "123 Market Street"
CURRENCY = "₹"
TAX_RATE = 5.0
DISCOUNT_TIERS = [(2000, 15), (1000, 10), (500, 5)]

app = Flask(__name__)
app.secret_key = "replace-this-with-a-random-secret-key"
app.config["DATABASE"] = str(Path(__file__).with_name("grocery.db"))

SAMPLE_PRODUCTS = [
    ("Rice", 60.00, 100, "kg"),
    ("Flour", 45.00, 80, "kg"),
    ("Sugar", 42.00, 75, "kg"),
    ("Milk", 30.00, 60, "ltr"),
    ("Eggs", 7.00, 120, "pc"),
    ("Tomato", 35.00, 50, "kg"),
    ("Potato", 28.00, 90, "kg"),
    ("Onion", 32.00, 70, "kg"),
    ("Oil", 150.00, 40, "ltr"),
    ("Tea", 220.00, 25, "kg"),
    ("Bread", 40.00, 35, "pc"),
    ("Salt", 20.00, 45, "kg"),
]

TEMPLATES = {
    "base.html": """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}{{ store_name }}{% endblock %}</title>
  <style>
    :root { --green:#176b43; --green-dark:#105235; --green-light:#eaf5ee; --ink:#203129; --muted:#68776e; --border:#dce7df; --danger:#b42318; --surface:#fff; --bg:#f4f8f5; }
    * { box-sizing:border-box; }
    body { margin:0; color:var(--ink); background:var(--bg); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
    nav { background:var(--green); color:white; padding:0 24px; }
    .nav-inner { max-width:1200px; min-height:60px; margin:auto; display:flex; align-items:center; gap:24px; }
    .brand { margin-right:auto; color:white; font-weight:750; text-decoration:none; font-size:18px; }
    nav a:not(.brand) { color:#e9f7ed; text-decoration:none; font-weight:600; }
    nav a:hover { color:white; text-decoration:underline; }
    main { max-width:1200px; margin:28px auto; padding:0 20px 40px; }
    h1 { margin:0 0 20px; font-size:28px; line-height:1.2; }
    h2 { font-size:19px; margin:0 0 14px; }
    .card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px; box-shadow:0 3px 12px #183d2710; }
    .grid { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:20px; align-items:start; }
    .stack { display:grid; gap:20px; }
    label { display:block; font-weight:650; margin-bottom:6px; }
    input, button { font:inherit; }
    input[type="text"], input[type="number"], input[type="search"] { width:100%; padding:9px 11px; border:1px solid #cbd8ce; border-radius:7px; color:var(--ink); background:white; }
    input:focus { outline:2px solid #9dd0ad; border-color:var(--green); }
    .field { margin-bottom:15px; }
    .button { display:inline-flex; align-items:center; justify-content:center; border:0; border-radius:7px; background:var(--green); color:white; font-weight:700; padding:9px 14px; text-decoration:none; cursor:pointer; }
    .button:hover { background:var(--green-dark); }
    .button.secondary { background:#edf3ef; color:var(--ink); border:1px solid var(--border); }
    .button.danger { background:#fff0ef; color:var(--danger); border:1px solid #f1c6c2; }
    .button.small { padding:6px 10px; font-size:13px; }
    .button:disabled { opacity:.55; cursor:not-allowed; }
    .actions { display:flex; gap:9px; flex-wrap:wrap; align-items:center; }
    .table-wrap { overflow-x:auto; }
    table { width:100%; border-collapse:collapse; }
    th, td { text-align:left; padding:10px 9px; border-bottom:1px solid var(--border); vertical-align:middle; }
    th { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
    td.numeric, th.numeric { text-align:right; white-space:nowrap; }
    .muted { color:var(--muted); }
    .price { font-weight:700; white-space:nowrap; }
    .product-list { max-height:590px; overflow:auto; }
    .product-row { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 0; border-bottom:1px solid var(--border); }
    .product-row:last-child { border-bottom:0; }
    .product-detail { min-width:0; }
    .product-name { font-weight:700; }
    .product-meta { color:var(--muted); font-size:13px; }
    .qty-input { width:82px !important; padding:6px 7px !important; }
    .totals { width:min(100%,380px); margin:14px 0 0 auto; }
    .total-line { display:flex; justify-content:space-between; padding:5px 0; gap:16px; }
    .total-line.grand { border-top:2px solid var(--border); margin-top:5px; padding-top:11px; font-weight:800; font-size:19px; }
    .hint { min-height:24px; margin-top:8px; color:var(--green-dark); font-size:13px; }
    .flash { padding:11px 14px; border-radius:8px; margin-bottom:14px; background:#eaf5ee; border:1px solid #c6e2ce; }
    .flash.error { background:#fff0ef; border-color:#f1c6c2; color:#8e1b13; }
    .summary { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:18px; }
    .summary .card { min-width:190px; }
    .summary-value { color:var(--green-dark); font-size:23px; font-weight:800; }
    .low-stock { color:var(--danger); font-weight:750; }
    .inline-form { display:flex; gap:8px; align-items:center; }
    .inline-form input { min-width:75px; }
    .empty { padding:20px 0; text-align:center; color:var(--muted); }
    @media (max-width:760px) {
      .nav-inner { padding:12px 0; gap:13px; flex-wrap:wrap; }
      .brand { flex-basis:100%; }
      main { margin-top:20px; padding-left:14px; padding-right:14px; }
      .grid { grid-template-columns:1fr; }
      h1 { font-size:24px; }
      .card { padding:16px; }
    }
    @media print {
      nav, .no-print, .flash { display:none !important; }
      body { background:white; }
      main { max-width:none; margin:0; padding:0; }
      .card { border:0; box-shadow:none; padding:0; }
    }
  </style>
  {% block head %}{% endblock %}
</head>
<body>
  <nav class="no-print"><div class="nav-inner">
    <a class="brand" href="{{ url_for('index') }}">{{ store_name }}</a>
    <a href="{{ url_for('index') }}">New Bill</a>
    <a href="{{ url_for('products') }}">Products</a>
    <a href="{{ url_for('bills') }}">Bill History</a>
  </div></nav>
  <main>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}<div class="flash {{ 'error' if category == 'error' else '' }}">{{ message }}</div>{% endfor %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>
  {% block scripts %}{% endblock %}
</body>
</html>
""",
    "billing.html": """
{% extends "base.html" %}
{% block title %}New Bill · {{ store_name }}{% endblock %}
{% block content %}
<h1>New Bill</h1>
<div class="grid">
  <section class="card">
    <h2>Products</h2>
    <div class="field"><input id="product-search" type="search" placeholder="Search products..." aria-label="Search products"></div>
    <div id="product-list" class="product-list">
      {% for product in products %}
      <div class="product-row" data-search="{{ product.name|lower }}">
        <div class="product-detail">
          <div class="product-name">{{ product.name }}</div>
          <div class="product-meta">{{ currency }}{{ '%.2f'|format(product.price) }} / {{ product.unit }} · {{ '%g'|format(product.stock) }} in stock</div>
        </div>
        <button class="button small add-product" type="button" data-id="{{ product.id }}">Add</button>
      </div>
      {% else %}<div class="empty">No products are currently in stock.</div>{% endfor %}
    </div>
  </section>
  <section class="card">
    <h2>Cart</h2>
    <div class="field"><label for="customer">Customer name <span class="muted">(optional)</span></label><input id="customer" type="text" maxlength="120" placeholder="Walk-in customer"></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Item</th><th>Qty</th><th class="numeric">Amount</th><th></th></tr></thead>
        <tbody id="cart-body"><tr><td colspan="4" class="empty">Your cart is empty.</td></tr></tbody>
      </table>
    </div>
    <div class="totals">
      <div class="total-line"><span>Subtotal</span><strong id="subtotal">{{ currency }}0.00</strong></div>
      <div class="total-line"><span>Discount (<span id="discount-pct">0</span>%)</span><strong id="discount">{{ currency }}0.00</strong></div>
      <div class="total-line"><span>Tax ({{ '%.2f'|format(tax_rate) }}%)</span><strong id="tax">{{ currency }}0.00</strong></div>
      <div class="total-line grand"><span>Total</span><span id="total">{{ currency }}0.00</span></div>
      <div id="discount-hint" class="hint" aria-live="polite">Add {{ currency }}500.00 more to get 5% off</div>
    </div>
    <div class="actions" style="margin-top:18px">
      <button id="clear-cart" class="button secondary" type="button">Clear</button>
      <button id="generate-bill" class="button" type="button" disabled>Generate Bill</button>
    </div>
    <div id="cart-error" class="flash error" role="alert" hidden style="margin-top:14px;margin-bottom:0"></div>
  </section>
</div>
{% endblock %}
{% block scripts %}
<script>
(() => {
  const products = {{ products|tojson }};
  const tiers = {{ discount_tiers|tojson }};
  const currency = {{ currency|tojson }};
  const taxRate = {{ tax_rate|tojson }};
  const cart = new Map();
  const body = document.getElementById("cart-body");
  const errorBox = document.getElementById("cart-error");

  const roundMoney = value => Math.round((value + Number.EPSILON) * 100) / 100;
  const money = value => currency + roundMoney(value).toFixed(2);
  const discountFor = subtotal => tiers.find(([minimum]) => subtotal >= minimum)?.[1] || 0;

  function updateTotals() {
    let subtotal = 0;
    for (const item of cart.values()) subtotal += roundMoney(item.product.price * item.qty);
    subtotal = roundMoney(subtotal);
    const pct = discountFor(subtotal);
    const discount = roundMoney(subtotal * pct / 100);
    const taxable = roundMoney(subtotal - discount);
    const tax = roundMoney(taxable * taxRate / 100);
    document.getElementById("subtotal").textContent = money(subtotal);
    document.getElementById("discount-pct").textContent = pct;
    document.getElementById("discount").textContent = money(discount);
    document.getElementById("tax").textContent = money(tax);
    document.getElementById("total").textContent = money(taxable + tax);
    document.getElementById("generate-bill").disabled = cart.size === 0;

    const next = tiers.slice().reverse().find(([minimum]) => subtotal < minimum);
    document.getElementById("discount-hint").textContent = next
      ? `Add ${money(next[0] - subtotal)} more to get ${next[1]}% off`
      : "Maximum discount applied";
  }

  function renderCart() {
    body.replaceChildren();
    if (cart.size === 0) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 4;
      cell.className = "empty";
      cell.textContent = "Your cart is empty.";
      row.append(cell);
      body.append(row);
    } else {
      for (const [id, item] of cart) {
        const row = document.createElement("tr");
        const name = document.createElement("td");
        name.textContent = item.product.name;
        const quantityCell = document.createElement("td");
        const quantity = document.createElement("input");
        quantity.type = "number";
        quantity.min = "0.01";
        quantity.step = "any";
        quantity.max = String(item.product.stock);
        quantity.value = String(item.qty);
        quantity.className = "qty-input";
        quantity.setAttribute("aria-label", `Quantity of ${item.product.name}`);
        quantity.addEventListener("input", () => {
          const value = Number(quantity.value);
          if (Number.isFinite(value) && value > 0) {
            item.qty = value;
            amount.textContent = money(item.product.price * value);
            updateTotals();
          }
        });
        quantityCell.append(quantity);
        const amount = document.createElement("td");
        amount.className = "numeric";
        amount.textContent = money(item.product.price * item.qty);
        const action = document.createElement("td");
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "button danger small";
        remove.textContent = "Remove";
        remove.setAttribute("aria-label", `Remove ${item.product.name}`);
        remove.addEventListener("click", () => { cart.delete(id); renderCart(); });
        action.append(remove);
        row.append(name, quantityCell, amount, action);
        body.append(row);
      }
    }
    updateTotals();
  }

  document.querySelectorAll(".add-product").forEach(button => {
    button.addEventListener("click", () => {
      const product = products.find(item => item.id === Number(button.dataset.id));
      if (!product) return;
      const current = cart.get(product.id);
      if (current) current.qty += 1;
      else cart.set(product.id, {product, qty: 1});
      errorBox.hidden = true;
      renderCart();
    });
  });

  document.getElementById("product-search").addEventListener("input", event => {
    const term = event.target.value.trim().toLowerCase();
    document.querySelectorAll(".product-row").forEach(row => {
      row.hidden = !row.dataset.search.includes(term);
    });
  });

  document.getElementById("clear-cart").addEventListener("click", () => {
    cart.clear();
    errorBox.hidden = true;
    renderCart();
  });

  document.getElementById("generate-bill").addEventListener("click", async event => {
    const button = event.currentTarget;
    button.disabled = true;
    errorBox.hidden = true;
    try {
      const response = await fetch({{ url_for('api_create_bill')|tojson }}, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          customer: document.getElementById("customer").value,
          items: Array.from(cart, ([product_id, item]) => ({product_id, qty: item.qty}))
        })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not create bill.");
      window.location.href = result.redirect;
    } catch (error) {
      errorBox.textContent = error.message || "Could not create bill. Please try again.";
      errorBox.hidden = false;
      button.disabled = cart.size === 0;
    }
  });

  renderCart();
})();
</script>
{% endblock %}
""",
    "invoice.html": """
{% extends "base.html" %}
{% block title %}Invoice {{ '%06d'|format(bill.id) }} · {{ store_name }}{% endblock %}
{% block content %}
<div class="actions no-print" style="justify-content:flex-end;margin-bottom:16px"><button class="button" onclick="window.print()">Print Invoice</button></div>
<section class="card invoice">
  <header style="text-align:center;border-bottom:1px solid var(--border);padding-bottom:16px;margin-bottom:18px">
    <h1 style="margin-bottom:5px">{{ store_name }}</h1>
    <div class="muted">{{ store_address }}</div>
    <h2 style="margin:15px 0 0">INVOICE #{{ '%06d'|format(bill.id) }}</h2>
  </header>
  <div style="display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:18px">
    <div><strong>Date:</strong> {{ bill.created }}<br><strong>Customer:</strong> {{ bill.customer or 'Walk-in customer' }}</div>
    <div><strong>Invoice:</strong> #{{ '%06d'|format(bill.id) }}</div>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Item</th><th class="numeric">Price</th><th class="numeric">Qty</th><th>Unit</th><th class="numeric">Amount</th></tr></thead>
      <tbody>{% for item in items %}
      <tr><td>{{ item.name }}</td><td class="numeric">{{ currency }}{{ '%.2f'|format(item.price) }}</td><td class="numeric">{{ item.qty }}</td><td>{{ item.unit }}</td><td class="numeric">{{ currency }}{{ '%.2f'|format(item.line_total) }}</td></tr>
      {% endfor %}</tbody>
    </table>
  </div>
  <div class="totals">
    <div class="total-line"><span>Subtotal</span><strong>{{ currency }}{{ '%.2f'|format(bill.subtotal) }}</strong></div>
    <div class="total-line"><span>Discount ({{ '%.0f'|format(bill.discount_pct) }}%)</span><strong>-{{ currency }}{{ '%.2f'|format(bill.discount) }}</strong></div>
    <div class="total-line"><span>Tax ({{ '%.2f'|format(tax_rate) }}%)</span><strong>{{ currency }}{{ '%.2f'|format(bill.tax) }}</strong></div>
    <div class="total-line grand"><span>Total</span><span>{{ currency }}{{ '%.2f'|format(bill.total) }}</span></div>
  </div>
  <p style="text-align:center;margin:35px 0 5px;font-weight:700">Thank you for shopping with us!</p>
</section>
{% endblock %}
""",
    "bills.html": """
{% extends "base.html" %}
{% block title %}Bill History · {{ store_name }}{% endblock %}
{% block content %}
<h1>Bill History</h1>
<div class="summary">
  <div class="card"><div class="muted">Bills today</div><div class="summary-value">{{ today_count }}</div></div>
  <div class="card"><div class="muted">Sales today</div><div class="summary-value">{{ currency }}{{ '%.2f'|format(today_sales) }}</div></div>
</div>
<section class="card">
  <h2>Latest bills <span class="muted">(up to 200)</span></h2>
  <div class="table-wrap"><table>
    <thead><tr><th>Invoice</th><th>Date</th><th>Customer</th><th class="numeric">Subtotal</th><th class="numeric">Discount</th><th class="numeric">Total</th><th></th></tr></thead>
    <tbody>
    {% for bill in bills %}
      <tr><td>#{{ '%06d'|format(bill.id) }}</td><td>{{ bill.created }}</td><td>{{ bill.customer or 'Walk-in customer' }}</td><td class="numeric">{{ currency }}{{ '%.2f'|format(bill.subtotal) }}</td><td class="numeric">{{ '%.0f'|format(bill.discount_pct) }}% · {{ currency }}{{ '%.2f'|format(bill.discount) }}</td><td class="numeric"><strong>{{ currency }}{{ '%.2f'|format(bill.total) }}</strong></td><td><a class="button small" href="{{ url_for('invoice', bill_id=bill.id) }}">View</a></td></tr>
    {% else %}<tr><td colspan="7" class="empty">No bills have been created yet.</td></tr>{% endfor %}
    </tbody>
  </table></div>
</section>
{% endblock %}
""",
    "products.html": """
{% extends "base.html" %}
{% block title %}Products · {{ store_name }}{% endblock %}
{% block content %}
<h1>Product Inventory</h1>
<section class="card" style="margin-bottom:20px">
  <h2>Add product</h2>
  <form method="post" action="{{ url_for('add_product') }}" class="grid" style="grid-template-columns:2fr 1fr 1fr 1fr auto;gap:12px;align-items:end">
    <div class="field" style="margin:0"><label for="new-name">Name</label><input id="new-name" name="name" required maxlength="100"></div>
    <div class="field" style="margin:0"><label for="new-price">Price ({{ currency }})</label><input id="new-price" type="number" name="price" min="0" step="0.01" required></div>
    <div class="field" style="margin:0"><label for="new-stock">Stock</label><input id="new-stock" type="number" name="stock" min="0" step="any" required></div>
    <div class="field" style="margin:0"><label for="new-unit">Unit</label><input id="new-unit" name="unit" required maxlength="20" placeholder="kg"></div>
    <button class="button" type="submit">Add</button>
  </form>
</section>
<section class="card">
  <h2>Current products</h2>
  <div class="table-wrap"><table>
    <thead><tr><th>Name</th><th class="numeric">Price ({{ currency }})</th><th class="numeric">Stock</th><th>Unit</th><th>Actions</th></tr></thead>
    <tbody>
    {% for product in products %}
      <tr>
        <td><form id="edit-product-{{ product.id }}" method="post" action="{{ url_for('update_product', product_id=product.id) }}"></form><input form="edit-product-{{ product.id }}" type="text" name="name" value="{{ product.name }}" required maxlength="100" aria-label="Product name"></td>
        <td><input form="edit-product-{{ product.id }}" type="number" name="price" value="{{ '%.2f'|format(product.price) }}" min="0" step="0.01" required aria-label="Price"></td>
        <td><input form="edit-product-{{ product.id }}" type="number" name="stock" value="{{ '%g'|format(product.stock) }}" min="0" step="any" required aria-label="Stock" class="{{ 'low-stock' if product.stock < 10 else '' }}"></td>
        <td><input form="edit-product-{{ product.id }}" type="text" name="unit" value="{{ product.unit }}" required maxlength="20" aria-label="Unit"></td>
        <td><div class="actions"><button class="button small" type="submit" form="edit-product-{{ product.id }}">Save</button><form method="post" action="{{ url_for('delete_product', product_id=product.id) }}" onsubmit="return confirm('Delete {{ product.name|e }} from inventory?')"><button class="button danger small" type="submit">Delete</button></form></div></td>
      </tr>
    {% else %}<tr><td colspan="5" class="empty">No products found.</td></tr>{% endfor %}
    </tbody>
  </table></div>
</section>
{% endblock %}
""",
}

app.jinja_loader = DictLoader(TEMPLATES)


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    connection = sqlite3.connect(app.config["DATABASE"], timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price REAL NOT NULL,
                stock REAL NOT NULL,
                unit TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created TEXT NOT NULL,
                customer TEXT NOT NULL DEFAULT '',
                subtotal REAL NOT NULL,
                discount REAL NOT NULL,
                discount_pct REAL NOT NULL DEFAULT 0,
                tax REAL NOT NULL,
                total REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bill_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL REFERENCES bills(id),
                name TEXT NOT NULL,
                price REAL NOT NULL,
                qty REAL NOT NULL,
                unit TEXT NOT NULL,
                line_total REAL NOT NULL
            );
            """
        )
        columns = {row["name"] for row in db.execute("PRAGMA table_info(bills)")}
        if "discount_pct" not in columns:
            db.execute("ALTER TABLE bills ADD COLUMN discount_pct REAL NOT NULL DEFAULT 0")
        product_count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if product_count == 0:
            db.executemany(
                "INSERT INTO products (name, price, stock, unit) VALUES (?, ?, ?, ?)",
                SAMPLE_PRODUCTS,
            )


def decimal_value(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label} must be a valid number.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a valid number.") from None
    if not number.is_finite():
        raise ValueError(f"{label} must be a valid number.")
    return number


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_totals(subtotal: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    discount_pct = Decimal("0")
    for minimum, percentage in DISCOUNT_TIERS:
        if subtotal >= Decimal(str(minimum)):
            discount_pct = Decimal(str(percentage))
            break
    discount = money(subtotal * discount_pct / Decimal("100"))
    tax = money((subtotal - discount) * Decimal(str(TAX_RATE)) / Decimal("100"))
    total = money(subtotal - discount + tax)
    return discount, discount_pct, tax, total


def template_context() -> dict[str, Any]:
    return {
        "store_name": STORE_NAME,
        "store_address": STORE_ADDRESS,
        "currency": CURRENCY,
        "tax_rate": TAX_RATE,
        "discount_tiers": DISCOUNT_TIERS,
    }


@app.get("/")
def index():
    with get_db() as db:
        products = db.execute(
            "SELECT id, name, price, stock, unit FROM products WHERE stock > 0 ORDER BY name"
        ).fetchall()
    return render_template(
        "billing.html",
        products=[dict(product) for product in products],
        **template_context(),
    )


@app.post("/api/bills")
def api_create_bill():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Request body must be a JSON object."), 400
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return jsonify(error="Add at least one product to the cart."), 400
    customer = payload.get("customer", "")
    if not isinstance(customer, str):
        return jsonify(error="Customer name must be text."), 400
    customer = customer.strip()[:120]

    try:
        requested: dict[int, Decimal] = {}
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Each cart item must be an object.")
            product_id = item.get("product_id")
            if isinstance(product_id, bool):
                raise ValueError("Each cart item must have a valid product.")
            try:
                product_id = int(product_id)
            except (TypeError, ValueError):
                raise ValueError("Each cart item must have a valid product.") from None
            qty = decimal_value(item.get("qty"), "Quantity")
            if qty <= 0:
                raise ValueError("Quantity must be greater than zero.")
            requested[product_id] = requested.get(product_id, Decimal("0")) + qty

        with get_db() as db:
            db.execute("BEGIN IMMEDIATE")
            ids = list(requested)
            placeholders = ",".join("?" for _ in ids)
            rows = db.execute(
                f"SELECT id, name, price, stock, unit FROM products WHERE id IN ({placeholders})",
                ids,
            ).fetchall()
            products_by_id = {row["id"]: row for row in rows}
            missing = [product_id for product_id in requested if product_id not in products_by_id]
            if missing:
                raise ValueError("One or more selected products no longer exist.")

            line_items: list[dict[str, Any]] = []
            subtotal = Decimal("0")
            for product_id, qty in requested.items():
                product = products_by_id[product_id]
                if qty > Decimal(str(product["stock"])):
                    raise ValueError(
                        f"Only {product['stock']:g} {product['unit']} of {product['name']} are available."
                    )
                price = money(Decimal(str(product["price"])))
                line_total = money(price * qty)
                subtotal += line_total
                line_items.append(
                    {
                        "id": product_id,
                        "name": product["name"],
                        "price": price,
                        "qty": qty,
                        "unit": product["unit"],
                        "line_total": line_total,
                    }
                )

            subtotal = money(subtotal)
            discount, discount_pct, tax, total = calculate_totals(subtotal)
            cursor = db.execute(
                """INSERT INTO bills
                   (created, customer, subtotal, discount, discount_pct, tax, total)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    customer,
                    float(subtotal),
                    float(discount),
                    float(discount_pct),
                    float(tax),
                    float(total),
                ),
            )
            bill_id = cursor.lastrowid
            for item in line_items:
                db.execute(
                    """INSERT INTO bill_items (bill_id, name, price, qty, unit, line_total)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        bill_id,
                        item["name"],
                        float(item["price"]),
                        float(item["qty"]),
                        item["unit"],
                        float(item["line_total"]),
                    ),
                )
                db.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (float(item["qty"]), item["id"]),
                )
    except ValueError as error:
        return jsonify(error=str(error)), 400
    except sqlite3.Error:
        app.logger.exception("Failed to save bill")
        return jsonify(error="The bill could not be saved. Please try again."), 500

    return jsonify(redirect=url_for("invoice", bill_id=bill_id)), 201


@app.get("/bill/<int:bill_id>")
def invoice(bill_id: int):
    with get_db() as db:
        bill = db.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
        if bill is None:
            return "Bill not found", 404
        items = db.execute(
            "SELECT name, price, qty, unit, line_total FROM bill_items WHERE bill_id = ? ORDER BY id",
            (bill_id,),
        ).fetchall()
    return render_template("invoice.html", bill=bill, items=items, **template_context())


@app.get("/bills")
def bills():
    today = date.today().isoformat()
    with get_db() as db:
        recent = db.execute(
            "SELECT * FROM bills ORDER BY id DESC LIMIT 200"
        ).fetchall()
        summary = db.execute(
            """SELECT COUNT(*) AS count, COALESCE(SUM(total), 0) AS sales
               FROM bills WHERE substr(created, 1, 10) = ?""",
            (today,),
        ).fetchone()
    return render_template(
        "bills.html",
        bills=recent,
        today_count=summary["count"],
        today_sales=summary["sales"],
        **template_context(),
    )


def product_form_values(form: Any) -> tuple[str, float, int, str]:
    name = form.get("name", "").strip()
    unit = form.get("unit", "").strip()
    if not name or len(name) > 100:
        raise ValueError("Product name is required and must be 100 characters or fewer.")
    if not unit or len(unit) > 20:
        raise ValueError("Unit is required and must be 20 characters or fewer.")
    price = decimal_value(form.get("price"), "Price")
    stock = decimal_value(form.get("stock"), "Stock")
    if price < 0:
        raise ValueError("Price cannot be negative.")
    if stock < 0:
        raise ValueError("Stock must be greater than or equal to zero.")
    return name, float(money(price)), float(stock), unit


@app.get("/products")
def products():
    with get_db() as db:
        inventory = db.execute(
            "SELECT id, name, price, stock, unit FROM products ORDER BY name"
        ).fetchall()
    return render_template("products.html", products=inventory, **template_context())


@app.post("/products/add")
def add_product():
    try:
        values = product_form_values(request.form)
        with get_db() as db:
            db.execute(
                "INSERT INTO products (name, price, stock, unit) VALUES (?, ?, ?, ?)",
                values,
            )
        flash(f"{values[0]} added to inventory.")
    except ValueError as error:
        flash(str(error), "error")
    except sqlite3.IntegrityError:
        flash("A product with that name already exists.", "error")
    return redirect(url_for("products"))


@app.post("/products/<int:product_id>/update")
def update_product(product_id: int):
    try:
        values = product_form_values(request.form)
        with get_db() as db:
            cursor = db.execute(
                "UPDATE products SET name = ?, price = ?, stock = ?, unit = ? WHERE id = ?",
                (*values, product_id),
            )
            if cursor.rowcount == 0:
                flash("Product not found.", "error")
            else:
                flash(f"{values[0]} updated.")
    except ValueError as error:
        flash(str(error), "error")
    except sqlite3.IntegrityError:
        flash("A product with that name already exists.", "error")
    return redirect(url_for("products"))


@app.post("/products/<int:product_id>/delete")
def delete_product(product_id: int):
    with get_db() as db:
        cursor = db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    flash("Product deleted." if cursor.rowcount else "Product not found.", "error" if not cursor.rowcount else "message")
    return redirect(url_for("products"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
