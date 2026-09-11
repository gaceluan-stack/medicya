import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\app\templates\index.html"
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        for idx, line in enumerate(file):
            if "stylesheet" in line or ".css" in line:
                print(f"Line {idx+1}: {line.strip()}")
