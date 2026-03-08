import asyncio
import httpx
import time
import os
import argparse

# Config
BACKEND_URL = "http://localhost:8000/api/predict"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc3Mjk2NDAwOX0.CRSpeV_M15EbBXbgIJdzPYiPUgyIGE0JqHAvXjq9Wgg"
TEST_IMAGE = "giloma.jpg"

async def send_prediction(client, idx):
    start = time.perf_counter()
    files = {'file': ('image.jpg', open(TEST_IMAGE, 'rb'), 'image/jpeg')}
    data = {'user_id': '3', 'scan_type': 'MRI'}
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    
    try:
        resp = await client.post(BACKEND_URL, files=files, data=data, headers=headers, timeout=60.0)
        if resp.status_code == 200:
            res = resp.json()
            scan_id = res.get('id')
            if not scan_id:
                print(f"[{idx:>2}] Failed to get scan_id")
                return None
                
            print(f"[{idx:>2}] Enqueued as scan_id={scan_id}. Polling...")
            
            # Poll for completion
            while True:
                poll_resp = await client.get(f"http://localhost:8000/api/scans/{scan_id}", headers=headers)
                if poll_resp.status_code == 200:
                    poll_res = poll_resp.json()
                    # Check if prediction is done
                    if poll_res.get('prediction_class') is not None:
                        elapsed = (time.perf_counter() - start) * 1000
                        print(f"[{idx:>2}] Success: {poll_res['prediction_class']} ({poll_res.get('confidence', 0)*100:.1f}%) - {elapsed:.0f}ms")
                        return elapsed
                await asyncio.sleep(1)
            
        else:
            print(f"[{idx:>2}] Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"[{idx:>2}] Exception: {e}")
        return None

async def run_load_test(concurrency=5, total=10):
    print(f"Starting load test: {total} requests with concurrency {concurrency}...")
    start_wall = time.perf_counter()
    
    async with httpx.AsyncClient() as client:
        tasks = [send_prediction(client, i) for i in range(total)]
        results = await asyncio.gather(*tasks)
    
    end_wall = time.perf_counter()
    latencies = [r for r in results if r is not None]
    
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        print("\n" + "="*40)
        print(f"Results:")
        print(f"  Total Requests: {total}")
        print(f"  Success:        {len(latencies)}")
        print(f"  Wall Time:      {end_wall - start_wall:.2f}s")
        print(f"  Avg Latency:    {avg_lat:.0f}ms")
        print(f"  P95 Latency:    {p95:.0f}ms")
        print("="*40)

if __name__ == "__main__":
    if not os.path.exists(TEST_IMAGE):
        print(f"Error: {TEST_IMAGE} not found.")
    else:
        asyncio.run(run_load_test(concurrency=3, total=3))
