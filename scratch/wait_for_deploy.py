import urllib.request
import time

url = "https://medic-ya.onrender.com/static/js/map.js"
headers = {'User-Agent': 'Mozilla/5.0'}

print("Waiting for deployment to serve the new map.js version with unpaid intercept...")
time.sleep(15)

for attempt in range(15):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8')
        if "Intercepta el estado impago del doctor para bloquear la redirección" in content:
            print(f"\n[SUCCESS] The new deployment is LIVE on Render!")
            break
        else:
            print(f"Attempt {attempt+1}: New version is not live yet. Waiting 15s...")
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {e}. Waiting 15s...")
    time.sleep(15)
