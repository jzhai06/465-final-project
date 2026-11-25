# Reselling Tracker

## Project overview

Reselling Tracker helps a reseller track inventory purchased from sourcing
locations, listings posted to sales platforms, and completed sales. It is
intended for individual resellers who need to search inventory, view related
listings, add inventory and listings, update prices, record sales, and review
profit reports.

The project is a Python Flask web application backed by SQLite. The relational
database is the primary data store; persistent project data is not stored in
JavaScript, JSON, CSV, or Python collections.

## Repository contents

- `erd.svg` - final entity-relationship diagram
- `schema.sql` - tables, constraints, index, and `v_sale_profit` view
- `insert_data.sql` - reproducible sample data
- `queries.sql` - final SQL query examples
- `transaction.sql` - transaction example with rollback demonstration
- `web_app.py` - Flask web application
- `templates/` - web dashboard HTML template
- `static/` - dashboard CSS and JavaScript
- `requirements.txt` - Python web dependencies
- `README.md` - setup, operation, and testing instructions
- No live database or hosted-service credentials are included

## DBMS

The project uses SQLite 3. No hosted service or account is required.

## Database setup

Install SQLite 3 and Python 3.9 or newer. The web application creates
`resell.db` automatically from `schema.sql` and `insert_data.sql` when the
database is missing or has no `item` table.

For manual setup, from the repository directory run:

```text
sqlite3 resell.db < schema.sql
sqlite3 resell.db < insert_data.sql
```

Run `schema.sql` first. It creates the tables, index, and view. It safely drops
existing project objects before recreating them. Run `insert_data.sql` next to
load the sample brands, categories, locations, platforms, items, listings, and
sales.

To run the final SQL queries:

```text
sqlite3 resell.db < queries.sql
```

The transaction example is intentionally rolled back and can be run with:

```text
sqlite3 resell.db < transaction.sql
```

## Application setup and run

Install the web dependency:

```text
python -m pip install -r requirements.txt
python web_app.py
```

Open `http://127.0.0.1:5000` in a browser.

The application opens `resell.db` by default. Set `RESELL_DATABASE` to use a
different SQLite database:

```text
set RESELL_DATABASE=C:\path\to\database.db
python web_app.py
```

All values supplied by the user are passed to SQL through parameters. The
application validates dates, numeric values, required text, and allowed item
conditions. Database constraint and record-not-found errors are returned as
clear interface messages.

## Major application operations

The interface provides:

1. **Search or browse items** - searches item titles or brands and displays
   active listing counts.
2. **View item listings** - joins items, brands, categories, listings, and
   platforms to show related data.
3. **Add an item** - inserts a validated item.
4. **Add a listing** - inserts a validated active listing.
5. **Update a listing price** - updates an existing listing.
6. **Record a sale** - transactionally inserts the sale, marks its listing
   sold, and ends the item's other active listings.
7. **Profit report** - groups the `v_sale_profit` view by platform and reports
   sales, revenue, net profit, and average days to sell.

## Demonstration checklist

After recreating the database and starting `python web_app.py`:

1. Search for `Nike` in Inventory.
2. Open item `1` to show its brand, category, location, and related listings.
3. Add or update an item/listing to demonstrate persistent modification.
4. Record a sale and show that the transaction updates the sale and listing
   records.
5. Open Analytics to show the platform and monthly profit reports.

For a clean demonstration database, rerun the two database setup commands
before starting the application.

## Design notes and limitations

The `v_sale_profit` view centralizes the multi-table profit calculation:
`sale_price - platform_fee - shipping_cost - purchase_cost`. The
python web_app.py``idx_listing_status_listed` index supports searches for active listings by
status and listed date. The application is a local Flask interface and does
not provide user accounts or concurrent multi-user access.

No passwords, API secrets, private keys, or hosted-service credentials are
required or included.
