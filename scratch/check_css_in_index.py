import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\app\templates\index.html"
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        content = file.read()
    print("Contains '/static/css/styles.css':", "/static/css/styles.css" in content)
    print("Contains 'styles.css':", "styles.css" in content)
    print("Contains '<style>':", "<style>" in content)
    
    # print lines with <style>
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if "<style>" in line or "</style>" in line:
            print(f"Line {idx+1}: {line.strip()}")
