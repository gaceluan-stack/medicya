import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\app\templates\static\js\map.js"
print("Reading file:", f)
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        lines = file.readlines()
    for idx, line in enumerate(lines):
        if "tilelayer" in line.lower() or "basemaps.cartocdn.com" in line.lower() or "openstreetmap" in line.lower():
            print(f"Line {idx+1}: {line.strip()}")
else:
    print("Does not exist!")
