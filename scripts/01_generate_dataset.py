"""
Data Pipeline Script: Transaction & Logistics Generator
Author: Zaid Kaiser (zaidkaiser2006@gmail.com)
Description: Generates sample D2C e-commerce orders, customer profiles, 
             and logistics cost data for RTO supply chain analysis.
"""

import os
import csv
import random
from datetime import datetime, timedelta

# Reproducibility seed
random.seed(42)

print("[INFO] Initializing dataset generation pipeline...")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

NUM_ORDERS = 25000
NUM_CUSTOMERS = 10000

# 1. Pincodes & City Tiers (Indian E-Commerce logistics hubs)
pincodes_data = [
    # Tier 1 (Metros)
    {"pincode": "110001", "city": "New Delhi", "state": "Delhi", "tier": "Tier-1", "base_rto_risk": 0.12},
    {"pincode": "400001", "city": "Mumbai", "state": "Maharashtra", "tier": "Tier-1", "base_rto_risk": 0.10},
    {"pincode": "560001", "city": "Bengaluru", "state": "Karnataka", "tier": "Tier-1", "base_rto_risk": 0.09},
    {"pincode": "600001", "city": "Chennai", "state": "Tamil Nadu", "tier": "Tier-1", "base_rto_risk": 0.11},
    {"pincode": "700001", "city": "Kolkata", "state": "West Bengal", "tier": "Tier-1", "base_rto_risk": 0.16},
    {"pincode": "500001", "city": "Hyderabad", "state": "Telangana", "tier": "Tier-1", "base_rto_risk": 0.11},
    
    # Tier 2
    {"pincode": "302001", "city": "Jaipur", "state": "Rajasthan", "tier": "Tier-2", "base_rto_risk": 0.22},
    {"pincode": "226001", "city": "Lucknow", "state": "Uttar Pradesh", "tier": "Tier-2", "base_rto_risk": 0.26},
    {"pincode": "411001", "city": "Pune", "state": "Maharashtra", "tier": "Tier-2", "base_rto_risk": 0.14},
    {"pincode": "380001", "city": "Ahmedabad", "state": "Gujarat", "tier": "Tier-2", "base_rto_risk": 0.15},
    {"pincode": "452001", "city": "Indore", "state": "Madhya Pradesh", "tier": "Tier-2", "base_rto_risk": 0.20},
    {"pincode": "800001", "city": "Patna", "state": "Bihar", "tier": "Tier-2", "base_rto_risk": 0.31},

    # Tier 3
    {"pincode": "247001", "city": "Saharanpur", "state": "Uttar Pradesh", "tier": "Tier-3", "base_rto_risk": 0.42},
    {"pincode": "842001", "city": "Muzaffarpur", "state": "Bihar", "tier": "Tier-3", "base_rto_risk": 0.45},
    {"pincode": "324001", "city": "Kota", "state": "Rajasthan", "tier": "Tier-3", "base_rto_risk": 0.28},
    {"pincode": "282001", "city": "Agra", "state": "Uttar Pradesh", "tier": "Tier-3", "base_rto_risk": 0.38},
    {"pincode": "826001", "city": "Dhanbad", "state": "Jharkhand", "tier": "Tier-3", "base_rto_risk": 0.40},
    {"pincode": "781001", "city": "Guwahati", "state": "Assam", "tier": "Tier-3", "base_rto_risk": 0.34},
    {"pincode": "141001", "city": "Ludhiana", "state": "Punjab", "tier": "Tier-3", "base_rto_risk": 0.25},
    {"pincode": "201301", "city": "Noida", "state": "Uttar Pradesh", "tier": "Tier-1", "base_rto_risk": 0.14}
]

pincode_file = os.path.join(DATA_DIR, "pincode_master.csv")
with open(pincode_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["pincode", "city", "state", "tier", "base_rto_risk"])
    writer.writeheader()
    writer.writerows(pincodes_data)

# 2. Customer Cohort Generation
first_names = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
               "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Chiara", "Myra", "Riya", "Sneha", "Pooja"]
last_names = ["Sharma", "Verma", "Patel", "Singh", "Yadav", "Kumar", "Gupta", "Mishra", "Joshi", "Mehta",
              "Reddy", "Nair", "Rao", "Chatterjee", "Banerjee", "Das", "Choudhury", "Bose", "Khan", "Malhotra"]

customer_records = []
segments = ["New", "Occasional", "Frequent", "VIP"]
segment_weights = [0.45, 0.30, 0.20, 0.05]

for cid in range(1, NUM_CUSTOMERS + 1):
    c_pincode = random.choice(pincodes_data)
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    account_created = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 300))
    seg = random.choices(segments, weights=segment_weights, k=1)[0]
    customer_records.append({
        "customer_id": f"CUST_{cid:05d}",
        "customer_name": name,
        "default_pincode": c_pincode["pincode"],
        "account_created_date": account_created.strftime("%Y-%m-%d"),
        "customer_segment": seg
    })

customer_file = os.path.join(DATA_DIR, "customers.csv")
try:
    with open(customer_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["customer_id", "customer_name", "default_pincode", "account_created_date", "customer_segment"])
        writer.writeheader()
        writer.writerows(customer_records)
except PermissionError:
    print(f"[NOTICE] {customer_file} is currently open in Excel or another program. Using existing dataset.")
    if os.path.exists(customer_file):
        with open(customer_file, "r", encoding="utf-8") as f:
            customer_records = list(csv.DictReader(f))

# 3. Order Generation with Business Heuristics
categories = [
    {"name": "Apparel & Fashion", "avg_price": 1499, "rto_mult": 1.35},
    {"name": "Footwear", "avg_price": 2299, "rto_mult": 1.40},
    {"name": "Beauty & Personal Care", "avg_price": 799, "rto_mult": 0.65},
    {"name": "Electronics & Audio", "avg_price": 2999, "rto_mult": 0.90},
    {"name": "Home & Kitchen", "avg_price": 1299, "rto_mult": 0.85}
]

courier_partners = [
    {"name": "Delhivery", "base_cost": 75, "delay_prob": 0.12},
    {"name": "BlueDart", "base_cost": 110, "delay_prob": 0.05},
    {"name": "Shadowfax", "base_cost": 65, "delay_prob": 0.20},
    {"name": "Xpressbees", "base_cost": 70, "delay_prob": 0.16}
]

order_records = []
start_date = datetime(2025, 3, 1)

total_rto_count = 0
total_logistics_loss_sum = 0
cod_total = 0
cod_rto = 0
prepaid_total = 0
prepaid_rto = 0

for oid in range(1, NUM_ORDERS + 1):
    cust = random.choice(customer_records)
    pincode_info = next(p for p in pincodes_data if p["pincode"] == cust["default_pincode"])
    category = random.choice(categories)
    courier = random.choice(courier_partners)
    
    order_date = start_date + timedelta(days=random.randint(0, 360), hours=random.randint(8, 23), minutes=random.randint(0, 59))
    
    price_var = random.gauss(category["avg_price"], category["avg_price"] * 0.22)
    order_value = max(299, round(price_var / 10) * 10)
    
    tier = pincode_info["tier"]
    if tier == "Tier-3":
        payment_method = random.choices(["COD", "UPI", "Credit Card", "Net Banking"], weights=[0.72, 0.20, 0.05, 0.03], k=1)[0]
    elif tier == "Tier-2":
        payment_method = random.choices(["COD", "UPI", "Credit Card", "Net Banking"], weights=[0.50, 0.35, 0.10, 0.05], k=1)[0]
    else:
        payment_method = random.choices(["COD", "UPI", "Credit Card", "Net Banking"], weights=[0.28, 0.45, 0.22, 0.05], k=1)[0]
        
    discount_pct = random.choice([0, 0.05, 0.10, 0.15, 0.20])
    discount_applied = int(order_value * discount_pct)
    final_amount = order_value - discount_applied
    
    promised_delivery_days = random.choice([3, 4, 5])
    is_delayed = random.random() < courier["delay_prob"]
    actual_delivery_days = promised_delivery_days + (random.randint(2, 6) if is_delayed else random.choice([-1, 0, 1]))
    actual_delivery_days = max(1, actual_delivery_days)
    sla_breached = 1 if actual_delivery_days > promised_delivery_days else 0
    
    # Baseline Risk Modeling
    risk_score = pincode_info["base_rto_risk"] * category["rto_mult"]
    
    if payment_method == "COD":
        risk_score *= 2.25
    else:
        risk_score *= 0.32
        
    if sla_breached:
        delay_days = actual_delivery_days - promised_delivery_days
        risk_score *= (1.0 + 0.25 * delay_days)
        
    if cust["customer_segment"] == "New":
        risk_score *= 1.35
    elif cust["customer_segment"] == "VIP":
        risk_score *= 0.35
    elif cust["customer_segment"] == "Frequent":
        risk_score *= 0.65
        
    rto_prob = min(0.92, max(0.02, risk_score))
    is_rto = 1 if (random.random() < rto_prob) else 0
    
    if is_rto:
        total_rto_count += 1
        order_status = "RTO"
        if sla_breached and random.random() < 0.45:
            reason = "Delivery Delayed beyond Promised SLA"
        elif payment_method == "COD":
            reason = random.choice([
                "Customer Refused at Doorstep (Mind Changed)",
                "Customer Unreachable / Phone Switched Off",
                "Cash Not Ready / Buyer Postponed"
            ])
        else:
            reason = random.choice([
                "Address Incomplete / Incorrect Pincode",
                "Package Damaged / Open Condition"
            ])
        delivery_date = ""
        return_date = (order_date + timedelta(days=actual_delivery_days + random.randint(3, 7))).strftime("%Y-%m-%d")
    else:
        order_status = "Delivered"
        reason = "Delivered Successfully"
        delivery_date = (order_date + timedelta(days=actual_delivery_days)).strftime("%Y-%m-%d")
        return_date = ""
        
    if payment_method == "COD":
        cod_total += 1
        if is_rto: cod_rto += 1
    else:
        prepaid_total += 1
        if is_rto: prepaid_rto += 1

    # Cost breakdown (INR)
    forward_freight = courier["base_cost"] + (25 if pincode_info["tier"] == "Tier-3" else 0)
    reverse_freight = round(forward_freight * 0.90) if is_rto else 0
    packaging_cost = 35
    cod_handling_fee = 40 if payment_method == "COD" else 0
    
    if is_rto:
        total_logistics_loss = forward_freight + reverse_freight + packaging_cost + cod_handling_fee
        realized_revenue = 0
    else:
        total_logistics_loss = 0
        realized_revenue = final_amount - (forward_freight + packaging_cost + cod_handling_fee)
        
    total_logistics_loss_sum += total_logistics_loss

    order_records.append({
        "order_id": f"ORD_{oid:06d}",
        "order_date": order_date.strftime("%Y-%m-%d %H:%M:%S"),
        "customer_id": cust["customer_id"],
        "pincode": pincode_info["pincode"],
        "city": pincode_info["city"],
        "state": pincode_info["state"],
        "city_tier": pincode_info["tier"],
        "product_category": category["name"],
        "payment_method": payment_method,
        "gross_order_value": order_value,
        "discount_amount": discount_applied,
        "net_order_value": final_amount,
        "courier_partner": courier["name"],
        "promised_delivery_days": promised_delivery_days,
        "actual_delivery_days": actual_delivery_days,
        "sla_breached": sla_breached,
        "order_status": order_status,
        "rto_flag": is_rto,
        "rto_reason": reason,
        "delivery_date": delivery_date,
        "return_date": return_date,
        "forward_freight": forward_freight,
        "reverse_freight": reverse_freight,
        "packaging_cost": packaging_cost,
        "cod_handling_fee": cod_handling_fee,
        "total_logistics_loss": total_logistics_loss,
        "realized_revenue": realized_revenue
    })

order_file = os.path.join(DATA_DIR, "raw_orders.csv")
order_headers = list(order_records[0].keys())

try:
    with open(order_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=order_headers)
        writer.writeheader()
        writer.writerows(order_records)
    print(f"[SUCCESS] Generated {len(order_records):,} transactions -> {order_file}")
except PermissionError:
    print(f"[NOTICE] {order_file} is currently open in Excel or another program. Using existing dataset.")
print(f"[SUMMARY] Total RTO Rate: {(total_rto_count / NUM_ORDERS * 100):.2f}%")
print(f"[SUMMARY] Total Net Freight Loss: INR {total_logistics_loss_sum:,.2f}")
print(f"[SUMMARY] COD RTO Rate: {(cod_rto / cod_total * 100):.2f}% | Prepaid RTO Rate: {(prepaid_rto / prepaid_total * 100):.2f}%")
