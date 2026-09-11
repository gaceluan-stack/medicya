import urllib.request
import json
import time

url = "https://medic-ya.onrender.com/api/proveedores/debug/citas?fecha=2026-08-26&hora_inicio=08:30&hora_fin=09:00&proveedor_id=92c2f9b3-e534-4add-86ad-bebd9023d3f4"
headers = {'User-Agent': 'Mozilla/5.0'}

print("Waiting 15 seconds for Render deployment...")
time.sleep(15)

for attempt in range(8):
    try:
        print(f"Attempt {attempt+1}: Fetching overlap details from {url}...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        print(f"\nResponse data ({len(data)} overlapping rows):")
        for idx, row in enumerate(data):
            print(f"{idx+1}. ID: {row['id']}")
            print(f"   Provider: {row['proveedor_id']}")
            print(f"   Patient: {row['paciente_nombre']}")
            print(f"   Date: {row['fecha']}")
            print(f"   Time: {row['hora_inicio']} to {row['hora_fin']}")
            print(f"   Status: {row['estado']}")
            print(f"   Services: {row['servicios']}")
        break
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(10)
