import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\app\db\models.py"
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        content = file.read()
    
    # print class CitaProveedor and the lines below it
    lines = content.splitlines()
    found = False
    for idx, line in enumerate(lines):
        if "class CitaProveedor" in line:
            found = True
            print(f"Line {idx+1}:")
            for i in range(idx, min(len(lines), idx + 25)):
                print(f"{i+1}: {lines[i]}")
            break
    if not found:
        print("class CitaProveedor not found!")
else:
    print("Does not exist!")
