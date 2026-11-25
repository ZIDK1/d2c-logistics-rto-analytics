"""
Parameterized SQLite analytical queries for D2C Logistics & RTO Intelligence.
Executes live aggregations across all 25,000 rows in data/d2c_logistics.db.
"""

import os
import sqlite3
from contextlib import closing
from typing import Any, Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "d2c_logistics.db")

SORTABLE_COLUMNS = {
    "rto_risk_score": "rto_risk_score",
    "net_order_value": "net_order_value",
    "order_date": "order_date",
    "city": "city",
    "total_logistics_loss": "total_logistics_loss",
}


def get_connection() -> sqlite3.Connection:
    """Open a read-only SQLite connection with Row mapping."""
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def build_where(filters: Dict[str, str], include_category: bool = True) -> Tuple[str, List[Any]]:
    """Build parameterized WHERE clause from filter dictionary."""
    clauses: List[str] = []
    params: List[Any] = []

    tier = filters.get("tier", "ALL")
    if tier and tier != "ALL":
        clauses.append("city_tier = ?")
        params.append(tier)

    payment = filters.get("payment", "ALL")
    if payment and payment != "ALL":
        clauses.append("payment_method = ?")
        params.append(payment)

    carrier = filters.get("carrier", "ALL")
    if carrier and carrier != "ALL":
        clauses.append("courier_partner = ?")
        params.append(carrier)

    category = filters.get("category", "ALL")
    if include_category and category and category != "ALL":
        clauses.append("product_category = ?")
        params.append(category)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def get_summary(filters: Dict[str, str]) -> Dict[str, Any]:
    """Compute exact KPIs, trends, Pareto window metrics, and carrier SLAs from SQLite."""
    where_sql, params = build_where(filters, include_category=True)

    with closing(get_connection()) as conn:
        cur = conn.cursor()

        # 1. Core KPI metrics + COD vs Prepaid split
        kpi_row = cur.execute(
            f"""
            SELECT
                COUNT(*) AS total_orders,
                COALESCE(SUM(rto_flag), 0) AS rto_orders,
                COALESCE(SUM(gross_order_value), 0) AS gmv,
                COALESCE(SUM(realized_revenue), 0) AS realized_revenue,
                COALESCE(SUM(total_logistics_loss), 0) AS dead_loss,
                COALESCE(SUM(CASE WHEN risk_tier = 'High Risk' THEN 1 ELSE 0 END), 0) AS high_risk_orders,
                COALESCE(SUM(preventable_loss_inr), 0) AS preventable_loss,
                COALESCE(SUM(CASE WHEN payment_method = 'COD' THEN 1 ELSE 0 END), 0) AS cod_orders,
                COALESCE(SUM(CASE WHEN payment_method = 'COD' THEN rto_flag ELSE 0 END), 0) AS cod_rtos,
                COALESCE(SUM(CASE WHEN payment_method != 'COD' THEN 1 ELSE 0 END), 0) AS prepaid_orders,
                COALESCE(SUM(CASE WHEN payment_method != 'COD' THEN rto_flag ELSE 0 END), 0) AS prepaid_rtos,
                COALESCE(SUM(CASE WHEN risk_tier = 'High Risk' AND payment_method = 'COD' THEN 1 ELSE 0 END), 0) AS high_risk_cod_orders
            FROM orders
            {where_sql}
            """,
            params,
        ).fetchone()

        total_orders = kpi_row["total_orders"] or 0
        rto_orders = kpi_row["rto_orders"] or 0
        gmv = float(kpi_row["gmv"])
        realized_rev = float(kpi_row["realized_revenue"])
        dead_loss = float(kpi_row["dead_loss"])
        cod_rate = (kpi_row["cod_rtos"] * 100.0 / kpi_row["cod_orders"]) if kpi_row["cod_orders"] else 0.0
        prepaid_rate = (kpi_row["prepaid_rtos"] * 100.0 / kpi_row["prepaid_orders"]) if kpi_row["prepaid_orders"] else 0.0
        disparity = (cod_rate / prepaid_rate) if prepaid_rate > 0 else 0.0

        kpis = {
            "total_orders": total_orders,
            "rto_orders": rto_orders,
            "gmv": round(gmv, 2),
            "realized_revenue": round(realized_rev, 2),
            "dead_loss": round(dead_loss, 2),
            "net_margin": round(realized_rev - dead_loss, 2),
            "rto_rate": round((rto_orders * 100.0 / total_orders) if total_orders else 0.0, 2),
            "cod_rto_rate": round(cod_rate, 1),
            "prepaid_rto_rate": round(prepaid_rate, 1),
            "disparity_ratio": round(disparity, 1),
            "high_risk_orders": kpi_row["high_risk_orders"] or 0,
            "high_risk_cod_orders": kpi_row["high_risk_cod_orders"] or 0,
            "preventable_loss": round(float(kpi_row["preventable_loss"]), 2),
        }

        # 2. Monthly trend (real SQLite GROUP BY YYYY-MM)
        monthly_rows = cur.execute(
            f"""
            SELECT
                SUBSTR(order_date, 1, 7) AS ym,
                COUNT(*) AS orders,
                COALESCE(SUM(rto_flag), 0) AS rtos,
                ROUND(COALESCE(SUM(realized_revenue), 0) / 100000.0, 2) AS rev_lakhs,
                ROUND(COALESCE(SUM(total_logistics_loss), 0) / 100000.0, 2) AS loss_lakhs
            FROM orders
            {where_sql}
            GROUP BY ym
            ORDER BY ym ASC
            """,
            params,
        ).fetchall()
        monthly = [
            {
                "month": f"{r['ym'][5:]}/{r['ym'][2:4]}",
                "orders": r["orders"],
                "rtos": r["rtos"],
                "rto_rate": round(r["rtos"] * 100.0 / r["orders"], 1) if r["orders"] else 0.0,
                "rev_lakhs": float(r["rev_lakhs"]),
                "loss_lakhs": float(r["loss_lakhs"]),
            }
            for r in monthly_rows
        ]

        # 3. Payment Method breakdown
        pay_rows = cur.execute(
            f"""
            SELECT
                payment_method,
                COUNT(*) AS orders,
                COALESCE(SUM(rto_flag), 0) AS rtos,
                ROUND(COALESCE(SUM(total_logistics_loss), 0), 2) AS loss
            FROM orders
            {where_sql}
            GROUP BY payment_method
            ORDER BY loss DESC
            """,
            params,
        ).fetchall()
        payment_mix = [
            {
                "method": r["payment_method"],
                "orders": r["orders"],
                "rtos": r["rtos"],
                "rto_rate": round(r["rtos"] * 100.0 / r["orders"], 1) if r["orders"] else 0.0,
                "loss": float(r["loss"]),
                "loss_share": round(float(r["loss"]) * 100.0 / dead_loss, 1) if dead_loss > 0 else 0.0,
            }
            for r in pay_rows
        ]

        # 4. Product Category breakdown (ignores category filter itself so user sees sibling bars)
        cat_where, cat_params = build_where(filters, include_category=False)
        cat_rows = cur.execute(
            f"""
            SELECT
                product_category,
                COUNT(*) AS orders,
                COALESCE(SUM(rto_flag), 0) AS rtos,
                ROUND(COALESCE(SUM(total_logistics_loss), 0), 2) AS loss
            FROM orders
            {cat_where}
            GROUP BY product_category
            ORDER BY (COALESCE(SUM(rto_flag), 0) * 1.0 / COUNT(*)) DESC
            """,
            cat_params,
        ).fetchall()
        categories = [
            {
                "category": r["product_category"],
                "orders": r["orders"],
                "rtos": r["rtos"],
                "rto_rate": round(r["rtos"] * 100.0 / r["orders"], 1) if r["orders"] else 0.0,
                "loss": float(r["loss"]),
            }
            for r in cat_rows
        ]

        # 5. Regional Pareto 80/20 via SQL Window Functions
        pareto_rows = cur.execute(
            f"""
            WITH CityAgg AS (
                SELECT
                    pincode,
                    city,
                    state,
                    city_tier,
                    COUNT(*) AS orders,
                    COALESCE(SUM(rto_flag), 0) AS rtos,
                    COALESCE(SUM(total_logistics_loss), 0) AS loss
                FROM orders
                {where_sql}
                GROUP BY pincode, city, state, city_tier
            ),
            Windowed AS (
                SELECT
                    *,
                    SUM(loss) OVER (ORDER BY loss DESC, pincode ASC) AS running_loss,
                    SUM(loss) OVER () AS total_loss
                FROM CityAgg
            )
            SELECT
                pincode,
                city,
                state,
                city_tier,
                orders,
                rtos,
                ROUND(rtos * 100.0 / orders, 1) AS rto_rate,
                ROUND(loss, 2) AS loss,
                ROUND(CASE WHEN total_loss > 0 THEN running_loss * 100.0 / total_loss ELSE 0 END, 1) AS cum_pct
            FROM Windowed
            ORDER BY loss DESC, pincode ASC
            """,
            params,
        ).fetchall()
        pareto = [
            {
                "pin": r["pincode"],
                "city": r["city"],
                "state": r["state"],
                "tier": r["city_tier"],
                "orders": r["orders"],
                "rtos": r["rtos"],
                "rto_rate": float(r["rto_rate"]),
                "loss": float(r["loss"]),
                "loss_lakhs": round(float(r["loss"]) / 100000.0, 2),
                "cum_pct": float(r["cum_pct"]),
            }
            for r in pareto_rows
        ]

        # 6. Carrier SLA Scorecard
        carrier_rows = cur.execute(
            f"""
            SELECT
                courier_partner,
                COUNT(*) AS shipments,
                COALESCE(SUM(sla_breached), 0) AS delayed,
                ROUND(AVG(actual_delivery_days - promised_delivery_days), 2) AS avg_delay,
                ROUND(SUM(CASE WHEN sla_breached = 1 THEN rto_flag ELSE 0 END) * 100.0 / NULLIF(SUM(sla_breached), 0), 1) AS delayed_rto,
                ROUND(SUM(CASE WHEN sla_breached = 0 THEN rto_flag ELSE 0 END) * 100.0 / NULLIF(COUNT(*) - SUM(sla_breached), 0), 1) AS ontime_rto,
                ROUND(COALESCE(SUM(total_logistics_loss), 0), 2) AS total_loss
            FROM orders
            {where_sql}
            GROUP BY courier_partner
            ORDER BY (COALESCE(SUM(sla_breached), 0) * 1.0 / COUNT(*)) ASC
            """,
            params,
        ).fetchall()
        carriers = [
            {
                "name": r["courier_partner"],
                "shipments": r["shipments"],
                "delayed": r["delayed"],
                "breach_rate": round(r["delayed"] * 100.0 / r["shipments"], 1) if r["shipments"] else 0.0,
                "avg_delay": float(r["avg_delay"] or 0.0),
                "delayed_rto": float(r["delayed_rto"] or 0.0),
                "ontime_rto": float(r["ontime_rto"] or 0.0),
                "total_loss": float(r["total_loss"]),
            }
            for r in carrier_rows
        ]

        # 7. Delay Penalty Curve (0d to 5+ days)
        delay_rows = cur.execute(
            f"""
            SELECT
                MIN(5, MAX(0, actual_delivery_days - promised_delivery_days)) AS delay_bucket,
                COUNT(*) AS orders,
                COALESCE(SUM(rto_flag), 0) AS rtos
            FROM orders
            {where_sql}
            GROUP BY delay_bucket
            ORDER BY delay_bucket ASC
            """,
            params,
        ).fetchall()
        bucket_map = {r["delay_bucket"]: r for r in delay_rows}
        delay_labels = ["On-Time", "+1 Day", "+2 Days", "+3 Days", "+4 Days", "+5+ Days"]
        delay_curve = []
        for idx, lbl in enumerate(delay_labels):
            row = bucket_map.get(idx)
            ords = row["orders"] if row else 0
            rtos = row["rtos"] if row else 0
            delay_curve.append(
                {
                    "label": lbl,
                    "orders": ords,
                    "rto_rate": round(rtos * 100.0 / ords, 1) if ords else 0.0,
                }
            )

        return {
            "source": "sqlite_live",
            "kpis": kpis,
            "monthly": monthly,
            "payment_mix": payment_mix,
            "categories": categories,
            "pareto": pareto,
            "carriers": carriers,
            "delay_curve": delay_curve,
        }


def get_orders_page(filters: Dict[str, str], max_page_size: int = 100) -> Dict[str, Any]:
    """Return paginated, filtered, sorted orders from the SQLite orders table."""
    where_sql, params = build_where(filters, include_category=True)
    extra_clauses = [where_sql.replace("WHERE ", "")] if where_sql else []

    risk_tier = filters.get("risk_tier", "ALL")
    if risk_tier and risk_tier != "ALL":
        extra_clauses.append("risk_tier = ?")
        params.append(risk_tier)

    search = (filters.get("search") or "").strip()
    if search:
        like = f"%{search}%"
        extra_clauses.append("(order_id LIKE ? OR customer_id LIKE ? OR city LIKE ? OR pincode LIKE ?)")
        params.extend([like, like, like, like])

    final_where = f"WHERE {' AND '.join(extra_clauses)}" if extra_clauses else ""

    sort_col = SORTABLE_COLUMNS.get(filters.get("sort", "rto_risk_score"), "rto_risk_score")
    sort_dir = "ASC" if (filters.get("dir") or "").upper() == "ASC" else "DESC"

    try:
        page = max(1, int(filters.get("page", 1)))
    except ValueError:
        page = 1
    try:
        page_size = min(max_page_size, max(10, int(filters.get("page_size", 25))))
    except ValueError:
        page_size = 25
    offset = (page - 1) * page_size

    with closing(get_connection()) as conn:
        cur = conn.cursor()
        total = cur.execute(f"SELECT COUNT(*) FROM orders {final_where}", params).fetchone()[0]
        rows = cur.execute(
            f"""
            SELECT
                order_id, order_date, customer_id, pincode, city, city_tier,
                product_category, payment_method, net_order_value,
                courier_partner, actual_delivery_days, promised_delivery_days,
                rto_risk_score, risk_tier, action_recommendation, order_status
            FROM orders
            {final_where}
            ORDER BY {sort_col} {sort_dir}, net_order_value DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "rows": [dict(r) for r in rows],
        }


def get_export_rows(filters: Dict[str, str], limit: int = 5000) -> List[Dict[str, Any]]:
    """Fetch filtered dispatch queue rows for CSV export."""
    data = get_orders_page({**filters, "page": "1", "page_size": str(limit)}, max_page_size=limit)
    return data["rows"]
