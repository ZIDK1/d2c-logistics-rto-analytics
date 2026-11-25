"""
Django views serving the unified dashboard UI and live SQLite REST endpoints.
"""

import csv
import io
import os
from django.http import HttpRequest, HttpResponse, JsonResponse
from . import queries

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")


def _extract_filters(request: HttpRequest) -> dict:
    return {
        "tier": request.GET.get("tier", "ALL"),
        "payment": request.GET.get("payment", "ALL"),
        "carrier": request.GET.get("carrier", "ALL"),
        "category": request.GET.get("category", "ALL"),
        "risk_tier": request.GET.get("risk_tier", "ALL"),
        "search": request.GET.get("search", ""),
        "sort": request.GET.get("sort", "rto_risk_score"),
        "dir": request.GET.get("dir", "DESC"),
        "page": request.GET.get("page", "1"),
        "page_size": request.GET.get("page_size", "25"),
    }


def index(request: HttpRequest) -> HttpResponse:
    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        return HttpResponse(f.read(), content_type="text/html; charset=utf-8")


def api_summary(request: HttpRequest) -> JsonResponse:
    return JsonResponse(queries.get_summary(_extract_filters(request)))


def api_orders(request: HttpRequest) -> JsonResponse:
    return JsonResponse(queries.get_orders_page(_extract_filters(request)))


def api_export_csv(request: HttpRequest) -> HttpResponse:
    rows = queries.get_export_rows(_extract_filters(request))

    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        buf.write("order_id,order_date,customer_id,city,city_tier,payment_method,net_order_value,courier_partner,rto_risk_score,risk_tier,action_recommendation\n")

    resp = HttpResponse(buf.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="rto_dispatch_queue.csv"'
    return resp
