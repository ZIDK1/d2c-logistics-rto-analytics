# Power BI Desktop Implementation Guide
**Author:** Zaid Kaiser ([zaidkaiser2006@gmail.com](mailto:zaidkaiser2006@gmail.com))  
**Table Name:** `rto_scored_orders` (`data/rto_scored_orders.csv`)  
**Theme:** `dashboard/power_bi_corporate_theme.json`  
**TMDL Measures Script:** `dashboard/power_bi_model.tmdl`

---

## 1. Import Data & Apply Theme

1. Open **Power BI Desktop** -> **Home -> Get Data -> Text/CSV**.
2. Load `data/rto_scored_orders.csv` (keep default table name `rto_scored_orders`).
3. Optional Star Schema extension: also load `data/customers.csv` and `data/pincode_master.csv`, then link `pincode` (`1:*`) and `customer_id` (`1:*`) in **Model View**.
4. In the **Design** ribbon -> **Themes dropdown -> Browse for themes...** -> select `dashboard/power_bi_corporate_theme.json`.

---

## 2. Import Measures & What-If Parameter (TMDL View)

In Power BI Desktop (versions with TMDL View enabled on the left sidebar):
1. Open the **TMDL** tab on the left rail.
2. Paste the contents of `dashboard/power_bi_model.tmdl` into the TMDL editor.
3. Click **Apply** to add all **17 formatted DAX measures** under `rto_scored_orders` along with the `Policy_Conversion_Rate` parameter table (`0` to `100` step `5`).

---

## 3. Report Layout (4 Pages)

### Page 1: Executive Overview
* **Top Row — 5 Card Visuals:**
  - `Gross Merchandise Value`
  - `Realized Revenue`
  - `Dead Freight Loss`
  - `Overall RTO Rate %`
  - `COD RTO Rate %` (or `COD Risk Disparity`)
* **Top Slicer Bar (Horizontal Slicers):** `city_tier`, `payment_method`, `courier_partner`.
* **Left Chart (Line and Clustered Column Chart):**
  - X-axis: `order_date` (Month hierarchy)
  - Column Y-axis: `Realized Revenue`, `Dead Freight Loss`
  - Line Y-axis: `Overall RTO Rate %`
* **Right Chart (Donut Chart):**
  - Legend: `payment_method`
  - Values: `Dead Freight Loss`
* **Bottom Left (Clustered Bar Chart):**
  - Y-axis: `product_category`
  - X-axis: `Overall RTO Rate %` (add Constant Line at `0.20` for 20% target)

### Page 2: Regional Pareto (80/20 Loss)
* **Top Visual (Line and Clustered Column Chart):**
  - X-axis: `city` (Sort descending by `Dead Freight Loss`)
  - Column Y-axis: `Dead Freight Loss`
* **Bottom Table Visual:**
  - Columns: `pincode`, `city`, `state`, `city_tier`, `Total Orders`, `Overall RTO Rate %`, `Dead Freight Loss`.

### Page 3: Carrier SLA & Delay Attribution
* **Top Row:** 4 Multi-Row Cards / Table per `courier_partner` showing `Total Orders`, `Carrier SLA Breach Rate %`, `Delayed RTO Rate %`, `On-Time RTO Rate %`.
* **Left Chart (Clustered Column Chart):**
  - X-axis: `courier_partner`
  - Y-axis: `Carrier SLA Breach Rate %`, `Delayed RTO Rate %`, `On-Time RTO Rate %`.
* **Right Chart (Line Chart):**
  - Create a calculated column `Delay Days = MIN(5, MAX(0, rto_scored_orders[actual_delivery_days] - rto_scored_orders[promised_delivery_days]))`.
  - X-axis: `Delay Days`, Y-axis: `Overall RTO Rate %`.

### Page 4: Policy Simulator & Dispatch Queue
* **Top Slicer (Single Value Slider):** `'Policy_Conversion_Rate'[Value]`.
* **KPI Cards:** `High Risk Orders`, `Preventable Freight Loss`, `Projected Freight Savings`, `Projected Margin Expansion %`.
* **Table Visual:** `order_id`, `order_date`, `customer_id`, `city`, `city_tier`, `payment_method`, `net_order_value`, `courier_partner`, `rto_risk_score`, `risk_tier`, `action_recommendation` (sort descending by `rto_risk_score`).

Save your report via **File -> Save As -> `D2C_Logistics_Analytics.pbix`**.
