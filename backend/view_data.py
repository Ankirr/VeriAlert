import sqlite3
import json
import sys
from pathlib import Path

db_path = Path(__file__).resolve().parent / "disaster_app.db"

def inspect_db():
    if not db_path.exists():
        print(f"Database file not found at {db_path}. Please run 'python app/run_phase1.py' first.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Total count
    cursor.execute("SELECT COUNT(*) FROM raw_disaster_items")
    total_count = cursor.fetchone()[0]
    print(f"\n==================================================")
    print(f"  DISASTER DATABASE INSPECTION ({total_count} TOTAL ITEMS)")
    print(f"==================================================")

    # Count by source_type
    cursor.execute("SELECT source_type, COUNT(*) FROM raw_disaster_items GROUP BY source_type")
    print("\n--- Summary by Source Type ---")
    for stype, count in cursor.fetchall():
        print(f"  • {stype}: {count} items")

    # Fetch 10 most recent records
    cursor.execute("""
        SELECT source, source_type, title, location_name, latitude, longitude, timestamp, url 
        FROM raw_disaster_items 
        ORDER BY timestamp DESC 
        LIMIT 10
    """)
    rows = cursor.fetchall()

    print("\n--- 10 Most Recent Collected Disaster Alerts ---")
    for idx, row in enumerate(rows, 1):
        source, stype, title, loc, lat, lon, ts, url = row
        print(f"\n[{idx}] {title}")
        print(f"    Source   : {source} ({stype})")
        print(f"    Location : {loc or 'N/A'} (Lat: {lat}, Lon: {lon})")
        print(f"    Time     : {ts}")
        print(f"    URL      : {url or 'N/A'}")

    conn.close()

if __name__ == "__main__":
    inspect_db()
