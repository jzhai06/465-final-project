"""Interactive CLI for the reselling tracker SQLite database."""

import argparse
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional


CONDITIONS = ("New", "Excellent", "Good", "Fair", "Poor")


def connect(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def prompt(message: str, required: bool = True) -> str:
    while True:
        value = input(message).strip()
        if value or not required:
            return value
        print("A value is required.")


def integer(message: str, minimum: Optional[int] = None) -> int:
    while True:
        try:
            value = int(prompt(message))
            if minimum is not None and value < minimum:
                raise ValueError
            return value
        except ValueError:
            suffix = f" at least {minimum}" if minimum is not None else ""
            print(f"Enter a whole number{suffix}.")


def money(message: str, positive: bool = False) -> float:
    while True:
        try:
            value = float(prompt(message))
            if value < 0 or (positive and value == 0):
                raise ValueError
            return value
        except ValueError:
            print("Enter a valid non-negative amount." if not positive else "Enter an amount greater than zero.")


def iso_date(message: str, default: Optional[str] = None) -> str:
    while True:
        value = prompt(f"{message} [{default}]: " if default else f"{message}: ", required=default is None)
        value = value or default
        try:
            date.fromisoformat(value)
            return value
        except (TypeError, ValueError):
            print("Enter a date in YYYY-MM-DD format.")


def print_rows(rows: list[sqlite3.Row]) -> None:
    if not rows:
        print("No records found.")
        return
    columns = rows[0].keys()
    widths = {
        column: max(len(column), *(len(str(row[column])) for row in rows))
        for column in columns
    }
    print(" | ".join(f"{column:{widths[column]}}" for column in columns))
    print("-+-".join("-" * widths[column] for column in columns))
    for row in rows:
        print(" | ".join(f"{str(row[column]):{widths[column]}}" for column in columns))


def browse_items(connection: sqlite3.Connection) -> None:
    term = prompt("Search title or brand (leave blank for all): ", required=False)
    rows = connection.execute(
        """
        SELECT i.item_id, i.title, b.brand_name AS brand, c.category_name AS category,
               i.condition, i.purchase_cost,
               COALESCE(SUM(l.status = 'active'), 0) AS active_listings
        FROM item i
        JOIN brand b ON b.brand_id = i.brand_id
        JOIN category c ON c.category_id = i.category_id
        LEFT JOIN listing l ON l.item_id = i.item_id
        WHERE (? = '' OR i.title LIKE '%' || ? || '%' OR b.brand_name LIKE '%' || ? || '%')
        GROUP BY i.item_id
        ORDER BY i.item_id
        """,
        (term, term, term),
    ).fetchall()
    print_rows(rows)


def show_item_details(connection: sqlite3.Connection) -> None:
    item_id = integer("Item ID: ", 1)
    rows = connection.execute(
        """
        SELECT i.item_id, i.title, b.brand_name AS brand, c.category_name AS category,
               p.platform_name AS platform, l.listing_id, l.list_price,
               l.status, l.listed_date
        FROM item i
        JOIN brand b ON b.brand_id = i.brand_id
        JOIN category c ON c.category_id = i.category_id
        LEFT JOIN listing l ON l.item_id = i.item_id
        LEFT JOIN platform p ON p.platform_id = l.platform_id
        WHERE i.item_id = ?
        ORDER BY l.listing_id
        """,
        (item_id,),
    ).fetchall()
    print_rows(rows)


def add_item(connection: sqlite3.Connection) -> None:
    print("Available brands:")
    print_rows(connection.execute("SELECT brand_id, brand_name FROM brand ORDER BY brand_name").fetchall())
    brand_id = integer("Brand ID: ", 1)
    print("Available categories:")
    print_rows(connection.execute("SELECT category_id, category_name FROM category ORDER BY category_name").fetchall())
    category_id = integer("Category ID: ", 1)
    title = prompt("Title: ")
    print("Condition options:", ", ".join(CONDITIONS))
    condition = prompt("Condition: ")
    while condition not in CONDITIONS:
        print("Choose one of the listed conditions.")
        condition = prompt("Condition: ")
    purchase_cost = money("Purchase cost: ")
    acquired_date = iso_date("Acquired date")
    connection.execute(
        """
        INSERT INTO item (brand_id, category_id, title, condition, purchase_cost, acquired_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (brand_id, category_id, title, condition, purchase_cost, acquired_date),
    )
    connection.commit()
    print("Item added.")


def add_listing(connection: sqlite3.Connection) -> None:
    item_id = integer("Item ID: ", 1)
    platform_id = integer("Platform ID: ", 1)
    list_price = money("List price: ", positive=True)
    listed_date = iso_date("Listed date", date.today().isoformat())
    connection.execute(
        """
        INSERT INTO listing (item_id, platform_id, list_price, listed_date)
        VALUES (?, ?, ?, ?)
        """,
        (item_id, platform_id, list_price, listed_date),
    )
    connection.commit()
    print("Listing added.")


def update_listing(connection: sqlite3.Connection) -> None:
    listing_id = integer("Listing ID: ", 1)
    row = connection.execute(
        "SELECT list_price, status FROM listing WHERE listing_id = ?", (listing_id,)
    ).fetchone()
    if row is None:
        print("Listing not found.")
        return
    print(f"Current price: {row['list_price']}; status: {row['status']}")
    new_price = money("New list price: ", positive=True)
    connection.execute(
        "UPDATE listing SET list_price = ? WHERE listing_id = ?",
        (new_price, listing_id),
    )
    connection.commit()
    print("Listing updated.")


def record_sale(connection: sqlite3.Connection) -> None:
    listing_id = integer("Listing ID to sell: ", 1)
    listing = connection.execute(
        "SELECT item_id, status FROM listing WHERE listing_id = ?", (listing_id,)
    ).fetchone()
    if listing is None:
        print("Listing not found.")
        return
    if listing["status"] != "active":
        print("Only an active listing can be sold.")
        return
    sale_date = iso_date("Sale date", date.today().isoformat())
    sale_price = money("Sale price: ", positive=True)
    platform_fee = money("Platform fee: ")
    shipping_cost = money("Shipping cost: ")
    try:
        with connection:
            connection.execute(
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
                UPDATE listing
                SET status = 'ended', ended_date = ?
                WHERE item_id = ? AND listing_id <> ? AND status = 'active'
                """,
                (sale_date, listing["item_id"], listing_id),
            )
    except sqlite3.IntegrityError as error:
        print(f"Sale could not be recorded: {error}")
        return
    print("Sale recorded; other active listings for this item were ended.")


def profit_report(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT platform_name, COUNT(*) AS sales,
               ROUND(SUM(sale_price), 2) AS revenue,
               ROUND(SUM(net_profit), 2) AS net_profit,
               ROUND(AVG(days_to_sell), 1) AS average_days_to_sell
        FROM v_sale_profit
        GROUP BY platform_name
        ORDER BY net_profit DESC
        """
    ).fetchall()
    print_rows(rows)


def run(database: Path) -> None:
    try:
        connection = connect(database)
    except sqlite3.Error as error:
        print(f"Could not open database: {error}")
        return
    actions = {
        "1": ("Search or browse items", browse_items),
        "2": ("View item listings (related data)", show_item_details),
        "3": ("Add an item", add_item),
        "4": ("Add a listing", add_listing),
        "5": ("Update a listing price", update_listing),
        "6": ("Record a sale", record_sale),
        "7": ("Profit report", profit_report),
    }
    try:
        while True:
            print("\nReselling Tracker")
            for key, (label, _) in actions.items():
                print(f"{key}. {label}")
            print("0. Exit")
            choice = input("Choose an option: ").strip()
            if choice == "0":
                break
            action = actions.get(choice)
            if action is None:
                print("Choose a listed menu option.")
                continue
            try:
                action[1](connection)
            except sqlite3.IntegrityError:
                print("The database rejected that change. Check IDs and duplicate values.")
            except sqlite3.Error as error:
                print(f"Database operation failed: {error}")
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage the reselling tracker database.")
    parser.add_argument("--db", type=Path, default=Path("resell.db"), help="SQLite database path")
    run(parser.parse_args().db)
