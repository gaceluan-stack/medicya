import urllib.request
import json
import time

url = "https://medic-ya.onrender.com/api/proveedores/debug/doctors"
headers = {'User-Agent': 'Mozilla/5.0'}

print("Waiting 15 seconds for Render deployment...")
time.sleep(15)

for attempt in range(8):
    try:
        print(f"Attempt {attempt+1}: Fetching doctors from {url}...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        print(f"\nSuccessfully retrieved {len(data)} doctors:")
        for idx, d in enumerate(data):
            print(f"{idx+1}. ID: {d['id']}, Name: {d['nombre_comercial']}, Premium: {d['es_premium']}, Cell: {d['celular_whatsapp']}")
        break
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(10)
