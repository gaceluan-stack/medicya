import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\app\templates\static\js\map.js"
print("Reading file:", f)
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        content = file.read()
    
    # Let's find any occurrences of wa.me or whatsapp
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if "wa.me" in line.lower() or "whatsapp" in line.lower() or "celular_whatsapp" in line.lower():
            print(f"Line {idx+1}: {line.strip()}")
else:
    print("Does not exist!")
