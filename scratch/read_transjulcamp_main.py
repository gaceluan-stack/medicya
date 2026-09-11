import os

f = r"C:\Users\User\Documents\antigravity\proyecto transjulcamp\backend\main.py"
print("Reading file:", f)
if os.path.exists(f):
    with open(f, "r", encoding="utf-8", errors="ignore") as file:
        content = file.read()
    print(content)
else:
    print("Does not exist!")
