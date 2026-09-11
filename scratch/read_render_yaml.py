import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\render.yaml"
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        print(file.read())
else:
    print("Does not exist!")
