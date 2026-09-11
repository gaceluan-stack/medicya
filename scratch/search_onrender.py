import os

project_dir = r"C:\Users\User\Documents\antigravity\proyecto transjulcamp"
print("Searching for 'onrender.com' in:", project_dir)

for root, dirs, files in os.walk(project_dir):
    if ".git" in root or "node_modules" in root or "__pycache__" in root:
        continue
    for f in files:
        file_path = os.path.join(root, f)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                for idx, line in enumerate(file):
                    if "onrender.com" in line.lower():
                        print(f"{file_path} (Line {idx+1}): {line.strip()}")
        except Exception:
            pass
