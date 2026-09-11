import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\app\templates\static\js\map.js"
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        for idx, line in enumerate(file):
            if "auto_response" in line.lower() or "autoresponse" in line.lower():
                print(f"Line {idx+1}: {line.strip()}")
