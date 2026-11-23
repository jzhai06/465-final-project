"""Flask web interface for the Reselling Tracker SQLite database."""

import os
import sqlite3
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, render_template, request


CONDITIONS = ("New", "Excellent", "Good", "Fair", "Poor")

app = Flask(__name__)
app.config["DATABASE"] = Path(os.environ.get("RESELL_DATABASE", "resell.db"))


def get_db():
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def rows_json(rows):
    return [dict(row) for row in rows]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():
    with get_db() as connection:
        stats = dict(connection.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM item) AS inventory,
              (SELECT COUNT(*) FROM listing WHERE status = 'active') AS active_listings,
              (SELECT COUNT(*) FROM sale) AS sales,
              (SELECT COALESCE(ROUND(SUM(net_profit), 2), 0) FROM v_sale_profit) AS net_profit
            """
        ).fetchone())
        recent = rows_json(connection.execute(
            """
            SELECT s.sale_id, s.sale_date, i.title, b.brand_name,
                   s.sale_price, v.net_profit
            FROM sale s
            JOIN listing l ON l.listing_id = s.listing_id
            JOIN item i ON i.item_id = l.item_id
            JOIN brand b ON b.brand_id = i.brand_id
            JOIN v_sale_profit v ON v.sale_id = s.sale_id
            ORDER BY s.sale_date DESC, s.sale_id DESC
            LIMIT 6
            """
        ).fetchall())
    return jsonify({"stats": stats, "recent": recent})


@app.route("/api/items")
def items():
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    parameters = [query, query, query]
    status_sql = ""
    if status == "active":
        status_sql = "HAVING active_listings > 0"
    elif status == "unsold":
        status_sql = "HAVING active_listings = 0"

    with get_db() as connection:
        rows = connection.execute(
            f"""
            SELECT i.item_id, i.title, b.brand_name AS brand,
                   c.category_name AS category, i.condition,
                   i.purchase_cost, i.acquired_date,
                   COALESCE(SUM(l.status = 'active'), 0) AS active_listings
            FROM item i
            JOIN brand b ON b.brand_id = i.brand_id
            JOIN category c ON c.category_id = i.category_id
            LEFT JOIN listing l ON l.item_id = i.item_id
            WHERE (? = '' OR i.title LIKE '%' || ? || '%' OR b.brand_name LIKE '%' || ? || '%')
            GROUP BY i.item_id
            {status_sql}
            ORDER BY i.item_id DESC
            """,
            tuple(parameters),
        ).fetchall()
    return jsonify(rows_json(rows))


@app.route("/api/items/<int:item_id>")
def item_detail(item_id):
    with get_db() as connection:
        item = connection.execute(
            """
            SELECT i.*, b.brand_name AS brand, c.category_name AS category,
                   sl.location_name AS location
            FROM item i
            JOIN brand b ON b.brand_id = i.brand_id
            JOIN category c ON c.category_id = i.category_id
            LEFT JOIN sourcing_location sl ON sl.location_id = i.location_id
            WHERE i.item_id = ?
            """,
            (item_id,),
        ).fetchone()
        if item is None:
            return jsonify({"error": "Item not found"}), 404
        listings = rows_json(connection.execute(
            """
            SELECT l.listing_id, p.platform_name, l.list_price,
                   l.listed_date, l.ended_date, l.status
            FROM listing l
            JOIN platform p ON p.platform_id = l.platform_id
            WHERE l.item_id = ?
            ORDER BY l.listing_id DESC
            """,
            (item_id,),
        ).fetchall())
    return jsonify({"item": dict(item), "listings": listings})


@app.route("/api/options")
def options():
    with get_db() as connection:
        result = {
            "brands": rows_json(connection.execute("SELECT * FROM brand ORDER BY brand_name").fetchall()),
            "categories": rows_json(connection.execute("SELECT * FROM category ORDER BY category_name").fetchall()),
            "locations": rows_json(connection.execute("SELECT * FROM sourcing_location ORDER BY location_name").fetchall()),
            "platforms": rows_json(connection.execute("SELECT * FROM platform ORDER BY platform_name").fetchall()),
            "conditions": list(CONDITIONS),
        }
    return jsonify(result)


@app.route("/api/items", methods=["POST"])
def create_item():
    data = request.get_json(silent=True) or {}
    required = ("brand_id", "category_id", "title", "condition", "purchase_cost", "acquired_date")
    if any(str(data.get(field, "")).strip() == "" for field in required):
        return jsonify({"error": "All item fields are required"}), 400
    if data["condition"] not in CONDITIONS:
        return jsonify({"error": "Invalid condition"}), 400
    try:
        date.fromisoformat(data["acquired_date"])
        cost = float(data["purchase_cost"])
        if cost < 0:
            raise ValueError
        with get_db() as connection:
            cursor = connection.execute(
                """
                INSERT INTO item (brand_id, category_id, location_id, title, condition, purchase_cost, acquired_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (int(data["brand_id"]), int(data["category_id"]),
                 data.get("location_id") or None, data["title"].strip(),
                 data["condition"], cost, data["acquired_date"]),
            )
            connection.commit()
        return jsonify({"message": "Item added", "item_id": cursor.lastrowid}), 201
    except (ValueError, TypeError):
        return jsonify({"error": "Use a valid date, cost, and IDs"}), 400
    except sqlite3.IntegrityError:
        return jsonify({"error": "Invalid brand, category, location, or duplicate constraint"}), 400


@app.route("/api/listings", methods=["POST"])
def create_listing():
    data = request.get_json(silent=True) or {}
    try:
        price = float(data["list_price"])
        if price <= 0:
            raise ValueError
        date.fromisoformat(data["listed_date"])
        with get_db() as connection:
            cursor = connection.execute(
                """
                INSERT INTO listing (item_id, platform_id, list_price, listed_date)
                VALUES (?, ?, ?, ?)
                """,
                (int(data["item_id"]), int(data["platform_id"]), price, data["listed_date"]),
            )
            connection.commit()
        return jsonify({"message": "Listing added", "listing_id": cursor.lastrowid}), 201
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Provide valid IDs, a positive price, and YYYY-MM-DD date"}), 400
    except sqlite3.IntegrityError:
        return jsonify({"error": "Invalid item or platform"}), 400


@app.route("/api/listings/<int:listing_id>", methods=["PATCH"])
def update_listing(listing_id):
    data = request.get_json(silent=True) or {}
    try:
        price = float(data["list_price"])
        if price <= 0:
            raise ValueError
        with get_db() as connection:
            cursor = connection.execute(
                "UPDATE listing SET list_price = ? WHERE listing_id = ?",
                (price, listing_id),
            )
            connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Listing not found"}), 404
        return jsonify({"message": "Listing updated"})
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Price must be greater than zero"}), 400


@app.route("/api/sales", methods=["POST"])
def create_sale():
    data = request.get_json(silent=True) or {}
    try:
        listing_id = int(data["listing_id"])
        sale_date = data["sale_date"]
        sale_price = float(data["sale_price"])
        platform_fee = float(data["platform_fee"])
        shipping_cost = float(data["shipping_cost"])
        date.fromisoformat(sale_date)
        if sale_price <= 0 or platform_fee < 0 or shipping_cost < 0:
            raise ValueError
        with get_db() as connection:
            listing = connection.execute(
                "SELECT item_id, status FROM listing WHERE listing_id = ?",
                (listing_id,),
            ).fetchone()
            if listing is None:
                return jsonify({"error": "Listing not found"}), 404
            if listing["status"] != "active":
                return jsonify({"error": "Only active listings can be sold"}), 400
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO sale (listing_id, sale_date, sale_price, platform_fee, shipping_cost)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (listing_id, sale_date, sale_price, platform_fee, shipping_cost),
                )
                connection.execute(
                    "UPDATE listing SET status = 'sold', ended_date = ? WHERE listing_id = ?",
                    (sale_date, listing_id),
                )
                connection.execute(
                    """
                    UPDATE listing SET status = 'ended', ended_date = ?
                    WHERE item_id = ? AND listing_id <> ? AND status = 'active'
                    """,
                    (sale_date, listing["item_id"], listing_id),
                )
        return jsonify({"message": "Sale recorded", "sale_id": cursor.lastrowid}), 201
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Provide valid sale values"}), 400
    except sqlite3.IntegrityError:
        return jsonify({"error": "This listing already has a sale"}), 400


@app.route("/api/report")
def report():
    with get_db() as connection:
        platforms = rows_json(connection.execute(
            """
            SELECT platform_name, COUNT(*) AS sales,
                   ROUND(SUM(sale_price), 2) AS revenue,
                   ROUND(SUM(net_profit), 2) AS net_profit,
                   ROUND(AVG(days_to_sell), 1) AS average_days_to_sell
            FROM v_sale_profit
            GROUP BY platform_name
            ORDER BY net_profit DESC
            """
        ).fetchall())
        monthly = rows_json(connection.execute(
            """
            SELECT strftime('%Y-%m', sale_date) AS month,
                   COUNT(*) AS sales,
                   ROUND(SUM(net_profit), 2) AS net_profit
            FROM v_sale_profit
            GROUP BY month
            ORDER BY month
            """
        ).fetchall())
    return jsonify({"platforms": platforms, "monthly": monthly})


@app.route("/api/listings")
def active_listings():
    with get_db() as connection:
        rows = rows_json(connection.execute(
            """
            SELECT l.listing_id, i.title, p.platform_name,
                   l.list_price, l.listed_date
            FROM listing l
            JOIN item i ON i.item_id = l.item_id
            JOIN platform p ON p.platform_id = l.platform_id
            WHERE l.status = 'active'
            ORDER BY l.listed_date DESC, l.listing_id DESC
            """
        ).fetchall())
    return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True)
