PRAGMA foreign_keys = ON;

.print
.print Transaction demo: record the sale of item 16 (Lululemon Define Jacket)

.print
.print BEFORE: listings for item 16
SELECT l.listing_id, p.platform_name AS platform, l.list_price, l.status, l.ended_date
FROM   listing l JOIN platform p ON p.platform_id = l.platform_id
WHERE  l.item_id = 16
ORDER  BY l.listing_id;

BEGIN TRANSACTION;


INSERT INTO sale (listing_id, sale_date, sale_price, platform_fee, shipping_cost)
VALUES (27, '2026-10-31', 84.00, 16.80, 7.97);


UPDATE listing
SET    status = 'sold',
       ended_date = '2026-10-31'
WHERE  listing_id = 27;

UPDATE listing
SET    status = 'ended',
       ended_date = '2026-10-31'
WHERE  item_id = 16
  AND  listing_id <> 27
  AND  status = 'active';

.print
.print INSIDE TRANSACTION (uncommitted): new sale and updated listings
SELECT l.listing_id, p.platform_name AS platform, l.list_price, l.status, l.ended_date
FROM   listing l JOIN platform p ON p.platform_id = l.platform_id
WHERE  l.item_id = 16
ORDER  BY l.listing_id;

SELECT sale_id, listing_id, sale_date, sale_price, platform_fee, shipping_cost
FROM   sale
WHERE  listing_id = 27;

ROLLBACK;

.print
.print AFTER ROLLBACK: item 16 listings are back to their original state
SELECT l.listing_id, p.platform_name AS platform, l.list_price, l.status, l.ended_date
FROM   listing l JOIN platform p ON p.platform_id = l.platform_id
WHERE  l.item_id = 16
ORDER  BY l.listing_id;

.print
.print AFTER ROLLBACK: sales count (still 12, the new sale is gone)
SELECT COUNT(*) AS num_sales FROM sale;