PRAGMA foreign_keys = ON;

.print
.print Requirement 1: Filtering and Sorting

SELECT listing_id, item_id, platform_id, list_price, listed_date,
       CAST(julianday('2026-10-31') - julianday(listed_date) AS INTEGER) AS days_listed
FROM   listing
WHERE  status = 'active'
  AND  listed_date < date('2026-10-31', '-60 day')
ORDER  BY listed_date ASC, list_price DESC;

.print
.print Requirement 2: INNER JOIN
SELECT s.sale_id, l.listing_id, l.list_price, s.sale_price, ROUND(l.list_price - s.sale_price, 2)                        AS discount_given,
       ROUND(100.0 * (l.list_price - s.sale_price) / l.list_price, 1) AS discount_pct
FROM   sale s INNER JOIN listing l ON l.listing_id = s.listing_id ORDER  BY discount_pct DESC;

.print
.print Requirement 3: LEFT JOIN

SELECT i.item_id,
       i.title,
       i.purchase_cost,
       COUNT(l.listing_id) AS listing_count
FROM   item i
LEFT JOIN listing l ON l.item_id = i.item_id
GROUP  BY i.item_id, i.title, i.purchase_cost
ORDER  BY listing_count ASC, i.item_id ASC;

.print
.print Requirement 4: Three-Table Join

SELECT i.title                                                   AS item,
       b.brand_name                                              AS brand,
       p.platform_name                                           AS platform,
       i.purchase_cost,
       l.list_price,
       ROUND(l.list_price * (1 - p.fee_percent / 100.0) - i.purchase_cost, 2) AS est_profit_before_shipping
FROM   listing l
JOIN   item     i ON i.item_id     = l.item_id
JOIN   platform p ON p.platform_id = l.platform_id
JOIN   brand    b ON b.brand_id    = i.brand_id
WHERE  l.status = 'active'
ORDER  BY est_profit_before_shipping DESC;

.print
.print Requirement 5: Aggregate Query

SELECT COUNT(*)                      AS num_sales,
       ROUND(SUM(sale_price), 2)     AS total_revenue,
       ROUND(AVG(sale_price), 2)     AS avg_sale_price,
       MIN(sale_price)               AS lowest_sale,
       MAX(sale_price)               AS highest_sale,
       ROUND(SUM(platform_fee), 2)   AS total_fees,
       ROUND(SUM(shipping_cost), 2)  AS total_shipping
FROM   sale;

.print
.print Requirement 6: GROUP BY and HAVING

SELECT p.platform_name                                       AS platform,
       COUNT(*)                                              AS num_sales,
       ROUND(AVG(julianday(s.sale_date) - julianday(l.listed_date)), 1)
                                                             AS avg_days_to_sell,
       ROUND(SUM(s.sale_price - s.platform_fee - s.shipping_cost - i.purchase_cost), 2)
                                                             AS total_net_profit
FROM   sale s JOIN   listing  l ON l.listing_id  = s.listing_id
JOIN   platform p ON p.platform_id = l.platform_id
JOIN   item     i ON i.item_id     = l.item_id
GROUP  BY p.platform_id, p.platform_name
HAVING COUNT(*) >= 3
ORDER  BY total_net_profit DESC;

.print
.print Requirement 7: Subquery

SELECT c.category_name                  AS category,
       COUNT(*)                         AS unsold_items,
       ROUND(SUM(i.purchase_cost), 2)   AS money_tied_up
FROM   item i JOIN   category c ON c.category_id = i.category_id
WHERE  i.item_id NOT IN (SELECT l.item_id FROM listing l JOIN   sale s ON s.listing_id = l.listing_id)
GROUP  BY c.category_id, c.category_name
ORDER  BY money_tied_up DESC;

.print
.print Requirement 8: Set Operation (EXCEPT)

SELECT i.item_id AS item_id, i.title AS title
FROM   item i
JOIN   listing l ON l.item_id = i.item_id
JOIN   platform p ON p.platform_id = l.platform_id
WHERE  l.status = 'active' AND p.platform_name = 'eBay'
EXCEPT SELECT i.item_id AS item_id, i.title AS title
FROM   item i
JOIN   listing l ON l.item_id = i.item_id
JOIN   platform p ON p.platform_id = l.platform_id
WHERE  l.status = 'active' AND p.platform_name = 'Poshmark'
ORDER  BY item_id;

.print
.print Requirement 9: Query Using the View (v_sale_profit)
SELECT sourcing_location                          AS location,
       COUNT(*)                                   AS items_sold,
       ROUND(SUM(purchase_cost), 2)               AS total_spent,
       ROUND(SUM(net_profit), 2)                  AS total_net_profit,
       ROUND(100.0 * SUM(net_profit) / SUM(purchase_cost), 0) AS roi_percent
FROM   v_sale_profit
GROUP  BY sourcing_location
ORDER  BY roi_percent DESC;

.print
.print Additional Query A: Monthly net profit (view)

SELECT strftime('%Y-%m', sale_date)   AS month,
       COUNT(*)                       AS items_sold,
       ROUND(SUM(sale_price), 2)      AS revenue,
       ROUND(SUM(net_profit), 2)      AS net_profit
FROM   v_sale_profit
GROUP  BY month
ORDER  BY month;

.print
.print Additional Query B: Brands by margin and speed (view)

SELECT brand_name                        AS brand,
       COUNT(*)                          AS items_sold,
       ROUND(AVG(days_to_sell), 1)       AS avg_days_to_sell,
       ROUND(AVG(net_profit), 2)         AS avg_profit_per_item
FROM   v_sale_profit
GROUP  BY brand_name
ORDER  BY avg_profit_per_item DESC;