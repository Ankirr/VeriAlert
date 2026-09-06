"""
Test and validation script for Phase 6 Delivery Layer.
Verifies all new FastAPI endpoints, filtering parameters, mathematical audit breakdowns,
and pipeline status reporting.
"""
import sys
import asyncio
from pathlib import Path

# Ensure stdout handles UTF-8 characters on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import httpx
from app.main import app

async def run_tests():
    print("=" * 70)
    print("  PHASE 6: DELIVERY LAYER API & AUDIT VERIFICATION")
    print("=" * 70)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        print("1. Testing GET /api/health...")
        r = await client.get("/api/health")
        assert r.status_code == 200, f"Health check failed: {r.status_code}"
        print(f"   [PASS] Health response: {r.json()['status']} (DB: {r.json()['database']})")

        # 2. Stats
        print("\n2. Testing GET /api/stats...")
        r = await client.get("/api/stats")
        assert r.status_code == 200
        stats = r.json()
        print(f"   [PASS] Total Clusters: {stats['total_clusters']}, Reports: {stats['total_underlying_reports']}, Avg Trust: {stats['average_trust_score']}")

        # 3. Regions endpoint
        print("\n3. Testing GET /api/regions...")
        r = await client.get("/api/regions")
        assert r.status_code == 200
        regions = r.json().get("regions", [])
        print(f"   [PASS] Found {len(regions)} distinct regions/locations in database.")
        print(f"          Sample: {regions[:5]}")

        # 4. Filter alerts by disaster_type
        print("\n4. Testing GET /api/alerts (Standard listing & filtering)...")
        r = await client.get("/api/alerts?limit=5")
        assert r.status_code == 200
        alerts = r.json()
        print(f"   [PASS] Retrieved {len(alerts)} alerts.")
        assert len(alerts) > 0, "Expected at least 1 alert in database"
        sample_id = alerts[0]["id"]

        # 5. Filter by severity
        print("\n5. Testing GET /api/alerts?severity=verified...")
        r = await client.get("/api/alerts?severity=verified")
        assert r.status_code == 200
        verified_alerts = r.json()
        print(f"   [PASS] Retrieved {len(verified_alerts)} VERIFIED alerts.")

        # 6. Filter by region
        sample_loc = alerts[0]["location_name"].split(",")[0].strip()
        print(f"\n6. Testing GET /api/alerts?region={sample_loc}...")
        r = await client.get(f"/api/alerts?region={sample_loc}")
        assert r.status_code == 200
        region_alerts = r.json()
        print(f"   [PASS] Retrieved {len(region_alerts)} alerts matching region '{sample_loc}'.")

        # 7. Alert detail with mathematical breakdown
        print(f"\n7. Testing GET /api/alerts/{sample_id} (Mathematical Audit Breakdown)...")
        r = await client.get(f"/api/alerts/{sample_id}")
        assert r.status_code == 200
        detail = r.json()
        breakdown = detail.get("trust_score_breakdown")
        assert breakdown is not None, "Alert detail must contain trust_score_breakdown!"
        
        print(f"   [PASS] Formula: {breakdown['formula']}")
        print(f"   [PASS] Source Authority (S_auth): {breakdown['components']['source_authority']['score']}")
        print(f"   [PASS] Corroboration Factor:      {breakdown['components']['corroboration']['score']} ({breakdown['components']['corroboration']['independent_sources_count']} sources)")
        print(f"   [PASS] Contradiction Penalty:     {breakdown['components']['contradiction_penalty']['penalty_value']}")
        print(f"   [PASS] Final Trust Score:         {breakdown['final_trust_score']} ({breakdown['veracity_band']})")
        print(f"   [PASS] Audit Defense Explanation:\n          \"{breakdown['audit_explanation']}\"")

        # 8. Map GeoJSON points
        print("\n8. Testing GET /api/map/points...")
        r = await client.get("/api/map/points")
        assert r.status_code == 200
        geojson = r.json()
        assert geojson["type"] == "FeatureCollection"
        print(f"   [PASS] Map GeoJSON returned {len(geojson['features'])} Point features.")

        # 9. Pipeline status check
        print("\n9. Testing GET /api/pipeline/status...")
        r = await client.get("/api/pipeline/status")
        assert r.status_code == 200
        status = r.json()
        print(f"   [PASS] Pipeline status: '{status['status']}', Current Phase: {status['current_phase']} ({status['phase_name']})")

    print("\n" + "=" * 70)
    print("  ALL PHASE 6 API & AUDIT TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_tests())
