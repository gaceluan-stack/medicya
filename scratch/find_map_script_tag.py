import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\app\templates\index.html"
print("Reading file:", f)
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        lines = file.readlines()
    for idx, line in enumerate(lines):
        if "map.js" in line or "styles.css" in line:
            print(f"Line {idx+1}: {line.strip()}")
else:
    print("Does not exist!")
