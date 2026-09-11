import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\app\templates\static\js\map.js"
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        for idx, line in enumerate(file):
            if "selectedbookingslots = [" in line.lower() or "selectedbookingslots.length = 0" in line.lower() or "recalculatequote" in line.lower():
                print(f"Line {idx+1}: {line.strip()}")
