import os

files_to_check = [
    r"C:\Users\User\Documents\antigravity\proyecto transjulcamp\backend\main.py",
    r"C:\Users\User\Documents\antigravity\proyecto transjulcamp\static\app.js"
]

for f in files_to_check:
    print(f"\n--- Reading: {f} ---")
    if not os.path.exists(f):
        print("Does not exist!")
        continue
    with open(f, "r", encoding="utf-8", errors="ignore") as file:
        lines = file.readlines()
    for idx, line in enumerate(lines):
        if any(k in line.lower() for k in ["ping", "keepalive", "awake", "render.com"]):
            print(f"Line {idx+1}: {line.strip()}")
