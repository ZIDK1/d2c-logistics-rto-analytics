-- ====================================================================
-- Database Schema: D2C E-Commerce Logistics & RTO Analytics
-- Author: Zaid Kaiser (zaidkaiser2006@gmail.com)
-- Environment: PostgreSQL / MySQL / BigQuery compatible
-- ====================================================================

-- Master Table: Pincode Reference Data
DROP TABLE IF EXISTS pincode_master;
CREATE TABLE pincode_master (
    pincode VARCHAR(10) PRIMARY KEY,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(50) NOT NULL,
    tier VARCHAR(10) NOT NULL,
    base_rto_risk DECIMAL(4, 2) NOT NULL
);

-- Master Table: Customers
DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    default_pincode VARCHAR(10) NOT NULL,
    account_created_date DATE NOT NULL,
    customer_segment VARCHAR(20) NOT NULL,
    FOREIGN KEY (default_pincode) REFERENCES pincode_master(pincode)
);

-- Fact Table: Orders & Shipping Transactions
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    order_id VARCHAR(20) PRIMARY KEY,
    order_date TIMESTAMP NOT NULL,
    customer_id VARCHAR(20) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(50) NOT NULL,
    city_tier VARCHAR(10) NOT NULL,
    product_category VARCHAR(50) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    gross_order_value DECIMAL(10, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) NOT NULL,
    net_order_value DECIMAL(10, 2) NOT NULL,
    courier_partner VARCHAR(50) NOT NULL,
    promised_delivery_days INT NOT NULL,
    actual_delivery_days INT NOT NULL,
    sla_breached INT NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    rto_flag INT NOT NULL,
    rto_reason VARCHAR(100),
    delivery_date DATE,
    return_date DATE,
    forward_freight DECIMAL(10, 2) NOT NULL,
    reverse_freight DECIMAL(10, 2) NOT NULL,
    packaging_cost DECIMAL(10, 2) NOT NULL,
    cod_handling_fee DECIMAL(10, 2) NOT NULL,
    total_logistics_loss DECIMAL(10, 2) NOT NULL,
    realized_revenue DECIMAL(10, 2) NOT NULL,
    -- Engine outputs
    rto_risk_score INT,
    risk_tier VARCHAR(20),
    action_recommendation VARCHAR(150),
    preventable_loss_inr DECIMAL(10, 2),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (pincode) REFERENCES pincode_master(pincode)
);

-- Optimization Indexes
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_pincode ON orders(pincode);
CREATE INDEX idx_orders_payment_status ON orders(payment_method, rto_flag);
CREATE INDEX idx_orders_courier_sla ON orders(courier_partner, sla_breached);
CREATE INDEX idx_orders_risk_tier ON orders(risk_tier);
