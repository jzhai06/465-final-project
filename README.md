# 465-final-project

# Reselling Tracker - Deliverable 3: Backend Implementation and Data
=============================================================

## DBMS USED
---------
SQLite 3 

## FILES
-------------------------
1. schema.sql - creates all tables, constraints, the index, and the view. Begins with DROP statements, so it can be re-run safely. This file will be ran first.
2. insert_data.sql - Loads dummy sample data (91 rows across 7 tables).

## SETUP INSTRUCTIONS
------------------
In command prompt, type in 
    sqlite3 resell.db < schema.sql
    sqlite3 resell.db < insert_data.sql


## DATABASE SUMMARY
----------------
7 tables: brand, category, sourcing location, platform, item, listing, sale.
  - item references brand, category, sourcing location, etc.
  - listing is the junction table for the many-to-many relationship between
    item and platform. It stores list price, listed date, ended date, and status.
  - sale references exactly one listing (UNIQUE listing_id, so a listing has
    0 or 1 sale) and stores sale_price, platform_fee, and shipping_cost.

## VIEW: v_sale_profit
-------------------
What it represents: one row per completed sale, with the item, brand, category,
platform, and sourcing location, plus net profit and the days it took to sell.
    net_profit = sale_price - platform_fee - shipping_cost - purchase_cost
Tables used: sale, listing, item, brand, category, platform, and
sourcing_location (LEFT JOIN, due to the fact that some items have no recorded location).
Why it is useful: profit depends on columns in 4 tables, so the view
computes it once. Reports such as profit by platform, brand, or store become
simple GROUP BY queries, and the application can show per-sale profit without
repeating the joins.

## INDEX: idx_listing_status_listed
--------------------------------
Columns: listing(status, listed_date).
Supports: finding listings by status and listing age, for example "active
listings that have been up more than 60 days without selling" (the stale
listings report) and the active-inventory screen. Filtering on status and
then a date range lets SQLite search the index instead of scanning every
listing row. (Checked with EXPLAIN QUERY PLAN: it uses this index.)