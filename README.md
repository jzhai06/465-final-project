# 465-final-project

# Reselling Tracker - Deliverable 5: Application

## Application

The application is a Python 3 command-line interface using SQLite's standard
library driver. The relational database remains the primary store; all
user-supplied values are passed through parameterized SQL statements.

## Setup and run

From this directory, recreate the database (the first command removes and
recreates the schema):

```text
sqlite3 resell.db < schema.sql
sqlite3 resell.db < insert_data.sql
python app.py
```

Python 3.9 or newer is recommended. No third-party packages are required. A
different database can be selected with `python app.py --db path/to/file.db`.

## Application operations

The interactive menu provides:

1. **Search or browse items** - searches item titles and brands and shows active listing counts.
2. **View item listings** - joins items, brands, categories, listings, and platforms.
3. **Add an item** - inserts a validated item using existing brand and category IDs.
4. **Add a listing** - inserts a validated active listing.
5. **Update a listing price** - updates an existing listing after checking its ID.
6. **Record a sale** - uses a transaction to insert the sale, mark its listing sold,
   and end the item's other active listings.
7. **Profit report** - groups the `v_sale_profit` view by platform and reports revenue,
   net profit, and average days to sell.

The application reports missing records, invalid input, constraint violations,
and database errors without exposing a traceback during normal use.

# Backend files

## DBMS USED
SQLite 3 

## FILES
1. schema.sql - creates all tables, constraints, the index, and the view. Begins with DROP statements, so it can be re-run safely. This file will be ran first.
2. insert_data.sql - Loads dummy sample data (91 rows across 7 tables).

## SETUP INSTRUCTIONS
In command prompt, type in 
    sqlite3 resell.db < schema.sql
    sqlite3 resell.db < insert_data.sql

## VIEW Explanation
v_sale_profit
What it represents: one row per completed sale, with the item, brand, category,
platform, and sourcing location, plus net profit and the days it took to sell.
    net_profit = sale_price - platform_fee - shipping_cost - purchase_cost
Tables used: sale, listing, item, brand, category, platform, and
sourcing_location (LEFT JOIN, due to the fact that some items have no recorded location).
Why it is useful: profit depends on columns in 4 tables, so the view
computes it once. Reports such as profit by platform, brand, or store become
simple GROUP BY queries, and the application can show per-sale profit without
repeating the joins.

## INDEX Explanation
idx_listing_status_listed
Columns: listing(status, listed_date).
Supports: finding listings by status and listing age, for example "active
listings that have been up more than 60 days without selling" (the stale
listings report) and the active-inventory screen. Filtering on status and
then a date range lets SQLite search the index instead of scanning every
listing row. (Checked with EXPLAIN QUERY PLAN: it uses this index.)