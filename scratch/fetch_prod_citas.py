import urllib.request
import json
import time

url = "https://medic-ya.onrender.com/api/proveedores/debug/citas"
headers = {'User-Agent': 'Mozilla/5.0'}

print("Waiting a few seconds for Render build to complete and wake up...")
time.sleep(10)

for attempt in range(10):
    try:
        print(f"Attempt {attempt+1}: Fetching {url}...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        print(f"\nSuccessfully retrieved {len(data)} appointments:")
        for idx, c in enumerate(data):
            print(f"{idx+1}. ID: {c['id']}, ProvID: {c['proveedor_id']}, Patient: {c['paciente_nombre']}, Date: {c['fecha']}, Time: {c['hora_inicio']}-{c['hora_fin']}, Status: {c['estado']}")
        break
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(10)
