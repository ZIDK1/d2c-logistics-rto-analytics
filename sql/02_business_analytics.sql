-- ====================================================================
-- Analytical Queries: D2C E-Commerce Logistics & Revenue Protection
-- Author: Zaid Kaiser (zaidkaiser2006@gmail.com)
-- Description: Business analytics scripts covering executive metrics, 
--              COD vulnerability, Pareto distribution, carrier SLAs, 
--              repeat-cancellation patterns, and policy simulation.
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. Executive Summary: Core Volumes & Financial Exposure
-- --------------------------------------------------------------------
SELECT 
    COUNT(order_id) AS total_orders,
    SUM(gross_order_value) AS total_gross_merchandise_value,
    SUM(realized_revenue) AS total_realized_revenue,
    SUM(total_logistics_loss) AS total_rto_dead_loss,
    ROUND(SUM(rto_flag) * 100.0 / COUNT(order_id), 2) AS overall_rto_rate_pct,
    ROUND(SUM(total_logistics_loss) * 100.0 / NULLIF(SUM(gross_order_value), 0), 2) AS logistics_loss_pct_of_gmv
FROM orders;


-- --------------------------------------------------------------------
-- 2. Payment Method Performance: Cash on Delivery vs Prepaid
-- --------------------------------------------------------------------
SELECT 
    payment_method,
    COUNT(order_id) AS order_volume,
    ROUND(COUNT(order_id) * 100.0 / SUM(COUNT(order_id)) OVER(), 2) AS volume_share_pct,
    SUM(CASE WHEN rto_flag = 1 THEN 1 ELSE 0 END) AS rto_orders,
    ROUND(SUM(rto_flag) * 100.0 / COUNT(order_id), 2) AS rto_rate_pct,
    SUM(total_logistics_loss) AS logistics_loss_inr,
    ROUND(AVG(actual_delivery_days), 1) AS avg_delivery_days
FROM orders
GROUP BY payment_method
ORDER BY rto_rate_pct DESC;


-- --------------------------------------------------------------------
-- 3. Pareto 80/20 Analysis: Regional Loss Concentration
-- Identifies critical pincodes accounting for the majority of freight loss.
-- --------------------------------------------------------------------
WITH PincodeLossSummary AS (
    SELECT 
        pincode,
        city,
        state,
        city_tier,
        COUNT(order_id) AS order_count,
        SUM(rto_flag) AS rto_count,
        ROUND(SUM(rto_flag) * 100.0 / COUNT(order_id), 2) AS pincode_rto_pct,
        SUM(total_logistics_loss) AS total_loss_inr
    FROM orders
    GROUP BY pincode, city, state, city_tier
),
RankedPincodes AS (
    SELECT 
        *,
        SUM(total_loss_inr) OVER(ORDER BY total_loss_inr DESC) AS running_loss_inr,
        SUM(total_loss_inr) OVER() AS grand_total_loss_inr
    FROM PincodeLossSummary
)
SELECT 
    pincode,
    city,
    state,
    city_tier,
    order_count,
    rto_count,
    pincode_rto_pct,
    total_loss_inr,
    ROUND(running_loss_inr * 100.0 / grand_total_loss_inr, 2) AS cumulative_loss_pct,
    CASE 
        WHEN (running_loss_inr * 100.0 / grand_total_loss_inr) <= 60 THEN 'Tier A Loss (High Priority)'
        WHEN (running_loss_inr * 100.0 / grand_total_loss_inr) <= 85 THEN 'Tier B Loss (Medium Priority)'
        ELSE 'Tier C Loss (Stable)'
    END AS loss_classification
FROM RankedPincodes
ORDER BY total_loss_inr DESC;


-- --------------------------------------------------------------------
-- 4. Carrier Partner SLA Performance & Delay Penalties
-- --------------------------------------------------------------------
SELECT 
    courier_partner,
    COUNT(order_id) AS assigned_shipments,
    SUM(sla_breached) AS delayed_orders,
    ROUND(SUM(sla_breached) * 100.0 / COUNT(order_id), 2) AS sla_breach_rate_pct,
    ROUND(AVG(actual_delivery_days - promised_delivery_days), 2) AS avg_delay_days,
    ROUND(SUM(CASE WHEN sla_breached = 1 THEN rto_flag ELSE 0 END) * 100.0 / NULLIF(SUM(sla_breached), 0), 2) AS rto_rate_when_delayed_pct,
    ROUND(SUM(CASE WHEN sla_breached = 0 THEN rto_flag ELSE 0 END) * 100.0 / NULLIF(COUNT(order_id) - SUM(sla_breached), 0), 2) AS rto_rate_when_on_time_pct,
    SUM(total_logistics_loss) AS total_courier_loss_inr
FROM orders
GROUP BY courier_partner
ORDER BY sla_breach_rate_pct DESC;


-- --------------------------------------------------------------------
-- 5. Repeat Cancellation Pattern Analysis (Window Functions)
-- --------------------------------------------------------------------
WITH CustomerOrderSequence AS (
    SELECT 
        customer_id,
        order_id,
        order_date,
        payment_method,
        rto_flag,
        gross_order_value,
        ROW_NUMBER() OVER(PARTITION BY customer_id ORDER BY order_date) AS order_sequence_num,
        LAG(rto_flag, 1) OVER(PARTITION BY customer_id ORDER BY order_date) AS prev_order_rto_flag,
        SUM(rto_flag) OVER(PARTITION BY customer_id) AS total_customer_rtos,
        COUNT(order_id) OVER(PARTITION BY customer_id) AS total_customer_orders
    FROM orders
)
SELECT 
    customer_id,
    total_customer_orders,
    total_customer_rtos,
    ROUND(total_customer_rtos * 100.0 / total_customer_orders, 1) AS customer_rto_rate_pct,
    SUM(CASE WHEN rto_flag = 1 AND prev_order_rto_flag = 1 THEN 1 ELSE 0 END) AS consecutive_rto_count,
    CASE 
        WHEN total_customer_orders >= 3 AND (total_customer_rtos * 1.0 / total_customer_orders) >= 0.70 THEN 'Restricted (High Non-Delivery Risk)'
        WHEN total_customer_orders >= 2 AND (total_customer_rtos * 1.0 / total_customer_orders) >= 0.50 THEN 'Flagged (Requires Verification)'
        ELSE 'Normal Profile'
    END AS account_status
FROM CustomerOrderSequence
GROUP BY customer_id, total_customer_orders, total_customer_rtos
HAVING total_customer_orders >= 3 AND total_customer_rtos >= 2
ORDER BY total_customer_rtos DESC, customer_rto_rate_pct DESC
LIMIT 50;


-- --------------------------------------------------------------------
-- 6. Financial Policy Simulation: Tier-3 COD Restriction Impact
-- Evaluates net margin difference if Tier-3 COD orders are incentivized/restricted.
-- --------------------------------------------------------------------
WITH CurrentState AS (
    SELECT 
        SUM(realized_revenue) AS current_realized_rev,
        SUM(total_logistics_loss) AS current_logistics_loss,
        SUM(realized_revenue) - SUM(total_logistics_loss) AS current_net_margin
    FROM orders
),
SimulatedPolicy AS (
    -- Assumptions:
    -- In Tier-3 COD orders, 60% of genuine buyers convert to digital payments.
    -- 40% non-genuine / speculative orders drop off, avoiding full reverse freight loss.
    SELECT 
        SUM(
            CASE 
                WHEN city_tier = 'Tier-3' AND payment_method = 'COD' THEN (realized_revenue * 0.60)
                ELSE realized_revenue 
            END
        ) AS simulated_realized_rev,
        SUM(
            CASE 
                WHEN city_tier = 'Tier-3' AND payment_method = 'COD' THEN (total_logistics_loss * 0.15)
                ELSE total_logistics_loss 
            END
        ) AS simulated_logistics_loss
    FROM orders
)
SELECT 
    ROUND(c.current_net_margin, 2) AS current_net_margin_inr,
    ROUND((s.simulated_realized_rev - s.simulated_logistics_loss), 2) AS projected_net_margin_inr,
    ROUND(((s.simulated_realized_rev - s.simulated_logistics_loss) - c.current_net_margin), 2) AS net_profit_increase_inr,
    ROUND((((s.simulated_realized_rev - s.simulated_logistics_loss) - c.current_net_margin) * 100.0 / c.current_net_margin), 2) AS margin_growth_pct
FROM CurrentState c
CROSS JOIN SimulatedPolicy s;


-- --------------------------------------------------------------------
-- 7. Operational Dispatch Queue View
-- Real-time prioritization view for fulfillment centers.
-- --------------------------------------------------------------------
CREATE OR REPLACE VIEW view_dispatch_priority_queue AS
SELECT 
    order_id,
    order_date,
    customer_id,
    city,
    city_tier,
    payment_method,
    net_order_value,
    courier_partner,
    rto_risk_score,
    risk_tier,
    action_recommendation
FROM orders
ORDER BY rto_risk_score DESC;
