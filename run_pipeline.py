"""
Master Pipeline Runner & Live Portal Server
Author: Zaid Kaiser (zaidkaiser2006@gmail.com)
Usage:
    python run_pipeline.py           # Runs ETL pipeline, SQL analytics, syncs index.html & opens it
    python run_pipeline.py --serve   # Starts live Django + SQLite dashboard on http://127.0.0.1:8000/
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def serve_live_portal():
    """Start the Django analytics server backed by data/d2c_logistics.db."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analytics_portal.settings")
    from django.core.management import execute_from_command_line

    def _open():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000/")

    threading.Thread(target=_open, daemon=True).start()
    print("[INFO] Starting live SQLite analytics server at http://127.0.0.1:8000/ ...")
    execute_from_command_line([sys.argv[0], "runserver", "127.0.0.1:8000", "--noreload"])


def run_etl_pipeline():
    """Execute dataset generation, risk scoring, SQLite analytics, and cube sync."""
    print("[INFO] Starting D2C Logistics Analytics Pipeline...")
    print("[INFO] Author: Zaid Kaiser (zaidkaiser2006@gmail.com)")
    print("-" * 60)

    steps = [
        ("[1/4] Running dataset generator...", "01_generate_dataset.py"),
        ("\n[2/4] Running risk scoring engine...", "02_rto_risk_engine.py"),
        ("\n[3/4] Ingesting into SQLite and executing analytical queries...", "03_run_sql_analytics.py"),
        ("\n[4/4] Synchronizing dashboard cube with dataset...", "04_sync_dashboard.py"),
    ]

    for label, script in steps:
        print(label)
        ret = subprocess.run([sys.executable, os.path.join(BASE_DIR, "scripts", script)])
        if ret.returncode != 0:
            print(f"[ERROR] Failed at {script}.")
            sys.exit(1)

    dashboard_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(dashboard_path):
        webbrowser.open("file://" + dashboard_path)
        print(f"\n[SUCCESS] Dashboard launched at: {dashboard_path}")

    print("-" * 60)
    print("[INFO] Pipeline execution finished successfully.")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        serve_live_portal()
    else:
        run_etl_pipeline()
