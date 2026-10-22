PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_sale_profit;
DROP INDEX IF EXISTS idx_listing_status_listed;
DROP TABLE IF EXISTS sale;
DROP TABLE IF EXISTS listing;
DROP TABLE IF EXISTS item;
DROP TABLE IF EXISTS platform;
DROP TABLE IF EXISTS sourcing_location;
DROP TABLE IF EXISTS category;
DROP TABLE IF EXISTS brand;

CREATE TABLE brand (
    brand_id    INTEGER PRIMARY KEY,
    brand_name  TEXT NOT NULL UNIQUE          
);

CREATE TABLE category (
    category_id   INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE
);

CREATE TABLE sourcing_location (
    location_id   INTEGER PRIMARY KEY,
    location_name TEXT NOT NULL,
    city          TEXT NOT NULL,
    UNIQUE (location_name, city)
);

CREATE TABLE platform (
    platform_id   INTEGER PRIMARY KEY,
    platform_name TEXT NOT NULL UNIQUE,
    fee_percent   REAL NOT NULL CHECK (fee_percent >= 0 AND fee_percent <= 100)  
);

CREATE TABLE item (
    item_id        INTEGER PRIMARY KEY,
    brand_id       INTEGER NOT NULL REFERENCES brand(brand_id),
    category_id    INTEGER NOT NULL REFERENCES category(category_id),
    location_id    INTEGER REFERENCES sourcing_location(location_id),  -- NULL = bought online / mixed lot
    title          TEXT NOT NULL,
    condition      TEXT NOT NULL DEFAULT 'Good' CHECK (condition IN ('New', 'Excellent', 'Good', 'Fair', 'Poor')),
    purchase_cost  REAL NOT NULL CHECK (purchase_cost >= 0),
    acquired_date  TEXT NOT NULL              
);

CREATE TABLE listing (
    listing_id   INTEGER PRIMARY KEY,
    item_id      INTEGER NOT NULL REFERENCES item(item_id),
    platform_id  INTEGER NOT NULL REFERENCES platform(platform_id),
    list_price   REAL NOT NULL CHECK (list_price > 0),
    listed_date  TEXT NOT NULL,               -- ISO date
    ended_date   TEXT,                        -- NULL while the listing is still live
    status       TEXT NOT NULL DEFAULT 'active'
                 CHECK (status IN ('active', 'sold', 'ended')),
    CHECK (ended_date IS NULL OR ended_date >= listed_date),
    CHECK ((status = 'active' AND ended_date IS NULL) OR (status IN ('sold', 'ended') AND ended_date IS NOT NULL))
);

CREATE TABLE sale (
    sale_id        INTEGER PRIMARY KEY,
    listing_id     INTEGER NOT NULL UNIQUE REFERENCES listing(listing_id),
    sale_date      TEXT NOT NULL,             -- ISO date
    sale_price     REAL NOT NULL CHECK (sale_price > 0),
    platform_fee   REAL NOT NULL DEFAULT 0 CHECK (platform_fee >= 0),
    shipping_cost  REAL NOT NULL DEFAULT 0 CHECK (shipping_cost >= 0)
);

CREATE INDEX idx_listing_status_listed ON listing (status, listed_date);

CREATE VIEW v_sale_profit AS
SELECT
    s.sale_id,
    s.sale_date,
    i.item_id,
    i.title AS item_title,
    b.brand_name,
    c.category_name,
    p.platform_name,
    sl.location_name AS sourcing_location, 
    i.purchase_cost,
    s.sale_price,
    s.platform_fee,
    s.shipping_cost,
    ROUND(s.sale_price - s.platform_fee - s.shipping_cost - i.purchase_cost, 2) AS net_profit,
    CAST(julianday(s.sale_date) - julianday(l.listed_date) AS INTEGER)          AS days_to_sell
FROM sale s
JOIN listing  l ON l.listing_id  = s.listing_id
JOIN item     i ON i.item_id     = l.item_id
JOIN brand    b ON b.brand_id    = i.brand_id
JOIN category c ON c.category_id = i.category_id
JOIN platform p ON p.platform_id = l.platform_id
LEFT JOIN sourcing_location sl ON sl.location_id = i.location_id;