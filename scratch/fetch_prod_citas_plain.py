import urllib.request
import json

url = "https://medic-ya.onrender.com/api/proveedores/debug/citas"
headers = {'User-Agent': 'Mozilla/5.0'}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode('utf-8'))
    print(f"Retrieved {len(data)} rows.")
    for idx, c in enumerate(data[:5]):
        print(f"{idx+1}: {c}")
except Exception as e:
    print("Error:", e)
