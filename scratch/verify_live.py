import urllib.request
import json
import time

url = "https://medic-ya.onrender.com/api/proveedores/92c2f9b3-e534-4add-86ad-bebd9023d3f4/agenda-disponibilidad?fecha=2026-08-26"
headers = {'User-Agent': 'Mozilla/5.0'}

print("Polling today's availability to wait for the Render deployment to complete...")

for attempt in range(12):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        slots = data.get('slots', [])
        # Find if 08:30 is libre
        s_0830 = next((s for s in slots if s['hora_inicio'] == '08:30'), None)
        if s_0830:
            if not s_0830['libre']:
                print(f"\n[SUCCESS] Render deployment is LIVE! 08:30 is correctly marked as occupied/past.")
                print("All slots:")
                for idx, s in enumerate(slots):
                    print(f"  {idx+1}. {s['hora_inicio']} - {s['hora_fin']}: {'FREE' if s['libre'] else 'OCCUPIED/PAST'}")
                break
            else:
                print(f"Attempt {attempt+1}: 08:30 is still FREE. Old deployment is still running. Waiting 15s...")
        else:
            print(f"Attempt {attempt+1}: 08:30 slot not found in response. Waiting 15s...")
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {e}. Waiting 15s...")
    time.sleep(15)
