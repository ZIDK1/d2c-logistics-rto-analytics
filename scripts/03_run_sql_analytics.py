"""
SQL Analytics Runner (SQLite)
Author: Zaid Kaiser (zaidkaiser2006@gmail.com)
Description: Loads generated CSV data into an automated SQLite database and executes 
             the production SQL queries from sql/02_business_analytics.sql live.
"""

import os
import csv
import sqlite3

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DATA_DIR, "d2c_logistics.db")

# Reset existing DB or tables safely for a clean run
if os.path.exists(DB_PATH):
    try:
        os.remove(DB_PATH)
    except PermissionError:
        pass

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.executescript("""
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS pincode_master;
""")

print("[INFO] Creating database schema and importing CSV data...")

# 1. Pincodes Table
cursor.execute("""
CREATE TABLE pincode_master (
    pincode TEXT PRIMARY KEY,
    city TEXT,
    state TEXT,
    tier TEXT,
    base_rto_risk REAL
);
""")

with open(os.path.join(DATA_DIR, "pincode_master.csv"), "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    p_data = [(r["pincode"], r["city"], r["state"], r["tier"], float(r["base_rto_risk"])) for r in reader]
cursor.executemany("INSERT INTO pincode_master VALUES (?, ?, ?, ?, ?)", p_data)

# 2. Customers Table
cursor.execute("""
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT,
    default_pincode TEXT,
    account_created_date TEXT,
    customer_segment TEXT
);
""")

with open(os.path.join(DATA_DIR, "customers.csv"), "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    c_data = [(r["customer_id"], r["customer_name"], r["default_pincode"], r["account_created_date"], r["customer_segment"]) for r in reader]
cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", c_data)

# 3. Orders Table
cursor.execute("""
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    order_date TEXT,
    customer_id TEXT,
    pincode TEXT,
    city TEXT,
    state TEXT,
    city_tier TEXT,
    product_category TEXT,
    payment_method TEXT,
    gross_order_value REAL,
    discount_amount REAL,
    net_order_value REAL,
    courier_partner TEXT,
    promised_delivery_days INTEGER,
    actual_delivery_days INTEGER,
    sla_breached INTEGER,
    order_status TEXT,
    rto_flag INTEGER,
    rto_reason TEXT,
    delivery_date TEXT,
    return_date TEXT,
    forward_freight REAL,
    reverse_freight REAL,
    packaging_cost REAL,
    cod_handling_fee REAL,
    total_logistics_loss REAL,
    realized_revenue REAL,
    rto_risk_score INTEGER,
    risk_tier TEXT,
    action_recommendation TEXT,
    preventable_loss_inr REAL
);
""")

with open(os.path.join(DATA_DIR, "rto_scored_orders.csv"), "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    o_data = []
    for r in reader:
        o_data.append((
            r["order_id"], r["order_date"], r["customer_id"], r["pincode"], r["city"], r["state"],
            r["city_tier"], r["product_category"], r["payment_method"], float(r["gross_order_value"]),
            float(r["discount_amount"]), float(r["net_order_value"]), r["courier_partner"],
            int(r["promised_delivery_days"]), int(r["actual_delivery_days"]), int(r["sla_breached"]),
            r["order_status"], int(r["rto_flag"]), r["rto_reason"], r["delivery_date"], r["return_date"],
            float(r["forward_freight"]), float(r["reverse_freight"]), float(r["packaging_cost"]),
            float(r["cod_handling_fee"]), float(r["total_logistics_loss"]), float(r["realized_revenue"]),
            int(r["rto_risk_score"]), r["risk_tier"], r["action_recommendation"], float(r["preventable_loss_inr"])
        ))

cursor.executemany("INSERT INTO orders VALUES (" + ",".join(["?"] * 31) + ")", o_data)
conn.commit()

print(f"[SUCCESS] Loaded {len(p_data)} Pincodes, {len(c_data):,} Customers, and {len(o_data):,} Orders into SQLite!\n")


def print_table(title, headers, rows):
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(val)))
            
    header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_line)
    print(separator)
    for row in rows:
        print(" | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(row)))
    print()


# --------------------------------------------------------------------
# QUERY 1: EXECUTIVE KPI SUMMARY
# --------------------------------------------------------------------
q1 = """
SELECT 
    COUNT(order_id) AS total_orders,
    'INR ' || PRINTF('%,d', CAST(SUM(gross_order_value) AS INT)) AS total_gmv,
    'INR ' || PRINTF('%,d', CAST(SUM(realized_revenue) AS INT)) AS total_realized_rev,
    'INR ' || PRINTF('%,d', CAST(SUM(total_logistics_loss) AS INT)) AS dead_freight_loss,
    ROUND(SUM(rto_flag) * 100.0 / COUNT(order_id), 2) || '%' AS overall_rto_rate
FROM orders;
"""
cursor.execute(q1)
print_table("QUERY 1: EXECUTIVE KPI SUMMARY (Financial Exposure)", 
            ["Total Orders", "Gross GMV", "Realized Revenue", "Dead Freight Loss", "Overall RTO %"],
            cursor.fetchall())


# --------------------------------------------------------------------
# QUERY 2: PAYMENT METHOD BREAKDOWN (COD vs Prepaid)
# --------------------------------------------------------------------
q2 = """
SELECT 
    payment_method,
    COUNT(order_id) AS orders,
    ROUND(COUNT(order_id) * 100.0 / (SELECT COUNT(*) FROM orders), 1) || '%' AS volume_share,
    SUM(rto_flag) AS rto_count,
    ROUND(SUM(rto_flag) * 100.0 / COUNT(order_id), 2) || '%' AS rto_rate,
    'INR ' || PRINTF('%,d', CAST(SUM(total_logistics_loss) AS INT)) AS logistics_loss
FROM orders
GROUP BY payment_method
ORDER BY SUM(rto_flag) * 100.0 / COUNT(order_id) DESC;
"""
cursor.execute(q2)
print_table("QUERY 2: CASH ON DELIVERY (COD) VS PREPAID MATRIX", 
            ["Payment Method", "Order Volume", "Volume Share", "RTO Count", "RTO Rate %", "Logistics Dead Loss"],
            cursor.fetchall())


# --------------------------------------------------------------------
# QUERY 3: TOP 6 PINCODES BY FREIGHT LOSS (Pareto Analysis)
# --------------------------------------------------------------------
q3 = """
WITH PincodeLossSummary AS (
    SELECT 
        pincode,
        city,
        city_tier,
        COUNT(order_id) AS orders,
        ROUND(SUM(rto_flag) * 100.0 / COUNT(order_id), 1) || '%' AS rto_pct,
        CAST(SUM(total_logistics_loss) AS INT) AS total_loss_int
    FROM orders
    GROUP BY pincode, city, city_tier
),
RankedPincodes AS (
    SELECT 
        *,
        SUM(total_loss_int) OVER(ORDER BY total_loss_int DESC) AS running_loss,
        SUM(total_loss_int) OVER() AS grand_total_loss
    FROM PincodeLossSummary
)
SELECT 
    pincode,
    city,
    city_tier,
    orders,
    rto_pct,
    'INR ' || PRINTF('%,d', total_loss_int) AS loss_amount,
    ROUND(running_loss * 100.0 / grand_total_loss, 1) || '%' AS cumulative_loss_pct,
    CASE 
        WHEN (running_loss * 100.0 / grand_total_loss) <= 60 THEN 'Tier A Loss (Critical)'
        ELSE 'Tier B Loss'
    END AS priority
FROM RankedPincodes
ORDER BY total_loss_int DESC
LIMIT 6;
"""
cursor.execute(q3)
print_table("QUERY 3: PARETO 80/20 ANALYSIS (Top Pincodes Causing Majority of Losses)", 
            ["Pincode", "City", "Tier", "Orders", "RTO %", "Loss (INR)", "Cumulative Loss %", "Loss Tier"],
            cursor.fetchall())


# --------------------------------------------------------------------
# QUERY 4: CARRIER SLA BREACH PERFORMANCE
# --------------------------------------------------------------------
q4 = """
SELECT 
    courier_partner,
    COUNT(order_id) AS shipments,
    ROUND(SUM(sla_breached) * 100.0 / COUNT(order_id), 1) || '%' AS delay_rate,
    ROUND(SUM(CASE WHEN sla_breached = 1 THEN rto_flag ELSE 0 END) * 100.0 / NULLIF(SUM(sla_breached), 0), 1) || '%' AS rto_rate_when_delayed,
    ROUND(SUM(CASE WHEN sla_breached = 0 THEN rto_flag ELSE 0 END) * 100.0 / NULLIF(COUNT(order_id) - SUM(sla_breached), 0), 1) || '%' AS rto_rate_on_time,
    'INR ' || PRINTF('%,d', CAST(SUM(total_logistics_loss) AS INT)) AS carrier_loss
FROM orders
GROUP BY courier_partner
ORDER BY SUM(sla_breached) * 100.0 / COUNT(order_id) DESC;
"""
cursor.execute(q4)
print_table("QUERY 4: CARRIER SLA BREACH & DELAY PENALTY MATRIX", 
            ["Courier Partner", "Shipments", "Delay Rate %", "RTO Rate (Delayed)", "RTO Rate (On-Time)", "Total Carrier Loss"],
            cursor.fetchall())


# --------------------------------------------------------------------
# QUERY 5: FINANCIAL POLICY SIMULATION (What-If In SQL)
# --------------------------------------------------------------------
q5 = """
WITH CurrentState AS (
    SELECT 
        SUM(realized_revenue) AS current_rev,
        SUM(total_logistics_loss) AS current_loss,
        SUM(realized_revenue) - SUM(total_logistics_loss) AS current_margin
    FROM orders
),
SimulatedPolicy AS (
    SELECT 
        SUM(
            CASE 
                WHEN city_tier = 'Tier-3' AND payment_method = 'COD' THEN (realized_revenue * 0.60)
                ELSE realized_revenue 
            END
        ) AS sim_rev,
        SUM(
            CASE 
                WHEN city_tier = 'Tier-3' AND payment_method = 'COD' THEN (total_logistics_loss * 0.15)
                ELSE total_logistics_loss 
            END
        ) AS sim_loss
    FROM orders
)
SELECT 
    'INR ' || PRINTF('%,d', CAST(c.current_margin AS INT)) AS current_net_margin,
    'INR ' || PRINTF('%,d', CAST((s.sim_rev - s.sim_loss) AS INT)) AS projected_net_margin,
    'INR ' || PRINTF('%,d', CAST(((s.sim_rev - s.sim_loss) - c.current_margin) AS INT)) AS net_gain_inr,
    '+' || ROUND((((s.sim_rev - s.sim_loss) - c.current_margin) * 100.0 / c.current_margin), 2) || '%' AS margin_growth_pct
FROM CurrentState c
CROSS JOIN SimulatedPolicy s;
"""
cursor.execute(q5)
print_table("QUERY 5: WHAT-IF SCENARIO (Financial Impact of Restricting Tier-3 COD)", 
            ["Current Net Margin", "Projected Net Margin", "Net Gain (INR)", "Margin Growth %"],
            cursor.fetchall())

conn.close()
print("[INFO] Analytical queries executed successfully across 25,000 orders.")
