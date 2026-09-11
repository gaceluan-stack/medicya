import os

project_dir = r"C:\Users\User\Documents\antigravity\proyecto transjulcamp"
keywords = ["render", "ping", "awake", "keep", "alive", "cron", "request"]

print("Searching files in:", project_dir)
for root, dirs, files in os.walk(project_dir):
    if ".git" in root or "node_modules" in root or "__pycache__" in root:
        continue
    for f in files:
        if f.endswith(".py") or f.endswith(".js") or f.endswith(".bat") or f.endswith(".toml") or f.endswith(".yaml"):
            file_path = os.path.join(root, f)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as file_content:
                    content = file_content.read()
                found = [k for k in keywords if k in content.lower()]
                if found:
                    print(f"File: {file_path} contains keywords: {found}")
            except Exception as e:
                pass
