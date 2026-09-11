import urllib.request
import json
import time

url = "https://medic-ya.onrender.com/api/proveedores/92c2f9b3-e534-4add-86ad-bebd9023d3f4/agenda-disponibilidad?fecha=2026-08-26"
headers = {'User-Agent': 'Mozilla/5.0'}

print("Waiting 15 seconds for Render deployment...")
time.sleep(15)

for attempt in range(8):
    try:
        print(f"Attempt {attempt+1}: Fetching today's availability from {url}...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        print("\nSlots returned for today:")
        for idx, s in enumerate(data.get('slots', [])):
            print(f"{idx+1}. {s['hora_inicio']} - {s['hora_fin']}: {'FREE (libre)' if s['libre'] else 'OCCUPIED / PAST (ocupado/pasado)'}")
        break
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(10)
