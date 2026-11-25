"""
Risk Scoring & Decision Engine
Author: Zaid Kaiser (zaidkaiser2006@gmail.com)
Description: Implements a heuristic multi-factor risk scoring pipeline to classify incoming 
             D2C orders and evaluate potential freight recovery under policy simulations.
"""

import os
import csv
from collections import defaultdict

print("[INFO] Initializing RTO risk scoring pipeline...")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
raw_orders_path = os.path.join(DATA_DIR, "raw_orders.csv")
scored_orders_path = os.path.join(DATA_DIR, "rto_scored_orders.csv")

orders = []
with open(raw_orders_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        orders.append(row)

# Sort chronologically to simulate live streaming evaluation
orders.sort(key=lambda x: x["order_date"])

cust_history = defaultdict(lambda: {"total_orders": 0, "rto_orders": 0})
pincode_history = defaultdict(lambda: {"total_orders": 0, "rto_orders": 0})

scored_records = []
total_potential_savings = 0
high_risk_count = 0

for ord in orders:
    cid = ord["customer_id"]
    pin = ord["pincode"]
    pay_method = ord["payment_method"]
    cat = ord["product_category"]
    tier = ord["city_tier"]
    
    c_tot = cust_history[cid]["total_orders"]
    c_rto = cust_history[cid]["rto_orders"]
    c_rto_rate = (c_rto / c_tot) if c_tot > 0 else 0.35
    
    p_tot = pincode_history[pin]["total_orders"]
    p_rto = pincode_history[pin]["rto_orders"]
    p_rto_rate = (p_rto / p_tot) if p_tot > 5 else 0.30
    
    # Feature Weighting Matrix:
    # 1. Payment Method (Weight: 40%)
    score = 0
    if pay_method == "COD":
        score += 38
    elif pay_method == "Net Banking":
        score += 8
    else:
        score += 4
        
    # 2. Pincode Risk Rating (Weight: 25%)
    score += min(25, int(p_rto_rate * 55))
    
    # 3. Customer Profile History (Weight: 20%)
    if c_tot == 0:
        score += 12
    else:
        score += min(20, int(c_rto_rate * 25))
        
    # 4. Product Category Vulnerability (Weight: 15%)
    if cat in ["Apparel & Fashion", "Footwear"]:
        score += 14
    elif cat in ["Electronics & Audio"]:
        score += 8
    else:
        score += 4
        
    risk_score = min(100, max(5, score))
    
    # Prescriptive thresholds
    if risk_score >= 68:
        risk_tier = "High Risk"
        recommendation = "Enforce Prepaid (INR 50 Incentive) or Dispatch OTP Verification"
        high_risk_count += 1
        if pay_method == "COD" and int(ord["rto_flag"]) == 1:
            total_potential_savings += float(ord["total_logistics_loss"])
    elif risk_score >= 40:
        risk_tier = "Medium Risk"
        recommendation = "Assign Tier-1 Courier Partner & Send Priority Dispatch Alert"
    else:
        risk_tier = "Low Risk"
        recommendation = "Standard Fast-Track Dispatch"
        
    cust_history[cid]["total_orders"] += 1
    pincode_history[pin]["total_orders"] += 1
    if int(ord["rto_flag"]) == 1:
        cust_history[cid]["rto_orders"] += 1
        pincode_history[pin]["rto_orders"] += 1
        
    row_copy = dict(ord)
    row_copy["rto_risk_score"] = risk_score
    row_copy["risk_tier"] = risk_tier
    row_copy["action_recommendation"] = recommendation
    row_copy["preventable_loss_inr"] = float(ord["total_logistics_loss"]) if (risk_tier == "High Risk" and pay_method == "COD" and int(ord["rto_flag"]) == 1) else 0.0
    
    scored_records.append(row_copy)

fieldnames = list(scored_records[0].keys())
try:
    with open(scored_orders_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scored_records)
    print(f"[SUCCESS] Scored orders saved -> {scored_orders_path} ({len(scored_records):,} records)")
except PermissionError:
    print(f"[NOTICE] {scored_orders_path} is currently open in Excel or another program. Retaining existing file.")
print(f"[SUMMARY] High Risk Orders Flagged: {high_risk_count:,} ({(high_risk_count / len(orders) * 100):.1f}%)")
print(f"[SUMMARY] Total Preventable Logistics Loss: INR {total_potential_savings:,.2f}")
