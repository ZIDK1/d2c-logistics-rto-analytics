"""
Dashboard Synchronization & Offline Cube Builder
Author: Zaid Kaiser (zaidkaiser2006@gmail.com)
Description: Queries data/d2c_logistics.db to precompute an exact multi-dimensional
             analytical cube and injects it into the shared dashboard template so
             both live Django/SQLite mode and static index.html produce identical
             figures across every filter combination.
"""

import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "d2c_logistics.db")
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")


def build_offline_cube(db_path: str) -> dict:
    """Compute exact pre-aggregated multi-dimensional slices from SQLite."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()

    tiers = [r[0] for r in cur.execute("SELECT DISTINCT city_tier FROM orders ORDER BY city_tier").fetchall()]
    payments = [r[0] for r in cur.execute("SELECT DISTINCT payment_method FROM orders ORDER BY payment_method").fetchall()]
    carriers = [r[0] for r in cur.execute("SELECT DISTINCT courier_partner FROM orders ORDER BY courier_partner").fetchall()]
    categories = [r[0] for r in cur.execute("SELECT DISTINCT product_category FROM orders ORDER BY product_category").fetchall()]
    ym_list = [r[0] for r in cur.execute("SELECT DISTINCT SUBSTR(order_date, 1, 7) AS ym FROM orders ORDER BY ym").fetchall()]
    months = [f"{ym[5:]}/{ym[2:4]}" for ym in ym_list]

    pin_rows = cur.execute(
        "SELECT DISTINCT pincode, city, state, city_tier FROM orders ORDER BY pincode"
    ).fetchall()
    pincodes = [{"pin": r[0], "city": r[1], "state": r[2], "tier": r[3]} for r in pin_rows]

    t_idx = {v: i for i, v in enumerate(tiers)}
    p_idx = {v: i for i, v in enumerate(payments)}
    c_idx = {v: i for i, v in enumerate(carriers)}
    cat_idx = {v: i for i, v in enumerate(categories)}
    m_idx = {v: i for i, v in enumerate(ym_list)}
    pin_idx = {p["pin"]: i for i, p in enumerate(pincodes)}

    # 1. KPI cells (Tier x Payment x Carrier x Category)
    kpi_cells = []
    for r in cur.execute(
        """
        SELECT
            city_tier, payment_method, courier_partner, product_category,
            COUNT(*),
            COALESCE(SUM(rto_flag), 0),
            ROUND(COALESCE(SUM(gross_order_value), 0), 2),
            ROUND(COALESCE(SUM(realized_revenue), 0), 2),
            ROUND(COALESCE(SUM(total_logistics_loss), 0), 2),
            COALESCE(SUM(CASE WHEN risk_tier = 'High Risk' THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN risk_tier = 'High Risk' AND payment_method = 'COD' THEN 1 ELSE 0 END), 0),
            ROUND(COALESCE(SUM(preventable_loss_inr), 0), 2)
        FROM orders
        GROUP BY city_tier, payment_method, courier_partner, product_category
        """
    ).fetchall():
        kpi_cells.append([t_idx[r[0]], p_idx[r[1]], c_idx[r[2]], cat_idx[r[3]], *r[4:]])

    # 2. Monthly cells
    monthly_cells = []
    for r in cur.execute(
        """
        SELECT
            city_tier, payment_method, courier_partner, product_category, SUBSTR(order_date, 1, 7) AS ym,
            COUNT(*),
            COALESCE(SUM(rto_flag), 0),
            ROUND(COALESCE(SUM(realized_revenue), 0), 2),
            ROUND(COALESCE(SUM(total_logistics_loss), 0), 2)
        FROM orders
        GROUP BY city_tier, payment_method, courier_partner, product_category, ym
        """
    ).fetchall():
        monthly_cells.append([t_idx[r[0]], p_idx[r[1]], c_idx[r[2]], cat_idx[r[3]], m_idx[r[4]], *r[5:]])

    # 3. Pareto cells (Pincode x Payment x Carrier x Category)
    pareto_cells = []
    for r in cur.execute(
        """
        SELECT
            pincode, payment_method, courier_partner, product_category,
            COUNT(*),
            COALESCE(SUM(rto_flag), 0),
            ROUND(COALESCE(SUM(total_logistics_loss), 0), 2)
        FROM orders
        GROUP BY pincode, payment_method, courier_partner, product_category
        """
    ).fetchall():
        pareto_cells.append([pin_idx[r[0]], p_idx[r[1]], c_idx[r[2]], cat_idx[r[3]], *r[4:]])

    # 4. Carrier cells
    carrier_cells = []
    for r in cur.execute(
        """
        SELECT
            city_tier, payment_method, courier_partner, product_category,
            COUNT(*),
            COALESCE(SUM(sla_breached), 0),
            COALESCE(SUM(actual_delivery_days - promised_delivery_days), 0),
            COALESCE(SUM(CASE WHEN sla_breached = 1 THEN rto_flag ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN sla_breached = 0 THEN rto_flag ELSE 0 END), 0),
            ROUND(COALESCE(SUM(total_logistics_loss), 0), 2)
        FROM orders
        GROUP BY city_tier, payment_method, courier_partner, product_category
        """
    ).fetchall():
        carrier_cells.append([t_idx[r[0]], p_idx[r[1]], c_idx[r[2]], cat_idx[r[3]], *r[4:]])

    # 5. Delay curve cells
    delay_cells = []
    for r in cur.execute(
        """
        SELECT
            city_tier, payment_method, courier_partner, product_category,
            MIN(5, MAX(0, actual_delivery_days - promised_delivery_days)) AS db,
            COUNT(*),
            COALESCE(SUM(rto_flag), 0)
        FROM orders
        GROUP BY city_tier, payment_method, courier_partner, product_category, db
        """
    ).fetchall():
        delay_cells.append([t_idx[r[0]], p_idx[r[1]], c_idx[r[2]], cat_idx[r[3]], *r[4:]])

    # 6. Representative sampled queue spanning all risk tiers & dimensions
    conn.row_factory = sqlite3.Row
    cur_r = conn.cursor()
    sample_rows = []
    for rt, lim in [("High Risk", 90), ("Medium Risk", 55), ("Low Risk", 55)]:
        rows = cur_r.execute(
            """
            SELECT
                order_id, order_date, customer_id, pincode, city, city_tier,
                product_category, payment_method, net_order_value,
                courier_partner, actual_delivery_days, promised_delivery_days,
                rto_risk_score, risk_tier, action_recommendation, order_status
            FROM orders
            WHERE risk_tier = ?
            ORDER BY rto_risk_score DESC, net_order_value DESC
            LIMIT ?
            """,
            (rt, lim),
        ).fetchall()
        sample_rows.extend([dict(x) for x in rows])

    conn.close()

    return {
        "dims": {
            "tiers": tiers,
            "payments": payments,
            "carriers": carriers,
            "categories": categories,
            "months": months,
            "pincodes": pincodes,
            "delayLabels": ["On-Time", "+1 Day", "+2 Days", "+3 Days", "+4 Days", "+5+ Days"],
        },
        "kpiCells": kpi_cells,
        "monthlyCells": monthly_cells,
        "paretoCells": pareto_cells,
        "carrierCells": carrier_cells,
        "delayCells": delay_cells,
        "sampleOrders": sample_rows,
    }


def main():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"SQLite database not found at {DB_PATH}. Run scripts/03_run_sql_analytics.py first.")

    print("[INFO] Building multi-dimensional analytical cube from SQLite...")
    cube = build_offline_cube(DB_PATH)
    cube_json = json.dumps(cube, separators=(",", ":"), ensure_ascii=False)

    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    start_marker = "// <OFFLINE_CUBE_START>"
    end_marker = "// <OFFLINE_CUBE_END>"
    s_idx = html.find(start_marker)
    e_idx = html.find(end_marker)
    if s_idx == -1 or e_idx == -1 or e_idx <= s_idx:
        raise RuntimeError("Offline cube markers not found in index.html.")

    new_block = f"{start_marker}\n    window.__OFFLINE_CUBE__ = {cube_json};\n    {end_marker}"
    synced_html = html[:s_idx] + new_block + html[e_idx + len(end_marker):]

    with open(INDEX_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(synced_html)
    print(f"[SUCCESS] Synced offline cube ({len(synced_html):,} bytes) -> {INDEX_HTML_PATH}")


if __name__ == "__main__":
    main()
