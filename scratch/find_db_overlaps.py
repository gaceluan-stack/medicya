import urllib.request
import json
import time

# Generate 30-minute slots from 09:00 to 17:00
slots = []
h, m = 9, 0
while h < 17:
    slots.append(f"{h:02d}:{m:02d}")
    m += 30
    if m == 60:
        m = 0
        h += 1
slots.append("17:00")

# For each slot, calculate start and end, and query the debug endpoint
print("Checking overlaps for each time slot:")
prov_id = "92c2f9b3-e534-4add-86ad-bebd9023d3f4"
fecha = "2026-08-26"

overlap_slots = []
free_slots = []

for i in range(len(slots) - 1):
    start = slots[i]
    end = slots[i+1]
    url = f"https://medic-ya.onrender.com/api/proveedores/debug/citas?fecha={fecha}&hora_inicio={start}&hora_fin={end}&proveedor_id={prov_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        if len(data) > 0:
            print(f"  - Slot {start} to {end}: OVERLAP found! (booked by {data[0]['paciente_nombre']})")
            overlap_slots.append(start)
        else:
            print(f"  - Slot {start} to {end}: FREE")
            free_slots.append(start)
    except Exception as e:
        print(f"  - Slot {start} to {end} failed: {e}")
        time.sleep(1)

print("\nSummary:")
print("Overlapped/Booked starting hours:", overlap_slots)
print("Free starting hours:", free_slots)
