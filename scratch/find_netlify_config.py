import os

search_roots = [
    os.path.expandvars(r"%APPDATA%"),
    os.path.expandvars(r"%LOCALAPPDATA%"),
    os.path.expandvars(r"%USERPROFILE%")
]

for root_dir in search_roots:
    print(f"\nSearching deeply in: {root_dir}")
    for root, dirs, files in os.walk(root_dir):
        if "node_modules" in root or ".git" in root or "Cache" in root or "Local State" in root:
            continue
        # Only print paths containing netlify
        if "netlify" in root.lower():
            for f in files:
                if f == "config.json" or f == "state.json":
                    print("Found:", os.path.join(root, f))
