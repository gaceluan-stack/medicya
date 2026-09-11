import os

f = r"C:\Users\User\Documents\antigravity\proyecto transjulcamp\static\app.js"
print("Reading file:", f)
if os.path.exists(f):
    with open(f, "r", encoding="utf-8", errors="ignore") as file:
        lines = file.readlines()
    for idx, line in enumerate(lines):
        # search for render, ping, keep, alive (ignore casing, exclude typical variables)
        line_lower = line.lower()
        if "ping" in line_lower or "alive" in line_lower or "awake" in line_lower:
            # exclude typing or shopping or similar if easy, but let's print all first
            print(f"Line {idx+1}: {line.strip()}")
else:
    print("Does not exist!")
