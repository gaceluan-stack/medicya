import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\app\db\models.py"
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        content = file.read()
    
    lines = content.splitlines()
    found = False
    for idx, line in enumerate(lines):
        if "class Factura" in line:
            found = True
            print(f"Line {idx+1}:")
            for i in range(idx, min(len(lines), idx + 25)):
                print(f"{i+1}: {lines[i]}")
            break
    if not found:
        print("class Factura not found!")
else:
    print("Does not exist!")
